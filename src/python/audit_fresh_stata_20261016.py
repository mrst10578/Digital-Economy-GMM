"""Check archived independent 2026-10-16 Stata run and fresh WDI audit.
Does not run Stata or fetch WDI. A PASS is not causal model validation.
"""
from __future__ import annotations
import csv
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / "evidence/tablet-stata-2026-10-16"
PREV = ROOT / "evidence/tablet-stata-2026-10-15/production_full_rank_model_status.csv"
WORKBOOK = ROOT / "data/raw/Balanced_Panel_Data.xlsx"
VARIABLES = {"Growth","ln_Productivity","Internet","Broadband",
             "ICT_Exports","Unemployment","Inflation","RnD"}
FIELDS = ("N","Ng","instruments","sargan_p","hansen_p","ar1_p","ar2_p")

def rows(path: Path) -> list[dict[str,str]]:
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def main() -> None:
    run = json.loads((E / "fresh_qa_verified.json").read_text())
    sha = hashlib.sha256(WORKBOOK.read_bytes()).hexdigest()
    assert sha == run["workbook_sha256"], "Different historical workbook"
    assert run["pretests_pass"] == 16 and run["models_pass"] == 6
    assert run["warnings"] == 0 and run["historical_diagnostic_differences"] == []
    assert run["scientifically_accepted_causal_models"] == 0

    current = rows(E / "model_status.csv")
    historical = rows(PREV)
    assert len(current)==len(historical)==6
    assert len({x["model"] for x in current}) == 6
    for a,b in zip(current,historical):
        assert a["model"] == b["model"]
        assert a["rc"] == "0" and a["status"] == "DIAGNOSTIC_HOLD"
        for field in FIELDS:
            n,m = Decimal(a[field]),Decimal(b[field])
            tol = Decimal(0) if field in ("N","Ng","instruments") else Decimal("0.000001")
            assert abs(n-m)<=tol, (a["model"],field,n,m)

    log = (E/"fresh_run_all_real_stata.log").read_text()
    stats = re.findall(r"^STATA_TEST_STATUS (IPS|FISHER) (\w+) rc=(\d+)$",log,re.M)
    assert len(stats)==16 and {(test,var) for test,var,rc in stats} == {
        (test,var) for test in ("IPS","FISHER") for var in VARIABLES
    }
    assert all(rc=="0" for _,_,rc in stats)
    models = re.findall(r"^STATA_MODEL_ESTIMATED=([A-Z0-9_]+) status=DIAGNOSTIC_HOLD",log,re.M)
    assert len(models)==6 and set(models)=={r["model"] for r in current}
    assert "STATA_PRETEST_SCRIPT_RETURN_CODE=0" in log
    assert "RUN_ALL_SCRIPT_COMPLETED" in log and "STATA_STATUS_EXPORT_OK" in log
    assert not re.search(r"(?im)^\s*(?:Warning:|STATA_MODEL_FAILED=|r\(\d+\);)|dropped due to collinearity|covariance matrix of moments is singular",log)
    assert "xtabond2" in log

    live = (E/"wdi_live_audit.txt").read_text()
    matches = re.findall(r"^WDI_CHECK (\w+) match (\d+) different (\d+) currently_missing (\d+)$",live,re.M)
    assert len(matches)==8 and {x[0] for x in matches} == {
        "Growth","Productivity","Internet","Broadband",
        "ICT_Exports","Unemployment","Inflation","RnD"}
    assert sum(int(x[1]) for x in matches)==6606
    assert sum(int(x[2]) for x in matches)==162
    assert all(x[3]=="0" for x in matches)
    assert {x[0]:int(x[2]) for x in matches if int(x[2])}=={"Inflation":130,"ICT_Exports":32}
    assert 'SUMMARY_CHECK {"structural_ok": true, "WDI_success": 8,' in live

    output={
       "result":"PASS: verified real Stata 17 MP log and live WDI audit snapshot",
       "fresh_pre_estimation_tests":16,"fresh_gmm_models":6,
       "stated_numerical_warnings":0,"historical_diagnostic_differences":0,
       "WDI_live_comparisons":6768,"WDI_snapshot_differences":162,
       "dataset_sha256":sha,"causal_models_accepted":0,
       "warning":"This checks archived real device evidence; Stata is NOT run by GitHub Actions."
    }
    target=ROOT/"outputs/fresh_stata_qa"
    target.mkdir(parents=True,exist_ok=True)
    (target/"latest.json").write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(output,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
