#!/usr/bin/env python3
"""Compare source-identical official Comtrade preview and authenticated full API.

Four requests: exact same reporter/year/HS and product with World partner.
Access key only in HTTPS header; never in source/logs/result. No fake zeroes.
"""
import os,json,time,hashlib
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/"evidence/extended/COMTRADE_HS_AS_REPORTED_FULL_VS_PREVIEW_DIAG_2026-10-17.json"
CASES=[
 ("USA_HS_2022_847130_FULL","data","HS",842,2022,"847130"),
 ("USA_HS_2022_847130_PREVIEW","public","HS",842,2022,"847130"),
 ("AZE_HS_2017_8471_FULL","data","HS",31,2017,"8471"),
 ("AZE_HS_2017_8471_PREVIEW","public","HS",31,2017,"8471"),
]
def main():
 key=os.environ.get("COMTRADE_API_KEY","").strip()
 assert key,"API secret required"
 result=[]
 for name,access,edition,reporter,year,heading in CASES:
  endpoint="data/v1/get" if access=="data" else "public/v1/preview"
  params={"reporterCode":str(reporter),"period":str(year),"flowCode":"M",
          "cmdCode":heading,"partnerCode":"0","maxRecords":"30"}
  url="https://comtradeapi.un.org/"+endpoint+"/C/A/"+edition+"?"+urlencode(params)
  headers={"User-Agent":"Official-ICT-HS-Preview-Full-Comparison/1.0",
          "Accept":"application/json"}
  if access=="data": headers["Ocp-Apim-Subscription-Key"]=key
  entry={"case":name,"edition":edition,"reporter":reporter,
         "year":year,"cmdCode":heading,"endpoint":endpoint,
         "status":None,"rows":None,"reported_count":None,
         "response_error":None,"body_sha256":None,"first_two_trade_rows":[],
         "http_error":None}
  try:
   with urlopen(Request(url,headers=headers),timeout=40) as r:
    b=r.read(8_000_000)
    entry["status"]=r.status
   entry["body_sha256"]=hashlib.sha256(b).hexdigest()
   j=json.loads(b)
   entry["reported_count"]=j.get("count")
   entry["response_error"]=str(j.get("error",""))[:200]
   entries=j.get("data",[])
   if isinstance(entries,list):
    entry["rows"]=len(entries)
    entry["first_two_trade_rows"]=[{k:it.get(k) for k in ("classificationCode",
      "cmdCode","period","reporterCode","partnerCode","flowCode","primaryValue")}
      for it in entries[:2]]
  except HTTPError as e:
   entry["status"]=e.code;entry["http_error"]=f"HTTP {e.code}"
  except (URLError,TimeoutError,ValueError) as e:
   entry["http_error"]=type(e).__name__
  result.append(entry)
  print("COMTRADE_EXACT_REQUEST_COMPARE",name,entry["status"],
        entry["rows"],entry["http_error"],flush=True)
  time.sleep(8)
 OUT.parent.mkdir(parents=True,exist_ok=True)
 OUT.write_text(json.dumps({"timestamp_utc":datetime.now(timezone.utc).isoformat(),
      "exclusively_official_Comtrade_endpoints":True,
      "secret_not_stored":True,"missing_not_zero":True,
      "eight_second_spacing":True,"requests":result},
      ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":main()
