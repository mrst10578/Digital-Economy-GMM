#!/usr/bin/env python3
"""Phase B small UN Comtrade test for 18 singleton years, no token and no Stata.

The multi-period public preview returned HTTP 400, so run ONE year at a time
for one prespecified reporter AZE, import from CHN, HS broad chapter 85.
Not all reporters/partners and not ICT-only; no causal or full-network claims.
"""
import csv
import hashlib
import json
import time
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import urlopen,Request
from urllib.parse import urlencode
from urllib.error import HTTPError,URLError

ROOT=Path(__file__).resolve().parents[3]
LOCK=ROOT/"config/extended/phase2_original_47_country_sample_lock.json"
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
OUT=ROOT/"outputs/extended/comtrade_aze_18_singleton_years"
URL="https://comtradeapi.un.org/public/v1/preview/C/A/HS"
REPORTER=31 # Azerbaijan, UN M49
PARTNER=156 # China, UN M49

def query(y):
    p=urlencode({"reporterCode":REPORTER,"partnerCode":PARTNER,
                 "period":y,"cmdCode":"85","flowCode":"M",
                 "maxRecords":40,"breakdownMode":"classic"})
    url=URL+"?"+p
    last=""
    for attempt in range(3):
        try:
            request=Request(url,headers={"User-Agent":"PhaseB-Research-AZE-single-year-Comtrade/1.0",
                                         "Accept":"application/json"})
            with urlopen(request,timeout=30) as response:
                raw=response.read(2_000_000)
                assert len(raw)<2_000_000
                data=json.loads(raw)
            assert isinstance(data,dict) and isinstance(data.get("data"),list)
            return data,raw,url,""
        except (HTTPError,URLError,TimeoutError,ValueError,AssertionError) as exc:
            last=f"{type(exc).__name__}: {str(exc)[:190]}"
            if isinstance(exc,HTTPError) and exc.code not in (408,429,500,502,503,504):
                break
            time.sleep(1.5*(attempt+1))
    return None,b"",url,last

def main():
    lock=json.loads(LOCK.read_text(encoding="utf-8"))
    assert hashlib.sha256(RAW.read_bytes()).hexdigest()==lock["original_data_sha256"]
    assert "AZE" in lock["iso3_to_original_country_name"]
    OUT.mkdir(parents=True,exist_ok=True)
    raws=OUT/"raw";raws.mkdir(exist_ok=True)
    rows=[]
    for y in range(2005,2023):
        payload,raw,url,error=query(y)
        count=0
        status="API_ERROR"
        value=None
        if payload is not None:
            records=payload["data"]
            count=len(records)
            valid=[r for r in records if str(r.get("period",r.get("refYear"))) == str(y) and
                   int(r.get("reporterCode",-1)) == REPORTER and
                   int(r.get("partnerCode",-1)) == PARTNER and
                   str(r.get("flowCode")) == "M" and str(r.get("cmdCode")) == "85"]
            if len(records)>=40: status="TRUNCATED"
            elif len(valid)!=len(records) or len(valid)>1:status="BAD_METADATA_OR_DUPLICATE"
            elif len(valid)==0:status="EMPTY_NOT_ZERO"
            else:
                status="OBSERVED"
                value=valid[0].get("primaryValue")
                value=float(value) if value is not None else None
            (raws/f"AZE_{y}_CHN_HS85.json").write_bytes(raw)
        rows.append({"ISO3":"AZE","year":y,"source_ISO3":"CHN","hs_code":"85",
                     "chapter85_is_ICT_only":"FALSE",
                     "value_nominal_usd":value,
                     "status":status,"records":count,"api_url":url,
                     "error":error,"raw_sha256":hashlib.sha256(raw).hexdigest() if raw else ""})
        print("COMTRADE_SINGLE_YEAR",y,status,"rows",count,"value",value,"error",error,flush=True)
        time.sleep(.5)
    with (OUT/"aze_2005_2022_partner_china_HS85.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    counts={k:sum(r["status"]==k for r in rows) for k in set(r["status"] for r in rows)}
    report={"phase":"EXTENDED_DATA_EXPERIMENTAL",
            "reporter":"AZE","partner":"CHN",
            "observed_rows":counts.get("OBSERVED",0),"possible_2005_2022_rows":18,
            "status_counts":counts,
            "single_year_requests":18,
            "early_year_seen":rows[0]["status"]=="OBSERVED",
            "late_year_seen":rows[-1]["status"]=="OBSERVED",
            "this_is_one_of_47_reporters":True,
            "other_8_country_18year_coverage_unverified":True,
            "HS85_only_not_equivalent_to_ICT_products":True,
            "zero_missing_imputation":True,
            "no_stata_used":True,
            "original_source_sha256_unchanged":lock["original_data_sha256"],
            "cannot_prove_causal_spillover":True,
            "timestamp_utc":datetime.now(timezone.utc).isoformat()}
    (OUT/"summary.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("COMTRADE_SINGLE_YEAR_AUDIT_COMPLETE",json.dumps(counts),flush=True)
    assert counts.get("API_ERROR",0)==0 and counts.get("TRUNCATED",0)==0 and counts.get("BAD_METADATA_OR_DUPLICATE",0)==0,"No false full-panel assertion"

if __name__=="__main__":
    main()
