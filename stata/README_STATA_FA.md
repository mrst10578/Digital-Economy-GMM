# راهنمای کوتاه Stata

**راهنمای جامع و مخصوص فرد کم‌تجربه در ریشه بسته است:** `STATA_START_HERE_FA.md`.

Stata نسخه ۱۶ یا جدیدتر با مجوز معتبر لازم است. در ریشه بسته استخراج‌شده دستورهای زیر را وارد کن:

```stata
cd "C:/PATH/TO/Digital_Economy_Stata_Ready"
capture which xtabond2
if _rc ssc install xtabond2, replace
do "stata/RUN_ALL.do"
```

در صورت خطای واقعی کتابخانه Mata، `ssc install moremata, replace` و سپس `mata: mata mlib index` را با رعایت متن خطا اجرا کن.

برنامه با فایل `data/processed/stata_ready.dta` کار می‌کند. `ln_Productivity` موجود را دوباره تولید نمی‌کند و داده اصلی را تغییر نمی‌دهد. خروجی‌ها در `outputs/stata` شامل `RUN_ALL_REAL_STATA.log`، `model_status.csv`، `model_status.dta` و فایل‌های `.ster` فقط برای تخمین‌های موفق است.

**این بسته از نظر ساختاری در CI بررسی می‌شود، اما در Stata هنوز اجرا نشده است.** موفقیت در تخمین هم به معنی پذیرش علمی مدل نیست؛ تعداد ابزار، Hansen/Sargan، AR(1)/AR(2)، Difference-in-Hansen و هشدارهای عددی باید جدا کنترل شوند.
