"""Deterministically verify the 2026-10-15 current-WDI comparison snapshot."""
from __future__ import annotations
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import openpyxl

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
EVIDENCE=ROOT/"evidence/tablet-stata-2026-10-15"
EXPECTED={"ICT_Exports":("BX.GSR.CCIS.ZS",32),
          "Inflation":("FP.CPI.TOTL.ZG",130)}
def main():
    workbook=openpyxl.load_workbook(RAW,read_only=True,data_only=True)
    rows=list(workbook.active.values)
    columns=list(rows[0])
    source={(r[columns.index("ISO3")],int(r[columns.index("Year")])):r
            for r in rows[1:] if r[columns.index("ISO3")]}
    assert len(source)==846, "Raw workbook keys changed"
    data=list(csv.DictReader((EVIDENCE/"wdi_revision_cells.csv").open(encoding="utf-8")))
    assert len(data)==162
    assert len({(r["column"],r["ISO3"],r["Year"]) for r in data})==162
    counts=Counter(r["column"] for r in data)
    for col,(indicator,n) in EXPECTED.items():
        assert counts[col]==n
    for r in data:
        col=r["column"]
        assert col in EXPECTED and r["indicator"]==EXPECTED[col][0]
        original=float(source[(r["ISO3"],int(r["Year"]))][columns.index(col)])
        old=float(r["original"])
        current=float(r["current_WDI"])
        delta=float(r["delta"])
        assert math.isclose(original,old,rel_tol=1e-13,abs_tol=1e-12)
        assert math.isclose(current-old,delta,rel_tol=1e-10,abs_tol=1e-10)
        assert abs(current-old)>max(1e-4,abs(current)*1e-5)
        assert math.isfinite(current)
    audit=json.loads((EVIDENCE/"wdi_oct15_source_audit.json").read_text())
    summary=json.loads((EVIDENCE/"wdi_revision_summary.json").read_text())
    sha=hashlib.sha256(RAW.read_bytes()).hexdigest()
    assert sha==audit["source_sha256"]==summary["source_sha256"]
    assert not audit["structural_errors"] and not audit["domain_violations"]
    refs=audit["wdi_current_comparison"]
    assert len(refs)==8 and all(x["verified"] for x in refs.values())
    assert sum(x["matched"] for x in refs.values())==6606
    assert sum(x["different"] for x in refs.values())==162
    assert sum(x["missing_in_current_WDI"] for x in refs.values())==0
    assert summary["changed_cell_count"]==162 and summary["by_column"]==dict(counts)
    print("SOURCE_SNAPSHOT_AUDIT_PASS",json.dumps({
        "source_sha256":sha,"workbook_observations":len(source),
        "current_WDI_source_comparisons":6768,"unchanged":6606,
        "revisions_2026_10_15":dict(counts),"original_source_mutated":False,
        "note":"Checks archived source comparison, not a new live download or causal validity"}))
if __name__=="__main__":
    main()
