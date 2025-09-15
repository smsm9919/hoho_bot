
# strategy_guard.py
import os, time, hashlib
from collections import deque

def _fenv(k, d):
    try: return float(os.getenv(k, d))
    except: return float(d)

def _ienv(k, d):
    try: return int(os.getenv(k, d))
    except: return int(d)

def _benv(k, d):
    return os.getenv(k, str(d)).strip().lower() in ("1","true","yes","y","on")

def _sigkey(symbol, tf, side, price):
    raw = f"{symbol}|{tf}|{side}|{round(float(price or 0),6)}"
    return hashlib.sha1(raw.encode()).hexdigest()

def attach_guard(userbot):
    # Governance
    MAX_TRADES_PER_HOUR    = _ienv("MAX_TRADES_PER_HOUR", 3)
    COOLDOWN_AFTER_CLOSE   = _ienv("COOLDOWN_AFTER_CLOSE", 300)
    MIN_BARS_BETWEEN_FLIPS = _ienv("MIN_BARS_BETWEEN_FLIPS", 5)
    # Filters
    USE_FILTERS            = _benv("USE_DIRECTION_FILTERS", True)
    MIN_ADX                = _fenv("MIN_ADX", 25.0)
    RSI_BUY_MIN            = _fenv("RSI_BUY_MIN", 55.0)
    RSI_SELL_MAX           = _fenv("RSI_SELL_MAX", 45.0)
    SPIKE_ATR_MULT         = _fenv("SPIKE_ATR_MULT", 1.8)
    MIN_TP_PERCENT         = _fenv("MIN_TP_PERCENT", 0.75)
    # Capital
    ENFORCE_TRADE_PORTION  = _benv("ENFORCE_TRADE_PORTION", True)
    TARGET_TRADE_PORTION   = _fenv("TARGET_TRADE_PORTION", 0.60)
    # Fallback ATR multipliers (if user's calc not available)
    ATR_SL_MULT            = _fenv("ATR_SL_MULT", 0.8)
    ATR_TP_MULT            = _fenv("ATR_TP_MULT", 1.2)

    recent_ts = deque()
    seen_keys = deque(maxlen=128)
    state = {"last_close": 0.0, "last_flip_bar": -10}

    # enforce trade portion (no signature changes)
    if ENFORCE_TRADE_PORTION:
        try:
            setattr(userbot, "TRADE_PORTION", TARGET_TRADE_PORTION)
            print(f"[guard] TRADE_PORTION enforced -> {TARGET_TRADE_PORTION:.2f}")
        except Exception:
            pass

    # helpers
    def _trim_hour():
        now = time.time()
        while recent_ts and now - recent_ts[0] > 3600:
            recent_ts.popleft()

    def _metrics():
        price  = float(getattr(userbot, "current_price", 0.0) or 0.0)
        atr    = float(getattr(userbot, "current_atr", 0.0) or 0.0)
        adx    = float(getattr(userbot, "adx_value", 0.0) or 0.0)
        rsi    = float(getattr(userbot, "rsi_value", 0.0) or 0.0)
        ema200 = float(getattr(userbot, "ema_200_value", 0.0) or 0.0)
        lastd  = getattr(userbot, "last_direction", None)
        sym    = getattr(userbot, "SYMBOL", "DOGE-USDT")
        tf     = getattr(userbot, "INTERVAL", "15m")
        return price, atr, adx, rsi, ema200, lastd, sym, tf

    def _spike(curr, prev, atr):
        try: return abs(curr - prev) > SPIKE_ATR_MULT * max(atr, 1e-9)
        except: return False

    def _tp_pct(price, side, atr):
        try:
            tp, _sl = userbot.calculate_tp_sl(price, atr if atr>0 else 1e-6, side)
        except Exception:
            tp = price + ATR_TP_MULT*atr if side=="BUY" else price - ATR_TP_MULT*atr
        try: return abs(tp - price) / max(price, 1e-9) * 100.0
        except: return 0.0

    # patch close_position
    _orig_close = userbot.close_position
    def _wrap_close(reason, exit_price):
        ok = _orig_close(reason, exit_price)
        if ok: state["last_close"] = time.time()
        return ok
    userbot.close_position = _wrap_close

    # patch place_order
    _orig_place = userbot.place_order
    def _wrap_place(side, qty):
        price, atr, adx, rsi, ema200, lastd, sym, tf = _metrics()

        # cooldown after close
        since_close = time.time() - state["last_close"]
        if since_close < COOLDOWN_AFTER_CLOSE:
            print(f"🕒 Cooldown {int(COOLDOWN_AFTER_CLOSE - since_close)}s — skip")
            return False

        # rate limit
        _trim_hour()
        if len(recent_ts) >= MAX_TRADES_PER_HOUR:
            print("⛔ Max trades/hour — skip")
            return False

        # idempotency
        skey = _sigkey(sym, tf, side, price)
        if skey in seen_keys:
            print("⛔ Duplicate signal — skip")
            return False

        # prevent fast flip by bars
        try:
            df = userbot.get_klines()
            bar_idx = len(df) - 1 if (df is not None and len(df)) else 0
        except Exception:
            bar_idx = 0
        if lastd and ((side=="BUY" and lastd=="SELL") or (side=="SELL" and lastd=="BUY")):
            if (bar_idx - state["last_flip_bar"]) < MIN_BARS_BETWEEN_FLIPS:
                print("⛔ Prevent fast flip — wait bars")
                return False

        # directional filters
        if USE_FILTERS:
            try:
                df = userbot.get_klines()
                cc = float(df['close'].iloc[-1]); pc = float(df['close'].iloc[-2])
            except Exception:
                cc = price; pc = price
            if _spike(cc, pc, atr):
                print("⛔ Spike detected — skip")
                return False
            if adx < MIN_ADX:
                print(f"⛔ Weak trend ADX {adx:.1f} < {MIN_ADX}")
                return False
            if side == "BUY":
                if ema200 and not (price > ema200):
                    print("⛔ BUY blocked: price ≤ EMA200")
                    return False
                if rsi < RSI_BUY_MIN:
                    print(f"⛔ BUY blocked: RSI {rsi:.1f} < {RSI_BUY_MIN}")
                    return False
            else:
                if ema200 and not (price < ema200):
                    print("⛔ SELL blocked: price ≥ EMA200")
                    return False
                if rsi > RSI_SELL_MAX:
                    print(f"⛔ SELL blocked: RSI {rsi:.1f} > {RSI_SELL_MAX}")
                    return False
            if _tp_pct(price, side, atr) < MIN_TP_PERCENT:
                print("⛔ R:R too small — skip")
                return False

        # enforce 60% capital cap for qty sanity (with leverage)
        try:
            from bingx_balance import get_balance_usdt
            bal = float(get_balance_usdt())
            lev = float(getattr(userbot, "LEVERAGE", 1))
            portion = TARGET_TRADE_PORTION if ENFORCE_TRADE_PORTION else float(getattr(userbot,"TRADE_PORTION", TARGET_TRADE_PORTION))
            max_qty = round(((bal + float(getattr(userbot,"compound_profit",0.0))) * portion * lev) / max(price,1e-9), 2)
            if qty > max_qty * 1.05:
                print(f"⛔ Qty {qty} > max {max_qty} — skip")
                return False
        except Exception:
            pass

        ok = _orig_place(side, qty)
        if ok:
            seen_keys.append(skey)
            recent_ts.append(time.time())
            if lastd and ((side=="BUY" and lastd=="SELL") or (side=="SELL" and lastd=="BUY")):
                state["last_flip_bar"] = bar_idx
        return ok

    userbot.place_order = _wrap_place
    print("✅ strategy_guard attached (anti-reverse, cooldown, rate-limit, filters, 60% capital).")
