
# runner.py
# يشغّل بوتك كما هو، يربط strategy_guard بدون تعديل الدوال الأساسية،
# ويعرّض Flask app كرمز WSGI باسم "app" لاستخدامه مع gunicorn على Render.

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
    return hasattr(m, "app") and hasattr(m, "main_bot_loop") and callable(getattr(m, "main_bot_loop")) \
        and hasattr(m, "place_order") and callable(getattr(m, "place_order")) \
        and hasattr(m, "close_position") and callable(getattr(m, "close_position"))

def _load_userbot():
    module = os.getenv("BOT_MODULE", "bot").replace(".py", "")
    mod = _try_import(module)
    if mod and _looks_like_bot(mod):
        print(f"[runner] loaded bot module: {module}")
        return mod
    # autodetect any .py file
    for name in os.listdir("."):
        if name.endswith(".py") and name not in {"runner.py", "strategy_guard.py", "bingx_balance.py", "render.yaml", "requirements.txt", "README.md"}:
            mod = _spec_import(os.path.abspath(name))
            if mod and _looks_like_bot(mod):
                print(f"[runner] autodetected bot module: {name}")
                return mod
    raise ModuleNotFoundError("Could not find bot module. Set BOT_MODULE env var to your bot file name without .py (e.g., doge_bot).")

# ---- load user bot ----
userbot = _load_userbot()

# تعطيل أي keep_alive خاص بمنصات أخرى
try:
    userbot.keep_alive = lambda: None
except Exception:
    pass

# ربط الحارس
from strategy_guard import attach_guard
attach_guard(userbot)

# ابدأ حلقة التداول في خيط مستقل
Thread(target=userbot.main_bot_loop, daemon=True).start()

# عرّض Flask app لاستخدامه مع gunicorn: runner:app
app = userbot.app
