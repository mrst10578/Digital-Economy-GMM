#!/usr/bin/env python3
"""All-years source HS revision discovery for the exact professor 47-country sample.

Uses UN Comtrade public /getDA, not the 500-row trade preview. Data availability
does not imply HS6 trade values are accessible. Never infer a revision from year.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pycountry

ROOT = Path(__file__).resolve().parents[3]
LOCK = ROOT / "config/extended/phase2_original_47_country_sample_lock.json"
BASE = ROOT / "data/raw/Balanced_Panel_Data.xlsx"
EDITION_CSV = ROOT / "data/extended/official_ict_hs6/unctad_ict_goods_official_hs6_1992_to_2022.csv"
OUT = ROOT / "outputs/extended/source_47_edition_all_years"
SOURCE = "https://comtradeapi.un.org/public/v1/getDA/C/A/HS"
EDITION_CODES = {"H0", "H1", "H2", "H3", "H4", "H5", "H6"}
YEARS = tuple(range(2005, 2023))

def request(year):
    params={"period":str(year)}
    url=SOURCE+"?"+urlencode(params)
    for attempt in range(3):
        try:
            with urlopen(Request(url,headers={"User-Agent":"Academic-ICT-HS-Edition-Coverage/1.0",
                  "Accept":"application/json"}),timeout=60) as stream:
                raw=stream.read(25_000_001)
                http=stream.status
            if len(raw)>25_000_000:
                raise ValueError("Source metadata response exceeded 25 MB cap")
            data=json.loads(raw)
            if not isinstance(data,dict) or not isinstance(data.get("data"),list):
                raise ValueError("Unexpected UN Comtrade getDA source schema")
            if data.get("count") is not None and int(data["count"])!=len(data["data"]):
                raise ValueError("getDA declared row count does not equal available rows")
            return raw,data,http,url
        except HTTPError as exc:
            if exc.code in (429,500,502,503,504) and attempt<2:
                time.sleep(14*(attempt+1));continue
            raise RuntimeError(f"Unresolved source availability HTTP {exc.code} for {year}") from None
        except URLError as exc:
            if attempt<2:
                time.sleep(14*(attempt+1));continue
            raise RuntimeError(f"Source availability network error {type(exc).__name__}") from None
    raise RuntimeError(f"Source availability failed for {year}")

def main():
    lock=json.loads(LOCK.read_text(encoding="utf-8"))
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==lock["original_data_sha256"]
    assert len(lock["iso3_to_original_country_name"])==47
    m49={}
    for iso in lock["iso3_to_original_country_name"]:
        country=pycountry.countries.get(alpha_3=iso)
        assert country is not None, f"Unmapped original ISO country {iso}"
        code=int(country.numeric)
        assert code not in m49
        m49[code]=iso
    with EDITION_CSV.open(encoding="utf-8",newline="") as f:
        editions={x["Comtrade_classificationCode"] for x in csv.DictReader(f)}
    assert editions==EDITION_CODES
    OUT.mkdir(parents=True,exist_ok=True)
    results=[]
    manifests=[]
    for year in YEARS:
        raw,data,http,url=request(year)
        (OUT/f"raw_getDA_all_reporters_{year}.json").write_bytes(raw)
        seen=defaultdict(list)
        for rec in data["data"]:
            if not isinstance(rec,dict):raise ValueError("getDA includes non-object record")
            if int(rec.get("period",-1))!=year:
                raise ValueError(f"Unexpected source period in {year}")
            rep=int(rec.get("reporterCode",-1))
            if rep in m49:
                seen[rep].append(rec)
        for rep,iso in sorted(m49.items()):
            recs=seen.get(rep,[])
            original=[r for r in recs if r.get("isOriginalClassification") is True
                      and r.get("classificationCode") in EDITION_CODES]
            unique=sorted({r["classificationCode"] for r in original})
            status=("VERIFIED_SINGLE_SOURCE_REVISION" if len(unique)==1
                   else "MISSING_SOURCE_NOT_ZERO" if not recs
                   else "AMBIGUOUS_OR_UNSUPPORTED_SOURCE_REVISION")
            results.append({"ISO3":iso,"M49":rep,"Year":year,
                "status":status,
                "source_HS_edition":unique[0] if len(unique)==1 else "",
                "source_rows_matching_original_47":len(recs),
                "source_metadata_original_rows":len(original),
                "all_returned_classifications":";".join(sorted(
                   {str(r.get("classificationCode","")) for r in recs})),
                "no_year_based_edition_assumption":True,
                "absent_is_not_zero":True})
        manifests.append({"Year":year,"source_url_no_secret":url,
            "http_status":http,"declared_count":data.get("count"),
            "raw_rows":len(data["data"]),
            "sha256":hashlib.sha256(raw).hexdigest(),
            "matching_47_country_rows":sum(len(v) for v in seen.values())})
        print("PHASE2_OFFICIAL_GETDA_47_SOURCE_YEAR",year,"HTTP",http,
              "rows",len(data["data"]),
              "matches",manifests[-1]["matching_47_country_rows"],flush=True)
        time.sleep(7)
    assert len(results)==846 and len({(r["ISO3"],r["Year"]) for r in results})==846
    with (OUT/"47_country_18_year_HS_revision_2005_2022.csv").open(
         "w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(results[0]))
        writer.writeheader();writer.writerows(sorted(results,key=lambda x:(x["ISO3"],x["Year"])))
    status=Counter(r["status"] for r in results)
    (OUT/"FULL_COVERAGE_AND_PROVENANCE.json").write_text(json.dumps({
        "phase":"EXTENDED_DATA_EXPERIMENTAL",
        "status":dict(status),
        "sample_country_year_slots":len(results),
        "source_metadata_requests":len(manifests),
        "source":manifests,
        "raw_source_files_retained_as_actions_artifact":True,
        "country_year_trade_values_downloaded":False,
        "HS6_comparability_not_established":True,
        "metadata_absent_never_imputed":True,
        "original_professor_data_sha256":lock["original_data_sha256"],
        "utc":datetime.now(timezone.utc).isoformat()
    },ensure_ascii=False,indent=2)+"\n")
    print("PHASE2_OFFICIAL_GETDA_47x18_COMPLETE",dict(status),flush=True)

if __name__=="__main__":main()
