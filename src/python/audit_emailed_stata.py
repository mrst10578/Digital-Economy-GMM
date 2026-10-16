"""Audit exact ZIP retrieved from user's Gmail message, without inventing Stata results.
Unpacks *only* for reading; never executes any emailed .do or unknown executable.
"""
from __future__ import annotations
import csv, hashlib, io, json, re, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"evidence/stata-2026-10-09/outputs.zip"
OUT=ROOT/"outputs/stata_mail_audit"
OUT.mkdir(parents=True,exist_ok=True)
def decode(data):
    for enc in ("utf-8-sig","cp1252","latin-1"):
        try: return data.decode(enc)
        except UnicodeDecodeError: pass
    return data.decode("utf-8","replace")
def safe_name(s): return s.replace("\\","/").strip("/")
def main():
    assert SOURCE.exists(), "Missing original email ZIP"
    sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    audit={"source":"Gmail message 1a1221dbc8efcdc9, subject: digital economy; original outputs.zip",
           "zip_sha256":sha,"source_bytes":SOURCE.stat().st_size,"entries":[],
           "csv_records":{},"logs":{},"potential_models":[],"stata_executed":False,
           "interpretation":"Run statuses are factual, not a model-validity verdict."}
    with zipfile.ZipFile(SOURCE) as z:
        bad=z.testzip()
        assert bad is None,f"ZIP corrupt entry {bad}"
        names=[i for i in z.infolist() if not i.is_dir()]
        assert len(names)<200,"Unexpected number of entries"
        assert sum(i.file_size for i in names)<50_000_000,"Unreasonable total extracted size"
        for i in names:
            name=safe_name(i.filename)
            assert not name.startswith("/") and ".." not in Path(name).parts, "ZipSlip entry"
            if "__MACOSX" in name: continue
            audit["entries"].append({"name":name,"bytes":i.file_size})
            lower=name.lower()
            if lower.endswith(".csv"):
                data=decode(z.read(i))
                dest=OUT/Path(name).name
                dest.write_text(data,encoding="utf-8")
                rows=list(csv.DictReader(io.StringIO(data)))
                audit["csv_records"][name]=rows[:100]
                if "model_status" in lower:
                    audit["potential_models"]=rows
            if lower.endswith(".log") or lower.endswith(".txt"):
                contents=decode(z.read(i))
                (OUT/(Path(name).name+".txt")).write_text(contents,encoding="utf-8")
                lines=contents.splitlines()
                triggers=re.compile(r"^.*(STATA_|MODEL_|xtabond2|Hansen|Sargan|[Aa]rellano|AR\([12]\)|Difference-in-Hansen|instrument|Instruments|[Ee]rror|[Ww]arning|r\([0-9]+\)|[Ss]ingular|[Cc]ollinear|[Rr]ank|[Ff]ailed|[Pp]ostfile).*$")
                selected=[(n+1,x[:500]) for n,x in enumerate(lines) if triggers.search(x)]
                audit["logs"][name]={"lines":len(lines),"highlights":selected[:300],
                                      "first_60":lines[:60],"last_60":lines[-60:]}
                print("\nLOG_FILE",name,"LINE_COUNT",len(lines))
                for n,line in selected[:120]: print("STATA_LOG_LINE",name,n,line[:460])
    for e in audit["entries"]:print("ARCHIVE_ENTRY",e["name"],e["bytes"])
    for name,rows in audit["csv_records"].items():
        print("CSV_CONTENT",name,json.dumps(rows,ensure_ascii=False)[:18000])
    names=" ".join(x["name"].lower() for x in audit["entries"])
    audit["has_full_log"]="run_all_real_stata.log" in names
    audit["has_status_csv"]="model_status.csv" in names
    audit["has_saved_models"]=any(x["name"].endswith(".ster") for x in audit["entries"])
    # A log or .ster can contain errors: do NOT equate filename presence with execution success.
    statuses=[x.get("status","") for x in audit["potential_models"]]
    audit["stata_executed"]=bool(any(x.startswith("DIAGNOSTIC_HOLD") or x=="INSTRUMENTS_GE_GROUPS" for x in statuses))
    audit["estimated_count"]=sum(x in ("DIAGNOSTIC_HOLD","INSTRUMENTS_GE_GROUPS","MISSING_INSTRUMENT_DIAGNOSTIC") for x in statuses)
    audit["failed_count"]=sum("FAILED" in x for x in statuses)
    # Independent, explicitly non-acceptance scientific screening.
    # Use exact Stata full text: Difference-in-Hansen subsets are not in model_status.csv.
    full=next((k for k in audit["logs"] if k.lower().endswith("run_all_real_stata.log")),None)
    scientific=[]
    panel_tests=[]
    if full:
        txt="\n".join(audit["logs"][full]["first_60"])  # placeholder replaced from original ZIP below
        with zipfile.ZipFile(SOURCE) as z:
            txt=decode(z.read(next(x for x in z.namelist() if x.lower().endswith("run_all_real_stata.log"))))
        all_lines=txt.splitlines()
        for var in ["Growth","ln_Productivity","Internet","Broadband",
                    "ICT_Exports","Unemployment","Inflation","RnD"]:
            name=re.escape(var)
            ips=re.search(r"Im.?Pesaran.?Shin unit-root test for "+name+
                r"(?s:.*?)W-t-bar\s+([-+]?[0-9.]+)\s+([0-9.]+)",txt)
            fis=re.search(r"Fisher-type unit-root test for "+name+
                r"(?s:.*?)Inverse chi-squared\(\d+\)\s+P\s+([-+]?[0-9.]+)\s+([0-9.]+)",txt)
            panel_tests.append({"variable":var,
                "IPS_stat":ips.group(1) if ips else "",
                "IPS_p":ips.group(2) if ips else "",
                "Fisher_chi2":fis.group(1) if fis else "",
                "Fisher_p":fis.group(2) if fis else ""})
        for row in audit["potential_models"]:
            name=row["model"]
            pos=next((i for i,x in enumerate(all_lines) if x.startswith("STATA_MODEL_ESTIMATED="+name+" ")),None)
            if pos is None:
                scientific.append({"model":name,"found_in_log":False})
                continue
            start=pos
            while start>0 and not all_lines[start].lstrip().startswith(". capture noisily xtabond2 "):
                start-=1
            block=all_lines[start:pos]
            warn_singular=any("covariance matrix of moments is singular" in x for x in block)
            dropped=[x.strip() for x in block if "dropped due to collinearity" in x]
            diffs=[]
            group=None
            for x in block:
                if x.startswith("  GMM instruments for levels"):group="GMM instruments for levels"
                elif x.startswith("  gmm("):group=x.strip()
                elif x.lstrip().startswith("Hansen test excluding group:"):
                    ex=re.search(r"chi2\((\d+)\).*?Prob > chi2 =\s*([.0-9]+)",x)
                    if ex and group:
                        diffs.append({"subset":group,"excluded_df":int(ex.group(1)),
                                      "excluded_p":ex.group(2)})
                elif x.lstrip().startswith("Difference (null H = exogenous):"):
                    diff=re.search(r"chi2\((\d+)\).*?Prob > chi2 =\s*([.0-9]+)",x)
                    if diff and group:
                        obj=next((v for v in reversed(diffs) if v["subset"]==group and "difference_p" not in v),None)
                        if obj is not None:
                            obj["difference_df"]=int(diff.group(1))
                            obj["difference_p"]=diff.group(2)
            coefs={}
            for term in ["Internet","Broadband","ICT_Exports","Unemployment","Inflation","RnD"]:
                match=next((re.match(r"^\s*"+term+r"\s*\|\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)",x)
                            for x in block if re.match(r"^\s*"+term+r"\s*\|",x)),None)
                if match:
                    coefs[term]={"estimate":match.group(1),"std_error":match.group(2),"p":match.group(4)}
            flags=[]
            hansen=float(row["hansen_p"]) if row.get("hansen_p") else float("nan")
            ar1=float(row["ar1_p"]) if row.get("ar1_p") else float("nan")
            ar2=float(row["ar2_p"]) if row.get("ar2_p") else float("nan")
            sargan=float(row["sargan_p"]) if row.get("sargan_p") else float("nan")
            if hansen<.05:flags.append("HANSEN_REJECTS_5PCT")
            if ar2<.05:flags.append("AR2_REJECTS_5PCT")
            if ar1>=.05:flags.append("AR1_NOT_SIGNIFICANT_5PCT")
            if sargan<.05:flags.append("NONROBUST_SARGAN_REJECTS_5PCT")
            if warn_singular:flags.append("SINGULAR_ROBUST_MOMENT_COVARIANCE")
            if dropped:flags.append("YEAR_DUMMY_DROPPED")
            if int(row["instruments"])>=int(row["Ng"]):flags.append("INSTRUMENTS_GE_GROUPS")
            for d in diffs:
                if d.get("excluded_df")==0:flags.append("LEVEL_SUBSET_EXCLUSION_ZERO_DF")
                pv=d.get("difference_p")
                if pv and float(pv)<.05:flags.append("DIFFERENCE_HANSEN_SUBSET_REJECTS_5PCT:"+d["subset"])
            scientific.append({"model":name,"found_in_log":True,"run_status":row["status"],
                  "coefs":coefs,"difference_hansen":diffs,"singular":warn_singular,
                  "dropped_year_terms":dropped,"flags":flags,"accepted_scientifically":False})
    audit["scientific_model_review"]=scientific
    audit["stata_panel_unit_root_tests"]=panel_tests
    with (OUT/"stata_scientific_diagnostics.csv").open("w",encoding="utf-8",newline="") as h:
        cols=["model","run_status","instruments","groups","hansen_p","sargan_p","ar1_p","ar2_p","internet_coef","internet_p","diagnostic_flags"]
        wr=csv.DictWriter(h,fieldnames=cols);wr.writeheader()
        for m in scientific:
            base=next((x for x in audit["potential_models"] if x["model"]==m["model"]),{})
            wr.writerow({"model":m["model"],"run_status":m.get("run_status",""),
                 "instruments":base.get("instruments"),"groups":base.get("Ng"),
                 "hansen_p":base.get("hansen_p"),"sargan_p":base.get("sargan_p"),
                 "ar1_p":base.get("ar1_p"),"ar2_p":base.get("ar2_p"),
                 "internet_coef":m.get("coefs",{}).get("Internet",{}).get("estimate"),
                 "internet_p":m.get("coefs",{}).get("Internet",{}).get("p"),
                 "diagnostic_flags":";".join(m.get("flags",[]))})
    with (OUT/"stata_panel_unit_roots.csv").open("w",encoding="utf-8",newline="") as h:
        wr=csv.DictWriter(h,fieldnames=["variable","IPS_stat","IPS_p","Fisher_chi2","Fisher_p"])
        wr.writeheader();wr.writerows(panel_tests)
    for m in scientific:
        print("SCIENTIFIC_FLAGS",m["model"],json.dumps(m.get("flags",[]),ensure_ascii=False))
        print("DIFFERENCE_HANSEN_ACTUAL",m["model"],json.dumps(m.get("difference_hansen",[]),ensure_ascii=False))
    print("STATA_UNIT_ROOTS",json.dumps(panel_tests,ensure_ascii=False))
    (OUT/"emailed_stata_audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
    print("STATA_EMAIL_AUDIT_SUMMARY",json.dumps({k:audit[k] for k in (
        "zip_sha256","source_bytes","has_full_log","has_status_csv",
        "has_saved_models","stata_executed","estimated_count","failed_count")},ensure_ascii=False))
if __name__=="__main__":main()
