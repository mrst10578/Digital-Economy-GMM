#!/usr/bin/env python3
"""Two-slice real HS6 bilateral full Comtrade pilot with source-area safeguards.

Never substitute customs-area reporters for ISO states. Original country panel
remains read-only; do not estimate FTECH or GMM from these demonstration years.
"""
from __future__ import annotations
import csv,hashlib,json,os,time,math
from datetime import datetime,timezone
from decimal import Decimal
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode
from urllib.request import Request,urlopen
import pycountry

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
LOCK=ROOT/"config/extended/phase2_original_47_country_sample_lock.json"
FLAGS=ROOT/"data/extended/comtrade/source_hs_revisions_47/47_country_18_year_source_HS_with_customs_area_flags.csv"
CAT=ROOT/"data/extended/official_ict_hs6/unctad_ict_goods_official_hs6_1992_to_2022.csv"
OUT=ROOT/"data/extended/comtrade/authenticated_HS6_two_bilateral_source_pilot"
LIMIT=500
CASES=[
  ("AZE",2017,31,"H4","847130","EXACT_ISO_COUNTRY_SOURCE"),
  ("USA",2022,842,"H6","847130","CUSTOMS_AREA_CANDIDATE_NOT_EXACT_COUNTRY")
]
def get_raw(key,url):
  for attempt in range(3):
    try:
      with urlopen(Request(url,headers={"User-Agent":"Academic-ICT-HS6-Bilateral-Full-Source-Pilot/1.0",
        "Ocp-Apim-Subscription-Key":key,"Accept":"application/json"}),timeout=80) as response:
        body=response.read(15_000_001)
        if len(body)>15_000_000:raise ValueError("Response larger than raw bound")
        assert response.status==200
        return body
    except HTTPError as exc:
      if exc.code in (429,500,502,503,504) and attempt<2:
        time.sleep(13*(attempt+1));continue
      raise RuntimeError(f"Comtrade HS6 source HTTP {exc.code}; no invalid data promoted") from None
    except (TimeoutError,URLError):
      if attempt<2:time.sleep(13*(attempt+1));continue
      raise RuntimeError("Comtrade source connection could not be verified") from None
  raise RuntimeError("Comtrade source unavailable")
