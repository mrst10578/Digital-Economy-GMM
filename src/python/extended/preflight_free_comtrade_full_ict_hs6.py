#!/usr/bin/env python3
"""One-call credential-gated feasibility of full UN Comtrade HS6 annual imports.

Uses 8 real UNCTAD HS2017 ICT products; no hard-coded/traced API key. This is
NOT the 47-country production collector. Only manual workflow_dispatch with
an authorized free subscription key. Never print, embed, or log credentials.
"""
from __future__ import annotations
import csv, hashlib, json, math, os, time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[3]
CAT=ROOT/"data/extended/official_ict_hs6/unctad_ict_goods_official_hs6_1992_to_2022.csv"
BASE=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
LOCK=ROOT/"config/extended/phase2_original_47_country_sample_lock.json"
OUT=ROOT/"outputs/extended/official_comtrade_full_api_preflight"
ENDPOINT="https://comtradeapi.un.org/data/v1/get/C/A/H5"
LIMIT=100_000
MAX_RAW=48_000_000
def main():
    key=os.environ.get("COMTRADE_API_KEY","").strip()
    if not key: raise RuntimeError("COMTRADE_API_KEY not configured; zero API calls made")
    lock=json.loads(LOCK.read_text(encoding="utf-8"))
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==lock["original_data_sha256"]
    with CAT.open(encoding="utf-8",newline="") as f:
        rows=list(csv.DictReader(f))
    edition=sorted({x["HS6"] for x in rows if x["Comtrade_classificationCode"]=="H5"})
    assert len(rows)==691 and len(edition)==92
    assert all(len(code)==6 and code.isdigit() for code in edition)
    goods=edition[:8]
    url=ENDPOINT+"?"+urlencode({
        "reporterCode":31,"period":2017,"flowCode":"M","cmdCode":",".join(goods),
        "maxRecords":LIMIT,"breakdownMode":"classic"
    })
    req=Request(url,headers={"User-Agent":"Academic-Research-ICT-HS6-Secure-Preflight/1.0",
        "Accept":"application/json","Ocp-Apim-Subscription-Key":key})
    try:
        with urlopen(req,timeout=90) as stream:
            raw=stream.read(MAX_RAW+1)
            http_status=stream.status
    except HTTPError as exc:
        raise RuntimeError(f"Comtrade full API HTTP {exc.code}; check valid subscription access") from None
    except (URLError,TimeoutError) as exc:
        raise RuntimeError(f"Comtrade full API connection error: {type(exc).__name__}") from None
    assert http_status==200 and len(raw)<=MAX_RAW
    obj=json.loads(raw)
    assert isinstance(obj,dict) and isinstance(obj.get("data"),list)
    data=obj["data"]
    if len(data)>=LIMIT:raise RuntimeError("Response hit free 100k cap; do not trust slice")
    seen=set();bad=[]
    for rec in data:
        try:
            code=str(rec["cmdCode"])
            assert code in goods
            assert int(rec.get("period",rec.get("refYear",-1)))==2017
            assert int(rec["reporterCode"])==31
            assert rec["flowCode"]=="M"
            assert rec["classificationCode"]=="H5"
            assert rec.get("primaryValue") is not None
            val=float(rec["primaryValue"])
            assert math.isfinite(val) and val>=0
            partner=int(rec["partnerCode"])
            assert partner>=0
            k=(2017,code,partner)
            assert k not in seen
            seen.add(k)
        except (AssertionError,KeyError,TypeError,ValueError):
            bad.append({"code":str(rec.get("cmdCode","")),"period":str(rec.get("period",""))})
    if bad:raise RuntimeError(f"Returned {len(bad)} records with invalid HS6 metadata; no promotion")
    count=Counter(str(x["cmdCode"]) for x in data)
    if not data:raise RuntimeError("No rows; do not infer zero trade from missing preview")
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"raw_2017_AZE_8_ict_hs6_full_api.json").write_bytes(raw)
    manifest={
      "source":"UN Comtrade authenticated free API",
      "endpoint_without_credentials":ENDPOINT,
      "params_without_credentials":{"reporterCode":31,"period":2017,"flowCode":"M",
        "cmdCode":",".join(goods),"maxRecords":LIMIT},
      "reference_catalog_sha256":hashlib.sha256(CAT.read_bytes()).hexdigest(),
      "raw_response_sha256":hashlib.sha256(raw).hexdigest(),
      "http_status":http_status,"observed_rows_including_world":len(data),
      "expected_product_codes":goods,"codes_with_at_least_one_reported_record":dict(count),
      "all_8_products_present":set(count)==set(goods),
      "records_uniquely_identified":True,"no_truncation_under_free_100K_cap":True,
      "key_was_never_stored_or_logged":True,"year_2017_H5_only":True,
      "is_complete_47_country_18_year_network":False,
      "is_final_technology_spillover_proxy":False,
      "phase_A_unmodified":True,"timestamp_utc":datetime.now(timezone.utc).isoformat()
    }
    (OUT/"QUALITY.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    print("PHASE2_FULL_API_PRELIMINARY_AUTHENTICATED_PASS",
      "observed_rows",len(data),"selected_HS6",len(goods),
      "n_responding_codes",len(count),"never log subscription key",flush=True)
if __name__=="__main__":main()
