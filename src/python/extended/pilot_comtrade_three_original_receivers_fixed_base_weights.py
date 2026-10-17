#!/usr/bin/env python3
"""Phase B: fixed source weights feasibility across three NEW recipients.

Only KGZ, MDA, PAN (geographically varied originally-OECD-absent countries)
and only pre-base years 2005..2007, HS headings 8471 and 8517. Predeclared
selection is based on continents/data feasibility, not response coefficients.
No Stata, no model, no causal or final spillover claims.

All origins queried via partnerCode absent; World M49=0 is denominator only.
Missing country×year×heading origin is missing, NOT zero. A source-year heading
weight is illustrative, and 2005..07 baseline shares remain PROVISIONAL.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
import time
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
import pycountry

ROOT=Path(__file__).resolve().parents[3]
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
LOCK=ROOT/"config/extended/phase2_original_47_country_sample_lock.json"
OUT=ROOT/"outputs/extended/comtrade_three_reporters_2005_2007_all_partners"
API="https://comtradeapi.un.org/public/v1/preview/C/A/HS"
DESTINATIONS=("KGZ","MDA","PAN")
BASE_YEARS=(2005,2006,2007)
HS=("8471","8517")
CAP=500

def query(url):
    err=""
    for i in range(4):
        try:
            rq=Request(url,headers={"User-Agent":"PhaseB-Academic-Country-Origin-Pilot/1.0","Accept":"application/json"})
            with urlopen(rq,timeout=30) as f:
                raw=f.read(6_000_000)
                assert len(raw)<6_000_000
            obj=json.loads(raw)
            assert isinstance(obj,dict) and isinstance(obj.get("data"),list)
            return obj,raw,""
        except (HTTPError,URLError,TimeoutError,AssertionError,ValueError) as exc:
            err=f"{type(exc).__name__}: {str(exc)[:180]}"
            if isinstance(exc,HTTPError) and exc.code not in (408,429,500,502,503,504):break
            time.sleep(1.5*(i+1))
    return None,b"",err

def csvout(name,rows):
    assert rows
    with (OUT/name).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)

def main():
    lock=json.loads(LOCK.read_text(encoding="utf-8"))
    assert hashlib.sha256(RAW.read_bytes()).hexdigest()==lock["original_data_sha256"]
    m49={int(pycountry.countries.get(alpha_3=iso).numeric):iso for iso in lock["iso3_to_original_country_name"]}
    assert len(m49)==47 and all(iso in lock["iso3_to_original_country_name"] for iso in DESTINATIONS)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"raw_api").mkdir(exist_ok=True)
    all_partner_rows=[]
    coverage=[]
    for dest in DESTINATIONS:
        reporter=int(pycountry.countries.get(alpha_3=dest).numeric)
        for y in BASE_YEARS:
            for h in HS:
                url=API+"?"+urlencode({"reporterCode":reporter,"period":y,"flowCode":"M",
                    "cmdCode":h,"maxRecords":CAP,"breakdownMode":"classic"})
                obj,raw,err=query(url)
                state="API_ERROR";n=0;bad=0;dup=0;seen=set();world=None;orig_val=0.0;orig_cnt=0
                if obj is not None:
                    recs=obj["data"]
                    n=len(recs)
                    (OUT/"raw_api"/f"{dest}_{y}_HS{h}.json").write_bytes(raw)
                    for rec in recs:
                        try:
                            partner=int(rec.get("partnerCode",-1))
                            val=float(rec["primaryValue"])
                            good=(int(rec.get("reporterCode",-1))==reporter
                                and int(rec.get("period",rec.get("refYear",-1)))==y
                                and str(rec.get("flowCode"))=="M" and str(rec.get("cmdCode"))==h
                                and partner>=0 and val>=0 and math.isfinite(val))
                            if not good:bad+=1;continue
                            if partner in seen:dup+=1;continue
                            seen.add(partner)
                            if partner==0:world=val
                            if partner in m49 and partner!=reporter:
                                orig_cnt+=1;orig_val+=val
                            all_partner_rows.append({
                                "destination_ISO3":dest,"Year":y,"HS4":h,
                                "origin_M49":partner,"origin_ISO3_in_original_47":m49.get(partner,""),
                                "value_nominal_USD":val,
                                "World_aggregate_not_a_source":partner==0,
                                "not_final_technology_spillover":True})
                        except (TypeError,ValueError,KeyError):
                            bad+=1
                    state=("CAPPED" if n>=CAP else "BAD_METADATA_OR_DUPLICATE" if bad or dup else
                           "VALID_PREVIEW" if n else "EMPTY_UNREPORTED_NOT_ZERO")
                frac=orig_val/world if world and world>0 else None
                coverage.append({"destination_ISO3":dest,"Year":y,"HS4":h,
                    "status":state,"preview_rows":n,
                    "country_origins_in_original_47":orig_cnt,
                    "world_reported_USD":world,
                    "reported_original_47_source_USD":orig_val,
                    "observed_origins_fraction_of_world":frac,
                    "raw_response_sha256":hashlib.sha256(raw).hexdigest() if raw else "",
                    "duplicates":dup,"bad_metadata":bad,"error":err,
                    "origin_coverage_not_proof_full_partner_data":True,
                    "no_stata_or_causal_estimation":True})
                print("COMTRADE_MULTIRECIPIENT",dest,y,h,state,"allrows",n,
                    "original_sources",orig_cnt,"share_of_world",frac,"error",err,flush=True)
                time.sleep(.7)
    assert len(coverage)==18
    csvout("three_country_18_annual_source_coverage.csv",coverage)
    if all_partner_rows:csvout("three_country_2005_2007_partners.csv",all_partner_rows)
    combined=[]
    for dest in DESTINATIONS:
        yrs=[x for x in coverage if x["destination_ISO3"]==dest]
        denom=sum(float(x["world_reported_USD"]) for x in yrs if x["world_reported_USD"] is not None)
        numer=sum(float(x["reported_original_47_source_USD"]) for x in yrs)
        groups=defaultdict(list)
        for r in all_partner_rows:
            if r["destination_ISO3"]==dest and r["origin_ISO3_in_original_47"] and r["origin_ISO3_in_original_47"]!=dest:
                groups[r["origin_ISO3_in_original_47"]].append(r)
        combined.append({"destination_ISO3":dest,
            "world_total_USD_2005_2007_2_HS4":denom,
            "observed_origins_value_USD":numer,
            "observed_origins_fraction_of_reported_world":numer/denom if denom>0 else None,
            "observed_source_countries_in_original_47":len(groups),
            "source_countries_with_six_reported_cells":sum(len(v)==6 for v in groups.values()),
            "source_weight_quality":"PROVISIONAL_NOT_FULLY_OBSERVED"})
    csvout("three_country_preperiod_weight_feasibility.csv",combined)
    failed=[r for r in coverage if r["status"]!="VALID_PREVIEW" or r["world_reported_USD"] is None]
    summary={
        "phase":"EXTENDED_DATA_EXPERIMENTAL",
        "source_run_scope":"KGZ,MDA,PAN 2005-2007, all partners, HS 8471 and 8517",
        "requests_attempted":18,"valid_headings":18-len(failed),
        "bad_queries":[{"country":r["destination_ISO3"],"year":r["Year"],"heading":r["HS4"],"status":r["status"]} for r in failed],
        "partner_trade_values":len(all_partner_rows),
        "base_period_weight_feasibility":combined,
        "original_data_sha256":lock["original_data_sha256"],
        "original_professor_phase_modified":False,
        "not_all_HS_based_ICT":True,
        "no_missing_filled_as_zero":True,
        "no_foreign_technology_causal_identification":True,
        "no_Stata_executed":True,
        "timestamp_utc":datetime.now(timezone.utc).isoformat()}
    (OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("COMTRADE_MULTIRECIPIENT_SUMMARY",json.dumps(combined),flush=True)
    print("COMTRADE_MULTIRECIPIENT_DONE valid",18-len(failed),"of 18",flush=True)
    assert not failed,"One response missing; do not claim six complete source headings."

if __name__=="__main__":
    main()
