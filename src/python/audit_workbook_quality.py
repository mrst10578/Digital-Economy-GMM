"""Zero-mutation panel workbook integrity and current WDI source cross-check."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import urllib.parse
import urllib.request
import openpyxl

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/Balanced_Panel_Data.xlsx"
TWIN = ROOT / "sources/Balanced_Panel_Data.xlsx"
OUT = ROOT / "outputs/quality_review"
IND = {"Growth": "NY.GDP.MKTP.KD.ZG", "Productivity": "SL.GDP.PCAP.EM.KD",
       "Internet": "IT.NET.USER.ZS", "Broadband": "IT.NET.BBND.P2",
       "ICT_Exports": "BX.GSR.CCIS.ZS", "Unemployment": "SL.UEM.TOTL.ZS",
       "Inflation": "FP.CPI.TOTL.ZG", "RnD": "GB.XPD.RSDV.GD.ZS"}
ALL_VARS = ("Country", "ISO3", "Year", *IND.keys())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fetch(pair):
    column, code = pair
    q=urllib.parse.urlencode({"format":"json","date":"2005:2022","per_page":20000})
    url=f"https://api.worldbank.org/v2/country/all/indicator/{code}?{q}"
    request=urllib.request.Request(url, headers={"User-Agent":"Research-Data-Provenance-Audit/2.0"})
    with urllib.request.urlopen(request,timeout=38) as resp:
        response=json.load(resp)
    if not isinstance(response,list) or len(response)!=2 or not isinstance(response[1],list):
        raise ValueError("Nonstandard WDI response")
    if int(response[0].get("pages",1))!=1:
        raise ValueError("WDI API pagination detected; refuse partial comparison")
    data={(r["countryiso3code"],int(r["date"])):float(r["value"])
          for r in response[1] if r and r.get("countryiso3code") and r.get("value") is not None}
    return column,code,url,data

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    book=openpyxl.load_workbook(RAW, data_only=False, read_only=False)
    active=book.active
    records=list(active.values)
    headers=records[0]
    assert set(ALL_VARS).issubset(headers)
    rows=[dict(zip(headers,r)) for r in records[1:] if any(x is not None for x in r)]
    errors=[]
    key=set()
    countries={}
    for line,r in enumerate(rows,start=2):
        k=(r["ISO3"],r["Year"])
        if k in key:errors.append(f"Duplicate key {k}")
        key.add(k)
        if not isinstance(r["Year"],int) or not 2005<=r["Year"]<=2022:
            errors.append(f"Year invalid at line {line}")
        if not isinstance(r["ISO3"],str) or len(r["ISO3"])!=3:
            errors.append(f"ISO3 invalid at line {line}")
        if r["ISO3"] in countries and countries[r["ISO3"]]!=r["Country"]:
            errors.append(f"Country label changed for {r['ISO3']}")
        countries[r["ISO3"]]=r["Country"]
        for col in IND:
            v=r[col]
            if not isinstance(v,(float,int)) or not math.isfinite(v):
                errors.append(f"Invalid numerical value {col} row {line}")
    ranges={"Productivity":(0,None),"Internet":(0,100),"Broadband":(0,None),
            "ICT_Exports":(0,100),"Unemployment":(0,100),"RnD":(0,None),
            "Growth":(-100,None),"Inflation":(-100,None)}
    domain_violations=[]
    for r in rows:
        for col,(low,high) in ranges.items():
            v=r[col]
            if isinstance(v,(int,float)) and not (v > low if col=="Productivity" else v >= low):
                domain_violations.append([r["ISO3"],r["Year"],col,v,"below minimum"])
            if high is not None and isinstance(v,(int,float)) and v>high:
                domain_violations.append([r["ISO3"],r["Year"],col,v,"above maximum"])
    formula_count=sum(c.data_type=="f" for line in active for c in line)
    excel_error_count=sum(c.data_type=="e" for line in active for c in line)
    if formula_count:errors.append(f"Unexpected formulas: {formula_count}")
    if excel_error_count:errors.append(f"Excel error cells: {excel_error_count}")
    if domain_violations:errors.append(f"Domain violations: {len(domain_violations)}")
    if len(rows)!=846 or len(countries)!=47 or sorted({r["Year"] for r in rows})!=list(range(2005,2023)):
        errors.append("Unexpected country/year/row count")
    if any(sum(r["ISO3"]==code for r in rows)!=18 for code in countries):
        errors.append("Unbalanced country panels")
    if sha(RAW)!=sha(TWIN):
        errors.append("Raw workbook differs from original sources copy")
    range_report={}
    for col in IND:
        low=min(rows,key=lambda x:x[col]); high=max(rows,key=lambda x:x[col])
        jumps=[]
        for cc in countries:
            sub=sorted((r for r in rows if r["ISO3"]==cc),key=lambda r:r["Year"])
            for prev,next_ in zip(sub,sub[1:]):
                delta=next_[col]-prev[col]
                jumps.append((abs(delta),cc,next_["Year"],round(delta,5)))
        range_report[col]={"minimum":{"iso3":low["ISO3"],"year":low["Year"],"value":low[col]},
                          "maximum":{"iso3":high["ISO3"],"year":high["Year"],"value":high[col]},
                          "top_absolute_yearly_changes":sorted(jumps,reverse=True)[:3]}
    outcome={"timestamp_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
             "source_sha256":sha(RAW),"source_twin_sha256":sha(TWIN),
             "records":len(rows),"countries":len(countries),
             "years":len({r['Year'] for r in rows}),"formulas":formula_count,
             "excel_errors":excel_error_count,"structural_errors":errors,
             "domain_violations":domain_violations[:30],"ranges":range_report,
             "wdi_current_comparison":{},
             "note":"Current WDI revisions and gaps do not automatically mean historical input was corrupted; no raw data changed."}
    if errors:
        print("STRUCTURAL_OR_DOMAIN_ERRORS",errors,flush=True)
    else:
        print("STRUCTURAL_AND_DOMAIN_CHECKS_PASS",len(rows),len(countries),len(IND),flush=True)
    if os.environ.get("SOURCE_AUDIT_OFFLINE") == "1":
        outcome["wdi_current_comparison"] = {"status":"NOT_CHECKED_OFFLINE_MODE"}
        (OUT/"source_quality_latest.json").write_text(json.dumps(outcome,indent=2,ensure_ascii=False)+"\n")
        print("OFFLINE_STRUCTURE_AUDIT", "PASS" if not errors else "FAIL",flush=True)
        if errors:raise SystemExit(2)
        return
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(fetch,pair):pair[0] for pair in IND.items()}
        for future in as_completed(futures):
            column=futures[future]
            try:
                col,code,url,reference=future.result()
                similar=0;different=0;no_value=0;examples=[]
                for r in rows:
                    current=reference.get((r["ISO3"],r["Year"]))
                    if current is None:
                        no_value+=1
                        continue
                    absolute=abs(float(r[col])-current)
                    isclose=absolute<=max(1e-4,abs(current)*1e-5)
                    if isclose:
                        similar+=1
                    else:
                        different+=1
                        if len(examples)<10:
                            examples.append({"country":r["ISO3"],"year":r["Year"],
                                "raw":r[col],"latest_WDI":current,"absolute_delta":absolute})
                outcome["wdi_current_comparison"][col]={"indicator":code,"verified":True,
                    "matched":similar,"different":different,"missing_in_current_WDI":no_value,
                    "example_differences":examples,"URL":url}
                print("WDI_CHECK",col,"match",similar,"different",different,"currently_missing",no_value,flush=True)
            except Exception as exc:
                outcome["wdi_current_comparison"][column]={"verified":False,"error":str(exc)}
                print("WDI_UNVERIFIED",column,str(exc)[:120],flush=True)
    (OUT/"source_quality_latest.json").write_text(json.dumps(outcome,indent=2,ensure_ascii=False)+"\n")
    print("SUMMARY_CHECK",json.dumps({"structural_ok":not errors,
        "WDI_success":sum(v.get("verified",False) for v in outcome["wdi_current_comparison"].values()),
        "WDI_disagree":sum(v.get("different",0) for v in outcome["wdi_current_comparison"].values()),
        "WDI_missing":sum(v.get("missing_in_current_WDI",0) for v in outcome["wdi_current_comparison"].values())}),flush=True)
    if errors:
        raise SystemExit(2)
if __name__=="__main__":
    main()
