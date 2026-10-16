"""Check real-Stata joint-digital and lag-unity Wald evidence.

Executed on the authorized tablet, NOT within GitHub Actions.
Passing a Wald test does not repair potentially invalid System-GMM moments.
"""
from __future__ import annotations
import csv
from decimal import Decimal
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVID = ROOT / "evidence/tablet-stata-2026-10-16"
RAW = ROOT / "data/raw/Balanced_Panel_Data.xlsx"
MODEL = EVID / "professor_system_gmm_stats.csv"
NEW = EVID / "professor_joint_restrictions.csv"
LOG = EVID / "professor_joint_restrictions_real_stata.log"
SCRIPT = ROOT / "stata/tablet_diagnostics/13_professor_joint_digital_and_persistence.do"
HASH = "474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b"

def table(p:Path)->list[dict[str,str]]:
    with p.open(encoding="utf-8-sig",newline="") as fh:
        return list(csv.DictReader(fh))
def dec(s:str)->Decimal:
    n=Decimal(s)
    assert n.is_finite(),f"Missing, nonfinite statistic: {s}"
    return n

def main()->None:
    assert hashlib.sha256(RAW.read_bytes()).hexdigest()==HASH
    source=SCRIPT.read_text()
    assert "test Internet Broadband ICT_Exports" in source
    assert "test L.`y' = 1" in source
    assert "twostep robust small artests(2)" in source
    assert "lag(2 2) collapse split" in source
    assert "ivstyle($digital_year_dummies_sys)" in source
    assert "JOINT_TESTS_COMPLETE" in source

    rows=table(NEW)
    assert len(rows)==2 and {r["outcome"] for r in rows}=={"Growth","ln_Productivity"}
    primary={r["outcome"]:r for r in table(MODEL) if r["method"]=="twostep"}
    assert set(primary)=={"Growth","ln_Productivity"}

    log=LOG.read_text(errors="replace")
    assert "JOINT_TESTS_COMPLETE:" in log and "JOINT_MODEL_FAILURES=0" in log
    assert "JOINT_RESTRICTION_FAILURES=0" in log
    assert len(re.findall(r"^JOINT_MODEL_OK outcome=",log,re.M))==2
    assert not re.search(r"(?im)^\s*Warning:|^JOINT_MODEL_FAILED|^r\(\d+\);|covariance matrix of moments is singular|dropped due to collinearity",log)
    report={}
    for r in rows:
        y=r["outcome"]
        assert r["rc"]=="0" and r["joint_rc"]=="0" and r["persistence_rc"]=="0"
        assert (int(r["N"]),int(r["Ng"]),int(r["instruments"]))==(799,47,31)
        for col in ("lag_coef","lag_se","joint_F","joint_p","persistence_F","persistence_p","hansen_p","ar1_p","ar2_p"):
            dec(r[col])
        for col in ("joint_p","persistence_p","hansen_p","ar1_p","ar2_p"):
            assert 0<=dec(r[col])<=1
        base=primary[y]
        assert abs(dec(r["lag_coef"])-dec(base["b_lag"]))<=Decimal("0.000001")
        assert abs(dec(r["lag_se"])-dec(base["se_lag"]))<=Decimal("0.000001")
        assert abs(dec(r["hansen_p"])-dec(base["hansen_p"]))<=Decimal("0.000001")
        for name,expr in (
           ("TEST_DIGITAL_JOINT_RESULT",r"^TEST_DIGITAL_JOINT_RESULT outcome="+y+r" F=([^ ]+) p=([^\s]+)"),
           ("TEST_LAG_EQUAL_ONE_RESULT",r"^TEST_LAG_EQUAL_ONE_RESULT outcome="+y+r" F=([^ ]+) p=([^\s]+)")
        ):
            mark=re.search(expr,log,re.M)
            assert mark, f"Missing {name} actual Stata marker for {y}"
            F,p=map(Decimal,mark.groups())
            fcol,pcol=("joint_F","joint_p") if "DIGITAL" in name else ("persistence_F","persistence_p")
            assert abs(F-dec(r[fcol]))<=Decimal("0.00001")
            assert abs(p-dec(r[pcol]))<=Decimal("0.000001")
        report[y]={
            "joint_digital_F":r["joint_F"],"joint_digital_p":r["joint_p"],
            "lag_coefficient":r["lag_coef"],"lag_equals_one_F":r["persistence_F"],"lag_equals_one_p":r["persistence_p"],
            "joint_digital_rejected_at_5pct":dec(r["joint_p"])<Decimal(".05"),
            "lag_equal_one_rejected_at_5pct":dec(r["persistence_p"])<Decimal(".05")
        }
    assert all(not v["joint_digital_rejected_at_5pct"] for v in report.values())
    assert report["Growth"]["lag_equal_one_rejected_at_5pct"]
    assert not report["ln_Productivity"]["lag_equal_one_rejected_at_5pct"]
    verdict={
       "status":"PASS: native Stata two professor System-GMM models and Wald restrictions checked",
       "executed_in_ci":False,
       "dataset_sha256":HASH,
       "model_count":2,"restrictions_tested":4,
       "technical_execution_errors":0,
       "causal_models_accepted":0,
       "models":report,
       "scientific_warning":"Wald inference is conditional on System GMM instruments, which have independently failed overidentification subset tests; lag=1 Wald test is not a panel unit-root test."
    }
    out=ROOT/"outputs/professor_joint_wald_audit"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest.json").write_text(json.dumps(verdict,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(verdict,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
