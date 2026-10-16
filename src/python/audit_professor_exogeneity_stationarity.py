"""Independent archive QA for the professor's instrument and stationarity gates.

Original CIPS is the *actual* R workflow-14 artifact (64 tests).
IPS/Fisher and lag-2 relevance are outputs of native tablet Stata/MP 17.
This script does not run R or Stata and does not prove causal identification.
"""
from __future__ import annotations

import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/"evidence/scientific-gates-2026-10-16"
STATA=E/"productivity_unitroot_grid_stata.csv"
RELEVANCE=E/"lag2_year_adjusted_relevance.csv"
CIPS=E/"cips_full_64_original_r_workflow14.csv"
LOG=E/"instrument_relevance_productivity_unitroot_real_stata.log"
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
SCRIPT=ROOT/"stata/tablet_diagnostics/17_professor_exogeneity_relevance_and_unit_root.do"
RAW_HASH="474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b"
CIPS_HASH="d4a208883040b4594ae4ce93fb2eabc7d66ac4c48e504ea8070c3a6f5f980c58"

def tab(path:Path)->list[dict[str,str]]:
    with path.open(encoding="utf-8-sig",newline="") as fh:
        return list(csv.DictReader(fh))
def dec(x:str)->Decimal:
    value=Decimal(x)
    assert value.is_finite(),x
    return value

def main()->None:
    assert hashlib.sha256(RAW.read_bytes()).hexdigest()==RAW_HASH
    assert hashlib.sha256(CIPS.read_bytes()).hexdigest()==CIPS_HASH, "Original R artifact unexpectedly modified"
    do=SCRIPT.read_text()
    for expected in (
        'do "stata/01_environment_and_data.do"',
        "vce(cluster panel_id)",
        "regress `lhs' L2.`v' i.Year",
        "xtunitroot ips `variable', lags(`lag')",
        "xtunitroot fisher `variable', dfuller lags(`lag')",
        "D.ln_Productivity",
    ):
        assert expected in do, f"Missing fixed Stata test: {expected}"
    r=tab(RELEVANCE)
    expected_vars={
        "Growth","ln_Productivity","Internet","Broadband",
        "ICT_Exports","Unemployment","Inflation","RnD"
    }
    assert len(r)==8 and {x["instrument"] for x in r}==expected_vars
    relevance={}
    for row in r:
        assert row["rc"]=="0"
        assert (int(row["N"]),int(row["groups"]))==(752,47)
        for k in ("b_lag2","se_lag2","p_lag2","F_cluster","r2_year_adjusted","raw_corr"):
            dec(row[k])
        assert dec(row["se_lag2"])>0
        assert Decimal(0)<=dec(row["p_lag2"])<=Decimal(1)
        assert Decimal(-1)<=dec(row["raw_corr"])<=Decimal(1)
        relevance[row["instrument"]]={
            "year_adjusted_bivariate_lag2_coefficient":row["b_lag2"],
            "year_adjusted_bivariate_lag2_p":row["p_lag2"],
            "descriptive_nonrejection_at_5_percent":dec(row["p_lag2"])>=Decimal(".05")
        }
    cips=tab(CIPS)
    assert len(cips)==64
    assert {x["variable"] for x in cips}==expected_vars
    assert {x["status"] for x in cips}=={"OK"}
    assert {x["transformation"] for x in cips}=={"level","first_difference"}
    assert {x["type"] for x in cips}=={"drift","trend"}
    assert {x["lags"] for x in cips}=={"1","2"}
    assert all(x["test"]=="CIPS" for x in cips)
    assert len({(x["variable"],x["transformation"],x["type"],x["lags"]) for x in cips})==64
    for x in cips:
        dec(x["statistic"]);p=dec(x["p_value"])
        assert 0<=p<=1
    product_cips={
        f"{x['transformation']}_{x['type']}_lag{x['lags']}":x["p_value"]
        for x in cips if x["variable"]=="ln_Productivity"
    }
    assert len(product_cips)==8
    assert all(dec(product_cips[f"level_{det}_lag{lag}"])>=Decimal(".10")
               for det in ("drift","trend") for lag in (1,2))
    unit=tab(STATA)
    assert len(unit)==16
    expected_set={
        (var,test,determ,str(lag))
        for var in ("ln_Productivity","D_ln_Productivity")
        for test in ("IPS","Fisher")
        for determ in ("drift","trend")
        for lag in (1,2)
    }
    assert {(x["variable"],x["test"],x["deterministic"],x["lag"]) for x in unit}==expected_set
    for x in unit:
        assert x["rc"]=="0",x
        assert x["form"]==("level" if x["variable"]=="ln_Productivity" else "difference")
        p=dec(x["p1"])
        assert Decimal(0)<=p<=Decimal(1),x
        if x["p2"] not in ("", "."): dec(x["p2"])
    txt=LOG.read_text(errors="replace")
    assert "RELEVANCE_TOTAL=8" in txt and "RELEVANCE_FAILURE_COUNT=0" in txt
    assert "UNITROOT_TOTAL_COUNT=16" in txt and "UNITROOT_FAILURE_COUNT=0" in txt
    assert "TWO_SCIENCE_GATES_COMPLETE" in txt
    assert len(re.findall(r"^RELEVANCE_OK",txt,re.M))==8
    assert len(re.findall(r"^UNITROOT_RESULT",txt,re.M))==16
    assert not re.search(r"(?m)^RELEVANCE_FAILED|^UNITROOT_FAILED|^r\(\d+\);",txt)
    recorded={f"{x['form']}_{x['test']}_{x['deterministic']}_lag{x['lag']}":x["p1"] for x in unit}
    verdict={
       "audit_status":"PASS: original 64 real R CIPS tests and 8 plus 16 real Stata diagnostics validated",
       "stata_or_R_executed_in_GitHub_actions":False,
       "source_workbook_sha256":RAW_HASH,
       "original_R_workflow14_artifact_csv_sha256":CIPS_HASH,
       "original_CIPS_rows":64,
       "Stata_lag2_descriptive_instrument_relevance_regressions":8,
       "Stata_productivity_IPS_Fisher_specifications":16,
       "instrument_exogeneity_scientifically_validated":False,
       "System_GMM_models_validated_for_causality":0,
       "lag2_relevance":relevance,
       "CIPS_productivity":product_cips,
       "Stata_unitroot_p_values":recorded,
       "caveats":[
         "CIPS p=.10 or p=.01 can be boundary-truncated, not exact.",
         "IPS and Fisher depend on cross-sectional independence, unlike CIPS.",
         "Bivariate lag2 predictability after year controls does not certify instrument relevance conditional on the full GMM instrument matrix.",
         "None of these tests prove exogeneity, validity of System level moments or cointegration.",
       ]
    }
    out=ROOT/"outputs/professor_science_gates"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest.json").write_text(json.dumps(verdict,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(verdict,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
