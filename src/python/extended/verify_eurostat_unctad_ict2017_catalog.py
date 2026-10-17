#!/usr/bin/env python3
"""Crosscheck all 92 HS2017 ICT product codes against independent Eurostat annex.

Compares official UNCTAD 2025/2026 source PDF-derived code list and Eurostat
2025 XLS annex, including category IDs. If mismatch, stop rather than
silently add phantom 93rd product from a generic website description.
"""
from __future__ import annotations
import csv, hashlib, json, re
from collections import Counter
from pathlib import Path
import xlrd

ROOT=Path(__file__).resolve().parents[3]
UNCTAD=ROOT/"data/extended/official_ict_hs6/unctad_ict_goods_official_hs6_2002_2007_2012_2017_2022.csv"
EURO=ROOT/"outputs/extended/official_ict_hs6_probe/EUROSTAT_HS2017_XLS.xls"
MANIFEST=ROOT/"outputs/extended/official_ict_hs6_probe/SOURCE_ACCESS_PROBE.json"
OUT=ROOT/"data/extended/official_ict_hs6/HS2017_UNCTAD_EUROSTAT_INDEPENDENT_MATCH.json"

def string(v):
    return str(int(v)) if isinstance(v,float) and v.is_integer() else str(v).strip()

def main():
    official=json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected=next(x for x in official["sources"] if x["name"]=="EUROSTAT_HS2017_XLS")
    assert hashlib.sha256(EURO.read_bytes()).hexdigest()==expected["sha256"]
    with UNCTAD.open(encoding="utf-8",newline="") as fp:
        unctad={r["HS6"]:r for r in csv.DictReader(fp)
                if r["HS_edition"]=="HS2017"}
    assert len(unctad)==92
    book=xlrd.open_workbook(str(EURO),on_demand=True)
    sheet=book.sheet_by_index(0)
    active=""
    codes={}
    for idx in range(sheet.nrows):
        code=string(sheet.cell_value(idx,2)).strip()
        desc=string(sheet.cell_value(idx,3)).strip()
        if re.fullmatch("ICT0[1-5]",code):
            active=code
        if re.fullmatch(r"\d{6}",code):
            assert active, f"Unassigned Eurostat code at row {idx+1}"
            assert code not in codes, f"Duplicate Eurostat HS2017 code {code}"
            assert desc, f"No label for Eurostat {code}"
            codes[code]={"group":active,"description":desc,"row":idx+1}
    assert len(codes)==92, f"Eurostat data contains {len(codes)} codes, expected 92"
    missing_in_pdf=sorted(set(codes)-set(unctad))
    missing_in_xls=sorted(set(unctad)-set(codes))
    category_drift=[c for c in sorted(set(codes)&set(unctad))
        if codes[c]["group"]!=unctad[c]["ICT_group"]]
    if missing_in_pdf or missing_in_xls or category_drift:
        raise ValueError("Independent sources disagree on HS2017 code or category")
    result={
        "phase":"EXTENDED_DATA_EXPERIMENTAL",
        "UNCTAD_pdf_code_rows":len(unctad),
        "Eurostat_XLS_code_rows":len(codes),
        "all_codes_and_ICT01_through_ICT05_categories_match":True,
        "missing_in_UNCTAD":missing_in_pdf,
        "missing_in_Eurostat":missing_in_xls,
        "category_disagreements":category_drift,
        "UNCTAD_pdf_url":"https://unctadstat.unctad.org/EN/Classifications/DimHS2017Products_Ict_Hierarchy.pdf",
        "EUROSTAT_xls_url":expected["url"],"EUROSTAT_xls_sha256":expected["sha256"],
        "UNCTAD_pdf_sha256":next(iter(unctad.values()))["UNCTAD_pdf_sha256"],
        "general_UNCTAD_and_Eurostat_webpage_claims_93_goods":True,
        "independently_source_verified_catalog_has_92_codes":True,
        "scientific_treatment":"Use 92 exact codes from two matching original code lists; document website narrative inconsistency; NEVER manufacture a missing 93rd code",
        "full_ICT_HS_1992_1996_coding_not_yet_verified":True,
        "all_HS_editions_harmonized":False,
        "no_FTECH_or_GMM":True
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("HS2017_INDEPENDENT_OFFICIAL_UNCTAD_EUROSTAT_MATCH",len(codes),
          "HS6 products, groups identical, 93 narrative inconsistent",flush=True)
if __name__=="__main__": main()
