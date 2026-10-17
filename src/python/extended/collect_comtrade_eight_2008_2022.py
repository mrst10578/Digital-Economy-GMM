#!/usr/bin/env python3
"""Phase-2 source-only extension for 8 OECD-absent reporters, years 2008-2022.

Exactly two HS4 trial headings, 8471 and 8517. Not a historically unified ICT
classification. Public Comtrade preview may omit records even below its cap.
Results remain provenance-labeled experimental trade proxies. No FTECH or GMM.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import pycountry

ROOT = Path(__file__).resolve().parents[3]
LOCK = ROOT / "config/extended/phase2_original_47_country_sample_lock.json"
BASE = ROOT / "data/raw/Balanced_Panel_Data.xlsx"
OUTPUT = ROOT / "outputs/extended/phase2_eight_2008_22"
MODULE_PATH = Path(__file__).with_name("pilot_comtrade_oecd_missing_8_all_partners_preperiod.py")
SPEC = importlib.util.spec_from_file_location("comtrade_phase2_guardrails", MODULE_PATH)
BASELINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASELINE)
COHORTS = {
    "A": ("KGZ", "MAC"),
    "B": ("MDA", "MKD"),
    "C": ("MNG", "PAN"),
    "D": ("TTO", "URY"),
}
YEARS = tuple(range(2008, 2023))
HS_CODES = ("8471", "8517")
SOURCE_URL = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", required=True, choices=tuple(COHORTS))
    args = parser.parse_args()
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    sha = hashlib.sha256(BASE.read_bytes()).hexdigest()
    assert sha == lock["original_data_sha256"], "Professor source file changed"
    original = set(lock["iso3_to_original_country_name"])
    assert len(original) == 47
    m49_to_iso = {}
    for iso in original:
        obj = pycountry.countries.get(alpha_3=iso)
        assert obj and int(obj.numeric) not in m49_to_iso
        m49_to_iso[int(obj.numeric)] = iso
    output = OUTPUT / args.cohort
    raw_dir = output / "raw_API"
    raw_dir.mkdir(parents=True, exist_ok=True)
    coverage, partners = [], []
    for iso in COHORTS[args.cohort]:
        assert iso in original
        reporter = int(pycountry.countries.get(alpha_3=iso).numeric)
        for year in YEARS:
            for hs in HS_CODES:
                url = SOURCE_URL + "?" + urlencode({
                    "reporterCode": reporter, "period": year, "flowCode": "M",
                    "cmdCode": hs, "maxRecords": 500, "breakdownMode": "classic",
                })
                records, raw, error = BASELINE.request(url)
                status, valid, world, subset = BASELINE.inspect(
                    records, reporter, iso, year, hs, m49_to_iso
                )
                if raw:
                    (raw_dir / f"{iso}_{year}_HS{hs}_all_partners.json").write_bytes(raw)
                partners.extend(valid)
                observed_countries = [
                    x for x in valid
                    if x["partner_ISO3_if_in_original_sample"]
                    and x["partner_ISO3_if_in_original_sample"] != iso
                ]
                coverage.append({
                    "reporter_ISO3": iso, "Year": year, "HS4": hs,
                    "status": status,
                    "response_rows": len(records) if records is not None else "",
                    "valid_origin_rows_ex_world": len(valid) - 1 if valid else "",
                    "original_47_origin_count": len(observed_countries) if valid else "",
                    "world_nominal_usd": world if world is not None else "",
                    "sum_original_47_origins_nominal_usd": subset if subset is not None else "",
                    "observed_original_47_origin_share_of_world":
                        subset / world if world is not None and world > 0 else "",
                    "raw_response_sha256": hashlib.sha256(raw).hexdigest() if raw else "",
                    "url": url, "error": error,
                    "preview_not_exhaustive": "TRUE",
                    "missing_not_zero": "TRUE", "causal_claim": "FALSE",
                })
                print("PHASE2_COMTRADE_2008_22", args.cohort, iso, year, hs,
                      status, "n_source_rows", len(valid), "error", error, flush=True)
                time.sleep(0.75)
    assert len(coverage) == 60
    assert len({(r["reporter_ISO3"], r["Year"], r["HS4"]) for r in coverage}) == 60
    statuses = Counter(row["status"] for row in coverage)
    write_csv(output / "coverage.csv", BASELINE.METRICS, coverage)
    write_csv(output / "partner_records.csv", BASELINE.FIELDS, partners)
    manifest = {
        "phase": "EXTENDED_DATA_EXPERIMENTAL",
        "source": "UN Comtrade keyless public preview, not guaranteed exhaustive",
        "cohort": args.cohort, "receivers": list(COHORTS[args.cohort]),
        "years": [2008, 2022], "HS4_trial_headings": list(HS_CODES),
        "expected_queries": 60, "statuses": dict(statuses),
        "valid_queries": statuses["VALID_PREVIEW"],
        "observed_partner_rows_including_world": len(partners),
        "original_data_sha256": sha, "missing_as_zero": False,
        "complete_47x47_network": False,
        "complete_harmonized_ICT_goods": False,
        "FTECH_or_causal_estimations": False,
        "raw_payload_sha256_in_coverage": True,
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    bad = set(statuses) - {"VALID_PREVIEW", "EMPTY_UNREPORTED_NOT_ZERO"}
    if bad:
        print("PHASE2_FAIL_CLOSED_BAD_RESPONSES", sorted(bad), flush=True)
        raise SystemExit(2)
    print("PHASE2_SOURCE_COHORT_SUCCESS", args.cohort,
          "valid", statuses["VALID_PREVIEW"], "empty", statuses["EMPTY_UNREPORTED_NOT_ZERO"],
          "records", len(partners), flush=True)


if __name__ == "__main__":
    main()
