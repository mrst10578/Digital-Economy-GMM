"""Synthetic-input tests: do not substitute these for real research findings."""
import json
from pathlib import Path
import pandas as pd
from src.python.preflight import audit_dataframe, ROOT

def config():
    return json.loads((ROOT / "config" / "project.json").read_text(encoding="utf-8"))

def test_project_isolation_and_schema():
    c = config()
    assert c["scope"] in ("digital", "ai")
    assert c["repository"] == ("Digital-Economy-GMM" if c["scope"] == "digital" else "AI-Innovation-GMM")
    assert c["source_workbook"].endswith(".xlsx")
    assert {"ISO3", "Year"} <= set(c["required_columns"])

def test_audit_detects_duplicate_panel_keys():
    c = config()
    row = {key: 1.0 for key in c["required_columns"]}
    row.update(ISO3="AAA", Year=2020)
    result = audit_dataframe(pd.DataFrame([row,row]), c)
    assert result["duplicate_keys"] == 1
    assert result["status"] == "invalid"

def test_audit_distinguishes_data_from_model():
    c = config()
    row1 = {key: 1.0 for key in c["required_columns"]}
    row1.update(ISO3="AAA", Year=2020)
    row2 = dict(row1, Year=2021)
    result = audit_dataframe(pd.DataFrame([row1,row2]), c)
    assert result["status"] == "ready_for_methodology_audit"
    assert result["balanced"] is True
    assert result["matches_initial_expectations"] is False

def test_private_data_are_not_versioned():
    root = Path(__file__).resolve().parents[1]
    ignore = (root / ".gitignore").read_text(encoding="utf-8")
    assert "data/raw" in ignore
    assert "outputs/" in ignore
