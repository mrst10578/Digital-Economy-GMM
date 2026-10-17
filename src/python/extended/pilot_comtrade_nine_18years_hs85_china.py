#!/usr/bin/env python3
"""Pre-registered 9-country historical reporter→China pilot on HS chapter 85.

UN Comtrade keyless public/v1/preview, annual imports from China, HS85.
Data are electrical machinery (not equivalent to ICT products or knowledge
spillovers), nominal USD trade flows; 9 countries missing from OECD ICIO list.
Complete source-year matrix 2005-2022 of observations, missing as NA.
Use 3 predeclared 6-year batches per reporter; cap=200 per request; if response
truncates, signal INCOMPLETE not full panel. Never infer zero from no record.

All records are Phase-B only; no Stata, no impact estimates or causal claims.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
import time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

import pycountry

ROOT=Path(__file__).resolve().parents[3]
LOCK=ROOT/"config/extended/phase2_original_47_country_sample_lock.json"
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
OUT=ROOT/"outputs/extended/comtrade_historical_nine_reporters_china_hs85"
ISO_CODES=("AZE","KGZ","MAC","MDA","MKD","MNG","PAN","TTO","URY")
PERIODS=(tuple(range(2005,2011)),tuple(range(2011,2017)),tuple(range(2017,2023)))
URL="https://comtradeapi.un.org/public/v1/preview/C/A/HS"
PARTNER=156
MAXRECORDS=200

def fetch(url):
    last=""
    for i in range(3):
        try:
            r=Request(url,headers={"User-Agent":"Digital-Economy-GMM-PhaseB-Public-Data-Pilot/1.0","Accept":"application/json"})
            with urlopen(r,timeout=30) as response:
                raw=response.read(3_000_000)
                if len(raw)>=3_000_000: raise ValueError("truncated response")
                payload=json.loads(raw)
                assert isinstance(payload,dict)
                return payload,raw,None
        except (HTTPError,URLError,TimeoutError,ValueError) as error:
            last=f"{type(error).__name__}: {str(error)[:200]}"
            if isinstance(error,HTTPError) and error.code not in (429,500,502,503,504):
                break
            time.sleep(1.5*(i+1))
    return None,b"",last

def main():
    lock=json.loads(LOCK.read_text(encoding="utf-8"))
    assert hashlib.sha256(RAW.read_bytes()).hexdigest()==lock["original_data_sha256"]
    assert set(ISO_CODES).issubset(lock["iso3_to_original_country_name"])
    OUT.mkdir(parents=True,exist_ok=True)
    rawout=OUT/"raw_api";rawout.mkdir(exist_ok=True)
    audit=[]
    values={}
    for iso in ISO_CODES:
        m49=int(pycountry.countries.get(alpha_3=iso).numeric)
        for years in PERIODS:
            params={"reporterCode":m49,"partnerCode":PARTNER,
                    "period":",".join(map(str,years)),"cmdCode":"85",
                    "flowCode":"M","maxRecords":MAXRECORDS,
                    "breakdownMode":"classic"}
            url=URL+"?"+urlencode(params)
            data,raw,error=fetch(url)
            quality="API_ERROR";count=0;duplicate=0;found=set()
            if data is not None:
                if data.get("error"):error=str(data["error"])[:220]
                records=data.get("data")
                if isinstance(records,list):
                    count=len(records)
                    quality="TRUNCATED_CAP" if count>=MAXRECORDS else "RETURNED"
                    for r in records:
                        yr=int(r.get("period",r.get("refYear",0)))
                        if yr not in years or int(r.get("reporterCode",-1))!=m49 or int(r.get("partnerCode",-1))!=PARTNER:
                            quality="METADATA_MISMATCH"
                            continue
                        if str(r.get("flowCode"))!="M" or str(r.get("cmdCode"))!="85":
                            quality="METADATA_MISMATCH"
                            continue
                        key=(iso,yr)
                        if key in values:duplicate+=1
                        else:
                            v=r.get("primaryValue")
                            values[key]=None if v is None else float(v)
                            found.add(yr)
                else:quality="UNEXPECTED_API_FORMAT"
                (rawout/f"{iso}_{min(years)}_{max(years)}.json").write_bytes(raw)
            audit.append({"ISO3":iso,"M49":m49,"years":"+".join(map(str,years)),
                          "request_url":url,"response_rows":count,
                          "years_with_unique_records":len(found),
                          "duplicates":duplicate,
                          "status":quality,"error":error or "",
                          "raw_response_sha256":hashlib.sha256(raw).hexdigest() if raw else ""})
            print("HISTORIC_PILOT",iso,min(years),max(years),quality,
                  "n_records",count,"years",len(found),"dup",duplicate,"error",error,flush=True)
            time.sleep(.65)
    def save(path,records):
        with path.open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=list(records[0]))
            w.writeheader();w.writerows(records)
    full=[]
    for iso in ISO_CODES:
        for y in range(2005,2023):
            value=values.get((iso,y))
            full.append({"ISO3":iso,"Year":y,"partner_ISO3":"CHN",
                         "HS":"85","import_value_nominal_usd":value,
                         "is_reported":(iso,y) in values,
                         "source":"UN Comtrade keyless preview; not full trade extract"})
    assert len(full)==9*18 and len(audit)==9*3
    save(OUT/"trade_9_country_18year_partner_CHN_HS85.csv",full)
    save(OUT/"api_27_batch_audit.csv",audit)
    coverage=[]
    for iso in ISO_CODES:
        present={y for (i,y) in values if i==iso}
        coverage.append({"ISO3":iso,"present_years":len(present),
                         "missing_years":18-len(present),
                         "full_historical_18years":len(present)==18,
                         "early_2005_record":2005 in present,
                         "late_2022_record":2022 in present})
    save(OUT/"reporter_coverage.csv",coverage)
    bad=sum(r["status"]!="RETURNED" or r["duplicates"]>0 for r in audit)
    summary={"phase":"EXTENDED_DATA_EXPERIMENTAL",
            "original_sha256":lock["original_data_sha256"],
            "original_phase_unchanged":True,"queries":len(audit),
            "expected_9_country_18_year_cells":162,
            "unique_reporter_year_records":len(values),
            "missing_not_zero":162-len(values),
            "all_27_requests_untruncated_valid":bad==0,
            "failed_or_capped_or_duplicate_requests":bad,
            "countries_with_18_reported_years":[x["ISO3"] for x in coverage if x["full_historical_18years"]],
            "year_by_year_china_imports_of_HS85_not_ICT_specific":True,
            "possible_comtrade_revision_or_classification_changes":True,
            "further_work_requires_causal_identification":True,
            "full_47x47_dataset_claimed":False,
            "GMM_model_run":False,
            "observed_at_utc":datetime.now(timezone.utc).isoformat()}
    (OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("HISTORIC_COMTRADE_COMPLETE",json.dumps({k:summary[k] for k in ("unique_reporter_year_records","missing_not_zero","failed_or_capped_or_duplicate_requests","countries_with_18_reported_years")}),flush=True)
    # This is strict: a truncated/failed preview is incomplete, never trustworthy complete coverage.
    assert bad==0,"Pilot data acquisition incomplete; do not claim 18-year country coverage"

if __name__=="__main__":
    main()
