"""Audit Stata's prespecified *alternative estimand* of productivity growth.
Does not run Stata and does not equate nonrejection with valid causal moments.
"""
from __future__ import annotations
import csv, hashlib, json, re
from decimal import Decimal
from pathlib import Path

R=Path(__file__).resolve().parents[2]
E=R/"evidence/scientific-gates-2026-10-16"
D=R/"data/raw/Balanced_Panel_Data.xlsx"
DO=R/"stata/tablet_diagnostics/20_productivity_growth_theory_led_candidate.do"
CSV=E/"theory_led_productivity_growth_system_gmm_stats.csv"
LOG=E/"theory_led_productivity_growth_system_gmm_real_stata.log"
RAW_SHA="474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b"

def decimal(s:str)->Decimal:
    v=Decimal(s)
    assert v.is_finite(),s
    return v

def main()->None:
    assert hashlib.sha256(D.read_bytes()).hexdigest()==RAW_SHA,"Original data altered"
    code=DO.read_text(encoding="utf-8")
    for fragment in ("generate double Productivity_Growth = D.ln_Productivity",
            "generate double d_`v' = D.`v'",
            "lag(2 2) collapse split",
            "gmmstyle(d_Internet d_Broadband d_ICT_Exports d_RnD, lag(2 2) collapse)",
            "gmmstyle(d_Unemployment d_Inflation, lag(2 2) collapse)",
            "twostep robust small artests(2)",
            "ALTERNATIVE_COMPLETED"):
        assert fragment in code,fragment
    with CSV.open(newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
    assert len(rows)==2
    assert {r["method"] for r in rows}=={"twostep","onestep"}
    s=LOG.read_text(errors="replace")
    assert len(re.findall(r"^ALTERNATIVE_OK method=",s,re.M))==2
    assert "ALTERNATIVE_FAILED_COUNT=0" in s
    assert "ALTERNATIVE_TOTAL_COUNT=2" in s
    assert "ALTERNATIVE_COMPLETED: new research estimand" in s
    assert not re.search(r"(?im)^\s*Warning:|^ALTERNATIVE_FAILED method=|^r\(\d+\);|covariance matrix of moments is singular",s)
    metrics={}
    for r in rows:
        assert r["rc"]=="0"
        assert (int(r["N"]),int(r["Ng"]),int(r["instruments"]))==(752,47,30)
        for c in ("b_lag","se_lag","b_internet","se_internet","internet_p",
                  "hansen_p","sargan_p","ar1_p","ar2_p","diffh_dep_level_p","diffh_controls_p"):
            decimal(r[c])
        for c in ("internet_p","hansen_p","sargan_p","ar1_p","ar2_p","diffh_dep_level_p","diffh_controls_p"):
            assert 0 <= decimal(r[c]) <= 1
        assert decimal(r["se_lag"])>0 and decimal(r["se_internet"])>0
        assert decimal(r["internet_p"])>Decimal(".05")
        assert decimal(r["sargan_p"])<Decimal(".05"),"Sargan rejection must not be concealed"
        assert decimal(r["hansen_p"])>Decimal(".05")
        metrics[r["method"]]={k:r[k] for k in (
            "b_lag","b_internet","internet_p","hansen_p","sargan_p",
            "ar1_p","ar2_p","diffh_dep_level_p","diffh_controls_p")}
    assert decimal(metrics["twostep"]["ar1_p"]) > Decimal(".05")
    assert decimal(metrics["onestep"]["ar1_p"]) < Decimal(".05")
    assert decimal(metrics["twostep"]["diffh_dep_level_p"]) > Decimal(".05")
    results={
        "audit":"PASS: 2 real Stata alternative product-growth regressions independently validated",
        "ci_runs_stata":False,
        "source_workbook_sha256":RAW_SHA,
        "original_professor_model_untouched":True,
        "new_dependent_variable":"D.ln_Productivity",
        "new_regressor_transform":"D.x for all six explanatory variables",
        "scientific_status":"DIAGNOSTIC_HOLD not a validated causal model",
        "reestimates_without_execution_errors":2,
        "alternative_estimand_cannot_replace_professor_original_without_methodology_decision":True,
        "models":metrics,
        "explicit_cautions":[
           "Both Sargan tests reject at 5%, and the main two-step AR1 does not reject.",
           "The same Hansen p in one-step/two-step is from the same instrument moments; not independent confirmation.",
           "A non-rejected Difference-in-Hansen group does not prove exogeneity or non-weak instruments.",
           "Productivity growth differs from the original professor level log productivity outcome.",
           "No direct cross-border technology-spillover variable has been validated."
        ]
    }
    folder=R/"outputs/professor_theory_alternative_audit"
    folder.mkdir(parents=True,exist_ok=True)
    (folder/"latest.json").write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(results,ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
