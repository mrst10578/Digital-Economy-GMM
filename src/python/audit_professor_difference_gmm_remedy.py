"""Audit two-outcome original-estimand Difference-GMM remedy and fixed lag2/3 predictive proxies.
CI does not run Stata. Nonrejection of Hansen/Sargan cannot prove exogeneity.
"""
from __future__ import annotations
import csv, hashlib, json, re
from decimal import Decimal
from pathlib import Path

R=Path(__file__).resolve().parents[2]
E=R/"evidence/scientific-gates-2026-10-16"
BASE=R/"evidence/tablet-stata-2026-10-16/professor_system_gmm_stats.csv"
RAW=R/"data/raw/Balanced_Panel_Data.xlsx"
MAIN=E/"difference_gmm_l23_two_primary_outcomes.csv"
LOG=E/"difference_gmm_l23_two_primary_outcomes_real_stata.log"
SCRIPT=R/"stata/tablet_diagnostics/21_prespecified_two_outcome_difference_gmm_l23.do"
RELEVANCE=E/"difference_gmm_l23_predictive_relevance.csv"
RELEVANCE_LOG=E/"difference_gmm_l23_predictive_relevance_real_stata.log"
RELEVANCE_SCRIPT=R/"stata/tablet_diagnostics/22_diff_l23_predictive_relevance.do"
EXPECTED_SHA="474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b"

def table(p):
    with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def dec(x):
    v=Decimal(x)
    assert v.is_finite(),x
    return v
def checklog(s,marker,number):
    assert len(re.findall("^"+marker,s,re.M))==number,(marker,number)
    assert not re.search(r"(?im)^\s*Warning:|^r\(\d+\);|covariance matrix of moments is singular|dropped due to collinearity",s)
def main():
    assert hashlib.sha256(RAW.read_bytes()).hexdigest()==EXPECTED_SHA
    script=SCRIPT.read_text()
    assert "noleveleq twostep robust small artests(2)" in script
    assert "noleveleq robust small artests(2)" in script
    assert script.count("lag(2 3) collapse)")>=6
    assert "ivstyle($digital_year_dummies_diff, equation(diff))" in script
    log=LOG.read_text(errors="replace")
    checklog(log,"DIFF_REPAIR_OK outcome=",4)
    assert "DIFF_REPAIR_FAILURES=0" in log and "DIFF_REPAIR_TOTAL_COUNT=4" in log
    assert "DIFF_REPAIR_COMPLETE:" in log
    assert len(re.findall(r"Hansen test of overid. restrictions:\s*chi2\(7\)",log))==4
    assert len(re.findall(r"Sargan test of overid. restrictions:\s*chi2\(7\)",log))==4
    got=table(MAIN)
    expected={(o,m) for o in ("Growth","ln_Productivity") for m in ("twostep","onestep")}
    assert len(got)==4 and {(r["outcome"],r["estimator"]) for r in got}==expected
    original={r["outcome"]:r for r in table(BASE) if r["method"]=="twostep"}
    assert set(original)=={"Growth","ln_Productivity"}
    models={}
    for r in got:
        assert r["rc"]=="0"
        assert (int(r["N"]),int(r["Ng"]),int(r["instruments"]))==(752,47,30)
        for k in ("b_lag","se_lag","b_internet","se_internet","p_internet",
                  "joint_p","hansen_p","sargan_p","ar1_p","ar2_p"):
            dec(r[k])
        for k in ("p_internet","joint_p","hansen_p","sargan_p","ar1_p","ar2_p"):
            assert 0<=dec(r[k])<=1,(r,k)
        assert dec(r["se_lag"])>0 and dec(r["se_internet"])>0
        assert dec(r["hansen_p"])>Decimal(".05") and dec(r["sargan_p"])>Decimal(".05")
        assert dec(r["ar2_p"])>Decimal(".05")
        models[f'{r["outcome"]}:{r["estimator"]}']={
            "lag_coef":r["b_lag"],"internet_beta":r["b_internet"],
            "internet_p":r["p_internet"],"joint_digital_p":r["joint_p"],
            "hansen_p":r["hansen_p"],"sargan_p":r["sargan_p"],
            "ar1_p":r["ar1_p"],"ar2_p":r["ar2_p"],
            "original_system_hansen_p":original[r["outcome"]]["hansen_p"]}
    assert all(dec(r["ar1_p"])>Decimal(".05") for r in got if r["estimator"]=="twostep")
    assert all(dec(r["ar1_p"])<Decimal(".05") for r in got if r["estimator"]=="onestep")
    assert all(dec(r["joint_p"])>Decimal(".05") for r in got)
    rs=RELEVANCE_SCRIPT.read_text()
    assert "regress `target' L2.`v' L3.`v' i.Year, vce(cluster panel_id)" in rs
    assert "test L2.`v' L3.`v'" in rs
    rl=RELEVANCE_LOG.read_text(errors="replace")
    checklog(rl,"DIFF_RELEVANCE_OK v=",8)
    assert "DIFF_RELEVANCE_FAILURES=0" in rl
    assert "DIFF_RELEVANCE_COUNT=8" in rl
    assert "DIFF_RELEVANCE_COMPLETE" in rl
    relevance=table(RELEVANCE)
    assert len(relevance)==8
    expected_vars={"Growth","ln_Productivity","Internet","Broadband",
                   "ICT_Exports","Unemployment","Inflation","RnD"}
    assert {r["variable"] for r in relevance}==expected_vars
    lag_check={}
    for r in relevance:
        assert r["rc"]=="0" and int(r["countries"])==47
        assert int(r["N"])>=700
        for k in ("coefficient_l2","coefficient_l3","joint_F","joint_p","r2"):
            dec(r[k])
        assert dec(r["joint_F"])>=0 and 0<=dec(r["joint_p"])<=1
        lag_check[r["variable"]]={"joint_cluster_F":r["joint_F"],"joint_p":r["joint_p"],
                                  "instrument_proxy_not_formal_rank_or_exogeneity_test":True}
    verdict={
        "status":"PASS: 4 genuine overidentified difference-GMM fits plus 8 independent fixed lag predictive checks",
        "original_source_sha256":EXPECTED_SHA,
        "original_professor_outcomes_unchanged":True,
        "difference_only_instead_of_professor_requested_system":True,
        "overidentification_df":7,
        "number_of_instruments":30,
        "number_of_groups":47,
        "models":models,
        "lag_relevance_descriptive_only":lag_check,
        "formally_exogeneity_proven":False,
        "causal_models_unconditionally_accepted":0,
        "scientific_warning":"Hansen/Sargan nonrejection at 5% does not establish moments. AR(1) not rejected in two-step, weak lag instruments possible with persistent productivity, and the professor specifically requested System GMM.",
        "statistical_program_executed_in_GitHub_CI":False
    }
    out=R/"outputs/professor_difference_remedy_audit"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest.json").write_text(json.dumps(verdict,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(verdict,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
