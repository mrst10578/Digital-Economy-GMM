#!/usr/bin/env python3
"""Find official reporter/year HS revision from Comtrade availability; verify with one goods query.

No fixed calendar classification. Explicitly throttle authenticated API.
Only full API responses are used; all data is provisional until later audit.
Never log any key.
"""
from __future__ import annotations
import hashlib,json,os,time
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/"evidence/extended/COMTRADE_AUTHENTICATED_AZE_2017_SOURCE_EDITION_CHECK_2026-10-17.json"
BASE="https://comtradeapi.un.org"
M49={"H0":"HS1992","H1":"HS1996","H2":"HS2002","H3":"HS2007","H4":"HS2012","H5":"HS2017","H6":"HS2022"}
def req(key,endpoint,params,attempts=2):
 url=BASE+endpoint+"?"+urlencode(params)
 for i in range(attempts):
    try:
        with urlopen(Request(url,headers={
            "User-Agent":"Academic-ICT-Research-Source-Revision-Audit/1.0",
            "Ocp-Apim-Subscription-Key":key,"Accept":"application/json"
        }),timeout=40) as res:
            data=res.read(8_000_000)
            status=res.status
        j=json.loads(data)
        assert isinstance(j,dict) and isinstance(j.get("data"),list)
        return {"status":status,"body_sha256":hashlib.sha256(data).hexdigest(),
            "count":j.get("count"),"error":str(j.get("error",""))[:240],
            "data":j["data"]}
    except HTTPError as e:
        if e.code in (429,500,502,503) and i==0:
            time.sleep(11)
            continue
        return {"status":e.code,"error":f"HTTP {e.code}","count":None,
                "body_sha256":None,"data":[]}
    except (URLError,TimeoutError,ValueError) as e:
        return {"status":None,"error":type(e).__name__,"count":None,
                "body_sha256":None,"data":[]}
def main():
 key=os.environ.get("COMTRADE_API_KEY","").strip()
 if not key:raise RuntimeError("Secret missing; no API call")
 queries=[("AZE",31,2017),("USA",842,2017),("TTO",780,2022)]
 results=[]
 for code,reporter,year in queries:
    r=req(key,"/data/v1/getDa/C/A/HS",{
       "reporterCode":str(reporter),"period":str(year)})
    data=r.pop("data")
    item={"ISO3":code,"reporterCode":reporter,"year":year,
       "source_url_without_key":"/data/v1/getDa/C/A/HS",
       "available_rows":len(data),"reply":r,
       "source_revisions":sorted({str(x.get("classificationCode",""))
                                for x in data}),
       "available_public_metadata":[{
          k:x.get(k) for k in ["reporterCode","period","classificationCode",
             "isOriginalClassification","isPartnerDetail","isCmdDetail","isAggregate",
             "isNetWgtEstimated"]} for x in data[:12]]}
    results.append(item)
    print("COMTRADE_GETDA_SOURCE_YEAR",code,year,
         "http",r["status"],"rows",len(data),
         "revisions",item["source_revisions"],flush=True)
    time.sleep(5)
 official=[x for x in results[0]["available_public_metadata"]
           if x["classificationCode"] in M49 and x["isOriginalClassification"] is True]
 # Comtrade can return multiple original classifications, refuse arbitrary choice.
 edition=official[0]["classificationCode"] if len(official)==1 else ""
 if edition:
    trial=req(key,f"/data/v1/get/C/A/{edition}",{
       "reporterCode":"31","period":"2017","flowCode":"M",
       "partnerCode":"0","cmdCode":"8471","maxRecords":"30"})
    data=trial.pop("data")
    results[0]["source_specific_hs4_full_api_probe"]={
      "source_edition":edition,"response":trial,
      "n_records":len(data),
      "first_2_records":[{
         k:x.get(k) for k in ["reporterCode","period","classificationCode",
             "cmdCode","partnerCode","flowCode","primaryValue"]}
             for x in data[:2]]}
    print("AZE_SOURCE_EDITION_TRADE_VERIFY",edition,"http",
       trial["status"],"records",len(data),flush=True)
 summary={"phase":"EXTENDED_DATA_EXPERIMENTAL",
          "UTC":datetime.now(timezone.utc).isoformat(),
          "API_key_value_never_logged":True,
          "source_revision_from_data_availability_not_calendar":True,
          "rate_limit_throttled_5s_between_requests":True,
          "missing_never_assumed_zero":True,
          "country_year_results":results}
 OUT.parent.mkdir(parents=True,exist_ok=True)
 OUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
if __name__=="__main__":main()
