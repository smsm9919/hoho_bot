import time
from dataclasses import dataclass
from typing import Dict, Any, Tuple

@dataclass
class GuardParams:
    spike_atr_mult_1bar: float = 2.2
    spike_pct_3bars: float = 3.5
    adx_strong: float = 25.0
    early_adverse_atr: float = 1.5
    early_window_min: int = 10
    trail_start_atr: float = 0.8
    trail_step_atr: float = 0.4
    gap_slippage_pct: float = 0.9
    session_max_loss_usdt: float = 5.0
    session_cooldown_min: int = 30

def pre_trade_block(state: Dict[str, Any], p: GuardParams) -> Tuple[bool, list]:
    reasons = []
    ok = True
    curr = float(state['current_price'])
    prev = float(state.get('previous_price', curr))
    atr  = float(state['atr'])
    adx  = float(state['adx'])
    st   = 1 if int(state.get('supertrend', 1)) > 0 else -1
    ema200 = float(state['ema200'])
    rsi = float(state['rsi'])
    sma3, sma5, sma7 = float(state['sma3']), float(state['sma5']), float(state['sma7'])
    last_dir = state.get('last_direction')
    mins_since = int(state.get('minutes_since_last_trade', 9999))

    if atr > 0 and abs(curr - prev) > p.spike_atr_mult_1bar * atr:
        ok = False; reasons.append(f"1bar spike>{p.spike_atr_mult_1bar}*ATR")

    pct3 = float(state.get('pct_change_3bars', 0.0))
    if abs(pct3) > p.spike_pct_3bars:
        ok = False; reasons.append(f"3bars move>{p.spike_pct_3bars}%")

    if adx >= p.adx_strong:
        reasons.append("Trend strong; avoid counter-trend entries")

    if last_dir and mins_since < 15:
        ok = False; reasons.append("Same direction within 15m")

    return ok, reasons

def post_fill_protection(side: str, entry: float, price: float, atr: float, p: GuardParams):
    if atr <= 0 or entry <= 0:
        return None, None, None
    if side == 'BUY':
        tp = round(entry + 1.2 * atr, 5)
        sl = round(entry - 0.8 * atr, 5)
    else:
        tp = round(entry - 1.2 * atr, 5)
        sl = round(entry + 0.8 * atr, 5)
    dyn = {"enabled": True,"start_profit_atr": p.trail_start_atr,"step_atr": p.trail_step_atr,"last_trail_price": None}
    return tp, sl, dyn

def trailing_update(side: str, entry: float, price: float, atr: float, dyn: dict):
    if not dyn or not dyn.get("enabled") or atr <= 0:
        return None
    moved_in_favor = (price - entry) if side == 'BUY' else (entry - price)
    if moved_in_favor < dyn["start_profit_atr"] * atr:
        return None
    step = dyn["step_atr"] * atr
    if side == 'BUY':
        sl_new = round(price - step, 5)
    else:
        sl_new = round(price + step, 5)
    dyn["last_trail_price"] = price
    return sl_new

def emergency_exit(side: str, entry: float, price: float, atr: float, fill_ts: float, p: GuardParams) -> bool:
    if atr <= 0 or not fill_ts:
        return False
    minutes = (time.time() - float(fill_ts)) / 60.0
    if minutes > p.early_window_min:
        return False
    adverse = (entry - price) if side == 'BUY' else (price - entry)
    return adverse > p.early_adverse_atr * atr

class SessionRisk:
    def __init__(self, p: GuardParams):
        self.p = p
        self.loss_acc = 0.0
        self.paused_until = 0.0
    def on_trade_close(self, pnl_usdt: float):
        self.loss_acc += min(0.0, pnl_usdt)
        if abs(self.loss_acc) >= self.p.session_max_loss_usdt:
            self.paused_until = time.time() + self.p.session_cooldown_min * 60
    def can_trade(self) -> bool:
        return time.time() >= self.paused_until
    def status(self):
        return {"loss_acc": round(self.loss_acc, 4),"paused": time.time() < self.paused_until,"resume_in_min": max(0, int((self.paused_until - time.time())/60))}
