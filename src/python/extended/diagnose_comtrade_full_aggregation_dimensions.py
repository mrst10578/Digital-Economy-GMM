#!/usr/bin/env python3
"""Diagnose why authenticated HS world aggregate returns multiple rows.

Only asks Azerbaijan's HS-as-reported 8471 2017 World slice; source metadata
and disaggregation dimensions retained for scientific selection of totals.
No trading sums invented; no secrets logged or stored.
"""
from __future__ import annotations
import hashlib,json,os,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/"evidence/extended/COMTRADE_HS_AS_REPORTED_WORLD_GRANULARITY_DIAG_2026-10-17.json"
ROOTURL="https://comtradeapi.un.org"
BASE={"reporterCode":"31","period":"2017","flowCode":"M","cmdCode":"8471","partnerCode":"0","maxRecords":"100","breakdownMode":"classic"}
CASES={
 "full_original_no_explicit_dimensions":{},
 "full_all_customs_C00":{"customsCode":"C00"},
 "full_all_transport_0":{"motCode":"0"},
 "full_customs_C00_and_transport_0":{"customsCode":"C00","motCode":"0"},
 "full_three_nonproduct_aggregate_dimensions":{"customsCode":"C00","motCode":"0","partner2Code":"0"},
 "preview_control":{"mode":"public"},
}
KEYS=("reporterCode","period","classificationCode","classificationSearchCode",
      "cmdCode","partnerCode","partner2Code","motCode","customsCode",
      "flowCode","primaryValue","isAggregate","isOriginalClassification",
      "isReported","aggrLevel","isLeaf","legacyEstimationFlag","isNetWgtEstimated",
      "qtyUnitCode","customsDesc","motDesc")
def main():
 key=os.environ.get("COMTRADE_API_KEY","").strip()
 if not key:raise RuntimeError("Configured Comtrade secret is required")
 results=[]
 for name,extra in CASES.items():
    mode=extra.get("mode","data")
    endpoint="/public/v1/preview/C/A/HS" if mode=="public" else "/data/v1/get/C/A/HS"
    params=dict(BASE)
    params.update({k:v for k,v in extra.items() if k!="mode"})
    url=ROOTURL+endpoint+"?"+urlencode(params)
    headers={"User-Agent":"Economic-Research-ICT-Granularity-Verification/1.0","Accept":"application/json"}
    if mode=="data":headers["Ocp-Apim-Subscription-Key"]=key
    result={"name":name,"mode":mode,"endpoint":endpoint,
        "params_without_secret":params,"http":None,
        "sha256":None,"json_count":None,"observed_rows":None,
        "record_dimension_keys":list(KEYS),
        "records_with_dimensions":[],"error":None}
    try:
        with urlopen(Request(url,headers=headers),timeout=50) as r:
            body=r.read(8_000_000);result["http"]=r.status
        obj=json.loads(body)
        assert isinstance(obj,dict) and isinstance(obj.get("data"),list)
        result["sha256"]=hashlib.sha256(body).hexdigest()
        result["json_count"]=obj.get("count")
        data=obj["data"]
        result["observed_rows"]=len(data)
        result["records_with_dimensions"]=[{k:rec.get(k) for k in KEYS} for rec in data[:100]]
    except (HTTPError,URLError,TimeoutError,ValueError) as e:
        result["http"]=getattr(e,"code",result["http"])
        result["error"]=type(e).__name__+((" HTTP "+str(e.code)) if isinstance(e,HTTPError) else "")
    results.append(result)
    print("COMTRADE_AGGREGATE_SCOPE_CONTROL",name,
          "HTTP",result["http"],"rows",result["observed_rows"],flush=True)
    time.sleep(8)
 OUT.parent.mkdir(parents=True,exist_ok=True)
 OUT.write_text(json.dumps({
    "status":"DIAGNOSTIC_ONLY_NOT_FINAL_TRADE_DATA",
    "run_timestamp_utc":datetime.now(timezone.utc).isoformat(),
    "source_edition_H4_from_getDA_verified":True,
    "HS_path_not_direct_H4_to_avoid_HTTP500":True,
    "no_key_disclosure":True,
    "never_sum_over_overlapping_aggregate_rows":True,
    "cases":results},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":main()
