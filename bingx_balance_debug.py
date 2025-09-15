# bingx_balance_debug.py
import os, time, hmac, hashlib, requests, json

API_KEY    = os.getenv("BINGX_API_KEY", "")
API_SECRET = os.getenv("BINGX_API_SECRET", "")
BASE_URL   = os.getenv("BINGX_BASE_URL", "https://open-api.bingx.com")
VERBOSE    = os.getenv("BALANCE_DEBUG", "false").strip().lower() in ("1","true","yes","on")

def _sign(params: dict) -> str:
    query = "&".join(f"{k}={params[k]}" for k in sorted(params))
    return hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()

def _req(method: str, path: str, params: dict):
    url = f"{BASE_URL}{path}"
    headers = {"X-BX-APIKEY": API_KEY}
    params = dict(params or {})
    params["timestamp"] = str(int(time.time() * 1000))
    params["signature"] = _sign(params)
    if VERBOSE:
        print(f"[debug] -> {method} {url} params={params}")
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, params=params, timeout=12)
        else:
            r = requests.post(url, headers=headers, params=params, timeout=12)
    except Exception as e:
        print(f"[balance] HTTP error: {e}")
        return None, f"http_error:{e}"
    if VERBOSE:
        print(f"[debug] <- status={r.status_code} body={r.text[:800]}")
    if r.status_code != 200:
        return None, f"http_{r.status_code}:{r.text}"
    try:
        return r.json(), None
    except json.JSONDecodeError:
        return None, f"json_error:{r.text}"

def get_balance_usdt(debug=False) -> float:
    dbg = VERBOSE or debug
    if not API_KEY or not API_SECRET:
        print("[balance] Missing BINGX_API_KEY / BINGX_API_SECRET")
        return 0.0

    data, err = _req("GET", "/openApi/swap/v2/user/balance", {})
    if data and isinstance(data, dict):
        if dbg: print(f"[debug] swap.v2 raw: {json.dumps(data)[:1000]}")
        if data.get("code") == 0:
            bal = data.get("data", {}).get("balance")
            if isinstance(bal, list):
                for a in bal:
                    if a.get("asset") == "USDT":
                        v = float(a.get("availableBalance") or a.get("availableMargin") or 0.0)
                        print(f"[balance] swap.v2 USDT = {v}")
                        return v
            if isinstance(bal, dict) and bal.get("asset") == "USDT":
                v = float(bal.get("availableMargin") or bal.get("availableBalance") or 0.0)
                print(f"[balance] swap.v2 USDT = {v}")
                return v
            print(f"[balance] swap.v2 no USDT field -> {bal}")
        else:
            print(f"[balance] swap.v2 non-zero code: {data.get('code')} msg={data.get('msg')}")
    else:
        if err: print(f"[balance] swap.v2 error: {err}")

    data, err = _req("GET", "/openApi/spot/v1/account/balance", {})
    if data and isinstance(data, dict):
        if dbg: print(f"[debug] spot raw: {json.dumps(data)[:1000]}")
        if data.get("code") == 0:
            for a in data.get("data", []):
                if a.get("asset") == "USDT":
                    free = float(a.get("free", 0.0))
                    print(f"[balance] spot USDT = {free}")
                    return free
            print("[balance] spot no USDT in response")
        else:
            print(f"[balance] spot non-zero code: {data.get('code')} msg={data.get('msg')}")
    else:
        if err: print(f"[balance] spot error: {err}")

    return 0.0

if __name__ == "__main__":
    v = get_balance_usdt(debug=True)
    print(f"[balance] USDT available = {v}")
