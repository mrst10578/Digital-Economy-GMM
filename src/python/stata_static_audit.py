"""Static-only Stata handoff audit. Does not execute Stata or validate econometric identification."""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
FILES=[
    "stata/RUN_ALL.do","stata/00_model_helpers.do","stata/01_environment_and_data.do",
    "stata/02_pre_estimation.do","stata/03_growth_models.do",
    "stata/04_productivity_models.do","stata/05_post_estimation_and_export.do",
    "stata/02_models.do"
]
MODEL_NAMES=["GROWTH_DIFF_L23","GROWTH_SYS_L22","GROWTH_SYS_L23_AUDIT",
             "PROD_DIFF_L23","PROD_SYS_L22","PROD_SYS_L23_AUDIT"]
def check(test, message):
    if not test: raise AssertionError(message)
def main():
    out=ROOT/"outputs/stata_static"
    out.mkdir(parents=True,exist_ok=True)
    contents={p:(ROOT/p).read_text(encoding="utf-8") for p in FILES}
    for p,s in contents.items():
        check(bool(s.strip()),f"Empty file {p}")
        b=0
        for n,ln in enumerate(s.splitlines(),1):
            line=ln.strip()
            if line.startswith("*") or not line: continue
            b+=line.count("{")-line.count("}")
            check(b>=0,f"Unmatched closing brace in {p}:{n}")
            if "xtabond2 " in line and not line.startswith("display"):
                check(line.count("(")==line.count(")"),f"Broken xtabond2 parentheses at {p}:{n}")
                check("collapse" in line and "artests(2)" in line,
                      f"Unsafe instrument diagnostic settings at {p}:{n}")
                check("lag(2 2)" in line or "lag(2 3)" in line,
                      f"Unregistered GMM lag window at {p}:{n}")
        check(b==0, f"Unclosed brace in {p}")
    main_do=contents["stata/RUN_ALL.do"]
    for p in FILES[1:-1]:
        check(f'do "{p}"' in main_do, f"RUN_ALL does not source {p}")
    check("postfile digital_post" in main_do, "No structured results handle")
    check("postclose digital_post" in contents["stata/05_post_estimation_and_export.do"],"No postclose")
    pre=contents["stata/01_environment_and_data.do"]
    check("capture confirm variable ln_Productivity" in pre,
          "Potential duplicate-variable crash for logged outcome")
    check("assert abs(ln_Productivity - ln(Productivity))" in pre,
          "Existing logged variable not independently checked")
    check("isid ISO3 Year" in pre and "xtset panel_id Year" in pre,
          "Panel identification incomplete")
    check("which xtabond2" in pre and "confirm file" in pre,
          "Missing xtabond2 or DTA preflight")
    check("xtunitroot ips" in contents["stata/02_pre_estimation.do"]
          and "xtunitroot fisher" in contents["stata/02_pre_estimation.do"],
          "Missing real Stata requested pre-estimation tests")
    models=contents["stata/03_growth_models.do"]+contents["stata/04_productivity_models.do"]
    for name in MODEL_NAMES: check(f"name({name})" in models,f"Missing model {name}")
    check(models.count("digital_success, name(")==6, "Not six success branches")
    check(models.count("digital_failure, name(")==6, "Not six failure branches")
    check(models.count(" split)")==4,"Difference-in-Hansen instrument group split missing")
    check(models.count(" noleveleq ")==2,"Difference GMM configuration missing")
    check(models.count("twostep robust small artests(2)")==4,
          "System two-step correction missing")
    check("e(hansenp)" in contents["stata/00_model_helpers.do"]
          and "e(sarganp)" in contents["stata/00_model_helpers.do"]
          and "e(j)" in contents["stata/00_model_helpers.do"]
          and "e(N_g)" in contents["stata/00_model_helpers.do"],
          "Stored estimates lack instrument / GMM diagnostics")
    doc=(ROOT/"STATA_START_HERE_FA.md").read_text(encoding="utf-8")
    for part in ["stata/RUN_ALL.do","model_status.csv","RUN_ALL_REAL_STATA.log",
                 "ssc install xtabond2","Stata","moremata"]:
        check(part in doc, f"Missing operator instruction {part}")
    path=ROOT/"data/processed/stata_ready.dta"
    check(path.is_file() and path.stat().st_size>5000,"Stata DTA missing or tiny")
    df=pd.read_stata(path)
    check(len(df)==846 and df.ISO3.nunique()==47,"Wrong DTA panel size")
    check(df.Year.min()==2005 and df.Year.max()==2022,"Wrong year coverage")
    check(not df.duplicated(["ISO3","Year"]).any(),"Nonunique keys")
    check(df.groupby("ISO3").Year.nunique().eq(18).all(),"Unbalanced panel")
    for c in ["Growth","Productivity","Internet","Broadband","ICT_Exports",
              "Unemployment","Inflation","RnD","ln_Productivity"]:
        check(c in df.columns and df[c].notna().all(),f"Missing {c}")
    check(((df["ln_Productivity"]-df["Productivity"].map(__import__("math").log)).abs()<1e-7).all(),
          "DTA logarithm not faithful")
    check(not (ROOT/"data/processed"/"stata_ready.dta").is_symlink(),"Symlinked DTA")
    result={"status":"PASS_STATIC_ONLY_NOT_STATA_RUN",
            "repo":"Digital-Economy-GMM",
            "source_dta_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "panel_rows":len(df),"countries":df.ISO3.nunique(),"model_scenarios":MODEL_NAMES,
            "do_file_count":len(FILES),
            "claims":"All do-files pass conservative structural checks; NOT syntax certification by Stata, and NOT econometric validity.",
            "external_stata_run":False}
    (out/"prestata_static_status.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False),flush=True)
if __name__=="__main__": main()
