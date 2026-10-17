#!/usr/bin/env python3
"""Join genuinely observed source-coverage metadata for nine receivers x 18 years.

No trade-weight renormalization, no FTECH score, no estimation, no imputation.
Both HS4 headings must have valid observed World aggregates before the annual
numeric summary is populated. A zero is never substituted for a missing year.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOCK = ROOT / "config/extended/phase2_original_47_country_sample_lock.json"
RAW_BASE = ROOT / "data/raw/Balanced_Panel_Data.xlsx"
AZE = ROOT / "data/extended/comtrade/AZE_HS8471_8517_annual_source_coverage.csv"
EIGHT = ROOT / "data/extended/comtrade/oecd_missing_hs4_2008_2022/eight_receivers_coverage_2005_2022.csv"
OUT = ROOT / "data/extended/comtrade/normalized"
DEST = ("AZE", "KGZ", "MAC", "MDA", "MKD", "MNG", "PAN", "TTO", "URY")


def csvrows(path):
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def wcsv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def coerce_observation(row, is_aze):
    value_key = "world_imports_nominal_usd" if is_aze else "world_nominal_usd"
    sample_key = ("original_47_origin_summed_imports_usd" if is_aze
                  else "sum_original_47_origins_nominal_usd")
    r = row["reporter_ISO3"]
    year = int(row["Year"])
    hs = row["HS4"]
    assert r in DEST and 2005 <= year <= 2022 and hs in ("8471", "8517")
    valid = row["status"] == "VALID_PREVIEW"
    world = float(row[value_key]) if valid else None
    sample = float(row[sample_key]) if valid else None
    if valid:
        assert math.isfinite(world) and world > 0 and math.isfinite(sample) and sample >= 0
        assert sample <= world * 1.01, "Impossible reported subset / World ratio"
    else:
        assert not row[value_key], "Unreliable slice must not have a numeric World value"
    return (r, year, hs), {"status": row["status"], "world": world, "strict": sample}


def main():
    config = json.loads(LOCK.read_text(encoding="utf-8"))
    assert hashlib.sha256(RAW_BASE.read_bytes()).hexdigest() == config["original_data_sha256"]
    assert len(config["iso3_to_original_country_name"]) == 47
    aze_rows, other_rows = csvrows(AZE), csvrows(EIGHT)
    assert len(aze_rows) == 36 and len(other_rows) == 288
    by_key = {}
    for raw, is_aze in [(r, True) for r in aze_rows] + [(r, False) for r in other_rows]:
        key, value = coerce_observation(raw, is_aze)
        assert key not in by_key, f"Duplicate receiver/year/HS4: {key}"
        by_key[key] = value
    expected = {(r, year, hs) for r in DEST
                for year in range(2005, 2023)
                for hs in ("8471", "8517")}
    assert set(by_key) == expected, "Missing or duplicate key in audited input panel"
    annual = []
    country_summary = []
    for country in DEST:
        complete = 0
        for year in range(2005, 2023):
            h1, h2 = by_key[country, year, "8471"], by_key[country, year, "8517"]
            all_valid = h1["status"] == h2["status"] == "VALID_PREVIEW"
            if all_valid:
                world = h1["world"] + h2["world"]
                strict = h1["strict"] + h2["strict"]
                share = strict / world
                complete += 1
            else:
                world = strict = share = None
            annual.append({
                "receiver_ISO3": country, "Year": year,
                "HS8471_status": h1["status"], "HS8517_status": h2["status"],
                "both_heading_values_observed": str(all_valid).upper(),
                "world_two_HS4_nominal_usd": format(world, ".4f") if world is not None else "",
                "strict_original_47_partner_trade_nominal_usd":
                    format(strict, ".4f") if strict is not None else "",
                "strict_observed_partner_share_of_world_not_completeness":
                    format(share, ".9f") if share is not None else "",
                "not_complete_unified_ICT_basket": "TRUE",
                "not_final_foreign_technology_exposure": "TRUE",
                "missing_partner_year_heading_never_zero": "TRUE",
            })
        country_summary.append({
            "receiver_ISO3": country,
            "valid_both_heading_years": complete, "years_expected": 18,
            "fully_observed_all_18_annual_two_heading_aggregates": str(complete == 18).upper(),
            "data_are_preview_not_proven_exhaustive": "TRUE",
            "FTECH_ready": "FALSE",
        })
    assert len(annual) == 162 and len(country_summary) == 9
    OUT.mkdir(parents=True, exist_ok=True)
    wcsv(OUT / "nine_receiver_annual_two_heading_coverage_2005_2022.csv", annual)
    wcsv(OUT / "nine_receiver_coverage_by_country_2005_2022.csv", country_summary)
    payload = {
        "phase": "EXTENDED_DATA_EXPERIMENTAL",
        "baseline_sha256_verified": config["original_data_sha256"],
        "source_aze_csv_sha256": hashlib.sha256(AZE.read_bytes()).hexdigest(),
        "source_eight_csv_sha256": hashlib.sha256(EIGHT.read_bytes()).hexdigest(),
        "receiver_year_slices": len(annual),
        "receiver_year_heading_slices": len(by_key),
        "fully_valid_two_heading_receiver_years":
            sum(x["both_heading_values_observed"] == "TRUE" for x in annual),
        "country_level": country_summary,
        "not_all_47_original_receivers": True,
        "both_trial_HS4_are_not_harmonized_full_ICT": True,
        "preview_coverage_not_verified_as_exhaustive": True,
        "all_missing_fields_remain_blank": True,
        "no_technology_spillover_or_causal_model_estimated": True,
        "no_stata_run_or_phase_A_update": True,
    }
    (OUT / "nine_receiver_annual_two_heading_coverage_2005_2022.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("PHASE2_9x18_SOURCE_COVERAGE_AUDIT_PASS",
          payload["fully_valid_two_heading_receiver_years"], "/162",
          "country_years", json.dumps(country_summary), flush=True)


if __name__ == "__main__":
    main()
