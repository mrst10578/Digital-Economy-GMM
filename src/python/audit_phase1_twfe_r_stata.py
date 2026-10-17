"""Independent Phase-1 TWFE: verify actual Stata and R evidence from one historical workbook.

Non-causal descriptive robustness, not a validity test for System GMM.
Usage: python -m src.python.audit_phase1_twfe_r_stata
"""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/"evidence/phase1-robust-2026-10-17"
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
EXPECTED="474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b"

def rows(filename):
    with (E/filename).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def verify():
    assert hashlib.sha256(RAW.read_bytes()).hexdigest()==EXPECTED
    stata=rows("twfe_stata_country_cluster.csv")
    r=rows("twfe_r_dk_coefficients.csv")
    summary=rows("twfe_r_diagnostics.csv")
    assert len(stata)==len(r)==18 and len(summary)==3
    model_sizes={"Growth":846,"ln_Productivity":846,"D_ln_Productivity":799}
    terms={"Growth":["Internet","Broadband","ICT_Exports","Unemployment","Inflation","RnD"],
           "ln_Productivity":["Internet","Broadband","ICT_Exports","Unemployment","Inflation","RnD"],
           "D_ln_Productivity":["D_Internet","D_Broadband","D_ICT_Exports","D_Unemployment","D_Inflation","D_RnD"]}
    expected={(m,t) for m,v in terms.items() for t in v}
    ai={(x["model"],x["term"]):x for x in stata}
    bi={(x["model"],x["term"]):x for x in r}
    assert set(ai)==set(bi)==expected
    assert set(s["model"] for s in summary)==set(model_sizes)
    max_delta=0.
    sample_factors=[]
    for key in expected:
        x,y=ai[key],bi[key]
        assert x["rc"]=="0" and int(x["Ng"])==47
        assert int(x["N"])==model_sizes[x["model"]]
        diff=abs(float(x["b"])-float(y["b"]))
        max_delta=max(max_delta,diff)
        assert diff<1e-7, ("coefficient mismatch",key,diff)
        ratio=float(x["se"])/float(y["se_cluster"])
        assert 1.015<ratio<1.030, ("finite-sample covariance correction outside expected range",key,ratio)
        sample_factors.append(ratio)
        # Country-cluster statistical conclusions use distinct Stata/R small-sample factors.
        assert (float(x["p"])<0.05)==(float(y["p_cluster"])<0.05),key
        for col in ("se_dk_lag1","se_dk_lag2","se_dk_lag3"):
            assert float(y[col])>0,key
    assert max(sample_factors)-min(sample_factors)<0.0001
    for s in summary:
        assert int(s["N"])==model_sizes[s["model"]]
        assert int(s["countries"])==47
        assert int(s["source_start"])==2005 and int(s["source_end"])==2022
        assert 0<=float(s["residual_cd_p"])<=1
    log=(E/"twfe_stata_real.log").read_text(errors="replace")
    assert "TWFE_FAIL_COUNT=0" in log and "TWFE_TOTAL_TERM_ROWS=18" in log
    assert "TWFE_REESTIMATION_COMPLETED_NO_CAUSAL_CLAIM" in log
    script=(ROOT/"src/r/phase1_robust_twfe_same_data.R").read_text()
    assert 'data/raw/Balanced_Panel_Data.xlsx' in script and 'model="within"' in script
    assert 'effect="twoways"' in script and "vcovSCC" in script
    result={"status":"PASS","source_sha256":EXPECTED,
            "models_checked":3,"coefficient_rows_checked":18,
            "max_absolute_r_vs_stata_coefficient_delta":max_delta,
            "stata_vs_r_cluster_se_factor_min":min(sample_factors),
            "stata_vs_r_cluster_se_factor_max":max(sample_factors),
            "correction_explanation":"Stata and plm use different finite-sample country-cluster multipliers; coefficient identities are exact within CSV display precision",
            "causal_identification":"NOT_ESTABLISHED",
            "productivity_system_gmm_hansen_invalidity":"NOT_REPAIRED"}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result

if __name__=="__main__":
    verify()
