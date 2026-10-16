"""Audit archived native Stata 2005-2019 System-GMM temporal sensitivity.
This does NOT execute Stata and does NOT establish causal identification.
"""
from __future__ import annotations
import csv
from decimal import Decimal
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / "evidence/tablet-stata-2026-10-16"
FILE = E / "prepandemic_system_gmm_stats.csv"
LOG = E / "prepandemic_system_gmm_real_stata.log"
SCRIPT = ROOT / "stata/tablet_diagnostics/12_professor_prepandemic_system_gmm.do"
BASE = E / "professor_system_gmm_stats.csv"
RAW = ROOT / "data/raw/Balanced_Panel_Data.xlsx"
SOURCE_SHA = "474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b"

def read_csv(path: Path) -> list[dict[str,str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))

def number(s: str) -> Decimal:
    n=Decimal(s)
    assert n.is_finite(), f"Missing or invalid numeric value: {s}"
    return n

def main() -> None:
    assert hashlib.sha256(RAW.read_bytes()).hexdigest() == SOURCE_SHA, "Workbook changed"
    script=SCRIPT.read_text(encoding="utf-8")
    assert "keep if Year <= 2019" in script
    assert "assert _N == 705" in script
    assert 'global pre_years "pyd_2-pyd_3 pyd_5-pyd_15"' in script
    assert "twostep robust small artests(2)" in script
    assert "lag(2 2) collapse split" in script
    assert "lag(2 2) collapse)" in script
    assert "ivstyle($pre_years)" in script
    rows=read_csv(FILE)
    assert len(rows)==2 and {r["outcome"] for r in rows} == {"Growth","ln_Productivity"}
    full=[r for r in read_csv(BASE) if r["method"]=="twostep"]
    assert len(full)==2 and {r["outcome"] for r in full}=={"Growth","ln_Productivity"}
    base={r["outcome"]:r for r in full}
    txt=LOG.read_text(errors="replace")
    assert len(re.findall(r"^PREPANDEMIC_OK outcome=",txt,re.M))==2
    assert len(re.findall(r"^PREPANDEMIC_START outcome=",txt,re.M))==2
    assert "PREPANDEMIC_FAILURE_COUNT=0" in txt
    assert "PREPANDEMIC_TOTAL_COUNT=2" in txt
    assert "PREPANDEMIC_RUN_COMPLETE" in txt
    assert not re.search(r"(?im)^\s*Warning:|dropped due to collinearity|covariance matrix of moments is singular|^PREPANDEMIC_FAILED|^r\(\d+\);",txt)
    result={"status":"PASS: 2 real native Stata pre-pandemic models and original comparison verified","stata_reexecuted_in_ci":False,"original_workbook_sha256":SOURCE_SHA,"prepandemic_period":"2005-2019","raw_country_years":705,"model_observations":658,"countries":47,"instruments":28,"models":{}}
    for r in rows:
        out=r["outcome"]
        assert r["rc"]=="0" and tuple(map(int,(r["N"],r["Ng"],r["instruments"])))==(658,47,28)
        vals={k:number(v) for k,v in r.items() if k not in ("outcome","rc","N","Ng","instruments")}
        for k in ("internet_p","sargan_p","hansen_p","ar1_p","ar2_p","diffh_dep_level_p","diffh_controls_p"):
            assert Decimal(0)<=vals[k]<=Decimal(1),(out,k)
        assert vals["lag_se"]>0 and vals["internet_se"]>0
        comparison=base[out]
        result["models"][out]={
           "full_sample_internet_beta":comparison["b_internet"],
           "prepandemic_internet_beta":r["internet_b"],
           "full_sample_lagged_outcome_beta":comparison["b_lag"],
           "prepandemic_lagged_outcome_beta":r["lag_b"],
           "full_sample_hansen_p":comparison["hansen_p"],
           "prepandemic_hansen_p":r["hansen_p"],
           "prepandemic_sargan_p":r["sargan_p"],
           "prepandemic_ar1_p":r["ar1_p"],
           "prepandemic_ar2_p":r["ar2_p"],
           "prepandemic_difference_in_hansen_outcome_level_p":r["diffh_dep_level_p"],
           "difference_in_hansen_outcome_level_rejected_at_5pct":vals["diffh_dep_level_p"]<Decimal(".05")
        }
    result["instrument_subset_rejection_count"]=sum(x["difference_in_hansen_outcome_level_rejected_at_5pct"] for x in result["models"].values())
    assert result["instrument_subset_rejection_count"]==2, "Recorded subgroup diagnostic interpretation changed"
    result["scientifically_accepted_causal_models"]=0
    result["limitation"]="Calendar-cut sensitivity is not instrument exogeneity, valid moment identification or external technology spillover measurement."
    folder=ROOT/"outputs/professor_temporal_audit"
    folder.mkdir(parents=True,exist_ok=True)
    (folder/"latest.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
