"""Independently check this repository's raw workbook against current public WDI API.
Never mutate input; current WDI revisions may differ from the original snapshot.
"""
import json, urllib.request, urllib.parse, ssl, time, hashlib
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
OUT=ROOT/"outputs/wdi"
IND={"Growth":"NY.GDP.MKTP.KD.ZG","Productivity":"SL.GDP.PCAP.EM.KD",
     "Internet":"IT.NET.USER.ZS","Broadband":"IT.NET.BBND.P2",
     "ICT_Exports":"BX.GSR.CCIS.ZS","Unemployment":"SL.UEM.TOTL.ZS",
     "Inflation":"FP.CPI.TOTL.ZG","RnD":"GB.XPD.RSDV.GD.ZS"}
def retrieve(ind):
    q=urllib.parse.urlencode({"format":"json","date":"2005:2022","per_page":20000})
    url="https://api.worldbank.org/v2/country/all/indicator/"+ind+"?"+q
    request=urllib.request.Request(url,headers={"User-Agent":"Digital-Economy-Research-Audit/1.0"})
    with urllib.request.urlopen(request,timeout=40,context=ssl.create_default_context()) as fp:
        j=json.load(fp)
    if not isinstance(j,list) or len(j)!=2: raise RuntimeError("WDI did not return data array")
    page_count=int(j[0].get("pages",1))
    if page_count>1: raise RuntimeError(f"WDI returned {page_count} pages; partial data not accepted")
    return {(e["countryiso3code"],int(e["date"])):e["value"]
            for e in j[1] if e and e.get("countryiso3code") and e.get("date") and e.get("value") is not None},url
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    a=pd.read_excel(RAW).sort_values(["ISO3","Year"])
    result={"input_sha256":hashlib.sha256(RAW.read_bytes()).hexdigest(),
            "requested_at_utc":pd.Timestamp.now(tz="UTC").isoformat(),
            "important":"Independent current WDI comparison, NOT proof of historical vintages or input integrity; raw data unchanged.",
            "comparisons":{}}
    rows=[]
    for col,ind in IND.items():
        try:
            lookup,url=retrieve(ind)
            checked=missing=close=disagree=0
            discrepancies=[]
            for _,r in a[["ISO3","Year",col]].iterrows():
                k=(str(r.ISO3),int(r.Year)); actual=lookup.get(k)
                if actual is None:
                    missing+=1
                    rows.append([col,ind,k[0],k[1],float(r[col]),None,None,"WDI_missing"])
                    continue
                checked+=1
                delta=float(r[col])-float(actual)
                good=abs(delta)<=max(1e-4,abs(float(actual))*1e-5)
                if good: close+=1
                else:
                    disagree+=1
                    discrepancies.append({"ISO3":k[0],"Year":k[1],"raw":float(r[col]),
                            "current_WDI":float(actual),"difference":delta})
                rows.append([col,ind,k[0],k[1],float(r[col]),float(actual),delta,
                             "near_equal" if good else "disagrees"])
            result["comparisons"][col]={"indicator":ind,"url":url,"success":True,
                "WDI_available_keys":len(lookup),"matched_near_equal":close,
                "mismatched":disagree,"WDI_missing":missing,
                "representative_mismatches":discrepancies[:15]}
        except Exception as e:
            result["comparisons"][col]={"indicator":ind,"success":False,
                                      "error":str(e),"status":"NOT_VERIFIED"}
        print("WDI_RESULT",col,json.dumps(result["comparisons"][col],ensure_ascii=False),flush=True)
        time.sleep(.25)
    cols=["variable","WDI_code","ISO3","Year","raw","WDI_current","delta","status"]
    pd.DataFrame(rows,columns=cols).to_csv(OUT/"per_cell_comparison.csv",index=False)
    (OUT/"wdi_audit.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("WDI_AUDIT_FINISHED",sum(x["success"] for x in result["comparisons"].values()),
          "of",len(IND),"indicators retrieved",flush=True)
if __name__=="__main__":main()
