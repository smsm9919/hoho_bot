from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class Params:
    rsi_buy: float = 50.0
    rsi_sell: float = 50.0
    adx_min: float = 20.0
    price_range_min: float = 1.0
    spike_atr_mult: float = 1.8
    block_same_dir_minutes: int = 60
    min_tp_percent: float = 0.75

class Strategy:
    def __init__(self, p: Params = Params()):
        self.p = p

    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        reasons: List[str] = []
        ok = True
        side = None

        price = float(state["current_price"])
        ema200 = float(state["ema200"])
        rsi = float(state["rsi"])
        adx = float(state["adx"])
        st  = 1 if int(state.get("supertrend", 1)) > 0 else -1
        sma3 = float(state["sma3"]); sma5 = float(state["sma5"]); sma7 = float(state["sma7"])
        prange = float(state["price_range"])
        atr = float(state["atr"])
        last_dir = state.get("last_direction")
        mins_since = int(state.get("minutes_since_last_trade", 9999))
        spike = bool(state.get("spike", False))

        if spike:
            ok = False; reasons.append(f"Spike>ATR*{self.p.spike_atr_mult:.1f}")
        if prange < self.p.price_range_min:
            ok = False; reasons.append(f"Range<{self.p.price_range_min:.1f}%")

        buy_ok = (price > ema200 and rsi >= self.p.rsi_buy and adx >= self.p.adx_min and st > 0 and (sma3 > sma5 > sma7))
        sell_ok = (price < ema200 and rsi <= self.p.rsi_sell and adx >= self.p.adx_min and st < 0 and (sma3 < sma5 < sma7))

        if last_dir and mins_since < self.p.block_same_dir_minutes:
            if (last_dir == "BUY" and buy_ok) or (last_dir == "SELL" and sell_ok):
                ok = False; reasons.append(f"SameDir<{self.p.block_same_dir_minutes}m")

        if ok and buy_ok:
            side = "BUY"
        elif ok and sell_ok:
            side = "SELL"
        else:
            if not buy_ok and not sell_ok:
                reasons.append("Pattern not aligned")

        est_tp_percent = None
        if atr > 0 and price > 0:
            est_tp_percent = (1.2 * atr / price) * 100

        return {
            "enter": bool(side) and ok,
            "side": side,
            "reasons": reasons,
            "est_tp_percent": est_tp_percent,
            "requirements": {"min_tp_percent": self.p.min_tp_percent},
        }
