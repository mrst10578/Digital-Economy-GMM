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
    (OUT/"emailed_stata_audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
    print("STATA_EMAIL_AUDIT_SUMMARY",json.dumps({k:audit[k] for k in (
        "zip_sha256","source_bytes","has_full_log","has_status_csv",
        "has_saved_models","stata_executed","estimated_count","failed_count")},ensure_ascii=False))
if __name__=="__main__":main()
