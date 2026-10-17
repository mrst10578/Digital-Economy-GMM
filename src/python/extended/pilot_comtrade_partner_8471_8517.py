#!/usr/bin/env python3
"""Two-year sample of ICT-relevant HS 8471 and 8517 by individual partners.

Azerbaijan, imported goods, 2005 and 2022. Two 4-digit classes are chosen
before results: 8471 computers/automatic data-processing machines, 8517
telephony/data transmission apparatus. HS definitions change historically;
this pilot neither fully defines ICT nor estimates productivity spillovers.

Unlike HS85 all electrical equipment, partnerCode omitted to ask for partner
breakdown for this one reporter-year-commodity. Validate whether the public
preview cap makes all-partner extraction feasible. Do not equate missing with zero.
"""
from __future__ import annotations
import csv
import hashlib
import json
import time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[3]
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
LOCK=ROOT/"config/extended/phase2_original_47_country_sample_lock.json"
OUT=ROOT/"outputs/extended/comtrade_aze_multi_partner_computers_telecom"
API="https://comtradeapi.un.org/public/v1/preview/C/A/HS"
CODES=("8471","8517")
YEARS=(2005,2022)
REPORTER=31
CAP=500

def fetch(url):
    last=""
    for retry in range(3):
        try:
            req=Request(url,headers={"User-Agent":"Academic-Research-ICT-Source-Check/1.0","Accept":"application/json"})
            with urlopen(req,timeout=32) as f:
                b=f.read(5_000_000)
                if len(b)>=5_000_000:raise ValueError("large response cap")
            j=json.loads(b)
            if not isinstance(j,dict) or not isinstance(j.get("data"),list):
                raise ValueError("Unrecognized API payload")
            return j,b,""
        except (HTTPError,URLError,TimeoutError,ValueError) as ex:
            last=f"{type(ex).__name__}: {str(ex)[:200]}"
            if isinstance(ex,HTTPError) and ex.code not in (429,408,500,502,503,504):break
            time.sleep(1.5*(retry+1))
    return None,b"",last

def main():
    lock=json.loads(LOCK.read_text(encoding="utf-8"))
    assert hashlib.sha256(RAW.read_bytes()).hexdigest()==lock["original_data_sha256"]
    OUT.mkdir(parents=True,exist_ok=True)
    orig=set(lock["iso3_to_original_country_name"])
    # Explicit baseline M49 map from ISO3 via ISO standard data source
    import pycountry
    m49={int(pycountry.countries.get(alpha_3=iso).numeric):iso for iso in orig}
    summary=[]
    partners=[]
    for y in YEARS:
        for cmd in CODES:
            url=API+"?"+urlencode({"reporterCode":REPORTER,"period":y,"flowCode":"M","cmdCode":cmd,"maxRecords":CAP,"breakdownMode":"classic"})
            obj,raw,error=fetch(url)
            status="API_ERROR";rlist=[];valid=[];bad=0
            if obj is not None:
                rlist=obj["data"]
                (OUT/f"raw_AZE_{y}_HS{cmd}_all_partners.json").write_bytes(raw)
                for rec in rlist:
                    try:
                        good=(int(rec.get("reporterCode",-1))==REPORTER and
                           int(rec.get("period",rec.get("refYear",-1)))==y and
                           str(rec.get("cmdCode"))==cmd and str(rec.get("flowCode"))=="M")
                        if good:valid.append(rec)
                        else:bad+=1
                    except (ValueError,TypeError):
                        bad+=1
                status=("TRUNCATED" if len(rlist)>=CAP else
                        "BAD_METADATA" if bad else
                        "PREVIEW_HAS_PARTNERS" if rlist else "PREVIEW_EMPTY")
            for rec in valid:
                p=int(rec.get("partnerCode",-1))
                v=rec.get("primaryValue")
                partners.append({
                    "reporter":"AZE","Year":y,"HS4":cmd,"partner_m49":p,
                    "partner_in_original_sample_ISO3":m49.get(p,""),
                    "value_nominal_usd":v,"is_world_aggregate":p==0,
                    "is_original_47_partner":p in m49,
                    "source_valid":status=="PREVIEW_HAS_PARTNERS",
                    "preliminary_not_complete_ICT_series":True,
                })
            actual_partners={int(x.get("partnerCode",-1)) for x in valid if int(x.get("partnerCode",-1))!=0}
            partner_in_original=actual_partners.intersection(m49)
            summary.append({
                "reporter":"AZE","Year":y,"HS4":cmd,"preview_rows":len(rlist),
                "status":status,"metadata_bad_count":bad,
                "distinct_partner_m49_ex_world":len(actual_partners),
                "distinct_original_47_partners":len(partner_in_original),
                "world_aggregate_present":any(int(x.get("partnerCode",-1))==0 for x in valid),
                "truncated":len(rlist)>=CAP,
                "url":url,"error":error,
                "raw_sha256":hashlib.sha256(raw).hexdigest() if raw else "",
                "new_data_used_in_original_professor_model":False})
            print("COMTRADE_PARTNER_PILOT",y,cmd,status,"rows",len(rlist),
                  "distinct_original_partners",len(partner_in_original),"bad",bad,"error",error,flush=True)
            time.sleep(.6)
    assert len(summary)==4
    def csvout(p,records):
        with p.open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(records[0]))
            w.writeheader();w.writerows(records)
    csvout(OUT/"four_query_summary.csv",summary)
    if partners:csvout(OUT/"original_country_partner_values.csv",partners)
    meta={"phase":"EXTENDED_DATA_EXPERIMENTAL","run_utc":datetime.now(timezone.utc).isoformat(),
          "four_queries":summary,
          "four_digit_HS8471_HS8517_not_full_ICT_basket":True,
          "legacy_HS_code_version_requires_harmonization":True,
          "no_full_panel_or_causal_exogeneity_inference":True,
          "no_stata_and_professor_phase_unmodified":True,
          "source_sha256":lock["original_data_sha256"]}
    (OUT/"summary.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    assert not any(r["status"] in ("API_ERROR","BAD_METADATA","TRUNCATED") for r in summary),"Public API missing/limited: pilot incomplete"
    print("COMTRADE_PARTNER_PILOT_DONE 4 requests; no Stata, no model, no complete-network claim",flush=True)

if __name__=="__main__":
    main()
