#!/usr/bin/env python3
"""Reclassify ambiguous 47x18 metadata into exact country vs customs-area candidate.

Source Comtrade M49 251 (France customs area) and 842 (US customs area) are
NOT identical to ISO numeric FRA 250 and USA 840. Inspect original sha-verified
yearly getDA responses and preserve both identities without collapsing them.
"""
from __future__ import annotations
import csv,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
RAW=ROOT/"outputs/extended/source_47_edition_all_years"
SOURCE=ROOT/"data/extended/comtrade/source_hs_revisions_47"
COV=SOURCE/"FULL_COVERAGE_AND_PROVENANCE.json"
TABLE=SOURCE/"47_country_18_year_HS_revision_2005_2022.csv"
LOCK=ROOT/"config/extended/phase2_original_47_country_sample_lock.json"
BASE=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
OUT=SOURCE
CANDIDATES={"FRA":{"strict_m49":250,"candidate_m49":251},
            "USA":{"strict_m49":840,"candidate_m49":842}}
VALID={"H0","H1","H2","H3","H4","H5","H6"}
def read(p):
 with p.open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))
def main():
  lock=json.loads(LOCK.read_text(encoding="utf-8"))
  assert hashlib.sha256(BASE.read_bytes()).hexdigest()==lock["original_data_sha256"]
  prov=json.loads(COV.read_text(encoding="utf-8"))
  assert prov["sample_country_year_slots"]==846 and prov["source_metadata_requests"]==18
  raw_by_year={}
  for yr in prov["source"]:
    year=int(yr["Year"]);path=RAW/f"raw_getDA_all_reporters_{year}.json"
    b=path.read_bytes()
    assert hashlib.sha256(b).hexdigest()==yr["sha256"]
    obj=json.loads(b)
    assert obj["count"]==yr["raw_rows"]==len(obj["data"])
    assert all(int(r["period"])==year for r in obj["data"])
    raw_by_year[year]=obj["data"]
  original=read(TABLE)
  assert len(original)==846
  revised=[]
  flags=Counter()
  for row in original:
    iso,year=row["ISO3"],int(row["Year"])
    strict=int(row["M49"]);source_rev=row["source_HS_edition"]
    candidate_code="";candidate_revision="";candidate_match_count=0
    territory_status="EXACT_ISO_COUNTRY_SOURCE"
    if iso in CANDIDATES:
       c=CANDIDATES[iso]
       assert strict==c["strict_m49"]
       candidate_code=str(c["candidate_m49"])
       candidates=[r for r in raw_by_year[year]
                   if int(r.get("reporterCode",-1))==c["candidate_m49"]
                   and r.get("isOriginalClassification") is True
                   and r.get("classificationCode") in VALID]
       editions=sorted({r["classificationCode"] for r in candidates})
       candidate_match_count=len(candidates)
       candidate_revision=editions[0] if len(editions)==1 else ""
       if source_rev:
           territory_status="STRICT_AND_CUSTOMS_CANDIDATE_REQUIRE_SEPARATE_REVIEW"
       elif len(editions)==1:
           territory_status="CUSTOMS_AREA_CANDIDATE_NOT_EXACT_COUNTRY"
       else:
           territory_status="MISSING_OR_AMBIGUOUS_CUSTOMS_CANDIDATE"
    elif row["status"]!="VERIFIED_SINGLE_SOURCE_REVISION":
       assert not source_rev
       territory_status="MISSING_EXACT_SOURCE_NOT_ZERO"
    elif source_rev not in VALID:raise ValueError("Invalid source revision")
    q=dict(row)
    q.update({
       "exact_original_ISO_country_M49":strict,
       "exact_original_country_source_revision":source_rev,
       "customs_area_candidate_reporter_M49":candidate_code,
       "customs_area_candidate_HS_revision":candidate_revision,
       "customs_area_original_source_records":candidate_match_count,
       "geographic_join_quality":territory_status,
       "candidate_not_automatically_approved_as_original_country":"TRUE",
       "do_not_impute_missing_as_zero":"TRUE"})
    revised.append(q);flags[territory_status]+=1
  assert len(revised)==846 and len({(x["ISO3"],x["Year"]) for x in revised})==846
  assert flags["EXACT_ISO_COUNTRY_SOURCE"]==804,dict(flags)
  assert sum(flags.values())==846
  OUT.mkdir(parents=True,exist_ok=True)
  with (OUT/"47_country_18_year_source_HS_with_customs_area_flags.csv").open(
       "w",encoding="utf-8",newline="") as f:
    wr=csv.DictWriter(f,fieldnames=list(revised[0]),lineterminator="\n")
    wr.writeheader();wr.writerows(revised)
  manifest={
     "phase":"EXTENDED_DATA_EXPERIMENTAL",
     "original_47_country_years":846,"raw_getDA_responses_SHA256_verified":18,
     "geographic_mapping_statuses":dict(flags),
     "country_specific_customs_candidates":CANDIDATES,
     "source_CANDIDATE_not_identical_to_ISO_country":True,
     "FRA_source_strict_country":250,
     "FRA_reporting_customs_area_candidate":251,
     "USA_source_strict_country":840,
     "USA_reporting_customs_area_candidate":842,
     "no_automatic_geographic_substitution":True,
     "no_FTECH_until_equivalent_economic_unit_design":True,
     "no_missing_zero_fill":True,
     "source_baseline_hash_verified":lock["original_data_sha256"],
  }
  (OUT/"FULL_47_REPORTER_CUSTOMS_AREA_CANDIDATE_AUDIT.json").write_text(
      json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
  print("47x18_SOURCE_REPORTER_CUSTOMS_AREA_CROSSWALK",dict(flags),flush=True)
if __name__=="__main__":main()
