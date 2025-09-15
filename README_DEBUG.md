# Balance Debug Pack (v2)
- `bingx_balance_debug.py`: يقرأ رصيد USDT ويطبع استجابات BingX عند تعيين `BALANCE_DEBUG=true`.
- طريقة الاستخدام:
  1) ضع المفاتيح في Env Vars: `BINGX_API_KEY`, `BINGX_API_SECRET`
  2) فعّل `BALANCE_DEBUG=true` مؤقتًا
  3) راقب اللوج على Render أو شغّل محليًا: `python bingx_balance_debug.py`
  4) بعد التشخيص عطّل `BALANCE_DEBUG`
