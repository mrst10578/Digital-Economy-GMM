"""Audit complete 47x2 native Stata country deletion experiment.
Observational sensitivity, NOT GMM identification or causal confirmation.
"""
from __future__ import annotations
import csv
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from statistics import median, mean
import re
import openpyxl

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/Balanced_Panel_Data.xlsx"
FOLDER = ROOT / "evidence/tablet-stata-2026-10-16"
CSV = FOLDER / "loo_47x2.csv"
LOG = FOLDER / "loo_47x2_real_stata.log"
PREV = ROOT / "evidence/tablet-stata-2026-10-15/full_rank_all_status.csv"
MODELS = {"Growth":"GROWTH_DIFF_L23", "ln_Productivity":"PROD_DIFF_L23"}
HASH = "474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b"

def dataset_countries() -> set[str]:
    w = openpyxl.load_workbook(RAW, read_only=True, data_only=True)
    it = iter(w.active.values)
    hdr=next(it)
    idx=hdr.index("ISO3")
    countries = {row[idx] for row in it if row[idx]}
    w.close()
    return countries

def read_table(p:Path) -> list[dict[str,str]]:
    with p.open(encoding="utf-8-sig",newline="") as fh:
        return list(csv.DictReader(fh))

def run() -> None:
    assert hashlib.sha256(RAW.read_bytes()).hexdigest() == HASH, "Source input changed"
    countries=dataset_countries()
    assert len(countries)==47 and "IRN" not in countries
    rows=read_table(CSV)
    assert len(rows)==94, f"Expected 47*2 rows; found {len(rows)}"
    assert len({(r["outcome"],r["dropped_country"]) for r in rows})==94, "Duplicate panel exclusions"
    log=LOG.read_text(errors="replace")
    good=re.findall(r"^LOO_OK outcome=(\w+) drop=(\w+)",log,re.M)
    failed=re.findall(r"^LOO_FAILED",log,re.M)
    warnings=re.findall(r"(?m)^Warning:",log)
    assert len(good)==94 and not failed, f"Log incomplete: {len(good)} completed"
    assert not warnings, f"Warning(s) in LOO execution: {len(warnings)}"
    assert "LOO_47X2_COMPLETED" in log and "LOO_TOTAL_FAILURES=0" in log
    old={r["model"]:r for r in read_table(PREV)}
    result={}
    for out,model in MODELS.items():
        part=[r for r in rows if r["outcome"]==out]
        assert len(part)==47 and {r["dropped_country"] for r in part}==countries
        for r in part:
            assert r["rc"]=="0" and int(r["Ng"])==46 and int(r["N"])==736
            assert int(r["instruments"])<int(r["Ng"])
            assert int(r["instruments"])==30
            for field in ("b_internet","se_internet","sargan_p","hansen_p","ar1_p","ar2_p"):
                x=float(r[field])
                assert math.isfinite(x), (r["dropped_country"],field)
            assert float(r["se_internet"])>0
            for field in ("sargan_p","hansen_p","ar1_p","ar2_p"):
                assert 0<=float(r[field])<=1
        base=float(old[model]["b_internet"])
        beta=[float(r["b_internet"]) for r in part]
        signs=sum((b>0)!=(base>0) for b in beta)
        m=mean(beta)
        jack_se=math.sqrt((len(beta)-1)/len(beta)*sum((b-m)**2 for b in beta))
        best=sorted(part, key=lambda r: abs(float(r["b_internet"])-base),reverse=True)[:5]
        result[out]={
            "baseline_internet_coefficient":base,
            "loo_internet_min":min(beta),"loo_internet_max":max(beta),
            "loo_internet_median":median(beta),
            "jackknife_se_exploratory_NOT_regression_se":jack_se,
            "excluded_country_sign_flips":signs,
            "exclusions_with_negative_coefficient":sum(b<0 for b in beta),
            "exclusions_with_positive_coefficient":sum(b>0 for b in beta),
            "reject_Hansen_at_5pct":sum(float(r["hansen_p"])<.05 for r in part),
            "reject_Sargan_at_5pct":sum(float(r["sargan_p"])<.05 for r in part),
            "AR1_not_rejected_at_5pct":sum(float(r["ar1_p"])>=.05 for r in part),
            "AR2_rejected_at_5pct":sum(float(r["ar2_p"])<.05 for r in part),
            "largest_5_shifts":[{"country":r["dropped_country"],"coefficient":float(r["b_internet"]),"difference_from_full_sample":float(r["b_internet"])-base} for r in best]
        }
    summary={
        "status":"PASS: archived real Stata 47-by-2 country deletion audit",
        "rows":len(rows),"unique_countries":len(countries),"models_per_outcome":47,
        "warning_count":len(warnings),"execution_failure_count":len(failed),
        "source_sha256":HASH,"model":"one-step Difference GMM robust, fixed full-rank year basis, lag(2 3) collapse",
        "outcomes":result,
        "scientifically_valid_causal_model_count":0,
        "method_caution":"Post-estimation sample sensitivity does not test conditional moment exogeneity, causal spillovers, or nonstationary levels."
    }
    out=ROOT/"outputs/loo_science"
    out.mkdir(parents=True,exist_ok=True)
    (out/"loo_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=="__main__":
    run()
