#!/usr/bin/env python3
"""Audit UN Comtrade customs-area codes that differ from standard M49/ISO3.

Source:
https://uncomtrade.org/docs/reporter-country-codes-and-their-custom-areas/
Comtrade partner 251 is France's customs area including Monaco and overseas.
Comtrade partner 842 includes US customs territory (Puerto Rico/USVI).
These are *candidates* for FRA and USA, NOT exact country observations.

Consumes PERMANENTLY archived source rows, no new API calls, no re-estimation.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOCK = ROOT / "config/extended/phase2_original_47_country_sample_lock.json"
BASE = ROOT / "data/raw/Balanced_Panel_Data.xlsx"
AZE = ROOT / "data/extended/comtrade/AZE_HS8471_8517_all_origins_2005_2022.csv"
EIGHT = ROOT / "data/extended/comtrade/oecd_missing_hs4_preperiod/partner_records_2005_2007.csv"
OUT = ROOT / "data/extended/comtrade"
CUSTOMS = {251: ("FRA", "France customs area includes Monaco and overseas territories"),
           842: ("USA", "US customs area includes Puerto Rico and US Virgin Islands")}
SOURCE = "https://uncomtrade.org/docs/reporter-country-codes-and-their-custom-areas/"
PREPERIOD = {2005, 2006, 2007}
HS = {"8471", "8517"}
COLS = ["receiver_ISO3", "preperiod_year_HS4_slices",
        "world_HS8471_8517_nominal_USD", "observed_strict_original_47_nominal_USD",
        "strict_iso_numeric_share_of_world", "france_customs_251_nominal_USD",
        "us_customs_842_nominal_USD",
        "incl_two_customs_area_proxies_nominal_USD",
        "incl_two_proxies_share_of_world_not_completeness",
        "difference_percentage_points_due_to_two_area_codes",
        "raw_partner_251_record_count", "raw_partner_842_record_count",
        "customs_proxies_are_not_exact_country_ISO3", "usable_as_final_FTECH_weights"]


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def analyze_one(receiver, rows):
    cells = defaultdict(list)
    keys = set()
    all_codes = set()
    for r in rows:
        if r["reporter_ISO3"] != receiver or int(r["Year"]) not in PREPERIOD:
            continue
        year, hs, m49 = int(r["Year"]), r["HS4"], int(r["partner_M49"])
        if hs not in HS:
            raise ValueError("Unplanned HS heading")
        key = (receiver, year, hs, m49)
        if key in keys:
            raise ValueError(f"Duplicate country-year-heading-partner {key}")
        keys.add(key)
        value = float(r["value_nominal_usd"])
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"Missing/nonfinite/negative trade value {key}")
        cells[year, hs].append((m49, value, r["partner_ISO3_if_in_original_sample"]))
        all_codes.add(m49)
    if set(cells) != {(year, h) for year in PREPERIOD for h in HS}:
        raise ValueError(f"Missing country-year-heading slice {receiver}")
    world = strict = fr = us = 0.0
    fr_n = us_n = 0
    for cell in cells.values():
        w = [v for c, v, iso in cell if c == 0]
        if len(w) != 1 or w[0] <= 0:
            raise ValueError("No unique positive World aggregate")
        world += w[0]
        for code, value, iso in cell:
            if code == 0:
                continue
            if iso and iso != receiver:
                strict += value
            if code == 251:
                if iso:
                    raise ValueError("251 must not silently map to FRA as exact ISO")
                fr += value
                fr_n += 1
            if code == 842:
                if iso:
                    raise ValueError("842 must not silently map to USA as exact ISO")
                us += value
                us_n += 1
    if (fr_n == 0 or us_n == 0):
        raise ValueError(f"Expected both historical custom-territory codes for {receiver}")
    if strict > world * 1.01:
        raise ValueError(f"Sample sum unexpectedly exceeds World {receiver}")
    incl = strict + fr + us
    return {
        "receiver_ISO3": receiver,
        "preperiod_year_HS4_slices": len(cells),
        "world_HS8471_8517_nominal_USD": format(world, ".3f"),
        "observed_strict_original_47_nominal_USD": format(strict, ".3f"),
        "strict_iso_numeric_share_of_world": format(strict / world, ".9f"),
        "france_customs_251_nominal_USD": format(fr, ".3f"),
        "us_customs_842_nominal_USD": format(us, ".3f"),
        "incl_two_customs_area_proxies_nominal_USD": format(incl, ".3f"),
        "incl_two_proxies_share_of_world_not_completeness": format(incl / world, ".9f"),
        "difference_percentage_points_due_to_two_area_codes":
            format((fr + us) / world * 100, ".5f"),
        "raw_partner_251_record_count": fr_n,
        "raw_partner_842_record_count": us_n,
        "customs_proxies_are_not_exact_country_ISO3": "TRUE",
        "usable_as_final_FTECH_weights": "FALSE",
    }


def main():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    base_sha = hashlib.sha256(BASE.read_bytes()).hexdigest()
    assert base_sha == lock["original_data_sha256"], "Original professor baseline SHA drift"
    originals = lock["iso3_to_original_country_name"]
    assert len(originals) == 47 and all(iso in originals for iso, _ in CUSTOMS.values())
    aze, eight = read_rows(AZE), read_rows(EIGHT)
    assert len(aze) == 1863 and len(eight) == 2030, "Unexpected source row change"
    receivers = ["AZE", "KGZ", "MAC", "MDA", "MKD", "MNG", "PAN", "TTO", "URY"]
    assert set(r["reporter_ISO3"] for r in eight) == set(receivers) - {"AZE"}
    results = [analyze_one(iso, aze if iso == "AZE" else eight) for iso in receivers]
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "CUSTOMS_AREA_CROSSWALK_AUDIT_2026-10-17.csv").open(
        "w", encoding="utf-8", newline="") as stream:
        w = csv.DictWriter(stream, fieldnames=COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(results)
    manifest = {
        "phase": "EXTENDED_DATA_EXPERIMENTAL",
        "source_territory_mapping": SOURCE,
        "original_dataset_SHA256": base_sha,
        "source_aze_n_rows": len(aze),
        "source_eight_n_rows": len(eight),
        "historical_customs_area_codes": {
            "251": {"proxy_iso3": "FRA", "equivalence": "NOT_EXACT",
                    "scope": CUSTOMS[251][1]},
            "842": {"proxy_iso3": "USA", "equivalence": "NOT_EXACT",
                    "scope": CUSTOMS[842][1]},
        },
        "definition": "Observed strict ISO-mapped original 47 source trade versus "
                      "descriptive what-if including 2 UN Comtrade customs-area proxies",
        "descriptive_what_if_is_not_complete_coverage": True,
        "crosswalk_not_applied_to_source_records": True,
        "world_aggregate_excluded_from_partner_sum": True,
        "no_missing_as_zero_or_causal_ftech": True,
        "no_data_from_future_years": True,
        "no_stata_or_gmm": True,
        "rows": len(results),
        "run_utc": datetime.now(timezone.utc).isoformat(),
    }
    (OUT / "CUSTOMS_AREA_CROSSWALK_AUDIT_2026-10-17.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for x in results:
        print("PHASE2_CUSTOMS_AREA", x["receiver_ISO3"],
              "strict", x["strict_iso_numeric_share_of_world"],
              "sensitivity", x["incl_two_proxies_share_of_world_not_completeness"],
              "delta_pp", x["difference_percentage_points_due_to_two_area_codes"], flush=True)
    print("PHASE2_CUSTOMS_AREA_AUDIT_PASS", len(results),
          "receivers, two flagged trade/customs territories, professor unchanged", flush=True)


if __name__ == "__main__":
    main()
