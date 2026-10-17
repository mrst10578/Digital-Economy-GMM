#!/usr/bin/env python3
"""Permanent compressed audit archive for all 18 original Comtrade getDA replies.

GitHub Actions artifacts expire; preserves public unmodified response bytes
behind SHA256 evidence so full 47x18 metadata can be reproduced years later.
"""
from __future__ import annotations
import hashlib,json,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
TEMP=ROOT/"outputs/extended/source_47_edition_all_years"
OUT=ROOT/"data/extended/comtrade/source_hs_revisions_47"
MANIFEST=OUT/"FULL_COVERAGE_AND_PROVENANCE.json"
def main():
  prov=json.loads(MANIFEST.read_text(encoding="utf-8"))
  assert prov["sample_country_year_slots"]==846
  assert prov["source_metadata_requests"]==18
  members={}
  total=0
  for item in prov["source"]:
    y=int(item["Year"])
    assert 2005<=y<=2022 and y not in members
    p=TEMP/f"raw_getDA_all_reporters_{y}.json"
    b=p.read_bytes()
    assert hashlib.sha256(b).hexdigest()==item["sha256"]
    parsed=json.loads(b)
    assert parsed["count"]==len(parsed["data"])==item["raw_rows"]
    assert all(int(r["period"])==y for r in parsed["data"])
    members[y]=p
    total+=len(b)
  assert sorted(members)==list(range(2005,2023))
  OUT.mkdir(parents=True,exist_ok=True)
  dest=OUT/"UN_Comtrade_public_getDA_18_original_year_responses_2005_2022.tar.gz"
  with tarfile.open(dest,"w:gz",compresslevel=9) as tar:
    for y in sorted(members):
      tar.add(members[y],arcname=members[y].name,recursive=False)
  digest=hashlib.sha256(dest.read_bytes()).hexdigest()
  with tarfile.open(dest,"r:gz") as archive:
    assert sorted(archive.getnames())==sorted(p.name for p in members.values())
    for year in sorted(members):
      with archive.extractfile(members[year].name) as stream:
         assert hashlib.sha256(stream.read()).hexdigest()==next(
             r["sha256"] for r in prov["source"] if r["Year"]==year)
  summary={
     "phase":"EXTENDED_DATA_EXPERIMENTAL",
     "original_source_bytes_total":total,
     "raw_annual_sources_sha256_verified":18,
     "country_year_slots_exact":846,
     "tar_gz_size_bytes":dest.stat().st_size,
     "tar_gz_sha256":digest,
     "original_response_sha256_by_year":{str(r["Year"]):r["sha256"] for r in prov["source"]},
     "source_endpoint_public":"https://comtradeapi.un.org/public/v1/getDA/C/A/HS",
     "source_public_data_no_subscription_key_required":True,
     "no_original_professor_panel_edited":True,
     "archive_contains_only_observed_original_metadata":True,
     "not_final_HS6_bilateral_network":True,
     "missing_not_fabricated_zero":True,
  }
  (OUT/"PERMANENT_18_RAW_GETDA_SOURCE_ARCHIVE_PROVENANCE.json").write_text(
     json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  print("PHASE2_ALL_18_OFFICIAL_SOURCE_RESPONSES_PERMANENTLY_HASH_VERIFIED",
        total,"original bytes",dest.stat().st_size,"archive bytes",flush=True)
if __name__=="__main__":main()
