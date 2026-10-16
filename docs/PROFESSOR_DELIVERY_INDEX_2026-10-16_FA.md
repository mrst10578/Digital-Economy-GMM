# صفحه نخست بسته علمی قابل ارائه به استاد

**پروژه:** ارزیابی رابطه شاخص‌های اقتصاد دیجیتال با رشد اقتصادی و بهره‌وری نیروی کار در پنل پویا  
**نمونه تاریخی:** ۴۷ کشور، ۲۰۰۵–۲۰۲۲، داده اولیه ۸۴۶ مشاهده  
**مدل‌های مرجع استاد:** System GMM دو‌مرحله‌ای `Growth` و `ln_Productivity` با ابزارهای وقفه ۲ و `collapse`  
**وضعیت تا ۱۶ اکتبر ۲۰۲۶:** **اجرا و کنترل عددی پایان یافته، اعتبار علی و شناسایی سرریز خارجی هنوز تأیید نشده است.**

## ترتیب پیشنهادی برای مطالعه و بررسی استاد

**۱. متن اصلی برای شروع:** [گزارش یکپارچه، دو جدول کامل نتایج، آزمون‌ها و رأی علمی](PROFESSOR_INTEGRATED_FINAL_SCIENTIFIC_VERDICT_2026-10-16_FA.md).

**۲. خروجی مستقل Stata:** [۱۴ ضریب دو مدل، خطاهای معیار، p و CI ۹۵٪](../evidence/scientific-gates-2026-10-16/professor_two_primary_system_gmm_full_coefficients.csv). همه از فایل‌های اصلی تخمین `.ster` بازخوانی شده‌اند، بدون تغییر مشخصات. برای رسیدگی به فرآیند محاسبات، [لاگ واقعی Stata](../evidence/scientific-gates-2026-10-16/professor_full_coefficient_export_real_stata.log) و [کد صدور جدول](../stata/tablet_diagnostics/19_professor_final_coefficient_export.do) موجود است.

**۳. دفترچه روش‌شناسی ابزارها:** [نقشه درون‌زایی تک‌تک متغیرها و آزمون وقفه دوم](PROFESSOR_INSTRUMENT_EXOGENEITY_AUDIT_2026-10-16_FA.md). این گزارش مشخص می‌کند چه فروضی نیاز به داوری استاد دارد و چرا عدم رد Hansen اثبات برون‌زایی نیست.

**۴. دفترچه آزمون‌های مانایی:** [شواهد CIPS، IPS و Fisher درباره سطح/تفاضل ln_Productivity](PROFESSOR_PRODUCTIVITY_STATIONARITY_REVIEW_2026-10-16_FA.md)، همراه با [۶۴ ردیف اصلی CIPS R](../evidence/scientific-gates-2026-10-16/cips_full_64_original_r_workflow14.csv) و [۱۶ تست واقعی Stata](../evidence/scientific-gates-2026-10-16/productivity_unitroot_grid_stata.csv).

**۵. فایل‌های پشتیبان روش اصلی استاد:** [کد اصلی رشد](../stata/03_growth_models.do)، [کد اصلی بهره‌وری](../stata/04_productivity_models.do)، [آمار دو تخمین مرجع و یک‌مرحله‌ای حساسیت](../evidence/tablet-stata-2026-10-16/professor_system_gmm_stats.csv) و [لاگ کامل Hansen/Sargan/AR/Difference-in-Hansen](../evidence/tablet-stata-2026-10-16/professor_system_gmm_native_stata.log).

**۶. حساسیت‌های مستقل:** [پنجره پیش از کرونا](PROFESSOR_SYSTEM_GMM_PREPANDEMIC_SENSITIVITY_FA.md)، [وقفه سوم ابزارها](PROFESSOR_GMM_LAG3_INSTRUMENT_SENSITIVITY_2026-10-16_FA.md)، [حذف معادله سطح و شرایط اولیه](PROFESSOR_GMM_LEVEL_MOMENTS_INITIAL_CONDITIONS_2026-10-16_FA.md) و [حذف تک‌کشوری در مدل Difference](GMM_JACKKNIFE_AND_RESIDUAL_CD_2026-10-16_FA.md).

**۷. کنترل خودکار علمی:** [ممیزی مستقل جدول‌ها](../src/python/audit_professor_final_primary_delivery.py) و [گردش‌کار GitHub](../.github/workflows/36-professor-final-scientific-verdict.yml) به همراه [ممیزی ابزار و مانایی](../src/python/audit_professor_exogeneity_stationarity.py). کنترل GitHub بر **شواهد بایگانی‌شده واقعی** است؛ نه اجرای تازه Stata در محیط GitHub.

## خلاصه عددی برای جلسه

| معیار مدل مرجع | رشد | ln_Productivity |
|---|---:|---:|
| ۷۹۹ مشاهده / ۴۷ کشور / ۳۱ ابزار | بله | بله |
| p آزمون مشترک سه شاخص دیجیتال | ۰٫۰۷۴۷۴ | ۰٫۴۱۵۷۴ |
| Hansen p | ۰٫۷۷۱۵۸ | **۰٫۰۳۵۴۵ (رد)** |
| AR(1) p | ۰٫۰۹۸۷۹ | ۰٫۱۴۱۶۲ |
| AR(2) p | ۰٫۴۱۲۸۹ | ۰٫۴۵۱۶۲ |
| Difference-in-Hansen، ابزار سطح وابسته p | ۰٫۷۰۵۲۱ | **۰٫۰۰۰۷۹۴ (رد)** |
| نتیجه اعتبار علّی | **تأیید نشده** | **تأیید نشده، برخی ابزارها رد شده‌اند** |

## یادداشت جهت ارائه

اگر استاد صرفاً اجرای دقیق مدل‌های تعیین‌شده و آزمون‌ها را خواسته، کار اجرایی با مدارک قابل بازتولید آماده رسیدگی است. اگر تأیید علمی **اثر علّی سرریز فناوری بین کشورها** را بخواهد، این بسته هنوز چنین ادعایی را ثابت نمی‌کند. نتیجه ضعیف یا ردشده نباید حذف یا با تغییر دلخواه وقفه/کشور/روش پنهان شود.

**داده تاریخی دست‌نخورده، شاخه `main` بدون تغییر و [PR پژوهشی شماره ۱](https://github.com/mrst10578/Digital-Economy-GMM/pull/1) تا زمان بررسی روش‌شناسی مستقل Draft و ادغام‌نشده بماند.**
