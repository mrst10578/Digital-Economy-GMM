"""Convert audited Excel panel into a real Stata .dta file (requires source workbook)."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
def main():
    cfg = json.loads((ROOT / "config" / "project.json").read_text(encoding="utf-8"))
    source = ROOT / "data" / "raw" / cfg["source_workbook"]
    if not source.exists():
        raise SystemExit(f"Source workbook unavailable: {source}; nothing converted.")
    df = pd.read_excel(source, engine="openpyxl")
    missing = set(cfg["required_columns"]) - set(df.columns)
    if missing:
        raise SystemExit(f"Missing required variables: {sorted(missing)}")
    if df.duplicated(["ISO3","Year"]).any():
        raise SystemExit("Duplicate ISO3/Year keys; stop before Stata conversion.")
    target = ROOT / "data" / "processed" / "stata_ready.dta"
    target.parent.mkdir(parents=True, exist_ok=True)
    df.to_stata(target, write_index=False, version=118)
    roundtrip = pd.read_stata(target)
    if len(roundtrip) != len(df):
        raise SystemExit("Row count changed during .dta conversion.")
    print(f"Converted {len(df)} rows to {target}; this is NOT a fitted model.")
if __name__ == "__main__":
    main()
