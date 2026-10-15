# بازتولید واقعی Digital Economy GMM روی تبلت | ۱۵ اکتبر ۲۰۲۶

## دامنه و محیط
- مخزن: `mrst10578/Digital-Economy-GMM`، شاخه `research/digital-economy-estimation-audit-20261008`، مبنا `af34220`.
- سخت‌افزار آزمایش: Samsung Galaxy Tab S6 Lite SM-P615، اندروید ۱۳، Termux + ADB Wireless Debugging + Winlator.
- موتور واقعی تخمین: Stata/MP 17.0، نسخه ۶۴بیتی x86-64 تحت Winlator؛ بسته رایگان `xtabond2` نسخه **۳.۷.۲** از مخزن عمومی David Roodman به همراه کتابخانه `lxtabond2.mlib`.
- داده **بدون تغییر منبع**: `data/raw/Balanced_Panel_Data.xlsx` با SHA256 برابر `474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b`. فایل در Stata به `.dta` تبدیل شد. ۸۴۶ مشاهده = ۴۷ کشور × ۱۸ سال؛ کلید `ISO3 Year` یکتا و پنل متوازن.
- فرمان اصلی: `do "stata/RUN_ALL.do"`، بدون تغییر در هیچ‌یک از مشخصات `xtabond2` موجود در شاخه پژوهشی.

## آزمون‌ها و صحت بازتولید
- آزمون‌های IPS و Fisher برای هشت سری: **۱۶ از ۱۶ بدون خطای اجرایی** (`rc=0`).
- هر **شش تخمین** Difference/System GMM اجرا شد (`rc=0`) و شش فایل `.ster` ساخته شد.
- `model_status.csv` خروجی اجرا به‌صورت **سلول‌به‌سلول و عددبه‌عدد** با `evidence/stata-2026-10-09/outputs.zip`، فایل `outputs/stata/model_status.csv`، منطبق شد: **۶ سطر × تمام ستون‌ها، صفر اختلاف**.
- هش SHA256 فایل CSV جدید: `4500031a1847d8f8105f66c6b4c6342e73d984be726509e6ea6225422419f54c`.
- هش SHA256 لاگ جدید (منحصراً اجرای تبلت): `85a59e2ea9f1510ec5dd2dca96083dd4ca9d1a9be9242e9f011cf53bdd2c2abc`؛ طول لاگ **۸۷٬۲۴۰ بایت**.
- پایان اسکریپت با `RUN_ALL_SCRIPT_COMPLETED` و وجود `STATA_STATUS_EXPORT_OK` تأیید شد. هیچ `STATA_MODEL_FAILED` ثبت نشد.

## جدول خروجی دستگاه

| مدل | N | گروه | ابزار | Hansen p | Sargan p | AR(1) p | AR(2) p |
|---|---:|---:|---:|---:|---:|---:|---:|
| GROWTH_DIFF_L23 | 752 | 47 | 30 | .46556112 | .35006931 | .034784086 | .28036368 |
| GROWTH_SYS_L22 | 799 | 47 | 31 | .77158344 | 2.5354148e-09 | .098791353 | .41289032 |
| GROWTH_SYS_L23_AUDIT | 799 | 47 | 38 | .80986029 | 2.0038432e-07 | .11272343 | .46692631 |
| PROD_DIFF_L23 | 752 | 47 | 30 | .32439509 | .79724592 | .13338913 | .42250559 |
| PROD_SYS_L22 | 799 | 47 | 31 | .035448708 | .57964462 | .14162306 | .45162004 |
| PROD_SYS_L23_AUDIT | 799 | 47 | 38 | .12474504 | .9242118 | .14302003 | .47218636 |

تمام وضعیت‌ها `DIAGNOSTIC_HOLD` باقی ماندند. شش هشدار **singular covariance matrix of moments** در خروجی جدید نیز تکرار شد. آزمون‌های Difference-in-Hansen و ملاحظات درج‌شده در `docs/STATA_REAL_RESULTS_AUDIT_FA.md` همچنان معتبرند و **هیچ مدل جدیدی از نظر علمی تأیید نشده است**.

## نکات بازتولید در Winlator
1. فهرست اسکریپت‌های `stata/` و فایل خام Excel از همان Commit دریافت شد. نسخه اصلی فایل Excel با SHA256 بررسی شد.
2. Stata در Winlator با `import excel, firstrow` داده را خواند و با کنترل تعداد/کلید/پنل، `stata_ready.dta` ساخت.
3. در Wine، اجرای `ssc install xtabond2` پیام `Java installation not found` برگرداند. کد و کتابخانه **رسمی متن‌باز** `xtabond2` به مسیر محلی PLUS اضافه شد و `mata: mata mlib index` موفق شد؛ `which xtabond2` نسخه ۳.۷.۲ را تأیید کرد. منبع: https://github.com/droodman/xtabond2.
4. `stata/RUN_ALL.do` با همه شش سناریوی اصلی و بدون تغییر در lag، collapse، robust یا روش تخمین اجرا شد.
5. گزارش‌ها و فایل‌های `.ster` در دستگاه در `Downloads/Digital_Economy_Stata_Ready/outputs/stata/` قرار دارند. این مسیر مکان ذخیره اجرای تبلت است، نه یک GitHub Artifact.

## مرز علمی و امنیتی
**اجرای موفق، تأیید روش‌شناسی یا ادعای سرریز علّی نیست.** هشدار تکین‌بودن ماتریس، Hansen زیرمجموعه‌ها، وابستگی مقطعی و مشکلات مانایی همچنان مانع پذیرش علمی نهایی‌اند. اطلاعات فعال‌سازی، لایسنس و شماره سریال به این سند وارد نشده‌اند. PR #1 باید همچنان Draft و Merge نشده باقی بماند.
