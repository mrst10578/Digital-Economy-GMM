#!/usr/bin/env python3
"""Build a non-destructive, provenance-labeled Comtrade partner-code crosswalk.

The two old customs unions/areas below cannot be treated as exact territorial
ISO3 countries. We retain both raw partner code and flagged candidate country.
No original country panel merge, no FTECH, and no causal estimation.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "data/raw/Balanced_Panel_Data.xlsx"
LOCK = ROOT / "config/extended/phase2_original_47_country_sample_lock.json"
INPUTS = (
    ("AZE_18year", ROOT / "data/extended/comtrade/AZE_HS8471_8517_all_origins_2005_2022.csv"),
    ("eight_receivers_baseperiod",
     ROOT / "data/extended/comtrade/oecd_missing_hs4_preperiod/partner_records_2005_2007.csv"),
)
OUT = ROOT / "data/extended/comtrade/normalized"
CUSTOMS_PROXIES = {251: ("FRA", "FRANCE_CUSTOMS_AREA_INCL_MONACO_OVERSEAS"),
                   842: ("USA", "US_CUSTOMS_AREA_INCL_PUERTO_RICO_USVI")}
FIELDS = [
    "receiver_ISO3", "Year", "HS4", "partner_M49_as_reported",
    "partner_ISO3_strict_original_47", "partner_candidate_ISO3_nonexact_customs_area",
    "partner_mapping_status", "customs_area_definition_flag",
    "is_world_aggregate", "value_nominal_usd", "source_panel",
    "HS_version_not_harmonized", "safe_to_use_as_final_FTECH",
]


def normalized_record(raw, source, originals):
    reporter, year, hs = raw["reporter_ISO3"], int(raw["Year"]), raw["HS4"]
    code, strict = int(raw["partner_M49"]), raw["partner_ISO3_if_in_original_sample"]
    value = float(raw["value_nominal_usd"])
    if (reporter not in originals or not 2005 <= year <= 2022
        or hs not in {"8471", "8517"}
        or code < 0 or not math.isfinite(value) or value < 0):
        raise ValueError("Malformed archived source row")
    candidate, flag = CUSTOMS_PROXIES.get(code, ("", ""))
    if code == 0:
        if strict or candidate:
            raise ValueError("World must never have a country identity")
        status = "WORLD_AGGREGATE_NOT_ORIGIN"
    elif candidate:
        if strict or candidate not in originals:
            raise ValueError("Customs-area candidate mistaken for exact ISO")
        status = "CUSTOMS_AREA_CANDIDATE_NOT_EXACT_ISO3"
    elif strict:
        if strict not in originals:
            raise ValueError("Exact partner outside original country lock")
        status = "EXACT_ISO3_SOURCE_MAPPING"
    else:
        status = "OTHER_ORIGIN_NOT_IN_ORIGINAL_47"
    return {
        "receiver_ISO3": reporter, "Year": year, "HS4": hs,
        "partner_M49_as_reported": code,
        "partner_ISO3_strict_original_47": strict,
        "partner_candidate_ISO3_nonexact_customs_area": candidate,
        "partner_mapping_status": status, "customs_area_definition_flag": flag,
        "is_world_aggregate": str(code == 0).upper(),
        "value_nominal_usd": raw["value_nominal_usd"],
        "source_panel": source, "HS_version_not_harmonized": "TRUE",
        "safe_to_use_as_final_FTECH": "FALSE",
    }


def main():
    config = json.loads(LOCK.read_text(encoding="utf-8"))
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == config["original_data_sha256"]
    originals = set(config["iso3_to_original_country_name"])
    assert len(originals) == 47
    clean = []
    source_counts = {}
    for source_name, path in INPUTS:
        with path.open(encoding="utf-8", newline="") as handle:
            raw_rows = list(csv.DictReader(handle))
        source_counts[source_name] = len(raw_rows)
        clean.extend(normalized_record(r, source_name, originals) for r in raw_rows)
    assert source_counts == {"AZE_18year": 1863, "eight_receivers_baseperiod": 2030}
    unique_keys = {(r["receiver_ISO3"], r["Year"], r["HS4"],
                    r["partner_M49_as_reported"]) for r in clean}
    assert len(unique_keys) == len(clean), "Duplicate reporter-year-heading-partner"
    clean.sort(key=lambda r: (r["receiver_ISO3"], r["Year"], r["HS4"],
                              r["partner_M49_as_reported"]))
    totals = Counter(r["partner_mapping_status"] for r in clean)
    assert len(clean) == 3893
    assert totals["WORLD_AGGREGATE_NOT_ORIGIN"] == 84
    assert totals["CUSTOMS_AREA_CANDIDATE_NOT_EXACT_ISO3"] == 167
    OUT.mkdir(parents=True, exist_ok=True)
    name = "nine_receiver_HS4_partner_code_provenance.csv"
    with (OUT / name).open("w", encoding="utf-8", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(clean)
    report = {
        "phase": "EXTENDED_DATA_EXPERIMENTAL",
        "original_baseline_sha256_verified": config["original_data_sha256"],
        "sources_and_counts": source_counts, "normalized_rows": len(clean),
        "mapping_status_counts": dict(totals),
        "number_of_world_records_excluded_as_sources": totals["WORLD_AGGREGATE_NOT_ORIGIN"],
        "customs_areas_not_equivalent_to_ISO_countries": {
            str(code): {"candidate_iso3": iso, "provenance": flag}
            for code, (iso, flag) in CUSTOMS_PROXIES.items()
        },
        "official_customs_area_documentation":
            "https://uncomtrade.org/docs/reporter-country-codes-and-their-custom-areas/",
        "never_renormalize_incomplete_trade_partner_weights": True,
        "HS_versions_not_harmonized": True,
        "not_a_complete_multi-country_18year_network": True,
        "no_FTECH_or_GMM_estimated": True,
        "source_data_unchanged": True,
        "run_utc": datetime.now(timezone.utc).isoformat(),
    }
    (OUT / "nine_receiver_HS4_partner_code_provenance.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PHASE2_PROVENANCE_NORMALIZATION_PASS", len(clean),
          "records", dict(totals), "No Stata or FTECH", flush=True)


if __name__ == "__main__":
    main()
