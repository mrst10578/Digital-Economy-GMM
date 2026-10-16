#!/usr/bin/env python3
"""Check whether 47 original countries are explicitly named in OECD 2025 ICIO.

Manual codes transcribed verbatim from official OECD ICIO 2025 annex PDF,
Table 1 pp. 2, https://webfs-sti.oecd.org/files/STI-PIE/ICIO/2025/ICIO2025annex.pdf

Note: Presence in OECD published-country list is NOT a measured country×year
or sector×country pair data-coverage audit; ROW aggregation cannot recover
specific missing bilateral country nodes.
"""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
LOCK=ROOT/"config/extended/phase2_original_47_country_sample_lock.json"
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
OUT=ROOT/"outputs/extended/oecd_icio_2025_geographic_screen"
ANNEX="https://webfs-sti.oecd.org/files/STI-PIE/ICIO/2025/ICIO2025annex.pdf"
TABLE="Table 1. Countries in published ICIO tables"
# Explicit 80 entries in OECD Annex Table 1 only. ROW and China/Mexico subregions excluded.
CODES=(
    "AGO ARE ARG AUS AUT BEL BGD BGR BLR BRA BRN CAN CHE CHL CHN CIV "
    "CMR COD COL CRI CYP CZE DEU DNK EGY ESP EST FIN FRA GBR GRC HKG "
    "HRV HUN IDN IND IRL ISL ISR ITA JOR JPN KAZ "
    "KHM KOR LAO LTU LUX LVA MAR MEX MLT MMR MYS NGA NLD NOR NZL "
    "PAK PER PHL POL PRT ROU RUS SAU SEN SGP STP SVK SVN SWE THA "
    "TUN TUR TWN UKR USA VNM ZAF"
).split()

def main():
    lock=json.loads(LOCK.read_text(encoding="utf-8"))
    assert hashlib.sha256(RAW.read_bytes()).hexdigest()==lock["original_data_sha256"]
    orig=lock["iso3_to_original_country_name"]
    assert len(orig)==47 and len(CODES)==80 and len(set(CODES))==80
    original_codes=set(orig)
    published=set(CODES)
    matched=sorted(original_codes & published)
    unmatched=sorted(original_codes-published)
    assert len(matched)==38 and unmatched==["AZE","KGZ","MAC","MDA","MKD","MNG","PAN","TTO","URY"]
    OUT.mkdir(parents=True,exist_ok=True)
    records=[]
    for iso in sorted(orig):
        records.append({
            "ISO3":iso,"baseline_country_name":orig[iso],
            "explicit_2025_OECD_ICIO_country_node":"YES" if iso in published else "NO",
            "missing_not_recoverable_from_ROW_as_country_specific":"YES" if iso not in published else "NO",
            "country_year_cells_2005_2022_NOT_YET_VERIFIED":"TRUE",
            "source_annex":ANNEX,
        })
    with (OUT/"country_node_screen_47.csv").open("w",encoding="utf-8",newline="") as fp:
        w=csv.DictWriter(fp,fieldnames=list(records[0]))
        w.writeheader();w.writerows(records)
    result={
        "phase":"EXTENDED_DATA_EXPERIMENTAL",
        "source_annex":ANNEX,
        "source_table":TABLE,
        "source_release":"OECD Inter-Country Input-Output 2025 edition, 2026 revision",
        "oecd_regular_economy_node_count":80,
        "base_countries":47,
        "explicitly_represented_base_countries":len(matched),
        "missing_country_specific_nodes":len(unmatched),
        "explicitly_represented_share_pct":round(100*len(matched)/47,2),
        "present_iso3":matched,"absent_iso3":unmatched,
        "years_stated_by_official_source":"1995-2022",
        "actual_country_year_sector_pair_coverage":"NOT TESTED; downloadable OECD matrices not yet parsed",
        "does_not_cover_all_47_countries":True,
        "rest_of_world_not_country_specific":True,
        "cannot_construct_47x47_fully_observed_OECD_bilateral_matrix":True,
        "baseline_workbook_sha256":lock["original_data_sha256"],
        "baseline_workbook_modified":False,
        "GMM_model_executed":False,
        "scientific_cautions":[
            "OECD includes Rest of World but this is NOT individual nodes for AZE/KGZ/MAC/MDA/MKD/MNG/PAN/TTO/URY.",
            "Listing 38 countries proves geographic names only, not annual bilateral trade coverage or source completeness.",
            "China and Mexico split processing variants are not extra countries; use regular ICIO nodes when comparing.",
            "Sector C26 (computer/electronic/optical products), J61 (telecom), J62_63 (IT) may help exposure measurement but do not identify causal technology spillovers.",
            "OECD origin-destination input-output relationships are estimated/accounting-consistent flows, not random shocks."
        ]
    }
    (OUT/"latest.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("OECD_ICIO_GEOGRAPHIC_AUDIT_PASS 38/47 explicitly covered; 9 without country nodes; no GMM",flush=True)
    print("OECD_MISSING_NODES",",".join(unmatched),flush=True)

if __name__=="__main__":
    main()
