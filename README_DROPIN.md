
# Drop-in Balanced Strategy (for existing bot)
Files:
- `runner.py` → entrypoint for Render (gunicorn) + keep-alive + enforce 10x / 60%.
- `strategy_guard.py` → balanced entries + full protections + rich logs.

How to use:
1) Add these files to your existing bot repo (next to your `bot.py` or `main.py`).
2) On Render:
   - Start Command:
     gunicorn -w 1 -b 0.0.0.0:$PORT runner:app
   - Environment:
     BOT_MODULE = your bot filename without .py  (e.g., bot)
     BINGX_API_KEY, BINGX_API_SECRET
     PUBLIC_URL (optional), PING_INTERVAL_SECONDS=60
3) Deploy. Check logs for:
   - strategy_guard attached
   - Keep-alive ping
   - indicators snapshot / NO-TRADE reasons / trade details
