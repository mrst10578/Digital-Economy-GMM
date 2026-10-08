# اجرای سریع و قابل کنترل Stata روی لپ‌تاپ دارای مجوز

۱. شاخه پژوهش را دانلود کن و در پوشه ریشه مخزن قرار بگیر.
۲. از بخش Artifacts اجرای موفق «Digital economy real data audit and OLS-FE benchmarks»، فایل stata_ready.dta را در مسیر data/processed/stata_ready.dta قرار بده.
۳. در Stata نسخه ۱۶ یا بالاتر اجرا کن:

    cd "C:\\PATH\\TO\\Digital-Economy-GMM"
    capture which xtabond2
    if _rc ssc install xtabond2
    do "stata/RUN_ALL.do"

۴. لاگ واقعی در outputs/stata/RUN_ALL_REAL_STATA.log ذخیره می‌شود. برآورد R یا gretl را خروجی Stata ننام.
۵. p-valueهای Hansen، Sargan، AR(1)، AR(2)، Difference-in-Hansen در صورت تولید معتبر، شمار ابزارها و تعداد کشورها را از لاگ استخراج و با اجرای R مقایسه کن.

**وضعیت:** این دستورات نوشته شده‌اند، اما اجرای واقعی در Stata هنوز انجام نشده است. اگر دستور خاصی در نسخه مجاز خطا داد، آن مدل را اجراشده تلقی نکن. بدون مشاهده آزمون‌ها از پذیرش مدل خودداری کن.
