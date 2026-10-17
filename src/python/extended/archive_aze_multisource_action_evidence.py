#!/usr/bin/env python3
"""Archive authentic AZE historic partner data from existing GH Actions artifact.

Must be invoked ONLY after downloading immutable completed Actions artifact from
run 39017139253. No new Comtrade API request, no Stata, no causal estimation.
Preserves normalized partner-level values and full response SHA-256 hashes.

Pre-2005:2007 fixed weight screen is DESCRIPTIVE ONLY, source-country-year
missingness is *not* imputed to zero. Never use these partial weights directly
as fully identified FTECH or spillover instrument.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
ART=ROOT/"outputs/extended/artefact_run_39017139253"
OUT=ROOT/"data/extended/comtrade"
EVIDENCE=ROOT/"evidence/extended"
LOCK=ROOT/"config/extended/phase2_original_47_country_sample_lock.json"
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
SRC_RUN=39017139253
WORLD_M49=0
BASE_YEARS=(2005,2006,2007)
HSCODES=("8471","8517")

def load_rows(path):
    with path.open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))

def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)

def main():
    config=json.loads(LOCK.read_text(encoding="utf-8"))
    actual_sha=hashlib.sha256(RAW.read_bytes()).hexdigest()
    assert actual_sha==config["original_data_sha256"]
    rows=load_rows(ART/"partner_observations.csv")
    coverage=load_rows(ART/"year_HS4_36_coverage.csv")
    summary=json.loads((ART/"summary.json").read_text(encoding="utf-8"))
    assert len(rows)==1863 and len(coverage)==36 and summary["requests_bad_or_truncated"]==0
    allowed={str(c) for c in config["iso3_to_original_country_name"]}
    assert len(allowed)==47
    bucket=defaultdict(dict)
    for r in rows:
        y=int(r["Year"])
        h=r["HS4"]
        m49=int(r["partner_M49"])
        iso=r["partner_ISO3_if_in_original_sample"]
        val=float(r["value_nominal_usd"])
        assert 2005<=y<=2022 and h in HSCODES and math.isfinite(val) and val>=0
        assert not iso or iso in allowed
        assert str(r["is_world_aggregate"]).lower()==str(m49==WORLD_M49).lower()
        assert m49 not in bucket[y,h],"Duplicate origin for year/HS heading"
        bucket[y,h][m49]=(val,iso)
    assert set(bucket)=={(y,h) for y in range(2005,2023) for h in HSCODES}
    world_sums=0.0
    orig_sums=0.0
    # Recompute all supplied aggregate numbers from real partner records AND
    # check original raw API JSON hashes before placing material in repository.
    for r in coverage:
        y=int(r["Year"]);h=r["HS4"];pairs=bucket[y,h]
        assert r["status"]=="VALID_PREVIEW"
        assert len(pairs)==int(r["all_distinct_partner_rows"])
        world=pairs[0][0]
        subset=sum(v for p,(v,iso) in pairs.items() if iso and iso!="AZE")
        assert math.isclose(world,float(r["world_imports_nominal_usd"]),rel_tol=1e-11)
        assert math.isclose(subset,float(r["original_47_origin_summed_imports_usd"]),rel_tol=1e-10,abs_tol=0.05)
        raw=(ART/"raw_API"/f"AZE_{y}_HS{h}_all_partner_rows.json").read_bytes()
        assert hashlib.sha256(raw).hexdigest()==r["raw_sha256"]
        if y in BASE_YEARS:
            world_sums+=world
            orig_sums+=subset
    origin_pre=defaultdict(list)
    for y in BASE_YEARS:
        for h in HSCODES:
            for m49,(amount,iso) in bucket[y,h].items():
                if iso and iso!="AZE":
                    origin_pre[iso].append((y,h,amount))
    all_origins={iso for pairs in bucket.values() for _,iso in pairs.values() if iso and iso!="AZE"}
    w=[]
    for iso in sorted(all_origins):
        observed=origin_pre.get(iso,[])
        unique={(y,h) for y,h,v in observed}
        assert len(unique)==len(observed)
        observed_sum=sum(v for y,h,v in observed)
        w.append({
            "destination_ISO3":"AZE","origin_ISO3":iso,
            "preperiod":"2005-2007","HS4":"8471+8517",
            "preperiod_observed_cells_out_of_6":len(unique),
            "all_6_cells_observed":len(unique)==6,
            "preperiod_reported_value_nominal_USD":format(observed_sum,".6f") if unique else "",
            "partial_reported_share_of_world_HS4":format(observed_sum/world_sums,".12f") if unique else "",
            "usable_as_final_weight":False,
            "missing_origin_year_heading_not_imputed":True,
            "not_a_causal_GMM_instrument":True,
        })
    assert len(w)==42 and sum(r["all_6_cells_observed"] for r in w)==19
    assert math.isclose(orig_sums/world_sums,.9069913984650341,abs_tol=1e-10)
    OUT.mkdir(parents=True,exist_ok=True)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    (OUT/"AZE_HS8471_8517_all_origins_2005_2022.csv").write_bytes((ART/"partner_observations.csv").read_bytes())
    (OUT/"AZE_HS8471_8517_annual_source_coverage.csv").write_bytes((ART/"year_HS4_36_coverage.csv").read_bytes())
    write_csv(OUT/"AZE_2005_2007_preliminary_source_weight_screen.csv",w)
    manifest={
      "phase":"EXTENDED_DATA_EXPERIMENTAL",
      "original_data_sha256":actual_sha,"original_phase_professor_modified":False,
      "source_run":SRC_RUN,"source_artifact":"PHASE2-AZE-all-partners-HS8471-HS8517-2005-2022-raw-audit",
      "original_partner_source_rows":len(rows),
      "annual_headings_checked":len(coverage),
      "raw_response_sha256_verified_count":len(coverage),
      "preperiod_2005_2007_world_import_HS8471_plus_8517_USD":world_sums,
      "preperiod_observed_origins_in_original_47_import_USD":orig_sums,
      "reported_47_origin_share":orig_sums/world_sums,
      "origins_ever_observed":len(w),
      "origins_preperiod_all_six_cells_observed":sum(r["all_6_cells_observed"] for r in w),
      "raw_json_retention":"Underlying GitHub Actions artifact expires after 30 days. Original raw payload hashes remain in annual source coverage file.",
      "data_quality":"No duplicate country-partner-year-heading rows; 36/36 source hashes match; no imputation.",
      "scientific_boundaries":[
          "These two HS headings are neither exhaustive nor time-harmonized ICT goods.",
          "Comtrade preview partner absence is missing, not a zero-trade claim.",
          "Partial origin shares over 2005-2007 World are not valid fully observed final trade weights.",
          "No FTECH index is computed. No valid causal instrument or external knowledge spillover is established.",
          "Only receiver Azerbaijan is represented for all-source historical HS4 lines."
      ],
      "st ata required".replace(" ","_"):False,
    }
    (OUT/"PROVENANCE_AND_QUALITY.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PHASE2_PERMANENT_PARTNER_ARCHIVE_PASS",len(rows),"rows",len(coverage),"year-headings",
          len(w),"original destinations",sum(r["all_6_cells_observed"] for r in w),"six-cell complete origins")
    print("PHASE2_PREPERIOD_WORLD_ORIGIN_COVERAGE",orig_sums/world_sums)
    print("PHASE2_CAUSAL_SPILLOVER_VALIDATED=FALSE; NO STATA; PHASE A UNCHANGED")

if __name__=="__main__":
    main()
