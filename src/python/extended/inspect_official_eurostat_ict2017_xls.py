#!/usr/bin/env python3
"""Inspect the independently published Eurostat HS2017 ICT workbook, without guessing codes."""
from pathlib import Path
import hashlib, json, re
from datetime import datetime,timezone
import xlrd

ROOT=Path(__file__).resolve().parents[3]
RAW=ROOT/"outputs/extended/official_ict_hs6_probe/EUROSTAT_HS2017_XLS.xls"
MANIFEST=ROOT/"outputs/extended/official_ict_hs6_probe/SOURCE_ACCESS_PROBE.json"
OUT=ROOT/"evidence/extended/official_eurostat_hs2017_xls_inspection_2026-10-17.json"
def ascode(v):
    if isinstance(v,float) and v.is_integer(): return str(int(v))
    return str(v).strip()
def main():
    m=json.loads(MANIFEST.read_text(encoding="utf-8"))
    e=next(x for x in m["sources"] if x["name"]=="EUROSTAT_HS2017_XLS")
    assert e["status"]=="VALID_SOURCE_BYTES"
    assert hashlib.sha256(RAW.read_bytes()).hexdigest()==e["sha256"]
    wb=xlrd.open_workbook(str(RAW),on_demand=True)
    result=[]
    for sheet in wb.sheets():
        rows=[]
        candidates=[]
        for i in range(sheet.nrows):
            cells=[ascode(sheet.cell_value(i,k)) for k in range(min(sheet.ncols,12))]
            if i<35:rows.append({"row":i+1,"values":cells})
            candidates.extend(v for v in cells if re.fullmatch(r"\d{6}",v))
        result.append({"name":sheet.name,"nrows":sheet.nrows,"ncols":sheet.ncols,
                       "first_35_rows":rows,"six_digit_cell_values_count":len(candidates),
                       "unique_six_digit_cell_values":len(set(candidates)),
                       "first_20_six_digit_codes":candidates[:20]})
        print("EUROSTAT_HS2017_XLS_INSPECT",sheet.name,"rows",sheet.nrows,
              "six_digit_cells",len(candidates),"unique",len(set(candidates)),flush=True)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"source_sha256":e["sha256"],"source_url":e["url"],
        "sheets":result,"no_classification_approved":True,
        "timestamp_utc":datetime.now(timezone.utc).isoformat()},
        ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":main()
