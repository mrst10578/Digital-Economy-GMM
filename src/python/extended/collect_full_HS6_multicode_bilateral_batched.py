#!/usr/bin/env python3
"""Authenticated real all-partner HS6 ICT multi-code batching feasibility.

Two real reporter-years, 8 edition-specific official UNCTAD HS6 items each,
four codes per HTTP request to test efficient complete origin discovery.
Production 47x18 FTECH requires an explicit later design and concordance.
"""
from __future__ import annotations
import csv,hashlib,json,os,time
from collections import defaultdict
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[3]
CAT=ROOT/"data/extended/official_ict_hs6/unctad_ict_goods_official_hs6_1992_to_2022.csv"
LOCK=ROOT/"config/extended/phase2_original_47_country_sample_lock.json"
BASE=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
SOURCE=ROOT/"data/extended/comtrade/source_hs_revisions_47/47_country_18_year_source_HS_with_customs_area_flags.csv"
WORLD=ROOT/"data/extended/comtrade/authenticated_HS6_2017_AZE_source_pilot/AZE_2017_eight_HS6_world_source.csv"
BILATERAL=ROOT/"data/extended/comtrade/authenticated_HS6_two_bilateral_source_pilot/two_HS6_all_original_partner_records.csv"
OUT=ROOT/"data/extended/comtrade/authenticated_HS6_multicode_bilateral_batch_pilot"
CASES=[("AZE",2017,31,"H4","EXACT_ISO_COUNTRY_SOURCE"),
       ("USA",2022,842,"H6","CUSTOMS_AREA_CANDIDATE_NOT_EXACT_COUNTRY")]
def read(path):
 with path.open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))
def source_request(key,iso,year,reporter,codes):
  params={"reporterCode":reporter,"period":year,
      "flowCode":"M","cmdCode":",".join(codes),
      "partner2Code":0,"motCode":0,"customsCode":"C00",
      "maxRecords":50000,"breakdownMode":"classic"}
  url="https://comtradeapi.un.org/data/v1/get/C/A/HS?"+urlencode(params)
  for attempt in range(3):
    try:
      with urlopen(Request(url,headers={
        "User-Agent":"ICT-Research-Authenticated-HS6-Multicode-Original-Partner-Pilot/1.0",
        "Accept":"application/json","Ocp-Apim-Subscription-Key":key}),timeout=100) as f:
        b=f.read(30_000_001)
        if len(b)>30_000_000:raise ValueError("Body exceeds 30MB strict cap")
        assert f.status==200
      return b
    except HTTPError as exc:
      if exc.code in (429,500,502,503,504) and attempt<2:
        time.sleep(20*(attempt+1));continue
      raise RuntimeError(f"Comtrade full HS6 multi-code HTTP {exc.code} for {iso}-{year}") from None
    except (URLError,TimeoutError):
      if attempt<2:time.sleep(20*(attempt+1));continue
      raise RuntimeError(f"Comtrade full HS6 multi-code request timeout for {iso}-{year}") from None
  raise RuntimeError("Exhausted source retries")
