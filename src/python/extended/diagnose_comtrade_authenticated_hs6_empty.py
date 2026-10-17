#!/usr/bin/env python3
"""Small credential-safe diagnostic: why first authenticated HS6 query yielded no rows.

All requests bounded, all parameters explicit, publish only response metadata
and at most five sanitized examples. No secret or auth URL in outputs.
"""
from __future__ import annotations
import hashlib,json,os,urllib.parse,urllib.request,urllib.error,time
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/"evidence/extended/COMTRADE_FULL_API_HS6_EMPTY_QUERY_DIAG_2026-10-17.json"
BASE="https://comtradeapi.un.org/data/v1/get/C/A/"
CASES=[
 ("AZE_H5_2017_HS6_one_world","H5",{"reporterCode":"31","period":"2017","cmdCode":"847130","flowCode":"M","partnerCode":"0","maxRecords":"30"}),
 ("AZE_H5_2017_HS4_world","H5",{"reporterCode":"31","period":"2017","cmdCode":"8471","flowCode":"M","partnerCode":"0","maxRecords":"30"}),
 ("USA_H5_2017_HS6_world","H5",{"reporterCode":"842","period":"2017","cmdCode":"847130","flowCode":"M","partnerCode":"0","maxRecords":"30"}),
 ("USA_H6_2022_HS6_world","H6",{"reporterCode":"842","period":"2022","cmdCode":"847130","flowCode":"M","partnerCode":"0","maxRecords":"30"}),
 ("USA_HS_2022_TOTAL_world","HS",{"reporterCode":"842","period":"2022","cmdCode":"TOTAL","flowCode":"M","partnerCode":"0","maxRecords":"30"}),
 ("AZE_H5_2017_HS6_one_all_origins","H5",{"reporterCode":"31","period":"2017","cmdCode":"847130","flowCode":"M","maxRecords":"80"}),
]
def main():
 key=os.getenv("COMTRADE_API_KEY","").strip()
 if not key: raise RuntimeError("Secret COMTRADE_API_KEY required, no API calls")
 audit=[]
 for name,version,params in CASES:
    url=BASE+version+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"Accept":"application/json",
        "User-Agent":"Academic-Comtrade-ICT-HS6-Query-Diagnostic/1.0",
        "Ocp-Apim-Subscription-Key":key})
    result={"name":name,"version":version,"params_without_credentials":params,
            "http_status":None,"response_fields":[],"reported_count":None,
            "validation_status":None,"server_error":None,"data_records":0,
            "first_records_public_fields":[],"body_sha256":None,"error":None}
    try:
        with urllib.request.urlopen(req,timeout=35) as f:
            b=f.read(2_000_000)
            result["http_status"]=f.status
        result["body_sha256"]=hashlib.sha256(b).hexdigest()
        j=json.loads(b)
        if isinstance(j,dict):
            result["response_fields"]=list(j)[:20]
            result["reported_count"]=j.get("count")
            result["validation_status"]=j.get("validationStatus")
            result["server_error"]=str(j.get("error",""))[:250]
            data=j.get("data")
            if isinstance(data,list):
                result["data_records"]=len(data)
                result["first_records_public_fields"]=[{
                    k:str(item.get(k,""))[:100] for k in (
                       "reporterCode","period","classificationCode",
                       "cmdCode","partnerCode","flowCode","primaryValue")}
                    for item in data[:2] if isinstance(item,dict)]
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,
            ValueError,UnicodeError) as exc:
        result["http_status"]=getattr(exc,"code",None)
        result["error"]=f"{type(exc).__name__}: {str(exc)[:120]}"
    audit.append(result)
    print("FULL_API_AUTHORIZED_DIAGNOSTIC",name,
          "http",result["http_status"],"count",result["reported_count"],
          "validation",result["validation_status"],"err",result["server_error"],flush=True)
    time.sleep(.4)
 OUT.parent.mkdir(parents=True,exist_ok=True)
 OUT.write_text(json.dumps({"timestamp_utc":datetime.now(timezone.utc).isoformat(),
     "authorization_secret_not_recorded":True,"query_count":len(CASES),
     "no_missing_replaced_by_zero":True,"cases":audit},
     ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("COMTRADE_AUTHENTICATED_DIAGNOSTIC_COMPLETE",len(audit),flush=True)
if __name__=="__main__":main()
