# بازآزمایی مستقل واقعی Stata | فاز اول مخصوص استاد | ۱۷ اکتبر ۲۰۲۶

**دامنه:** فقط داده تاریخی استاد، ۴۷ کشور، سال‌های ۲۰۰۵ تا ۲۰۲۲. هیچ داده جدیدی وارد نشده است.
**ابزار:** Stata/MP 17 داخل Winlator، کنترل از مسیر ADB، محیط جدا برای جلوگیری از تغییر لاگ‌های قدیمی.
**اعتبار فایل خام:** SHA256 برابر مقدار تاریخی و تأییدشده است.
**وضعیت اجرا:** چهار System GMM و چهار Difference GMM با کد خروجی صفر اجرا شدند؛ هر هشت سطر عددی با آرشیو قبلی در آستانه خطای 1e-7 منطبق هستند.

| مدل دو مرحله‌ای | رشد اقتصادی | لگاریتم سطح بهره‌وری |
|---|---:|---:|
| System GMM - Hansen | 0.7715834 | 0.0354487 |
| System GMM - AR(1) | 0.0987914 | 0.1416231 |
| System GMM - AR(2) | 0.4128903 | 0.4516201 |
| System GMM - Difference-in-Hansen سطح | 0.7052068 | 0.0007936 |
| Difference GMM - Hansen | 0.4655611 | 0.3243951 |
| Difference GMM - AR(1) | 0.0898767 | 0.1474692 |
| Difference GMM - AR(2) | 0.4762446 | 0.4568260 |

## داوری علمی
- **اجرای مجدد موفق** به معنی اعتبار شناسایی علّی نیست.
- در بهره‌وری System GMM، رد Hansen و Difference-in-Hansen ابزار سطح همچنان وجود دارد؛ مشکل برطرف نشده است.
- رشد System GMM فقط با محدودیت‌های تشخیص ابزارها و بدون ادعای علّی قابل گزارش است.
- Difference GMM یک تحلیل حساسیت متفاوت است؛ جانشین خودکار System GMM نیست.
- عدم معناداری شاخص‌های دیجیتال در سطح ۵ درصد نباید با تغییر انتخابی مدل پنهان شود.

## شواهد خروجی
- outputs/professor/PROFESSOR_SYSTEM_GMM_FOUR_RUNS.log
- outputs/professor/DIFFERENCE_GMM_OVERIDENTIFIED_L23_BOTH_MODELS.log
- outputs/professor/professor_system_gmm_stats.csv
- outputs/professor/diff_l23_two_outcomes_stats.csv
- RETEST_CHECK_RESULT.json

این گزارش صرفاً بازآزمایی محاسباتی است؛ ادعای حل بنیادی محدودیت‌های شناسایی ندارد.
