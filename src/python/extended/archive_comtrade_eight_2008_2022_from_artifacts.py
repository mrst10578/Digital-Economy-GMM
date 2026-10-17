#!/usr/bin/env python3
"""Merge four independent 2008-22 Comtrade source shards after FULL raw auditing.

Read all 240 original API responses from Actions artifacts and compare with every
normalized country-year-HS-partner observation. Preserve missing slices.
Only *source evidence*, not country-year panel models, is published in phase B.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOCK = ROOT / "config/extended/phase2_original_47_country_sample_lock.json"
BASE = ROOT / "data/raw/Balanced_Panel_Data.xlsx"
IN_ROOT = ROOT / "outputs/extended/phase2_eight_2008_22"
BASE_CSV_ROOT = ROOT / "data/extended/comtrade/oecd_missing_hs4_preperiod"
OUT = ROOT / "data/extended/comtrade/oecd_missing_hs4_2008_2022"
RECEIVERS = ("KGZ", "MAC", "MDA", "MKD", "MNG", "PAN", "TTO", "URY")
COHORTS = {"A": ("KGZ", "MAC"), "B": ("MDA", "MKD"),
           "C": ("MNG", "PAN"), "D": ("TTO", "URY")}
HS = ("8471", "8517")
COV_COLUMNS = (
    "reporter_ISO3", "Year", "HS4", "status", "response_rows",
    "valid_origin_rows_ex_world", "original_47_origin_count",
    "world_nominal_usd", "sum_original_47_origins_nominal_usd",
    "observed_original_47_origin_share_of_world", "raw_response_sha256",
    "url", "error", "preview_not_exhaustive", "missing_not_zero", "causal_claim"
)
SRC_COLUMNS = (
    "reporter_ISO3", "Year", "HS4", "partner_M49",
    "partner_ISO3_if_in_original_sample", "is_world_aggregate",
    "value_nominal_usd", "source_year_classification",
    "not_complete_or_causal_spillover"
)


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path, columns, data):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(data)


def main():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    hash_original = hashlib.sha256(BASE.read_bytes()).hexdigest()
    assert hash_original == lock["original_data_sha256"], "Baseline SHA changed"
    original_iso = set(lock["iso3_to_original_country_name"])
    assert len(original_iso) == 47 and set(RECEIVERS).issubset(original_iso)
    all_coverage, all_partners = [], []
    evidence_counts = {}
    for cohort, receiver_pair in COHORTS.items():
        shard = IN_ROOT / ("PHASE2-EIGHT-2008-2022-" + cohort)
        coverage = read_csv(shard / "coverage.csv")
        partners = read_csv(shard / "partner_records.csv")
        meta = json.loads((shard / "manifest.json").read_text(encoding="utf-8"))
        assert meta["cohort"] == cohort
        assert tuple(meta["receivers"]) == receiver_pair
        assert meta["original_data_sha256"] == hash_original
        assert meta["expected_queries"] == 60 and len(coverage) == 60
        assert meta["observed_partner_rows_including_world"] == len(partners)
        assert all(row["reporter_ISO3"] in receiver_pair for row in coverage)
        assert all(row["reporter_ISO3"] in receiver_pair for row in partners)
        assert set(row["status"] for row in coverage).issubset(
            {"VALID_PREVIEW", "EMPTY_UNREPORTED_NOT_ZERO"}
        ), "Bad response present: do not archive"
        observed_by_slice = defaultdict(list)
        for row in partners:
            year, hs = int(row["Year"]), row["HS4"]
            assert year in range(2008, 2023) and hs in HS
            v = float(row["value_nominal_usd"])
            assert math.isfinite(v) and v >= 0
            observed_by_slice[(row["reporter_ISO3"], year, hs)].append(row)
        for row in coverage:
            iso, year, hs = row["reporter_ISO3"], int(row["Year"]), row["HS4"]
            assert year in range(2008, 2023) and hs in HS
            filename = f"{iso}_{year}_HS{hs}_all_partners.json"
            raw = (shard / "raw_API" / filename).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == row["raw_response_sha256"]
            obj = json.loads(raw)
            records = obj["data"]
            part = observed_by_slice.get((iso, year, hs), [])
            if row["status"] == "EMPTY_UNREPORTED_NOT_ZERO":
                assert not part and len(records) == 0, "Missing mistakenly coded as zero"
                assert row["world_nominal_usd"] == ""
            else:
                assert row["status"] == "VALID_PREVIEW" and 0 < len(records) < 500
                assert len(part) == len(records) == int(row["response_rows"])
                ids = [int(x["partner_M49"]) for x in part]
                assert len(set(ids)) == len(ids), "Duplicate partner"
                assert ids.count(0) == 1, "Missing/duplicate World"
                for original, normalized in zip(records, part):
                    assert int(original["partnerCode"]) == int(normalized["partner_M49"])
                    assert str(original["cmdCode"]) == normalized["HS4"]
                    assert int(original.get("period", original.get("refYear"))) == year
                    assert original["flowCode"] == "M"
                    assert math.isclose(float(original["primaryValue"]),
                                        float(normalized["value_nominal_usd"]),
                                        rel_tol=1e-12, abs_tol=1e-7)
                world = next(float(x["value_nominal_usd"]) for x in part
                             if int(x["partner_M49"]) == 0)
                assert math.isclose(world, float(row["world_nominal_usd"]), rel_tol=1e-12)
                assert row["preview_not_exhaustive"] == "TRUE"
        evidence_counts[cohort] = {
            "requests": len(coverage), "partner_records_including_world": len(partners),
            "status_counts": dict(Counter(row["status"] for row in coverage))
        }
        all_coverage.extend(coverage)
        all_partners.extend(partners)

    assert len(all_coverage) == 240
    uniq = {(r["reporter_ISO3"], int(r["Year"]), r["HS4"]) for r in all_coverage}
    assert uniq == {(iso, y, hs) for iso in RECEIVERS for y in range(2008, 2023) for hs in HS}
    keys = [(r["reporter_ISO3"], int(r["Year"]), r["HS4"], int(r["partner_M49"]))
            for r in all_partners]
    assert len(keys) == len(set(keys))
    prior_cov = read_csv(BASE_CSV_ROOT / "coverage_2005_2007.csv")
    prior_src = read_csv(BASE_CSV_ROOT / "partner_records_2005_2007.csv")
    assert len(prior_cov) == 48 and len(prior_src) == 2030
    assert len(all_coverage) + len(prior_cov) == 288
    assert all(int(r["Year"]) <= 2007 for r in prior_cov)
    assert all(int(r["Year"]) <= 2007 for r in prior_src)
    all_coverage.sort(key=lambda r: (r["reporter_ISO3"], int(r["Year"]), r["HS4"]))
    all_partners.sort(key=lambda r: (r["reporter_ISO3"], int(r["Year"]), r["HS4"],
                                     int(r["partner_M49"])))
    full_coverage = sorted(prior_cov + all_coverage,
                           key=lambda r: (r["reporter_ISO3"], int(r["Year"]), r["HS4"]))
    assert len({(r["reporter_ISO3"], int(r["Year"]), r["HS4"]) for r in full_coverage}) == 288
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "coverage_2008_2022.csv", COV_COLUMNS, all_coverage)
    write_csv(OUT / "partner_records_2008_2022.csv", SRC_COLUMNS, all_partners)
    write_csv(OUT / "eight_receivers_coverage_2005_2022.csv", COV_COLUMNS, full_coverage)
    full_obs = prior_src + all_partners
    all_keys = [(r["reporter_ISO3"], r["Year"], r["HS4"], r["partner_M49"])
                for r in full_obs]
    assert len(set(all_keys)) == len(full_obs)
    status = dict(Counter(r["status"] for r in full_coverage))
    meta = {
        "phase": "EXTENDED_DATA_EXPERIMENTAL",
        "source": "UN Comtrade public preview, potentially incomplete irrespective of record count",
        "original_baseline_sha256_verified": hash_original,
        "reporter_countries": list(RECEIVERS),
        "years_coverage_2005_2022": [2005, 2022],
        "HS4_headings_only": list(HS),
        "extended_queries_2008_2022": len(all_coverage),
        "all_eight_reporter_year_hs_queries_2005_2022": len(full_coverage),
        "additional_partner_rows_including_world": len(all_partners),
        "total_eight_reporter_partner_rows_including_world": len(full_obs),
        "quality_by_cohort": evidence_counts,
        "all_historical_status_counts": status,
        "status_empty_means_unreported_not_zero": True,
        "raw_JSON_SHA256_per_query_verified": 240,
        "HS_subheadings_not_harmonized": True,
        "source_country_territory_crosswalk_not_final": True,
        "not_complete_ICT_commodity_basket": True,
        "not_complete_47_receivers": True,
        "not_final_FTECH_or_causal_evidence": True,
        "phase_A_professor_data_unchanged": True,
    }
    (OUT / "PROVENANCE_2008_2022.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("PHASE2_EIGHT_RECIPIENTS_FULL_YEARS_VERIFIED",
          "new_query_slices", len(all_coverage), "new_partner_records", len(all_partners),
          "combined_slices", len(full_coverage), "statuses", status,
          "PREVIEW_NOT_EXHAUSTIVE_FTECH_NOT_READY", flush=True)


if __name__ == "__main__":
    main()
