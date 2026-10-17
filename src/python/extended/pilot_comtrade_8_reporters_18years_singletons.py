#!/usr/bin/env python3
"""Phase B: 8 OECD-absent reporters x 18 annual imports FROM CHINA, HS85.

The initial AZE (9th) 18-year bilateral series has been verified/archived.
This experiment uses only officially public UN Comtrade preview, one reporter
one year at a time. HS85 is NOT an ICT-only classification nor a causal spillover.
No Stata, changes to professor data, imputation, or estimation.

Fixed independent reporter cohorts for two concurrent GitHub jobs:
  group 1: KGZ MAC MDA MKD
  group 2: MNG PAN TTO URY
Each job runs 4 x 18 = 72 singleton API requests with small delays.
Status is never converted to trade=0. If API rejects, report incomplete.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
import pycountry

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
LOCK=ROOT/"config/extended/phase2_original_47_country_sample_lock.json"
OUT=ROOT/"outputs/extended/comtrade_8_reporters_18_years_china_hs85"
API="https://comtradeapi.un.org/public/v1/preview/C/A/HS"
PARTNER=156
CHAPTER="85"
MAX_ROWS=40
GROUPS={"1":("KGZ","MAC","MDA","MKD"),"2":("MNG","PAN","TTO","URY")}
YEARS=range(2005,2023)

def fetch(url:str):
    error=""
    for retry in range(4):
        try:
            req=Request(url,headers={"User-Agent":"PhaseB-Academic-Trade-Coverage-Pilot/1.0","Accept":"application/json"})
            with urlopen(req,timeout=30) as stream:
                raw=stream.read(1_500_000)
                assert len(raw)<1_500_000,"API response cap"
                obj=json.loads(raw)
            assert isinstance(obj,dict) and isinstance(obj.get("data"),list),"Unexpected API response structure"
            return obj,raw,""
        except (HTTPError,URLError,TimeoutError,ValueError,AssertionError) as e:
            error=f"{type(e).__name__}: {str(e)[:200]}"
            if isinstance(e,HTTPError) and e.code not in (429,408,500,502,503,504):
                break
            time.sleep(1.2*(retry+1))
    return None,b"",error

def write_csv(path,rows):
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--group",choices=list(GROUPS),required=True)
    args=ap.parse_args()
    lock=json.loads(LOCK.read_text(encoding="utf-8"))
    original_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert lock["original_data_sha256"]==original_hash
    isos=GROUPS[args.group]
    assert len(isos)==4 and all(iso in lock["iso3_to_original_country_name"] for iso in isos)
    out=OUT/f"group_{args.group}"
    out.mkdir(parents=True,exist_ok=True)
    rawdir=out/"raw"
    rawdir.mkdir(exist_ok=True)
    rows=[]
    for iso in isos:
        meta=pycountry.countries.get(alpha_3=iso)
        assert meta is not None and int(meta.numeric)>0
        reporter=int(meta.numeric)
        for year in YEARS:
            params={"reporterCode":reporter,"partnerCode":PARTNER,
                    "period":year,"flowCode":"M","cmdCode":CHAPTER,
                    "maxRecords":MAX_ROWS,"breakdownMode":"classic"}
            url=API+"?"+urlencode(params)
            obj,raw,error=fetch(url)
            status="API_ERROR"
            count=0
            value=None
            source_hash=""
            if obj is not None:
                records=obj["data"]
                count=len(records)
                source_hash=hashlib.sha256(raw).hexdigest()
                (rawdir/f"{iso}_{year}_CHN_HS85.json").write_bytes(raw)
                check=[]
                for rec in records:
                    try:
                        check.append(int(rec.get("reporterCode",-1))==reporter and
                          int(rec.get("partnerCode",-1))==PARTNER and
                          int(rec.get("period",rec.get("refYear",-1)))==year and
                          str(rec.get("flowCode"))=="M" and
                          str(rec.get("cmdCode"))==CHAPTER)
                    except (TypeError,ValueError):
                        check.append(False)
                if len(records)>=MAX_ROWS:
                    status="CAPPED"
                elif not all(check) or len(records)>1:
                    status="BAD_METADATA_OR_DUPLICATE"
                elif len(records)==0:
                    status="EMPTY_UNREPORTED_NOT_ZERO"
                else:
                    value=records[0].get("primaryValue")
                    if value is None:
                        status="MISSING_PRIMARY_VALUE"
                    else:
                        value=float(value)
                        status="OBSERVED" if math.isfinite(value) and value>=0 else "BAD_VALUE"
            rows.append({"ISO3":iso,"Year":year,"partner_ISO3":"CHN",
                "reporter_m49":reporter,"partner_m49":PARTNER,
                "HS_chapter":CHAPTER,"flow":"M",
                "nominal_import_USD":value,"status":status,
                "response_record_count":count,
                "raw_response_sha256":source_hash,
                "public_API_url":url,"error":error,
                "only_HS85_not_narrow_ICT":"TRUE",
                "not_causal_measure":"TRUE"})
            print("TRADE_18YEAR",iso,year,status,"records",count,"value",value,"error",error,flush=True)
            time.sleep(.45)
    assert len(rows)==72 and len({(r["ISO3"],r["Year"]) for r in rows})==72
    write_csv(out/"observations.csv",rows)
    by_country=[]
    for iso in isos:
        items=[r for r in rows if r["ISO3"]==iso]
        statuses=Counter(r["status"] for r in items)
        by_country.append({"ISO3":iso,"observed_years":statuses["OBSERVED"],
            "api_failures":statuses["API_ERROR"],
            "missing_years":18-statuses["OBSERVED"],
            "all_18_years_observed":statuses["OBSERVED"]==18,
            "years_2005_2007_all_observed":all(r["status"]=="OBSERVED" for r in items if r["Year"] in (2005,2006,2007))})
    write_csv(out/"country_coverage.csv",by_country)
    status=Counter(r["status"] for r in rows)
    info={"phase":"EXTENDED_DATA_EXPERIMENTAL",
        "source":"UN Comtrade public preview",
        "original_sha256":original_hash,
        "baseline_modified":False,"group":args.group,
        "reporters":list(isos),"year_range":"2005-2022",
        "number_of_requests":72,
        "observed_cells":status["OBSERVED"],
        "missing_cells":72-status["OBSERVED"],
        "status_counts":dict(status),
        "country_coverage":by_country,
        "all_72_observed":status["OBSERVED"]==72,
        "raw_original_responses_archived":True,
        "no_imputation":True,
        "only_one_partner_CHN":True,
        "broad_electrical_chapter_HS85_not_narrow_ICT":True,
        "real_technology_spillovers_not_identified":True,
        "no_stata_and_no_GMM_run":True,
        "no_47x47_full_network_claimed":True,
        "timestamp_utc":datetime.now(timezone.utc).isoformat()}
    (out/"summary.json").write_text(json.dumps(info,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("TRADE_GROUP_COMPLETE",args.group,"observed",status["OBSERVED"],"of_72","statuses",dict(status),flush=True)
    for item in by_country:print("TRADE_COUNTRY_COVERAGE",item["ISO3"],item["observed_years"],"/18",flush=True)
    assert not any(k in status for k in ("API_ERROR","BAD_METADATA_OR_DUPLICATE","CAPPED","BAD_VALUE","MISSING_PRIMARY_VALUE")),"One or more responses unreliable. Archive partial, do not claim complete."
    # Empty preview is still a missing observation and not zero, not an error.

if __name__=="__main__":main()
