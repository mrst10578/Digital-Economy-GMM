"""Archive audit for fixed lag-3-only original professor System-GMM sensitivity.

Do not confuse non-rejection of Hansen with proving instrument validity.
Actual Stata runs are on the tablet; this file only checks preserved evidence.
"""
from __future__ import annotations
import csv
from decimal import Decimal
import hashlib
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/"evidence/tablet-stata-2026-10-16"
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
CSV=E/"professor_lag3_instrument_stress.csv"
LOG=E/"professor_lag3_instrument_stress_real_stata.log"
DO=ROOT/"stata/tablet_diagnostics/14_professor_system_lag3_instrument_stress.do"
MAIN=E/"professor_system_gmm_stats.csv"
HASH="474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b"
def rows(path):
    with path.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def d(v):
    n=Decimal(v)
    assert n.is_finite(),f"Missing or malformed numeric result: {v!r}"
    return n
def main():
    assert hashlib.sha256(RAW.read_bytes()).hexdigest()==HASH
    script=DO.read_text()
    assert "lag(3 3) collapse split" in script
    assert script.count("lag(3 3) collapse)")>=2
    assert "twostep robust small artests(2)" in script
    assert "LAG3_DH_MATRIX_LAYOUT" in script
    assert "inlist(colsof(__diffh),3,4)" in script
    assert "ivstyle($digital_year_dummies_sys)" in script
    body=LOG.read_text(errors="replace")
    assert "LAG3_MODEL_FAILURES=0" in body
    assert "LAG3_MODEL_TOTAL=2" in body
    assert "LAG3_SENSITIVITY_FINISHED" in body
    assert len(re.findall(r"^LAG3_START outcome=",body,re.M))==2
    assert len(re.findall(r"^LAG3_OK outcome=",body,re.M))==2
    assert not re.search(r"(?im)^\s*Warning:|covariance matrix of moments is singular|dropped due to collinearity|^LAG3_FAILED|^r\(\d+\);",body)
    # Stata wraps long output lines with a leading "> "; join the continuations\n    # before comparing native machine-output text with the CSV.\n    unwrapped=re.sub(r"\\n> ?", "", body)\n    v=rows(CSV)
    assert len(v)==2 and {x["outcome"] for x in v}=={"Growth","ln_Productivity"}
    prior={x["outcome"]:x for x in rows(MAIN) if x["method"]=="twostep"}
    assert len(prior)==2
    answer={}
    for x in v:
        y=x["outcome"]
        assert x["rc"]=="0"
        assert (int(x["N"]),int(x["Ng"]),int(x["instruments"]))==(799,47,31)
        for k in ("b_lag","b_internet","se_internet","p_internet","sargan_p","hansen_p","ar1_p","ar2_p","diffh_level_dep_p","diffh_controls_p"):
            d(x[k])
        for k in ("p_internet","sargan_p","hansen_p","ar1_p","ar2_p","diffh_level_dep_p","diffh_controls_p"):
            assert 0<=d(x[k])<=1,(y,k)
        assert d(x["se_internet"])>0
        layout=re.search(r"^LAG3_DH_MATRIX_LAYOUT outcome="+y+r" columns=(\d+) dependent_level_p=([^\s]+) controls_p=([^\s]+)",body,re.M)
        assert layout,f"Missing actual Stata subset moment extraction for {y}"
        assert int(layout.group(1))==(4 if y=="Growth" else 3)
        assert abs(d(layout.group(2))-d(x["diffh_level_dep_p"]))<Decimal(".000001")
        assert abs(d(layout.group(3))-d(x["diffh_controls_p"]))<Decimal(".000001")
        assert d(x["p_internet"])>Decimal(".05")
        assert d(x["ar1_p"])>Decimal(".05")
        answer[y]={
           "original_lag2_internet":prior[y]["b_internet"],
           "lag3_internet":x["b_internet"],
           "lag3_p_internet":x["p_internet"],
           "lag3_hansen_p":x["hansen_p"],
           "lag3_diffh_level_p":x["diffh_level_dep_p"],
           "lag3_ar1_p":x["ar1_p"],
           "lag3_ar2_p":x["ar2_p"],
           "lag3_lag_coefficient":x["b_lag"],
        }
    report={
       "status":"PASS: two lag-3-only full sample native Stata GMM results and corrected subset extraction",
       "data_sha256":HASH,
       "models_ran_in_stata":2,
       "Stata_ran_in_GitHub_CI":False,
       "numeric_warnings":0,
       "scientifically_accepted_causal_models":0,
       "caution":"This was a pre-specified sensitivity check. Large Hansen p-values can reflect weak instruments; no new model was selected as primary and AR1 is not rejected.",
       "models":answer
    }
    out=ROOT/"outputs/professor_lag3_audit";out.mkdir(parents=True,exist_ok=True)
    (out/"latest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