def main():
  key=os.environ.get("COMTRADE_API_KEY","").strip()
  if not key:raise RuntimeError("Secret required; no HTTP requests made")
  lock=json.loads(LOCK.read_text(encoding="utf-8"))
  assert hashlib.sha256(BASE.read_bytes()).hexdigest()==lock["original_data_sha256"]
  country_to_m49={}
  for iso in lock["iso3_to_original_country_name"]:
    o=pycountry.countries.get(alpha_3=iso)
    assert o is not None
    country_to_m49[int(o.numeric)]=iso
  source_rows={}
  with FLAGS.open(encoding="utf-8",newline="") as f:
    for row in csv.DictReader(f):
      source_rows[(row["ISO3"],int(row["Year"]))]=row
  assert len(source_rows)==846
  goods={}
  with CAT.open(encoding="utf-8",newline="") as f:
    for row in csv.DictReader(f):
      goods[(row["Comtrade_classificationCode"],row["HS6"])]=row
  rows=[];reports=[]
  OUT.mkdir(parents=True,exist_ok=True)
  for iso,year,reporter,revision,code,status in CASES:
    source=source_rows[(iso,year)]
    assert source["geographic_join_quality"]==status
    if status=="EXACT_ISO_COUNTRY_SOURCE":
      assert int(source["M49"])==reporter
      assert source["source_HS_edition"]==revision
    else:
      assert int(source["customs_area_candidate_reporter_M49"])==reporter
      assert source["customs_area_candidate_HS_revision"]==revision
      assert source["source_HS_edition"]==""
    assert (revision,code) in goods
    parameters={"reporterCode":reporter,"period":year,"flowCode":"M",
       "cmdCode":code,"partner2Code":0,"motCode":0,"customsCode":"C00",
       "maxRecords":LIMIT,"breakdownMode":"classic"}
    url="https://comtradeapi.un.org/data/v1/get/C/A/HS?"+urlencode(parameters)
    raw=get_raw(key,url)
    doc=json.loads(raw)
    assert isinstance(doc,dict) and isinstance(doc.get("data"),list)
    records=doc["data"]
    assert doc.get("count")==len(records)
    assert 0<len(records)<LIMIT, "Empty or truncated source, cannot promote"
    digest=hashlib.sha256(raw).hexdigest()
    (OUT/f"{iso}_{year}_{revision}_{code}_all_origins_raw.json").write_bytes(raw)
    partners=set()
    world=None;strict_sum=Decimal(0);strict_count=0
    for r in records:
       assert int(r["reporterCode"])==reporter
       assert int(r["period"])==year
       assert r["classificationCode"]==revision
       assert r["isOriginalClassification"] is True
       assert r["flowCode"]=="M" and str(r["cmdCode"])==code
       assert int(r.get("partner2Code",-1))==0
       assert int(r.get("motCode",-1))==0
       assert r.get("customsCode")=="C00"
       partner=int(r["partnerCode"])
       assert partner>=0 and partner not in partners
       partners.add(partner)
       val=Decimal(str(r["primaryValue"]))
       assert val.is_finite() and val>=0
       if partner==0:
         world=val
       if partner in country_to_m49 and partner not in (0,reporter):
         strict_sum+=val;strict_count+=1
       rows.append({"reporter_ISO3_original_candidate":iso,"Year":year,
        "reporter_area_M49_as_reported":reporter,
        "reporter_area_geographic_flag":status,
        "partner_M49_as_reported":partner,
        "partner_ISO3_strict_country_if_in_original_47":country_to_m49.get(partner,""),
        "partner_customs_area_candidate_flag":(
            "CUSTOMS_AREA_FRANCE_NONEXACT" if partner==251 else
            "CUSTOMS_AREA_USA_NONEXACT" if partner==842 else ""),
        "HS_revision_source":revision,"HS6":code,
        "ICT_group_UNCTAD":goods[(revision,code)]["ICT_group"],
        "nominal_usd_import_value":str(val),
        "is_world_aggregate":"TRUE" if partner==0 else "FALSE",
        "classic_all_customs_transport":"TRUE",
        "raw_response_sha256":digest,
        "not_final_FTECH_or_causal":"TRUE"})
    if world is None:raise RuntimeError("No World row: fail closed")
    if strict_sum>world*Decimal("1.15") and world!=0:
       raise RuntimeError("Strict country partners exceed World by >15%; investigate overlapping values")
    reports.append({
      "reporter_ISO3_candidate":iso,"Year":year,
      "reporter_M49_as_reported":reporter,
      "geographic_join_flag":status,"actual_original_HS_revision":revision,
      "HS6":code,"official_ICT_group":goods[(revision,code)]["ICT_group"],
      "http_status":200,"api_rows_including_world":len(records),
      "world_nominal_import_usd":str(world),
      "strict_original_47_observed_partner_country_count":strict_count,
      "strict_original_47_partner_sum_usd":str(strict_sum),
      "strict_subset_share_of_world":str(strict_sum/world) if world else None,
      "source_raw_sha256":digest,
      "no_record_imputed_zero":True,"no_source_country_area_equivalency_claim":True,
      "source_revision_verified_from_all_47_getDA":True,
      "partner_country_vs_customs_area_not_automatically_equated":True,
    })
    print("SOURCE_VERIFIED_FULL_HS6_BILATERAL",iso,year,revision,code,
       "partner_rows_including_world",len(records),"world_usd",world,
       "strict_original_partner_count",strict_count,flush=True)
    time.sleep(10)
  assert len(reports)==2
  assert len(rows)==sum(r["api_rows_including_world"] for r in reports)
  assert len({(r["reporter_ISO3_original_candidate"],r["Year"],
             r["HS6"],r["partner_M49_as_reported"]) for r in rows})==len(rows)
  with (OUT/"two_HS6_all_original_partner_records.csv").open(
       "w",encoding="utf-8",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n")
    w.writeheader();w.writerows(rows)
  with (OUT/"QUALITY_PROVENANCE.json").open("w",encoding="utf-8") as f:
     json.dump({
       "phase":"EXTENDED_DATA_EXPERIMENTAL",
       "original_source_sha256":lock["original_data_sha256"],
       "raw_source_HTTP_body_SHA_held_as_files":True,
       "full_api_HS_as_reported_with_original_source_revision":True,
       "all_customs_transport_classic_nonduplicate_partner":True,
       "reporters":reports,
       "cannot_treat_customs_area_USA_842_as_exact_USA_840":True,
       "FTECH_trade_weights_cannot_be_built_from_two_pilot_slices":True,
       "historically_harmonized_ICT_products_not_approved":True,
       "key_not_stored":True,
       "timestamp_utc":datetime.now(timezone.utc).isoformat()
     },f,ensure_ascii=False,indent=2)
     f.write("\n")
  print("FULL_SOURCE_BILATERAL_PILOT_VERIFIED_TOTAL_ROWS",len(rows),flush=True)
if __name__=="__main__":main()
