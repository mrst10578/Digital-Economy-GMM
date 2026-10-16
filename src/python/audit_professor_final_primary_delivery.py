"""Verify professor-ready FINAL primary System GMM coefficient/diagnostic tables.

Integrity and arithmetic verification of original native Stata .ster table export.
Scientific-interpretation gate is deliberately strict: no causal claims supported.
CI verifies saved outputs; it does not re-run Stata or R.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NEW = ROOT / "evidence/scientific-gates-2026-10-16"
OLD = ROOT / "evidence/tablet-stata-2026-10-16"
COEF = NEW / "professor_two_primary_system_gmm_full_coefficients.csv"
LOG = NEW / "professor_full_coefficient_export_real_stata.log"
CODE = ROOT / "stata/tablet_diagnostics/19_professor_final_coefficient_export.do"
RAW = ROOT / "data/raw/Balanced_Panel_Data.xlsx"
RAW_SHA = "474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b"
OUTCOMES = ("Growth", "ln_Productivity")
DIGITAL = ("Internet", "Broadband", "ICT_Exports")
CONTROLS = ("Unemployment", "Inflation", "RnD")
T_CRIT = Decimal("2.012895598919427")  # Stata t_(47-1), two-sided 95%

def rows(p: Path) -> list[dict[str, str]]:
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))

def d(x: str) -> Decimal:
    v = Decimal(x)
    assert v.is_finite(), f"Invalid coefficient or p-value: {x}"
    return v

def closish(a: str, b: str, eps=Decimal(".000001")) -> None:
    assert abs(d(a) - d(b)) <= eps, (a, b)

def main() -> None:
    assert hashlib.sha256(RAW.read_bytes()).hexdigest() == RAW_SHA
    script = CODE.read_text(encoding="utf-8")
    assert "estimates use" in script and "twostep.ster" in script
    assert "invttail" in script and "FINAL_FULL_TABLE_ROWS" in script
    lg = LOG.read_text(errors="replace")
    assert len(re.findall(r"^FINAL_COEFFICIENT_OK outcome=", lg, re.M)) == 14
    assert len(re.findall(r"^FINAL_STER_LOADED outcome=", lg, re.M)) == 2
    assert "FINAL_FULL_TABLE_ROWS=14" in lg
    assert "FINAL_FULL_COEFFICIENT_EXPORT_COMPLETED" in lg
    assert not re.search(r"(?im)^\s*Warning:|^FINAL_STER_LOAD_FAILED|^FINAL_COEFFICIENT_ERROR|^r\(\d+\);", lg)

    tbl = rows(COEF)
    assert len(tbl) == 14, "Two complete original model tables each with 7 terms required"
    assert len({(r["outcome"], r["term"]) for r in tbl}) == 14
    expected = {(out, term) for out in OUTCOMES
                for term in (f"L.{out}", *DIGITAL, *CONTROLS)}
    assert {(r["outcome"], r["term"]) for r in tbl} == expected
    status = {r["outcome"]: r for r in rows(OLD / "professor_system_gmm_stats.csv")
              if r["method"] == "twostep"}
    joint = {r["outcome"]: r for r in rows(OLD / "professor_joint_restrictions.csv")}
    assert set(status) == set(joint) == set(OUTCOMES)

    by_key: dict[tuple[str, str], dict[str, str]] = {}
    for r in tbl:
        assert (int(r["N"]), int(r["countries"]), int(r["instruments"])) == (799,47,31)
        for key in ("estimate","robust_se","t_stat","p_value","ci95_low","ci95_high"):
            d(r[key])
        assert d(r["robust_se"]) > 0
        assert Decimal(0) <= d(r["p_value"]) <= Decimal(1)
        assert d(r["ci95_low"]) <= d(r["estimate"]) <= d(r["ci95_high"])
        assert abs(d(r["estimate"])/d(r["robust_se"]) - d(r["t_stat"])) <= Decimal(".000005")
        assert abs(d(r["estimate"])-T_CRIT*d(r["robust_se"])-d(r["ci95_low"])) < Decimal(".000005")
        assert abs(d(r["estimate"])+T_CRIT*d(r["robust_se"])-d(r["ci95_high"])) < Decimal(".000005")
        by_key[r["outcome"],r["term"]] = r

    for out in OUTCOMES:
        model = status[out]
        assert model["rc"] == "0"
        for variable, cstem in (
            (f"L.{out}", "lag"),
            ("Internet", "internet"),
            ("Broadband", "broadband"),
            ("ICT_Exports", "ict"),
        ):
            row = by_key[out, variable]
            closish(row["estimate"], model["b_" + cstem])
            closish(row["robust_se"], model["se_" + cstem])
        closish(by_key[out, "Internet"]["p_value"], model["p_internet"])
        closish(joint[out]["lag_coef"],model["b_lag"])
        closish(joint[out]["hansen_p"],model["hansen_p"])
        assert d(joint[out]["joint_p"]) >= Decimal(".05")
        assert all(d(by_key[out, v]["p_value"]) >= Decimal(".05") for v in DIGITAL)
        assert all(d(by_key[out, v]["ci95_low"]) < 0 < d(by_key[out, v]["ci95_high"]) for v in DIGITAL)
    assert d(by_key["Growth", "Unemployment"]["p_value"]) < Decimal(".05")
    assert d(status["Growth"]["ar1_p"]) > Decimal(".05")
    assert d(status["ln_Productivity"]["hansen_p"]) < Decimal(".05")
    assert d(status["ln_Productivity"]["diffh_dep_level_p"]) < Decimal(".05")
    assert d(joint["ln_Productivity"]["persistence_p"]) > Decimal(".05")

    verdict = {
        "audit": "PASS: 14 true Stata original model coefficients and 95% CIs vs original saved model status",
        "stata_executed_in_CI": False,
        "original_workbook_sha256": RAW_SHA,
        "professor_original_twostep_System_GMM_models": 2,
        "full_coefficient_rows": len(tbl),
        "observations_per_original_model": 799,
        "countries": 47,
        "instruments_per_model": 31,
        "joint_digital_p": {out:joint[out]["joint_p"] for out in OUTCOMES},
        "individual_digital_5pct_significant": False,
        "growth_unemployment_nominal_p": by_key["Growth", "Unemployment"]["p_value"],
        "growth_unemployment_conditional_not_causal": True,
        "productivity_rho": by_key["ln_Productivity","L.ln_Productivity"]["estimate"],
        "productivity_rho_equal_one_wald_p": joint["ln_Productivity"]["persistence_p"],
        "growth_weak_ar1_pattern_p": status["Growth"]["ar1_p"],
        "productivity_hansen_rejected_p": status["ln_Productivity"]["hansen_p"],
        "productivity_dependency_level_diff_hansen_rejected_p": status["ln_Productivity"]["diffh_dep_level_p"],
        "scientifically_validated_causal_System_GMM_models": 0,
        "conclusion": "TECHNICAL DELIVERY COMPLETE; METHOD/CAUSAL ACCEPTANCE ON HOLD; original unmodified."
    }
    dest=ROOT/"outputs/professor_final_primary_audit"
    dest.mkdir(parents=True,exist_ok=True)
    (dest/"latest.json").write_text(json.dumps(verdict,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(verdict,ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
