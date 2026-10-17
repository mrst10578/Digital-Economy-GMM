from pathlib import Path
import hashlib,csv,json,math,datetime
root=Path('/sdcard/Download/Digital_Economy_Phase1_Retest_20261017')
prior=Path('/sdcard/Download/Digital_Economy_QA_20261016/outputs/professor')
latest=root/'outputs/professor'
raw=root/'data/raw/Balanced_Panel_Data.xlsx'
expected_hash='474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b'
assert hashlib.sha256(raw.read_bytes()).hexdigest()==expected_hash,'raw hash mismatch'
names=['professor_system_gmm_stats.csv','diff_l23_two_outcomes_stats.csv']
comparison={}
for name in names:
    with (prior/name).open(encoding='utf-8-sig',newline='') as f:
        before=list(csv.DictReader(f))
    with (latest/name).open(encoding='utf-8-sig',newline='') as f:
        after=list(csv.DictReader(f))
    key=('outcome','method' if name.startswith('professor_') else 'estimator')
    oldrows={tuple(row[k] for k in key):row for row in before}
    newrows={tuple(row[k] for k in key):row for row in after}
    assert len(before)==len(after)==4,(name,len(before),len(after))
    assert set(oldrows)==set(newrows),name
    assert all(row['rc']=='0' for row in after),name
    delta=0.0
    for keyvals,row in newrows.items():
        old=oldrows[keyvals]
        assert row.keys()==old.keys()
        for col,val in row.items():
            if col in ('outcome','method','estimator'):
                assert val==old[col],(name,keyvals,col,val,old[col])
            else:
                a,b=float(val),float(old[col])
                if not math.isnan(a) and not math.isnan(b):
                    delta=max(delta,abs(a-b))
                else:
                    assert math.isnan(a) and math.isnan(b)
    assert delta<1e-7,(name,delta)
    comparison[name]={'models':len(after),'max_abs_numerical_delta':delta,'all_rc_zero':True}
system={ (x['outcome'],x['method']):x for x in csv.DictReader((latest/names[0]).open())}
difference={ (x['outcome'],x['estimator']):x for x in csv.DictReader((latest/names[1]).open())}
for y in ('Growth','ln_Productivity'):
    x=system[(y,'twostep')]
    assert int(x['N'])==799 and int(x['Ng'])==47 and int(x['instruments'])==31
    z=difference[(y,'twostep')]
    assert int(z['N'])==752 and int(z['Ng'])==47 and int(z['instruments'])==30
logs=['PROFESSOR_SYSTEM_GMM_FOUR_RUNS.log','DIFFERENCE_GMM_OVERIDENTIFIED_L23_BOTH_MODELS.log']
for f in logs:
    t=(latest/f).read_text(errors='replace')
    assert len(t)>5000,f
assert 'PROFESSOR_FAILED_COUNT=0' in (latest/logs[0]).read_text(errors='replace')
assert 'DIFF_REPAIR_FAILURES=0' in (latest/logs[1]).read_text(errors='replace')
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
report={'status':'PASS','checked_utc':stamp,'only_original_source':True,'raw_sha256':expected_hash,'fresh_stata_run':True,'no_new_data':True,'comparisons':comparison,'raw_logs_sha256':{f:hashlib.sha256((latest/f).read_bytes()).hexdigest() for f in logs},'causal_validity':'NOT_ESTABLISHED','remaining_blockers':['productivity system GMM Hansen rejects 5 percent','productivity Difference-in-Hansen level instruments reject','AR(1) two-step nonrejection','weak-lag predictive relevance concern','no bilateral knowledge-flow data']}
(root/'RETEST_CHECK_RESULT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
rows=[]
rows.append('# بازآزمایی مستقل واقعی Stata | فاز اول مخصوص استاد | ۱۷ اکتبر ۲۰۲۶')
rows.append('')
rows.append('**دامنه:** فقط داده تاریخی استاد، ۴۷ کشور، سال‌های ۲۰۰۵ تا ۲۰۲۲. هیچ داده جدیدی وارد نشده است.')
rows.append('**ابزار:** Stata/MP 17 داخل Winlator، کنترل از مسیر ADB، محیط جدا برای جلوگیری از تغییر لاگ‌های قدیمی.')
rows.append('**اعتبار فایل خام:** SHA256 برابر مقدار تاریخی و تأییدشده است.')
rows.append('**وضعیت اجرا:** چهار System GMM و چهار Difference GMM با کد خروجی صفر اجرا شدند؛ هر هشت سطر عددی با آرشیو قبلی در آستانه خطای 1e-7 منطبق هستند.')
rows.append('')
rows.append('| مدل دو مرحله‌ای | رشد اقتصادی | لگاریتم سطح بهره‌وری |')
rows.append('|---|---:|---:|')
for label,k in [('System GMM - Hansen','hansen_p'),('System GMM - AR(1)','ar1_p'),('System GMM - AR(2)','ar2_p'),('System GMM - Difference-in-Hansen سطح','diffh_dep_level_p')]:
    rows.append(f"| {label} | {float(system[('Growth','twostep')][k]):.7f} | {float(system[('ln_Productivity','twostep')][k]):.7f} |")
for label,k in [('Difference GMM - Hansen','hansen_p'),('Difference GMM - AR(1)','ar1_p'),('Difference GMM - AR(2)','ar2_p')]:
    rows.append(f"| {label} | {float(difference[('Growth','twostep')][k]):.7f} | {float(difference[('ln_Productivity','twostep')][k]):.7f} |")
rows.extend(['','## داوری علمی','- **اجرای مجدد موفق** به معنی اعتبار شناسایی علّی نیست.','- در بهره‌وری System GMM، رد Hansen و Difference-in-Hansen ابزار سطح همچنان وجود دارد؛ مشکل برطرف نشده است.','- رشد System GMM فقط با محدودیت‌های تشخیص ابزارها و بدون ادعای علّی قابل گزارش است.','- Difference GMM یک تحلیل حساسیت متفاوت است؛ جانشین خودکار System GMM نیست.','- عدم معناداری شاخص‌های دیجیتال در سطح ۵ درصد نباید با تغییر انتخابی مدل پنهان شود.','','## شواهد خروجی','- outputs/professor/PROFESSOR_SYSTEM_GMM_FOUR_RUNS.log','- outputs/professor/DIFFERENCE_GMM_OVERIDENTIFIED_L23_BOTH_MODELS.log','- outputs/professor/professor_system_gmm_stats.csv','- outputs/professor/diff_l23_two_outcomes_stats.csv','- RETEST_CHECK_RESULT.json','','این گزارش صرفاً بازآزمایی محاسباتی است؛ ادعای حل بنیادی محدودیت‌های شناسایی ندارد.',''])
(root/'STATA_REAL_RETEST_STATUS_FA.md').write_text('\n'.join(rows),encoding='utf-8')
print('PHASE1_STATA_RETEST_INDEPENDENT_COMPARE_PASS')
print(json.dumps(report,ensure_ascii=False,indent=2))
