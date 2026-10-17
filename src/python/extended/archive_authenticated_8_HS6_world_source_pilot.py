#!/usr/bin/env python3
"""Promote exactly one validated authenticated full Comtrade 8-HS6 World pilot.

Read original GitHub Actions artifacts, verify both SHA256 and original baseline
without ever recovering/storing the subscription key, persist source-only data.
"""
from __future__ import annotations
import csv,hashlib,json,math,shutil
from decimal import Decimal
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[3]
INPUT=ROOT/"outputs/extended/official_comtrade_full_api_preflight"
RAW=INPUT/"raw_2017_AZE_8_ict_hs6_full_api.json"
QA=INPUT/"QUALITY.json"
ORIG=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
LOCK=ROOT/"config/extended/phase2_original_47_country_sample_lock.json"
CAT=ROOT/"data/extended/official_ict_hs6/unctad_ict_goods_official_hs6_1992_to_2022.csv"
OUT=ROOT/"data/extended/comtrade/authenticated_HS6_2017_AZE_source_pilot"
def main():
  lock=json.loads(LOCK.read_text(encoding="utf-8"))
  assert hashlib.sha256(ORIG.read_bytes()).hexdigest()==lock["original_data_sha256"]
  q=json.loads(QA.read_text(encoding="utf-8"))
  raw=RAW.read_bytes()
  assert hashlib.sha256(raw).hexdigest()==q["raw_response_sha256"]
  assert hashlib.sha256(CAT.read_bytes()).hexdigest()==q["reference_catalog_sha256"]
  assert q["http_status"]==200 and q["year_2017_revision_is_source_verified"]
  assert q["source_query_breakdownMode"]=="classic"
  assert q["source_world_partner_and_all_transport_customs_only"]
  assert q["source_edition_verified_from_authenticated_getDa"]=="H4"
  assert q["all_8_products_present"]
  assert not q["goods_with_missing_source_rows_not_zero"]
  assert q["observed_rows_including_world"]==8
  wanted=q["expected_product_codes"]
  assert len(wanted)==len(set(wanted))==8
  with CAT.open(encoding="utf-8",newline="") as f:
    official={r["HS6"]:r for r in csv.DictReader(f) if r["Comtrade_classificationCode"]=="H4"}
  assert set(wanted).issubset(official)
  obj=json.loads(raw)
  assert isinstance(obj,dict) and obj.get("count")==8
  source=obj.get("data")
  assert isinstance(source,list) and len(source)==8
  data=[]
  for row in source:
    code=str(row["cmdCode"])
    assert code in wanted
    assert int(row["reporterCode"])==31 and int(row["period"])==2017
    assert row["classificationCode"]=="H4"
    assert row["flowCode"]=="M"
    assert int(row["partnerCode"])==0
    assert int(row.get("partner2Code",-1))==0
    assert int(row.get("motCode",-1))==0
    assert row["customsCode"]=="C00"
    assert row["isOriginalClassification"] is True
    assert row["isAggregate"] is True
    val=Decimal(str(row["primaryValue"]))
    assert val.is_finite() and val>=0
    data.append({
      "reporter_ISO3":"AZE","Year":2017,
      "reporter_M49":31,"partner_M49_WORLD":0,
      "HS_version_reported":"H4",
      "HS6":code,
      "UNCTAD_ICT_group":official[code]["ICT_group"],
      "goods_description_source_UNCTAD":official[code]["description_as_published"],
      "flow":"M","nominal_import_value_usd":str(val),
      "source_route":"Comtrade full /data/v1/get/C/A/HS",
      "breakdownMode":"classic",
      "partner2Code":0,"motCode":0,"customsCode":"C00",
      "raw_source_sha256":q["raw_response_sha256"],
      "sample_original_47_source_only":"TRUE",
      "bilateral_partner_network_ready":"FALSE",
      "FTECH_or_GMM_approved":"FALSE"})
  assert set(r["HS6"] for r in data)==set(wanted)
  assert len(set(r["HS6"] for r in data))==8
  assert sum(1 for r in data if Decimal(r["nominal_import_value_usd"])>0)>=1
  OUT.mkdir(parents=True,exist_ok=True)
  dest=OUT/"AZE_2017_eight_HS6_world_source.csv"
  with dest.open("w",encoding="utf-8",newline="") as f:
     wr=csv.DictWriter(f,fieldnames=list(data[0]),lineterminator="\n")
     wr.writeheader();wr.writerows(sorted(data,key=lambda r:r["HS6"]))
  shutil.copyfile(RAW,OUT/"AZE_2017_eight_HS6_world_raw_comtrade.json")
  manifest={
    "phase":"EXTENDED_DATA_EXPERIMENTAL","authenticated_full_source_response_verified":True,
    "original_professor_panel_sha256":lock["original_data_sha256"],
    "original_raw_comtrade_sha256":q["raw_response_sha256"],
    "original_getDA_response_sha256":q["getDa_response_sha256"],
    "UNCTAD_official_catalog_sha256":q["reference_catalog_sha256"],
    "official_reporter_year_HS":"H4",
    "original_source_world_rows":8,"verified_unique_official_ict_HS6_codes":8,
    "nominal_usd_fields":True,
    "World_only_no_individual_foreign_origins":True,
    "HS6_historical_cross_edition_concordance_not_yet_verified":True,
    "source_2017_country_specific_data_only":True,
    "FTECH_or_GMM_ready":False,
    "secret_not_stored":True,
    "all_source_values_observed_not_imputed":True,
  }
  (OUT/"PROVENANCE_AND_QUALITY.json").write_text(
      json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  print("PHASE2_AUTHENTICATED_HS6_WORLD_SOURCE_ARCHIVED",len(data),
        "H4 official source AZE2017; no World sum over duplicates",flush=True)
if __name__=="__main__":main()
