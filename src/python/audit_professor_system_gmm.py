"""Verify the archived original two System-GMM professor models and one-step sensitivity.

Real Stata runs on the authorized tablet; this CI audits saved artifacts only.
Numerically successful estimation is NOT scientific acceptance or identification.
"""
from __future__ import annotations

import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
EVID = ROOT / "evidence/tablet-stata-2026-10-16"
DATA = ROOT / "data/raw/Balanced_Panel_Data.xlsx"
OLD = EVID / "model_status.csv"
NEW = EVID / "professor_system_gmm_stats.csv"
LOG = EVID / "professor_system_gmm_native_stata.log"
DO = ROOT / "stata/tablet_diagnostics/11_professor_system_gmm_two_equations.do"
EXPECT_HASH = "474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b"
VARS = ("Growth", "ln_Productivity")
METHODS = ("twostep", "onestep")
KEYS = ("N", "Ng", "instruments", "sargan_p", "hansen_p", "ar1_p", "ar2_p")

def read_rows(p: Path) -> list[dict[str, str]]:
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))

def D(val: str) -> Decimal:
    value = Decimal(val)
    assert value.is_finite(), f"Missing or nonfinite estimation statistic: {val}"
    return value

def main() -> None:
    assert hashlib.sha256(DATA.read_bytes()).hexdigest() == EXPECT_HASH
    new = read_rows(NEW)
    old = {r["model"]: r for r in read_rows(OLD)}
    assert len(new) == 4
    assert {(r["outcome"], r["method"]) for r in new} == {
        (outcome, method) for outcome in VARS for method in METHODS
    }
    saved_script = DO.read_text(encoding="utf-8")
    assert "twostep robust small artests(2)" in saved_script
    assert "lag(2 2) collapse split" in saved_script
    assert 'gmmstyle(Internet Broadband ICT_Exports RnD, lag(2 2) collapse)' in saved_script
    assert 'gmmstyle(Unemployment Inflation, lag(2 2) collapse)' in saved_script
    assert 'ivstyle($digital_year_dummies_sys)' in saved_script
    # The two two-step commands must exactly match the project's original
    # growth and productivity System-GMM specifications (model L2 only).
    for filename, dependent in (
        ("stata/03_growth_models.do", "Growth"),
        ("stata/04_productivity_models.do", "ln_Productivity"),
    ):
        source = (ROOT / filename).read_text(encoding="utf-8")
        candidates = [
            line.strip() for line in source.splitlines()
            if line.lstrip().startswith("capture noisily xtabond2 ")
            and "twostep robust small artests(2)" in line
        ]
        assert len(candidates) == 2, f"System specification count changed: {filename}"
        normalized = candidates[0].replace(dependent, "`y'")
        assert normalized in saved_script, f"Original model changed: {filename}"

    log = LOG.read_text(errors="replace")
    markers = re.findall(r"^PROFESSOR_OK outcome=(\w+) method=(\w+) N=(\d+) instruments=(\d+)", log, re.M)
    assert len(markers) == 4, "Incomplete real Stata run"
    assert {(x[0], x[1]) for x in markers} == {(x["outcome"], x["method"]) for x in new}
    assert "PROFESSOR_FAILED_COUNT=0" in log and "PROFESSOR_TOTAL_MODELS=4" in log
    assert "PROFESSOR_GMM_RUN_COMPLETED" in log
    assert not re.search(r"(?im)^Warning:|^PROFESSOR_FAILED outcome=|dropped due to collinearity|covariance matrix of moments is singular|^r\(\d+\);", log)

    for r in new:
        assert r["rc"] == "0"
        assert (int(r["N"]), int(r["Ng"]), int(r["instruments"])) == (799, 47, 31)
        for k in ("b_lag", "se_lag", "b_internet", "se_internet", "p_internet", 
                  "b_broadband", "se_broadband", "b_ict", "se_ict", "sargan_p",
                  "hansen_p", "ar1_p", "ar2_p", "diffh_dep_level_p", "diffh_ctrl_p"):
            D(r[k])
        assert D(r["se_lag"]) > 0 and D(r["se_internet"]) > 0
        for key in ("p_internet", "sargan_p", "hansen_p", "ar1_p", "ar2_p", 
                    "diffh_dep_level_p", "diffh_ctrl_p"):
            assert 0 <= D(r[key]) <= 1, (r["outcome"], r["method"], key)
        if r["method"] == "twostep":
            model = "GROWTH_SYS_L22" if r["outcome"] == "Growth" else "PROD_SYS_L22"
            for k in KEYS:
                a, b = D(r[k]), D(old[model][k])
                tol = Decimal(0) if k in ("N", "Ng", "instruments") else Decimal("0.000001")
                assert abs(a-b) <= tol, (model, k, str(a), str(b))

    rows = {(r["outcome"], r["method"]): r for r in new}
    growth = rows["Growth", "twostep"]
    productivity = rows["ln_Productivity", "twostep"]
    assert D(growth["sargan_p"]) < Decimal("0.05")
    assert D(growth["ar1_p"]) >= Decimal("0.05")
    assert D(productivity["hansen_p"]) < Decimal("0.05")
    assert D(productivity["diffh_dep_level_p"]) < Decimal("0.05")
    assert D(productivity["diffh_ctrl_p"]) < Decimal("0.05")
    assert all(D(r["p_internet"]) > Decimal(".05") for r in new)
    assert D(rows["Growth", "onestep"]["ar1_p"]) < Decimal(".05")

    result = {
        "audit": "PASS: full real Stata professor primary models and one-step sensitivity reproduced",
        "stata_executed_in_CI": False,
        "original_file_unchanged_sha256": EXPECT_HASH,
        "actual_system_gmm_estimations": 4,
        "primary_twostep_equations": 2,
        "onestep_robustness_estimations": 2,
        "technical_warnings": 0,
        "numerical_disagreements_from_previously_corrected_output": 0,
        "growth_twostep": {k: growth[k] for k in ("b_internet", "p_internet", "sargan_p", "hansen_p", "ar1_p", "ar2_p", "diffh_dep_level_p")},
        "productivity_twostep": {k: productivity[k] for k in ("b_lag", "b_internet", "p_internet", "sargan_p", "hansen_p", "ar1_p", "ar2_p", "diffh_dep_level_p", "diffh_ctrl_p")},
        "final_scientific_verdict": "DIAGNOSTIC_HOLD: zero causally accepted models",
        "warning": "Passing archived computations or not rejecting Hansen does not prove moment exogeneity."
    }
    output = ROOT / "outputs/professor_system_gmm_audit"
    output.mkdir(parents=True, exist_ok=True)
    (output / "latest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
