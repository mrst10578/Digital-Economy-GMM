# تحویل Stata به لپ‌تاپ دارای مجوز

**وضعیت تاریخی بسته:** بسته اولیه پیش از دریافت خروجی Stata آماده شده بود. **اکنون شش مدل واقعاً در ۹ اکتبر ۲۰۲۶ اجرا شده‌اند و گزارش علمی جدید موجود است.** برای دریافت فایل‌های بدون نصب اضافه، از Artifact موفق Workflow «Digital economy licensed Stata handoff ZIP» استفاده کنید و فایل ZIP را از حالت فشرده خارج کنید.

در پوشه Digital_Economy_Stata_Ready ساختار data/processed/stata_ready.dta، data/raw/Balanced_Panel_Data.xlsx، stata/RUN_ALL.do و دیگر do-fileها و اسناد فارسی آماده است. فایل DTA در Python از Excel همان مخزن ساخته و round-trip کنترل شده است.

پس از فعال‌سازی Stata قانونی و ورود به ریشه بسته، این دستورات را اجرا کنید:

~~~stata
cd "C:\PATH\TO\Digital_Economy_Stata_Ready"
capture which xtabond2
if _rc ssc install xtabond2
do "stata/RUN_ALL.do"
~~~

فایل‌های مرحله‌ای:
۱. stata/01_environment_and_data.do: شناسه، سال، وجود فایل و بسته.
۲. stata/02_pre_estimation.do: توصیف، IPS، Fisher و VIF.
۳. stata/03_growth_models.do: رشد؛ Difference و System GMM.
۴. stata/04_productivity_models.do: لگاریتم بهره‌وری؛ Difference و System.
۵. stata/05_post_estimation_and_export.do: ذخیره مدل‌هایی که واقعاً تخمین شده‌اند.

اگر یک مدل خطا داد، فقط مدل موفق در لاگ قابل گزارش است. لاگ واقعی در outputs/stata/RUN_ALL_REAL_STATA.log ایجاد می‌شود. از لاگ نهایی تعداد ابزار، جدول ضرایب، Hansen/Sargan، AR(1)، AR(2) و Difference-in-Hansen را فقط زمانی گزارش کنید که xtabond2 واقعاً حساب کرده باشد. اکنون اجرای واقعی Difference-in-Hansen و شش مدل در فایل ایمیل وجود دارد؛ برخی زیرگروه‌های ابزار رد شده‌اند و لازم است [ممیزی واقعی](STATA_REAL_RESULTS_AUDIT_FA.md) مطالعه شود. بعد از اجرا فایل‌های R/gretl را از Artifact دانلود و اختلاف ابزار و نمونه را بررسی کنید.

مقایسه‌های R/gretl به‌معنای سازگاری دقیق بسته‌های مختلف نیستند؛ در صورت عدم تطابق توضیح علمی و تنظیمات لازم است.


## راهنمای آخرین نسخه و فایل خروجی ساختاریافته

نسخه نهاییِ آماده قبل از Stata در `STATA_START_HERE_FA.md` (ریشه مخزن و ریشه ZIP) توضیح داده شده است. ZIP جدید شامل همه `.do`ها، DTA واقعی، راهنمای فارسی و نتیجه ممیزی استاتیک است. `stata/RUN_ALL.do` حالا علاوه بر متن log، `outputs/stata/model_status.csv` و `model_status.dta` با وضعیت هر شش سناریو، کد خطا، شمار گروه و ابزار و آزمون‌هایی که Stata *واقعاً* برگرداند ایجاد می‌کند. خروجی `.ster` فقط برای مدل‌هایی وجود خواهد داشت که اجرای برآوردشان موفق شود؛ هیچ‌کدام از این فایل‌ها تضمین اعتبار علمی مدل نیست. اجرای اولیه Stata انجام شده است؛ اجرای مجدد فقط برای بازتولید یا آزمون اصلاح اصولی لازم است.
