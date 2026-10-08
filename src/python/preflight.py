"""Data-only schema audit. No GMM estimation is attempted by this module."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

def audit_dataframe(df: pd.DataFrame, cfg: dict) -> dict:
    cols = cfg["required_columns"]
    missing_columns = [c for c in cols if c not in df.columns]
    result = {"status": "invalid" if missing_columns else "ready_for_methodology_audit",
              "required_columns_missing": missing_columns, "rows": int(len(df))}
    if missing_columns:
        return result
    result["nulls"] = int(df[cols].isna().sum().sum())
    result["duplicate_keys"] = int(df.duplicated(["ISO3", "Year"]).sum())
    result["countries"] = int(df["ISO3"].nunique(dropna=True))
    result["years"] = sorted(int(y) for y in df["Year"].dropna().unique())
    counts = df.groupby("ISO3")["Year"].nunique()
    result["balanced"] = bool(counts.nunique() == 1 and int(counts.iloc[0]) == len(result["years"])) if len(counts) else False
    result["matches_initial_expectations"] = (
        result["countries"] == cfg["initial_expected_countries"]
        and len(df) == cfg["initial_expected_rows"]
        and result["years"] == list(range(cfg["initial_year_min"], cfg["initial_year_max"] + 1))
    )
    if result["nulls"] or result["duplicate_keys"]:
        result["status"] = "invalid"
    return result

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", default=str(ROOT / "data" / "raw"))
    p.add_argument("--out-dir", default=str(ROOT / "outputs"))
    p.add_argument("--allow-missing", action="store_true")
    a = p.parse_args()
    cfg = json.loads((ROOT / "config" / "project.json").read_text(encoding="utf-8"))
    path = Path(a.data_dir) / cfg["source_workbook"]
    output = Path(a.out_dir)
    output.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        result = {"status": "waiting_for_source_files", "source_workbook": cfg["source_workbook"],
                  "note": "No original source data were used. No statistical results exist."}
        (output / "preflight_status.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0 if a.allow_missing else 2
    try:
        df = pd.read_excel(path, engine="openpyxl")
        result = audit_dataframe(df, cfg)
        result["source_workbook"] = cfg["source_workbook"]
    except Exception as exc:
        result = {"status": "failed_to_read_source", "error": str(exc)}
    (output / "preflight_status.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "ready_for_methodology_audit" else 3

if __name__ == "__main__":
    raise SystemExit(main())