def main():
  key=os.getenv("COMTRADE_API_KEY","").strip()
  if not key:raise RuntimeError("Missing Comtrade subscription secret: zero requests")
  baseline=json.loads(LOCK.read_text(encoding="utf-8"))
  assert hashlib.sha256(BASE.read_bytes()).hexdigest()==baseline["original_data_sha256"]
  catalog=read(CAT)
  catalogs=defaultdict(dict)
  for rec in catalog:catalogs[rec["Comtrade_classificationCode"]][rec["HS6"]]=rec
  assert len(catalog)==691 and len(catalogs)==7
  statuses={(r["ISO3"],int(r["Year"])):r for r in read(SOURCE)}
  assert len(statuses)==846
  prior_world={r["HS6"]:Decimal(r["nominal_import_value_usd"]) for r in read(WORLD)}
  assert len(prior_world)==8
  prior_bilateral={}
  for r in read(BILATERAL):
    if r["HS6"]=="847130" and r["is_world_aggregate"]=="TRUE":
      prior_bilateral[(r["reporter_ISO3_original_candidate"],int(r["Year"]))]=Decimal(r["nominal_usd_import_value"])
  assert len(prior_bilateral)==2
  OUT.mkdir(parents=True,exist_ok=True)
  provenance=[];partner_records=[];coverage=[]
  for iso,year,reporter,revision,geoflag in CASES:
    src=statuses[(iso,year)]
    assert src["geographic_join_quality"]==geoflag
    if geoflag=="EXACT_ISO_COUNTRY_SOURCE":
      assert src["source_HS_edition"]==revision and int(src["M49"])==reporter
    else:
      assert src["customs_area_candidate_HS_revision"]==revision
      assert int(src["customs_area_candidate_reporter_M49"])==reporter
      assert not src["source_HS_edition"]
    requested=sorted(catalogs[revision])[:8]
    assert len(requested)==8
    seen=set()
    for i in (0,4):
      codes=requested[i:i+4]
      raw=source_request(key,iso,year,reporter,codes)
      sha=hashlib.sha256(raw).hexdigest()
      name=f"{iso}_{year}_{revision}_batch_{i//4+1}_raw.json"
      (OUT/name).write_bytes(raw)
      doc=json.loads(raw)
      data=doc.get("data")
      assert isinstance(data,list) and doc.get("count")==len(data)
      assert len(data)<50000,"Full API maxRecords hit; records may be truncated"
      provenance.append({"reporter":iso,"Year":year,"source_reporter_area_M49":reporter,
          "source_HS_revision":revision,"HS6_requested":codes,
          "HTTP_200":True,"source_records":len(data),"raw_sha256":sha,
          "raw_response_file":name,"request_classic":True})
      for rec in data:
        code=str(rec["cmdCode"]);p=int(rec["partnerCode"])
        assert code in codes and (code,p) not in seen
        seen.add((code,p))
        assert int(rec["reporterCode"])==reporter
        assert int(rec["period"])==year
        assert rec["classificationCode"]==revision
        assert rec["isOriginalClassification"] is True
        assert rec["flowCode"]=="M"
        assert int(rec.get("partner2Code",-1))==0
        assert int(rec.get("motCode",-1))==0
        assert rec.get("customsCode")=="C00"
        v=Decimal(str(rec["primaryValue"]))
        assert v.is_finite() and v>=0
        partner_records.append({
          "reporter_ISO3_country_or_candidate":iso,"Year":year,
          "reporter_M49_as_reported":reporter,"reporter_geographic_flag":geoflag,
          "source_HS_revision":revision,"HS6":code,
          "UNCTAD_official_ICT_group":catalogs[revision][code]["ICT_group"],
          "partner_M49_as_reported":p,"partner_is_world":"TRUE" if p==0 else "FALSE",
          "partner_area_nonexact_flag":"FRANCE_CUSTOMS" if p==251 else "USA_CUSTOMS" if p==842 else "",
          "nominal_import_value_usd":str(v),
          "source_SHA256":sha,
          "not_final_FTECH":"TRUE"})
      print("PHASE2_SOURCE_MULTICODE_BILATERAL",iso,year,
            "code_batch",codes,"rows",len(data),flush=True)
      time.sleep(12)
    by_code=defaultdict(dict)
    for x in partner_records:
      if x["reporter_ISO3_country_or_candidate"]==iso and int(x["Year"])==year:
        by_code[x["HS6"]][int(x["partner_M49_as_reported"])]=Decimal(x["nominal_import_value_usd"])
    for code in requested:
      d=by_code.get(code,{})
      world=d.get(0)
      if iso=="AZE":
        assert code in prior_world and world is not None
        assert world==prior_world[code],f"AZE 2017 code {code} full-batch does not match independently archived World-only source"
      if code=="847130":
        assert world==prior_bilateral[(iso,year)],f"Historical HS6 bilateral World mismatch {iso}"
      coverage.append({"reporter_ISO3_candidate":iso,"Year":year,
          "source_reporter_M49":reporter,"source_HS_revision":revision,
          "HS6":code,"world_value_nominal_usd":str(world) if world is not None else "",
          "world_row_present":world is not None,
          "all_reported_partners_including_world":len(d),
          "status":"VALID_FULL_SOURCE_BILATERAL" if world is not None else "MISSING_WORLD_NOT_ZERO",
          "not_complete_47_country_network":True})
  assert len(provenance)==4 and len(coverage)==16
  keys={(x["reporter_ISO3_country_or_candidate"],x["Year"],x["HS6"],
         x["partner_M49_as_reported"]) for x in partner_records}
  assert len(keys)==len(partner_records)
  with (OUT/"two_reporter_years_eight_ict_HS6_bilateral_origins.csv").open(
       "w",encoding="utf-8",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(partner_records[0]),lineterminator="\n")
    w.writeheader();w.writerows(partner_records)
  with (OUT/"all_16_code_slices_coverage.csv").open("w",encoding="utf-8",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(coverage[0]),lineterminator="\n")
    w.writeheader();w.writerows(coverage)
  (OUT/"QUALITY_AND_PROVENANCE.json").write_text(json.dumps({
    "phase":"EXTENDED_DATA_EXPERIMENTAL",
    "original_professor_data_sha256":baseline["original_data_sha256"],
    "source_reporter_year_classification_verified":True,
    "eight_official_HS6_commodities_per_reporter_year":True,
    "four_authenticated_full_source_api_requests":True,
    "all_partner_record_keys_unique":True,
    "matched_8_2017_AZE_World_values_against_previous_independent_source":True,
    "matched_847130_World_values_against_previous_bilateral_source":True,
    "full_source_partner_rows_including_world":len(partner_records),
    "coverage_by_code":coverage,"raw_sources":provenance,
    "no_missing_imputed_zero":True,
    "nonexact_USA_customs_area_provenance_preserved":True,
    "not_full_47x18_FTECH_or_GMM":True,
    "subscription_key_never_stored":True,
    "completed_UTC":datetime.now(timezone.utc).isoformat(),
  },ensure_ascii=False,indent=2)+"\n")
  print("PHASE2_SOURCE_VERIFIED_MULTICODE_HS6_BILATERAL_COMPLETE",
        len(partner_records),"source rows",len(coverage),"code slices",flush=True)
if __name__=="__main__":main()
