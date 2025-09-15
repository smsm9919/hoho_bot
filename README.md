
# حزمة تشغيل احترافية لبوت BingX على Render (مع منع الصفقات العكسية)

**لا نلمس أي دالة أساسية في البوت.** نستخدم طبقة حارس تلتف وقت التشغيل.

## الملفات
- `runner.py` → يشغّل بوتك، يربط الحارس، ويعرّض `app` لـ gunicorn.
- `strategy_guard.py` → Anti-flip, تبريد, حد صفقات/ساعة, Idempotency, فلاتر اتجاه (EMA200/ADX/RSI/Spike), سقف 60% من رأس المال.
- `bingx_balance.py` → قراءة رصيد USDT من BingX (Futures ثم Spot كنسخة احتياطية).
- `render.yaml` → خدمة Render تستخدم gunicorn (إنتاجي).
- `requirements.txt` → الاعتمادات.

## الاستخدام
1) ضع **ملف البوت الأصلي** جنب هذه الملفات في الجذر.
2) إن كان اسم ملفك مش `bot.py`، أضف Env Var في Render:
   - `BOT_MODULE` = اسم الملف بدون `.py` (مثل: `doge_bot`).
3) Env Vars الأساسية:
   - `BINGX_API_KEY`, `BINGX_API_SECRET`
4) Env Vars اختيارية (توليف الحوكمة/الفلترة):
   - `MAX_TRADES_PER_HOUR=3`
   - `COOLDOWN_AFTER_CLOSE=300`
   - `MIN_BARS_BETWEEN_FLIPS=5`
   - `USE_DIRECTION_FILTERS=true`
   - `MIN_ADX=25`
   - `RSI_BUY_MIN=55`
   - `RSI_SELL_MAX=45`
   - `SPIKE_ATR_MULT=1.8`
   - `MIN_TP_PERCENT=0.75`
   - `ENFORCE_TRADE_PORTION=true`
   - `TARGET_TRADE_PORTION=0.60`

## النشر
- على Render، اربط المستودع واضغط Deploy. سيقرأ `render.yaml` ويشغّل:
  ```bash
  gunicorn -w 1 -b 0.0.0.0:$PORT runner:app
  ```
- اللوج عند البدء يجب أن يظهر:
  ```
  ✅ strategy_guard attached (anti-reverse, cooldown, rate-limit, filters, 60% capital).
  ```

## ملاحظات
- لضمان تنفيذ حقيقي للصفقات: المفاتيح لازم تكون **Futures/Swap** لو بتتداول عقود، وفي رصيد USDT في Futures Wallet.
- التحذير الأحمر بتاع Flask development يختفي لأننا بنستخدم gunicorn.
- الحارس يمنع الصفقات العكسية/العشوائية ويحافظ على الربح التراكمي عبر ضبط رأس المال والفلترة.

موفّق ✌️
