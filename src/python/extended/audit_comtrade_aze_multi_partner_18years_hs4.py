#!/usr/bin/env python3
"""Phase B preregistered complete historic multi-source partner feasibility.

Only receiver Azerbaijan (AZE) is tested, each year 2005..2022 for:
  HS 8471: automatic data processing machines
  HS 8517: telephony / transmission devices
All partner trade rows returned by the *public keyless preview*. The two HS4
categories are illustrative of ICT-related goods, not a stable/complete ICT
basket. Changes to HS code scope across editions need explicit harmonization.

For each year and code: assure reporter=AZE, year, flow=M, HS code; detect
truncation (500), duplicate partners, world aggregate, 47-original sample
coverage in USD. World aggregate is never treated as a partner.
Each raw response preserved in the separate Phase B Actions artifact.
No GMM/FE estimation, no use of Stata, no model updates to professor Phase A.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pycountry

ROOT=Path(__file__).resolve().parents[3]
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
LOCK=ROOT/"config/extended/phase2_original_47_country_sample_lock.json"
OUT=ROOT/"outputs/extended/comtrade_aze_2005_2022_all_source_countries_hs4"
API="https://comtradeapi.un.org/public/v1/preview/C/A/HS"
REPORTER=31
MAX_ROWS=500
HS_CODES=("8471","8517")
YEARS=range(2005,2023)

def download(url):
    last=""
    for r in range(4):
        try:
            req=Request(url,headers={"User-Agent":"Research-Academic-PhaseB-Country-Trade/1.0","Accept":"application/json"})
            with urlopen(req,timeout=30) as f:
                b=f.read(7_000_000)
                assert len(b)<7_000_000,"Response exceeds bounded research preflight"
                j=json.loads(b)
            assert isinstance(j,dict) and isinstance(j.get("data"),list),"Unexpected API response"
            return j,b,""
        except (HTTPError,URLError,TimeoutError,ValueError,AssertionError) as e:
            last=f"{type(e).__name__}: {str(e)[:180]}"
            if isinstance(e,HTTPError) and e.code not in (429,408,500,502,503,504):break
            time.sleep(1.3*(r+1))
    return None,b"",last

def dump_csv(file,rows):
    if not rows:return
    with file.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)

def main():
    lock=json.loads(LOCK.read_text(encoding="utf-8"))
    base_hash=hashlib.sha256(RAW.read_bytes()).hexdigest()
    assert base_hash==lock["original_data_sha256"]
    home=set(lock["iso3_to_original_country_name"])
    m49={int(pycountry.countries.get(alpha_3=x).numeric):x for x in home}
    assert len(m49)==47
    OUT.mkdir(parents=True,exist_ok=True)
    archive=OUT/"raw_API"
    archive.mkdir(exist_ok=True)
    metrics=[]
    partners=[]
    for year in YEARS:
        for code in HS_CODES:
            url=API+"?"+urlencode({"reporterCode":REPORTER,"period":year,"flowCode":"M",
                  "cmdCode":code,"maxRecords":MAX_ROWS,"breakdownMode":"classic"})
            obj,raw,error=download(url)
            status="API_ERROR"
            count=0
            bad=0
            duplicates=0
            observed={}
            if obj is not None:
                items=obj["data"]
                count=len(items)
                (archive/f"AZE_{year}_HS{code}_all_partner_rows.json").write_bytes(raw)
                for rec in items:
                    try:
                        ok=(int(rec.get("reporterCode",-1))==REPORTER
                         and int(rec.get("period",rec.get("refYear",-1)))==year
                         and str(rec.get("flowCode"))=="M"
                         and str(rec.get("cmdCode"))==code)
                        p=int(rec.get("partnerCode",-1))
                        v=rec.get("primaryValue")
                        if not ok or p<0 or v is None:
                            bad+=1;continue
                        v=float(v)
                        if not math.isfinite(v) or v<0:
                            bad+=1;continue
                        if p in observed:
                            duplicates+=1;continue
                        observed[p]=v
                        partners.append({"reporter_ISO3":"AZE","Year":year,
                            "HS4":code,"partner_M49":p,
                            "partner_ISO3_if_in_original_sample":m49.get(p,""),
                            "is_world_aggregate":p==0,"value_nominal_usd":v,
                            "source_year_classification":"HS as served by Comtrade; revision not harmonized",
                            "not_complete_or_causal_spillover":True})
                    except (TypeError,ValueError):
                        bad+=1
                status=("TRUNCATED" if count>=MAX_ROWS else
                    "INVALID_OR_DUPLICATE_ROWS" if bad or duplicates else
                    "VALID_PREVIEW" if items else "EMPTY_PREVIEW_NOT_ZERO")
            in_sample={p:v for p,v in observed.items() if p in m49 and p!=REPORTER}
            world=observed.get(0)
            subset=sum(in_sample.values())
            ratio=subset/world if world and world>0 else None
            # Do NOT interpret this ratio as completeness. Some missing country
            # breakdown, non-47 partners, and reexports are possible.
            metrics.append({"reporter_ISO3":"AZE","Year":year,"HS4":code,
                "status":status,"source_preview_rows":count,
                "all_distinct_partner_rows":len(observed),
                "distinct_original_47_origin_countries":len(in_sample),
                "world_imports_nominal_usd":world,
                "original_47_origin_summed_imports_usd":subset,
                "original_47_reported_partner_share_of_world":ratio,
                "metadata_failed_rows":bad,"duplicate_partners":duplicates,
                "raw_sha256":hashlib.sha256(raw).hexdigest() if raw else "",
                "api_url":url,"error":error,
                "all_partners_complete_claim":"FALSE",
                "HS4_comprehensive_ICT_claim":"FALSE",
                "causal_identification_claim":"FALSE"})
            print("COMTRADE_AZE_MULTIPARTNER",year,code,status,
                  "rows",count,"original_country_origins",len(in_sample),
                  "world",world,"in_sample_share",ratio,"error",error,flush=True)
            time.sleep(.55)
    assert len(metrics)==36
    dump_csv(OUT/"year_HS4_36_coverage.csv",metrics)
    dump_csv(OUT/"partner_observations.csv",partners)
    pre=[r for r in metrics if r["Year"] in (2005,2006,2007)]
    bad=sum(r["status"] not in ("VALID_PREVIEW","EMPTY_PREVIEW_NOT_ZERO") for r in metrics)
    observed=sum(r["status"]=="VALID_PREVIEW" for r in metrics)
    quality={
      "phase":"EXTENDED_DATA_EXPERIMENTAL",
      "original_sha256":base_hash,"original_professor_data_changed":False,
      "requests_expected":36,"requests_valid_nonempty":observed,
      "requests_bad_or_truncated":bad,
      "preperiod_2005_2007_requests":len(pre),
      "preperiod_requests_valid":sum(r["status"]=="VALID_PREVIEW" for r in pre),
      "n_reporter_countries":1,
      "n_partner_rows":len(partners),
      "n_country_year_code_observations":len(metrics),
      "all_reporting_years":18,
      "world_aggregate_must_not_count_as_source":True,
      "no_fully_representative_trade_network_asserted":True,
      "no_missing_imputed_zero":True,
      "two_narrower_HS4_categories_not_unified_ICT_basket":True,
      "per_year_HS_classification_may_change":True,
      "statically_defined_weights_future_step_only":True,
      "no_stata_or_GMM_run":True,
      "causal_spillover_validated":False,
      "timestamps_utc":datetime.now(timezone.utc).isoformat(),
    }
    (OUT/"summary.json").write_text(json.dumps(quality,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("COMTRADE_AZE_MULTIPARTNER_COMPLETE",observed,"of",len(metrics),
        "source_partners",len(partners),"bad",bad,flush=True)
    assert bad==0 and observed==36, "Not all API year/category panels valid; do not report complete"

if __name__=="__main__":
    main()
