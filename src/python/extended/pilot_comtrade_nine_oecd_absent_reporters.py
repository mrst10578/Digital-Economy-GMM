#!/usr/bin/env python3
"""Phase B public UN Comtrade pilot only. No paid key or Stata required.

Question: Are the nine original-country nodes missing as separately named
OECD ICIO 2025 economies addressable as trade REPORTERS in public UN Comtrade?

For each original missing ISO3, query 2005 and 2022 imports from China (M49
partner 156), HS headline chapter 85 (electrical machinery; NOT ICT-only).
Results are indicative evidence of a reporter/partner path, NOT 18-year
complete coverage or causal knowledge spillover. Empty preview != zero trade.
Do not attempt full 47×47 acquisition via the 500-row truncated preview.
"""
from __future__ import annotations
import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pycountry

ROOT=Path(__file__).resolve().parents[3]
LOCK=ROOT/"config/extended/phase2_original_47_country_sample_lock.json"
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
OUT=ROOT/"outputs/extended/comtrade_preview_country_pilot"
MISSING_IN_OECD=("AZE","KGZ","MAC","MDA","MKD","MNG","PAN","TTO","URY")
YEAR_SET=(2005,2022)
PARTNER=156    # China; directional partner anchor, NOT source of a causal shock
CHAPTER="85"   # broad HS chapter; NOT ICT goods code
API="https://comtradeapi.un.org/public/v1/preview/C/A/HS"
USER_AGENT="Digital-Economy-GMM-PhaseB-Comtrade-Reporter-Pilot/1.0 (research)"

def download(url:str):
    last_error=None
    for tries in range(3):
        try:
            request=Request(url,headers={"User-Agent":USER_AGENT,"Accept":"application/json"})
            with urlopen(request,timeout=30) as response:
                raw=response.read(2_000_000)
                assert len(raw)<2_000_000,"response too large for pilot"
                result=json.loads(raw)
                assert isinstance(result,dict),"Unrecognized Comtrade payload"
                return result,raw,None
        except (HTTPError, URLError, TimeoutError, ValueError, AssertionError) as exc:
            last_error=f"{type(exc).__name__}: {str(exc)[:240]}"
            if isinstance(exc,HTTPError) and exc.code not in (408,429,500,502,503,504):
                break
            time.sleep(1.3*(tries+1))
    return None,b"",last_error

def main():
    config=json.loads(LOCK.read_text(encoding="utf-8"))
    assert hashlib.sha256(RAW.read_bytes()).hexdigest()==config["original_data_sha256"]
    original_iso=set(config["iso3_to_original_country_name"])
    assert len(original_iso)==47 and set(MISSING_IN_OECD).issubset(original_iso)
    OUT.mkdir(parents=True,exist_ok=True)
    dump=OUT/"raw_preview"
    dump.mkdir(exist_ok=True)
    results=[]
    for iso in MISSING_IN_OECD:
        entity=pycountry.countries.get(alpha_3=iso)
        assert entity is not None and len(str(entity.numeric))==3
        m49=int(entity.numeric)
        for year in YEAR_SET:
            p=urlencode({"reporterCode":m49,"partnerCode":PARTNER,
                          "period":year,"flowCode":"M","cmdCode":CHAPTER,
                          "maxRecords":50,"breakdownMode":"classic"})
            url=f"{API}?{p}"
            obj,raw,error=download(url)
            status="API_ERROR"
            count=0
            mismatch=False
            notes=""
            if obj is not None:
                path=dump/f"{iso}_{year}_M_from_CHN_HS85.json"
                path.write_bytes(raw)
                recs=obj.get("data")
                api_error=obj.get("error")
                if isinstance(recs,list):
                    count=len(recs)
                    unexpected=[r for r in recs if
                        str(r.get("reporterCode","")) not in (str(m49),str(m49).zfill(3)) or
                        str(r.get("period",r.get("refYear","")))!=str(year) or
                        str(r.get("partnerCode",""))!=str(PARTNER)]
                    mismatch=bool(unexpected)
                    status=("PREVIEW_METADATA_MISMATCH" if mismatch else
                            "PREVIEW_CAP_50_NOT_EXHAUSTIVE" if count==50 else
                            "PREVIEW_HAS_ROWS" if count>0 else "PREVIEW_EMPTY_NOT_ZERO")
                else:
                    status="UNEXPECTED_API_FORMAT"
                if api_error:
                    notes=str(api_error)[:200]
            else:
                notes=error or "Unknown connection failure"
            results.append({
                "ISO3":iso,"name":config["iso3_to_original_country_name"][iso],
                "M49_reporter":m49,"year":year,"partner_ISO3":"CHN",
                "partner_M49":PARTNER,"direction":"import to reporter from China",
                "HS_chapter":CHAPTER,"HS_chapter_is_ICT_specific":"FALSE",
                "preview_rows":count,"status":status,
                "usable_as_full_18_year_coverage":"FALSE",
                "missing_preview_does_not_mean_zero_trade":"TRUE",
                "causal_spillover_established":"FALSE",
                "public_api_url":url,"error_or_api_note":notes,
                "raw_file_sha256":hashlib.sha256(raw).hexdigest() if raw else "",
            })
            print("COMTRADE_PILOT",iso,year,status,"rows",count,notes,flush=True)
            time.sleep(0.5)
    with (OUT/"reporter_pilot_9x2.csv").open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(results[0]))
        writer.writeheader();writer.writerows(results)
    counts={}
    for row in results:
        k=row["status"]
        counts[k]=counts.get(k,0)+1
    report={
        "phase":"EXTENDED_DATA_EXPERIMENTAL",
        "sample_original_sha256":config["original_data_sha256"],
        "original_workbook_modified":False,
        "nine_missing_OECD_country_nodes":list(MISSING_IN_OECD),
        "years_piloted":[2005,2022],
        "queries_attempted":len(results),
        "status_counts":counts,
        "reporter_with_at_least_one_2022_row":sorted({r["ISO3"] for r in results if r["year"]==2022 and r["status"] in ("PREVIEW_HAS_ROWS","PREVIEW_CAP_50_NOT_EXHAUSTIVE")}),
        "reporter_with_at_least_one_2005_row":sorted({r["ISO3"] for r in results if r["year"]==2005 and r["status"] in ("PREVIEW_HAS_ROWS","PREVIEW_CAP_50_NOT_EXHAUSTIVE")}),
        "zero_rows_mean_missing_not_zero":True,
        "subject":"HS chapter 85 imports from China; reporter/partner proof-of-concept only",
        "technology_specific_trade_link_defined":False,
        "all_47x47_18year_trade_coverage_verified":False,
        "keyless_public_preview_is_truncated_not_suitable_for_full_panel":True,
        "need_key_for_full_scale":{"likely":True,"how_to_ask":"Connect/use an authorized UN Comtrade free API subscription key securely if complete annual detailed extracts are required, never paste key into public GitHub."},
        "causal_identification_validated":False,
        "fetched_at_utc":datetime.now(timezone.utc).isoformat(),
        "technical_origin":"https://uncomtrade.org/docs/un-comtrade-api/",
    }
    (OUT/"reporter_pilot_summary.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    assert len(results)==18
    print("COMTRADE_PILOT_COMPLETE 18 keyless preview requests for 9 OECD-missing reporters at 2 historic dates; still NO full coverage inference",flush=True)

if __name__=="__main__":
    main()
