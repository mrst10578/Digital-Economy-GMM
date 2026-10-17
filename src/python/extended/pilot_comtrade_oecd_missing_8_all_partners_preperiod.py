#!/usr/bin/env python3
"""Preperiod multi-partner feasibility: eight reporters missing as independent OECD ICIO nodes.

UN Comtrade public preview; 2005-2007, HS8471 and HS8517, annual requests.
Not a harmonized/exhaustive ICT goods definition, and not causal spillovers.
No changes to professor dataset, no estimation, no missing-to-zero imputation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pycountry

ROOT = Path(__file__).resolve().parents[3]
LOCK = ROOT / "config/extended/phase2_original_47_country_sample_lock.json"
BASE = ROOT / "data/raw/Balanced_Panel_Data.xlsx"
OUT = ROOT / "outputs/extended/comtrade_eight_reporters_preperiod"
PERMANENT = ROOT / "data/extended/comtrade/oecd_missing_hs4_preperiod"
API = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
GROUPS = {"1": ("KGZ", "MAC", "MDA", "MKD"),
          "2": ("MNG", "PAN", "TTO", "URY")}
YEARS = (2005, 2006, 2007)
CODES = ("8471", "8517")
LIMIT = 500
FIELDS = ("reporter_ISO3", "Year", "HS4", "partner_M49",
          "partner_ISO3_if_in_original_sample", "is_world_aggregate",
          "value_nominal_usd", "source_year_classification",
          "not_complete_or_causal_spillover")
METRICS = ("reporter_ISO3", "Year", "HS4", "status", "response_rows",
           "valid_origin_rows_ex_world", "original_47_origin_count",
           "world_nominal_usd", "sum_original_47_origins_nominal_usd",
           "observed_original_47_origin_share_of_world",
           "raw_response_sha256", "url", "error",
           "preview_not_exhaustive", "missing_not_zero", "causal_claim")


def request(url: str):
    last_error = ""
    for attempt in range(4):
        try:
            req = Request(url, headers={
                "Accept": "application/json",
                "User-Agent": "Academic-ICT-Trade-Feasibility-Phase2/1.1",
            })
            with urlopen(req, timeout=35) as stream:
                raw = stream.read(8_000_001)
            if len(raw) > 8_000_000:
                raise ValueError("response exceeds size guard")
            document = json.loads(raw)
            if not isinstance(document, dict) or not isinstance(document.get("data"), list):
                raise ValueError("unrecognized Comtrade response")
            return document["data"], raw, ""
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            last_error = f"{type(exc).__name__}: {str(exc)[:180]}"
            if isinstance(exc, HTTPError) and exc.code not in (408, 429, 500, 502, 503, 504):
                break
            time.sleep(1.5 * (attempt + 1))
    return None, b"", last_error


def inspect(records, reporter, iso, year, hs, origin_map):
    """Invalid or incomplete slices contribute NO numeric records."""
    if records is None:
        return "API_ERROR", [], None, None
    if not records:
        return "EMPTY_UNREPORTED_NOT_ZERO", [], None, None
    if len(records) >= LIMIT:
        return "CAPPED_NOT_USABLE", [], None, None
    seen = set()
    values = []
    try:
        for rec in records:
            if (int(rec["reporterCode"]) != reporter
                or int(rec.get("period", rec.get("refYear", -1))) != year
                or str(rec["cmdCode"]) != hs or str(rec["flowCode"]) != "M"):
                return "BAD_METADATA", [], None, None
            partner = int(rec["partnerCode"])
            value = float(rec["primaryValue"])
            if partner < 0 or partner in seen or not math.isfinite(value) or value < 0:
                return "BAD_OR_DUPLICATE_VALUE", [], None, None
            seen.add(partner)
            values.append({
                "reporter_ISO3": iso,
                "Year": year, "HS4": hs, "partner_M49": partner,
                "partner_ISO3_if_in_original_sample": origin_map.get(partner, ""),
                "is_world_aggregate": partner == 0, "value_nominal_usd": value,
                "source_year_classification": "HS classification as served; not revision-harmonized",
                "not_complete_or_causal_spillover": True,
            })
    except (TypeError, ValueError, KeyError):
        return "BAD_METADATA_OR_VALUE", [], None, None
    world_rows = [r for r in values if r["is_world_aggregate"]]
    if len(world_rows) != 1:
        return "WORLD_AGGREGATE_UNAVAILABLE", [], None, None
    world = world_rows[0]["value_nominal_usd"]
    if world <= 0:
        return "WORLD_NONPOSITIVE", [], None, None
    subset = sum(r["value_nominal_usd"] for r in values
                 if r["partner_ISO3_if_in_original_sample"]
                 and r["partner_ISO3_if_in_original_sample"] != iso)
    return "VALID_PREVIEW", values, world, subset


def write_csv(path, fields, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", choices=("1", "2", "all"), default="all")
    args = parser.parse_args()
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    hash_baseline = hashlib.sha256(BASE.read_bytes()).hexdigest()
    assert hash_baseline == lock["original_data_sha256"], "Professor baseline changed!"
    origins = set(lock["iso3_to_original_country_name"])
    assert len(origins) == 47
    origin_map = {}
    for origin in origins:
        country = pycountry.countries.get(alpha_3=origin)
        assert country is not None, f"Unmapped original ISO3: {origin}"
        code = int(country.numeric)
        assert code not in origin_map
        origin_map[code] = origin

    chosen = GROUPS["1"] + GROUPS["2"] if args.group == "all" else GROUPS[args.group]
    assert len(chosen) == (8 if args.group == "all" else 4)
    assert set(chosen).issubset(origins) and len(set(chosen)) == len(chosen)
    run_dir = OUT / ("group_" + args.group)
    raw_dir = run_dir / "raw_API"
    raw_dir.mkdir(parents=True, exist_ok=True)
    observations, coverage = [], []
    for iso in chosen:
        reporter = int(pycountry.countries.get(alpha_3=iso).numeric)
        for year in YEARS:
            for hs in CODES:
                url = API + "?" + urlencode({
                    "reporterCode": reporter, "period": year, "flowCode": "M",
                    "cmdCode": hs, "maxRecords": LIMIT, "breakdownMode": "classic",
                })
                records, raw, error = request(url)
                status, valid, world, subset = inspect(records, reporter, iso, year, hs, origin_map)
                if raw:
                    (raw_dir / f"{iso}_{year}_HS{hs}_all_partners.json").write_bytes(raw)
                observations.extend(valid)
                origin_rows = [row for row in valid
                               if row["partner_ISO3_if_in_original_sample"]
                               and row["partner_ISO3_if_in_original_sample"] != iso]
                coverage.append({
                    "reporter_ISO3": iso, "Year": year, "HS4": hs,
                    "status": status, "response_rows": len(records) if records is not None else "",
                    "valid_origin_rows_ex_world": len(valid) - 1 if valid else "",
                    "original_47_origin_count": len(origin_rows) if valid else "",
                    "world_nominal_usd": world if world is not None else "",
                    "sum_original_47_origins_nominal_usd": subset if subset is not None else "",
                    "observed_original_47_origin_share_of_world":
                        subset / world if world is not None and world > 0 else "",
                    "raw_response_sha256": hashlib.sha256(raw).hexdigest() if raw else "",
                    "url": url, "error": error,
                    "preview_not_exhaustive": "TRUE", "missing_not_zero": "TRUE",
                    "causal_claim": "FALSE",
                })
                print("PHASE2_PREPERIOD", iso, year, hs, status,
                      "valid_records", len(valid), "error", error, flush=True)
                time.sleep(0.65)
    assert len(coverage) == len(chosen) * 6
    assert len({(r["reporter_ISO3"], r["Year"], r["HS4"]) for r in coverage}) == len(coverage)
    statuses = Counter(r["status"] for r in coverage)
    summary = {
        "phase": "EXTENDED_DATA_EXPERIMENTAL",
        "source": "UN Comtrade public preview (keyless)",
        "original_sha256_verified": hash_baseline,
        "receiver_countries": list(chosen),
        "years": list(YEARS), "hs4": list(CODES),
        "requests_expected": len(chosen) * 6, "requests_observed_valid": statuses["VALID_PREVIEW"],
        "status_counts": dict(statuses),
        "partner_rows_from_valid_responses_including_world": len(observations),
        "not_exhaustive_or_harmonized_ict": True,
        "no_zero_imputation": True, "no_valid_ftech_or_causal_identification": True,
        "not_complete_47_by_47_network": True,
        "no_stata_or_professor_dataset_mutation": True,
        "raw_payloads_in_short_lived_actions_artifact_only": True,
        "raw_payload_sha256_logged_for_successful_responses": True,
        "run_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_csv(run_dir / "coverage.csv", METRICS, coverage)
    write_csv(run_dir / "partner_records.csv", FIELDS, observations)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    # Partial data remain an artifact for audit, never promoted as research-ready weights.
    invalid = set(statuses) - {"VALID_PREVIEW", "EMPTY_UNREPORTED_NOT_ZERO"}
    if invalid:
        print("PHASE2_NOT_PROMOTED_UNRELIABLE_OR_INCOMPLETE_API_SLICES", sorted(invalid), flush=True)
        raise SystemExit(2)
    # Preserve normalized SOURCE observations and per-cell provenance, not an inferred FTECH index.
    PERMANENT.mkdir(parents=True, exist_ok=True)
    write_csv(PERMANENT / "coverage_2005_2007.csv", METRICS, coverage)
    write_csv(PERMANENT / "partner_records_2005_2007.csv", FIELDS, observations)
    (PERMANENT / "provenance.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("PHASE2_PREPERIOD_SOURCE_ARCHIVE_PASS", len(chosen), "reporters",
          len(coverage), "year-HS4 queries", len(observations),
          "partner records; research-ready FTECH=FALSE", flush=True)


if __name__ == "__main__":
    main()
