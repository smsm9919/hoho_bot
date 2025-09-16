# diag_bingx.py
import os, sys, time, hmac, hashlib, requests, json, urllib.parse

API_KEY    = (os.getenv("BINGX_API_KEY"   , "") or "").strip()
API_SECRET = (os.getenv("BINGX_API_SECRET", "") or "").strip()
ACCOUNT    = (os.getenv("BINGX_ACCOUNT_TYPE", "FUTURES") or "FUTURES").strip().upper()

BASE = "https://open-api.bingx.com"

DEFAULTS = {
    "FUTURES": "/openApi/swap/v2/user/balance",
    "SPOT"   : "/openApi/spot/v1/account/balance"
}

def mask(s):
    if not s: return ""
    return ("*" * max(0, len(s) - 4)) + s[-4:]

def sign(params: dict) -> str:
    qs = urllib.parse.urlencode(params)
    sig = hmac.new(API_SECRET.encode(), qs.encode(), hashlib.sha256).hexdigest()
    return qs + "&signature=" + sig

def http(method: str, path: str, params: dict) -> requests.Response:
    url = BASE + path
    headers = {"X-BX-APIKEY": API_KEY}
    payload = sign(params)
    if method.upper() == "POST":
        return requests.post(url, headers=headers, data=payload, timeout=15)
    else:
        return requests.get(url, headers=headers, data=payload, timeout=15)

def auth_and_balance():
    print(f"[BOOT] ACCOUNT={ACCOUNT}  API_KEY_SUFFIX={mask(API_KEY)}  KEY_LEN={len(API_KEY)}  SECRET_LEN={len(API_SECRET)}")
    if not API_KEY or not API_SECRET:
        return {"ok": False, "err": "Missing API keys."}

    path = DEFAULTS.get(ACCOUNT, DEFAULTS["FUTURES"])
    ts = int(time.time() * 1000)
    params = {"timestamp": ts, "recvWindow": 5000}

    try:
        r = http("GET", path, params)
        print(f"[AUTH-TEST] {r.status_code} {r.text[:300]}")
        if r.status_code == 200:
            return {"ok": True, "raw": r.json()}
        return {"ok": False, "err": f"HTTP {r.status_code}", "raw": r.text}
    except requests.RequestException as e:
        return {"ok": False, "err": f"Network error: {e}"}

if __name__ == "__main__":
    res = auth_and_balance()
    print("[RESULT]", res)
