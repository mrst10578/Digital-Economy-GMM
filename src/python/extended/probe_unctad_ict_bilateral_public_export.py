#!/usr/bin/env python3
"""Check only keyless public UNCTADstat ICT bilateral series metadata endpoints.

No third-party keys, no backdoor auth, no bulk unbounded downloads. A small
HTTP Range/head preflight decides if UNCTAD's *already harmonized* bilateral
ICT five-category dataset might avoid Comtrade preview limitations.
"""
from __future__ import annotations
import hashlib, json, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/"evidence/extended/UNCTAD_ICT_BILATERAL_PUBLIC_EXPORT_PREFLIGHT_2026-10-17.json"
HOST="https://unctadstat-api.unctad.org"
CANDIDATES={
 "metadata_ict_en":HOST+"/api/reportMetadata/US.IctGoodsValue/en",
 "metadata_ict":HOST+"/api/reportMetadata/US.IctGoodsValue",
 "csv_report_files":HOST+"/api/report-files/US.IctGoodsValue.csv",
 "csv_reportfiles":HOST+"/api/reportfiles/US.IctGoodsValue.csv",
}
LIMIT=16_384
def main():
    results=[]
    for name,url in CANDIDATES.items():
        row={"name":name,"url":url,"http_status":None,"content_type":"",
             "response_prefix_sha256":None,"content_length_claimed":None,
             "bytes_sampled":0,"JSON_keys":[],"CSV_first_field_names":[],
             "error":"","authenticated_key_used":False,"is_complete_dataset":False}
        try:
            req=Request(url,headers={
                "User-Agent":"Academic-Public-UNCTAD-ICT-Bilateral-Preflight/1.0",
                "Accept":"application/json,text/csv,*/*",
                "Range":f"bytes=0-{LIMIT-1}"})
            with urlopen(req,timeout=25) as resp:
                row["http_status"]=resp.status
                row["content_type"]=resp.headers.get("Content-Type","")
                row["content_length_claimed"]=resp.headers.get("Content-Length")
                b=resp.read(LIMIT)
            row["bytes_sampled"]=len(b)
            row["response_prefix_sha256"]=hashlib.sha256(b).hexdigest()
            if "json" in row["content_type"] and len(b)<LIMIT:
                obj=json.loads(b)
                row["JSON_keys"]=sorted(obj)[:25] if isinstance(obj,dict) else []
            elif "csv" in row["content_type"] and b:
                head=b.splitlines()[0][:500].decode("utf-8","replace")
                row["CSV_first_field_names"]=head.split(",")[:20]
        except (HTTPError,URLError,TimeoutError,ValueError,UnicodeError) as exc:
            row["http_status"]=getattr(exc,"code",None)
            row["error"]=f"{type(exc).__name__}: {str(exc)[:220]}"
        print("UNCTAD_ICT_BILATERAL_PUBLIC_PREFLIGHT",name,row["http_status"],
              row["content_type"],row["bytes_sampled"],row["error"],flush=True)
        results.append(row);time.sleep(.35)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({
        "phase":"EXTENDED_DATA_EXPERIMENTAL",
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "dataset":"UNCTAD ICT goods: Bilateral trade by category - Annual",
        "no_subscription_key_used":True,"only_bounded_16KB_HTTP_range_samples":True,
        "no_dataset_claimed_downloaded":True,
        "results":results,
        "source_website":"https://unctadstat.unctad.org/datacentre/",
    },indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":main()
