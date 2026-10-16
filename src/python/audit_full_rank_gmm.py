"""Check archived full-rank Stata outputs against historical figures, not causality."""
from __future__ import annotations
import csv
import io
import json
import re
import zipfile
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/"evidence/tablet-stata-2026-10-15"
ORIGINAL=ROOT/"evidence/stata-2026-10-09/outputs.zip"
NUMERIC=("N","Ng","instruments","sargan_p","hansen_p","ar1_p","ar2_p")
def read_csv(text):
    return {r["model"]:r for r in csv.DictReader(io.StringIO(text))}
def main():
    old=read_csv(zipfile.ZipFile(ORIGINAL).read("outputs/stata/model_status.csv").decode("utf-8-sig"))
    new=read_csv((EVIDENCE/"full_rank_all_status.csv").read_text(encoding="utf-8-sig"))
    assert len(old)==len(new)==6 and set(old)==set(new), "Six model IDs required"
    max_deviation=Decimal(0)
    for name,orig in old.items():
        cur=new[name]
        assert orig["status"]=="DIAGNOSTIC_HOLD", "Historical validity hold changed"
        assert cur["rc"]==orig["rc"]=="0", f"Execution failure: {name}"
        for field in NUMERIC:
            a=Decimal(orig[field])
            b=Decimal(cur[field])
            diff=abs(a-b)
            max_deviation=max(max_deviation,diff)
            if field in ("N","Ng","instruments"):
                assert a==b,f"Sample or instrument count changed: {name}/{field}"
            else:
                assert diff <= Decimal("0.000001"),f"Scientific statistic changed: {name}/{field}"
        assert cur["b_internet"] and Decimal(cur["b_internet"]).is_finite()
    log=(EVIDENCE/"full_rank_all_models.log").read_text(encoding="utf-8")
    assert len(re.findall(r"^FULL_RANK_ESTIMATED=",log,re.M))==6
    assert "FULL_RANK_ALL_MODELS_COMPLETE" in log
    assert not re.search(r"^Warning:|dropped due to collinearity|^r\(\d+\);",log,re.M), "A numerical or execution warning appeared"
    assert Decimal(new["PROD_SYS_L22"]["hansen_p"])<Decimal(".05"),"Scientific hold requires attention"
    assert Decimal(new["GROWTH_SYS_L22"]["sargan_p"])<Decimal(".05"),"Scientific hold requires attention"
    env=(ROOT/"stata/01_environment_and_data.do").read_text()
    growth=(ROOT/"stata/03_growth_models.do").read_text()
    prod=(ROOT/"stata/04_productivity_models.do").read_text()
    assert 'global digital_year_dummies_diff "yd_2-yd_16 yd_18"' in env
    assert 'global digital_year_dummies_sys "yd_2-yd_3 yd_5-yd_18"' in env
    for path in (growth,prod):
        calls=[s for s in path.splitlines() if s.startswith("capture noisily xtabond2 ")]
        assert len(calls)==3
        assert calls[0].count("$digital_year_dummies_diff")==2
        assert all(x.count("$digital_year_dummies_sys")==2 for x in calls[1:])
    # Independent integration rerun using the actual patched production .do files.
    integrated=read_csv((EVIDENCE/"production_full_rank_model_status.csv").read_text(encoding="utf-8"))
    assert len(integrated)==6 and set(integrated)==set(old)
    for name, row in integrated.items():
        assert row["status"]=="DIAGNOSTIC_HOLD" and row["rc"]=="0",f"Integration failed: {name}"
        for field in NUMERIC:
            a=Decimal(old[name][field])
            b=Decimal(row[field])
            assert abs(a-b)<=Decimal("0.000001"),f"Integration drift: {name}/{field}"
    integration_log=(EVIDENCE/"production_full_rank_integration.log").read_text(encoding="utf-8")
    assert len(re.findall(r"^STATA_MODEL_ESTIMATED=",integration_log,re.M))==6
    assert "INTEGRATION_GROWTH_SCRIPT_RC=0" in integration_log
    assert "INTEGRATION_PROD_SCRIPT_RC=0" in integration_log
    assert "INTEGRATION_FULL_RANK_EXECUTION_COMPLETED" in integration_log
    assert not re.search(r"^Warning:|dropped due to collinearity|^STATA_MODEL_FAILED=|^r\(\d+\);",
                         integration_log,re.M), "Original production scripts reintroduced a numerical warning"
    # Additional full native Stata rerun on 162 latest-WDI-sensitivity cells.
    latest_old=read_csv((EVIDENCE/"wdi_gmm_model_status.csv").read_text(encoding="utf-8"))
    latest_new=read_csv((EVIDENCE/"wdi_production_full_rank_model_status.csv").read_text(encoding="utf-8"))
    assert len(latest_new)==len(latest_old)==6 and set(latest_new)==set(latest_old)
    for name, row in latest_new.items():
        assert row["status"]=="DIAGNOSTIC_HOLD" and row["rc"]=="0",f"WDI integration error: {name}"
        for field in NUMERIC:
            assert abs(Decimal(row[field])-Decimal(latest_old[name][field]))<=Decimal("0.000001"),f"WDI source/basis drift: {name}/{field}"
    updated_log=(EVIDENCE/"wdi_production_full_rank_integration.log").read_text(encoding="utf-8")
    assert len(re.findall(r"^STATA_MODEL_ESTIMATED=",updated_log,re.M))==6
    assert "INTEGRATION_FULL_RANK_EXECUTION_COMPLETED" in updated_log
    assert "INTEGRATION_GROWTH_SCRIPT_RC=0" in updated_log and "INTEGRATION_PROD_SCRIPT_RC=0" in updated_log
    assert not re.search(r"^Warning:|dropped due to collinearity|^STATA_MODEL_FAILED=|^r\(\d+\);",
                         updated_log,re.M), "WDI revised actual Stata run emitted a numerical warning"
    status={"result":"PASS: six real Stata models, no covariance/collinearity warnings, historical numerical equivalence",
            "gmm_models_reproduced":6,"production_integrated_models_reproduced":6,"updated_WDI_clean_models":6,"max_absolute_historical_diagnostic_delta":str(max_deviation),
            "numerical_warnings":0,"models_accepted_as_causal":0,
            "note":"No statistical software warning is not proof of valid GMM instruments or causal spillovers."}
    out=ROOT/"outputs/full_rank_audit";out.mkdir(parents=True,exist_ok=True)
    (out/"latest.json").write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(status,ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
