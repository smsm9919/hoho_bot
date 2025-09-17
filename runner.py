
# runner.py — drop-in entrypoint for Render (no edits to core bot)
import os, importlib, importlib.util, types
from threading import Thread

def _try_import(name):
    try:
        return importlib.import_module(name)
    except Exception as e:
        print(f"[runner] import failed for {name}: {e}")
        return None

def _spec_import(path):
    try:
        spec = importlib.util.spec_from_file_location(os.path.splitext(os.path.basename(path))[0], path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        return mod
    except Exception as e:
        print(f"[runner] spec import failed for {path}: {e}")
        return None

def _looks_like_bot(m: types.ModuleType):
    return (
        hasattr(m, "app") and
        hasattr(m, "main_bot_loop") and callable(getattr(m, "main_bot_loop")) and
        hasattr(m, "place_order") and callable(getattr(m, "place_order")) and
        hasattr(m, "close_position") and callable(getattr(m, "close_position"))
    )

def _load_userbot():
    module = os.getenv("BOT_MODULE", "bot").replace(".py", "")
    mod = _try_import(module)
    if mod and _looks_like_bot(mod):
        print(f"[runner] loaded bot module: {module}")
        return mod
    for name in os.listdir("."):
        if name.endswith(".py") and name not in {"runner.py","strategy_guard.py","README_DROPIN.md"}:
            mod = _spec_import(os.path.abspath(name))
            if mod and _looks_like_bot(mod):
                print(f"[runner] autodetected bot module: {name}")
                return mod
    raise ModuleNotFoundError("Set BOT_MODULE env var to your bot file name without .py")

userbot = _load_userbot()

# Enforce leverage 10x + 60% capital per trade (no edits to core functions)
try:
    if int(getattr(userbot, "LEVERAGE", 0) or 0) != 10:
        setattr(userbot, "LEVERAGE", 10)
        print("[runner] LEVERAGE enforced -> 10x")
    if float(getattr(userbot, "TRADE_PORTION", 0) or 0) != 0.60:
        setattr(userbot, "TRADE_PORTION", 0.60)
        print("[runner] TRADE_PORTION enforced -> 60%")
except Exception as e:
    print(f"[runner] enforce note: {e}")

# Attach balanced guard
try:
    import strategy_guard
    if hasattr(strategy_guard, "attach_guard"):
        strategy_guard.attach_guard(userbot)
        print("[runner] strategy_guard attached")
except Exception as e:
    print(f"[runner] guard optional: {e}")

# Keep-alive ping every 60s
def _start_keep_alive():
    import requests, time
    url = os.getenv("PUBLIC_URL") or f"http://127.0.0.1:{os.getenv('PORT','10000')}"
    interval = int(os.getenv("PING_INTERVAL_SECONDS", "60"))
    def loop():
        while True:
            try:
                requests.head(url, timeout=8)
                print("🟢 Keep-alive ping", url)
            except Exception:
                print("🔴 Keep-alive failed", url)
            time.sleep(interval)
    Thread(target=loop, daemon=True).start()
_start_keep_alive()

# Start main loop & expose Flask app
Thread(target=userbot.main_bot_loop, daemon=True).start()
app = userbot.app
print("[runner] app exposed for gunicorn")
