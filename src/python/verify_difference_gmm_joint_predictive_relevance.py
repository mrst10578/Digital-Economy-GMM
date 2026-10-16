"""Reproduce original Excel -> joint lag2/lag3 instrument prediction result in CI.

This is a reproducibility test of observed held-out predictive R2, NOT a formal
weak-instrument, Hansen or exclusion restriction test. In particular a passing
build must never be displayed as "causal model accepted".
"""
from __future__ import annotations
import contextlib
import csv
from decimal import Decimal
import io
from pathlib import Path

from src.python import audit_difference_gmm_joint_predictive_relevance as run

ROOT=Path(__file__).resolve().parents[2]
ARCHIVED=ROOT/"evidence/scientific-gates-2026-10-16/diff_gmm_joint_lag2_3_47_country_oos_predictive.csv"
EXPECTED_COLUMNS=(
    "outcome",
    "differenced_endogenous_regressor",
    "full_sample_complete_case_rows",
    "country_holdout_folds",
    "lagged_instrument_columns",
    "within_year_in_sample_R2",
    "leave_one_country_out_predictive_R2",
    "oos_baseline_SSE",
    "oos_instrument_SSE",
    "instrument_assumptions_validated",
    "formal_GMM_weak_IV_test",
)
EXPECTED={f"{outcome}:{v}" for outcome in ("Growth","ln_Productivity")
          for v in (f"D.L.{outcome}", "D.Internet","D.Broadband","D.ICT_Exports",
                    "D.Unemployment","D.Inflation","D.RnD")}

def csv_rows(path:Path):
    with path.open(newline="",encoding="utf-8-sig") as f:
        rd=csv.DictReader(f)
        assert tuple(rd.fieldnames or ())==EXPECTED_COLUMNS,rd.fieldnames
        rows=list(rd)
    assert len(rows)==14
    mapping={(r["outcome"]+":"+r["differenced_endogenous_regressor"]):r for r in rows}
    assert set(mapping)==EXPECTED
    for r in rows:
        assert (r["full_sample_complete_case_rows"],r["country_holdout_folds"],
                r["lagged_instrument_columns"])==("705","47","14")
        assert (r["instrument_assumptions_validated"],r["formal_GMM_weak_IV_test"])==("NO","NO")
        for c in ("within_year_in_sample_R2","leave_one_country_out_predictive_R2",
                  "oos_baseline_SSE","oos_instrument_SSE"):
            assert Decimal(r[c]).is_finite(), (r,c)
        assert Decimal(r["oos_baseline_SSE"])>0
        # These are exact arithmetic identity checks, not interpretation claims.
        calc=1-Decimal(r["oos_instrument_SSE"])/Decimal(r["oos_baseline_SSE"])
        assert abs(calc-Decimal(r["leave_one_country_out_predictive_R2"]))<Decimal(".00000002")
    return mapping

def main():
    existing=csv_rows(ARCHIVED)
    with contextlib.redirect_stdout(io.StringIO()) as capture:
        run.main()
    log=capture.getvalue()
    assert "PREDICTIVE_AUDIT_PASS" in log
    assert "CAUSAL_MODELS_VALIDATED=0" in log
    regenerated=csv_rows(run.OUT/"complete_instrument_predictive_relevance.csv")
    assert regenerated.keys()==existing.keys()
    for key,orig in existing.items():
        new=regenerated[key]
        for k in EXPECTED_COLUMNS:
            if k in ("within_year_in_sample_R2","leave_one_country_out_predictive_R2",
                     "oos_baseline_SSE","oos_instrument_SSE"):
                assert abs(Decimal(orig[k])-Decimal(new[k]))<Decimal(".00000001"),(key,k,orig[k],new[k])
            else:
                assert orig[k]==new[k],(key,k,orig[k],new[k])
    # These are documented observations, NOT pass/fail model acceptance criteria.
    prod=regenerated["ln_Productivity:D.L.ln_Productivity"]
    growth=regenerated["Growth:D.L.Growth"]
    print("REPRODUCIBILITY_PASS 14 rows, 47 country holdouts, 14 lag2+lag3 candidates")
    print("GROWTH_DYNAMIC_HELDOUT_R2",growth["leave_one_country_out_predictive_R2"])
    print("PRODUCTIVITY_DYNAMIC_HELDOUT_R2",prod["leave_one_country_out_predictive_R2"])
    print("IS_FORMAL_WEAK_GMM_TEST=NO; IS_CAUSAL_EXOGENEITY_PROVEN=NO")

if __name__=="__main__":
    main()
