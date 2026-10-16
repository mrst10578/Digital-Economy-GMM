"""Check preserved native Stata tests of professor GMM level equation and initial conditions.

The tests were performed on Stata/MP 17 on an Android tablet via Winlator.
GitHub Actions only audits archived artifacts, not Stata.
Neither difference-GMM just-identification nor country convergence proves System moments.
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
SCRIPTS=ROOT/"stata/tablet_diagnostics"
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
SOURCE_HASH="474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b"

def table(p):
    with p.open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def num(v):
    x=Decimal(v)
    assert x.is_finite(),f"Nonfinite value: {v}"
    return x

def main():
    assert hashlib.sha256(RAW.read_bytes()).hexdigest()==SOURCE_HASH
    base={r["outcome"]:r for r in table(E/"professor_system_gmm_stats.csv") if r["method"]=="twostep"}
    assert set(base)=={"Growth","ln_Productivity"}
    diffscript=(SCRIPTS/"15_professor_matched_difference_removal.do").read_text()
    init_script=(SCRIPTS/"16_professor_initial_condition_descriptive.do").read_text()
    assert "noleveleq twostep robust small artests(2)" in diffscript
    assert "lag(2 2) collapse" in diffscript
    assert "ivstyle($digital_year_dummies_diff, equation(diff))" in diffscript
    assert "initial_y" in init_script and "mean_dy" in init_script
    assert "regress mean_dy initial_y, vce(robust)" in init_script

    diff=table(E/"professor_level_equation_removal.csv")
    initial=table(E/"professor_initial_condition_descriptives.csv")
    assert len(diff)==len(initial)==2
    assert {r["outcome"] for r in diff}=={r["outcome"] for r in initial}==set(base)
    diff_log=(E/"professor_level_equation_removal_real_stata.log").read_text(errors="replace")
    init_log=(E/"professor_initial_condition_descriptive_real_stata.log").read_text(errors="replace")
    assert "LEVEL_REMOVAL_FINISHED" in diff_log and "LEVEL_REMOVAL_FAILURES=0" in diff_log
    assert "LEVEL_REMOVAL_COUNT=2" in diff_log
    assert len(re.findall(r"^LEVEL_REMOVAL_OK outcome=",diff_log,re.M))==2
    assert "INITIAL_DESCRIPTIVE_COMPLETE" in init_log and "INITIAL_DESCRIPTIVE_FAILURES=0" in init_log
    assert len(re.findall(r"^INITIAL_DESCRIPTIVE_OK outcome=",init_log,re.M))==2
    for log in (diff_log,init_log):
        assert not re.search(r"(?im)^\s*Warning:|covariance matrix of moments is singular|dropped due to collinearity|^r\(\d+\);|LEVEL_REMOVAL_FAILED|INITIAL_DESCRIPTIVE_FAILED",log)
    assert len(re.findall(r"Hansen test of overid. restrictions:\s*chi2\(0\)",diff_log))==2
    assert len(re.findall(r"Sargan test of overid. restrictions:\s*chi2\(0\)",diff_log))==2
    models={}
    for r in diff:
        outcome=r["outcome"]
        assert r["rc"]=="0" and (int(r["N"]),int(r["Ng"]),int(r["instruments"]))==(752,47,23)
        assert r["hansen_p"]=="" and r["sargan_p"]=="", "chi2(0) cannot be a valid test p-value"
        for k in ("lag_b","lag_se","internet_b","internet_se","internet_p","ar1_p","ar2_p"):
            num(r[k])
        assert num(r["lag_se"])>0 and num(r["internet_se"])>0
        for k in ("internet_p","ar1_p","ar2_p"):
            assert 0<=num(r[k])<=1
        b=base[outcome]
        models[outcome]={
            "original_sys_lag2_lag_dependent_b":b["b_lag"],
            "difference_lag2_lag_dependent_b":r["lag_b"],
            "original_sys_lag2_internet_b":b["b_internet"],
            "difference_lag2_internet_b":r["internet_b"],
            "difference_lag2_internet_p":r["internet_p"],
            "difference_lag2_ar1_p":r["ar1_p"],
            "difference_lag2_ar2_p":r["ar2_p"],
            "overidentification_tests":"UNAVAILABLE: 0 degrees of freedom",
        }
    for r in initial:
        assert r["rc"]=="0" and (int(r["countries"]),int(r["periods"]))==(47,17)
        for k in ("slope","se","p","r2","mean_annual_change","sd_annual_change","share_positive_change"): num(r[k])
        for k in ("p","r2","share_positive_change"):
            assert 0<=num(r[k])<=1
        assert num(r["se"])>0
        assert num(r["slope"])<0, "Archived descriptive convergence pattern changed"
        models[r["outcome"]]["initial_vs_subsequent_mean_change_robust_slope"]=r["slope"]
        models[r["outcome"]]["initial_vs_subsequent_mean_change_p"]=r["p"]
        models[r["outcome"]]["initial_condition_note"]="Descriptive cross-sectional association only, not a test of System GMM level moment restrictions"
    output={
        "audit_result":"PASS: original sources and native two Difference GMM + two descriptive initial-condition regressions",
        "stata_executed_in_CI":False,
        "raw_sha256":SOURCE_HASH,
        "difference_gmm_executed_models":2,
        "initial_condition_exploratory_regressions":2,
        "difference_hansen_sargan_defined":False,
        "causally_validated_models":0,
        "interpretation":"Difference GMM lag2 with collapsed grouped moments is just identified here, so validity cannot be inferred; sample and basis differ from System. Initial levels vs mean changes do not identify individual effects.",
        "models":models
    }
    dest=ROOT/"outputs/professor_level_moment_audit";dest.mkdir(parents=True,exist_ok=True)
    (dest/"latest.json").write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(output,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
