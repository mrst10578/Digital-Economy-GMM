"""Verify archived, *already executed* Stata tablet results. This script DOES NOT run Stata or validate causality."""
from __future__ import annotations

import csv
from decimal import Decimal
import hashlib
import io
import json
import re
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evidence/tablet-stata-2026-10-15"
LEGACY = ROOT / "evidence/stata-2026-10-09/outputs.zip"
RAW = ROOT / "data/raw/Balanced_Panel_Data.xlsx"

def table(value: str) -> list[dict[str, str]]:
    rows = list(csv.DictReader(io.StringIO(value)))
    assert rows and len(rows) == len({x["model"] for x in rows}), "Duplicate or empty model rows"
    return rows

def equal_cell(a: str, b: str) -> bool:
    try:
        return Decimal(a) == Decimal(b)
    except Exception:
        return a == b

def main() -> None:
    history = zipfile.ZipFile(LEGACY).read("outputs/stata/model_status.csv").decode("utf-8-sig")
    old = table(history)
    replica = table((EVIDENCE / "model_status.csv").read_text(encoding="utf-8-sig"))
    assert len(old) == len(replica) == 6
    for a, b in zip(old, replica):
        assert a.keys() == b.keys(), f"Column mismatch: {a['model']}"
        assert all(equal_cell(a[k], b[k]) for k in a), f"Historical mismatch: {a['model']}"
        assert b["status"] == "DIAGNOSTIC_HOLD" and b["rc"] == "0"

    recorded = json.loads((EVIDENCE / "tablet_repro_audit.json").read_text())
    digest = hashlib.sha256(RAW.read_bytes()).hexdigest()
    assert digest == recorded["source_sha256"], "Source workbook changed"
    assert recorded["pretests_ok"] == 16 and recorded["new_models"] == 6
    assert recorded["singular_warnings"] == 6 and recorded["script_completed"]
    assert recorded["all_exactly_matching"] is True and not recorded["differences"]

    stress = table((EVIDENCE / "lag_window_stress.csv").read_text())
    planned = {
        "Growth_DIFF_L2", "Growth_DIFF_L3",
        "ln_Productivity_DIFF_L2", "ln_Productivity_DIFF_L3"
    }
    assert {x["model"] for x in stress} == planned
    for m in stress:
        assert m["rc"] == "0" and m["N"] == "752"
        assert m["Ng"] == "47" and m["instruments"] == "23"
        assert m["sargan_p"] == "" and m["hansen_p"] == "", "Overidentification p unexpectedly present"
        for k in ("ar1_p", "ar2_p", "b_internet"):
            Decimal(m[k])

    stress_log = (EVIDENCE / "lag_window_stress.log").read_text()
    assert stress_log.count("Warning: Two-step estimated covariance matrix of moments is singular.") == 4
    assert stress_log.count("Sargan test of overid. restrictions: chi2(0)") == 4
    assert stress_log.count("Hansen test of overid. restrictions: chi2(0)") == 4
    assert len(re.findall(r"^STRESS_ESTIMATED outcome=", stress_log, re.M)) == 4
    assert "STRESS_TEST_COMPLETE" in stress_log

    cd = table((EVIDENCE / "fe_cd_replication.csv").read_text())
    expected = {
        "Growth_static": (846, 18, 0.0564),
        "Growth_dynamic": (799, 17, 0.00568),
        "ln_Productivity_static": (846, 18, 0.00472),
        "ln_Productivity_dynamic": (799, 17, 0.225),
    }
    assert {x["model"] for x in cd} == set(expected)
    for row in cd:
        n, yrs, prior_p = expected[row["model"]]
        assert int(row["N"]) == n and int(row["years"]) == yrs
        assert int(row["groups"]) == 47
        assert abs(float(row["cd_p"]) - prior_p) < 0.0006, "Disagrees with rounded R plm benchmark"
        for k in ("cd_stat", "cd_p", "b_internet"):
            Decimal(row[k])
    cd_log = (EVIDENCE / "fe_cd_replication.log").read_text()
    assert len(re.findall(r"^CD_ESTIMATED outcome=", cd_log, re.M)) == 4
    assert "CD_TEST_SCRIPT_COMPLETE" in cd_log

    status = {
        "audit_kind": "stored Stata evidence verification, NOT re-execution",
        "historical_models_exactly_reproduced": len(replica),
        "pre_estimation_tests_reported_successful": recorded["pretests_ok"],
        "new_lag_sensitivity_models_executed": len(stress),
        "stress_singular_warnings": 4,
        "lag_sensitivity_overidentification_tests_available": False,
        "two_way_FE_residual_CD_reproductions": len(cd),
        "scientifically_accepted_causal_models": 0,
        "raw_workbook_sha256": digest,
        "result": "PASS: archived evidence is internally consistent; causal identification still UNVALIDATED",
    }
    out = ROOT / "outputs/tablet_audit"
    out.mkdir(parents=True, exist_ok=True)
    (out / "latest.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(status, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
