"""REAL official UN Comtrade HS2017 chapter 85 bilateral-import pilot.
NEVER a causal or full-sample estimation. No guessed missing trade flows.
"""
from __future__ import annotations
import hashlib, json, time, urllib.parse, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime,timezone
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
OUT=ROOT/"outputs/phase_b_pilot"
ISO_M49={"USA":840,"CHN":156,"DEU":276}
YEARS=[2018,2021]
API="https://comtradeapi.un.org/public/v1/preview/C/A/H5"
def fetch(reporter,partner,year):
    args=dict(period=str(year),reporterCode=str(ISO_M49[reporter]),
         partnerCode=str(ISO_M49[partner]),flowCode="M",cmdCode="85",
         breakdownMode="classic",maxRecords="100")
    url=API+"?"+urllib.parse.urlencode(args)
    # official no-login preview; no credentials or sensitive params.
    req=urllib.request.Request(url,headers={"User-Agent":"AcademicMethodsAudit/1.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=32) as response:
        assert response.status==200
        content=response.read(3_000_000)
    d=json.loads(content)
    if not isinstance(d,dict) or not isinstance(d.get("data"),list):
        raise ValueError("API response not valid UN Comtrade JSON data")
    count=int(d.get("count",len(d["data"])))
    if count>=100 or len(d["data"])>=100 or len(d["data"])!=count:
        raise ValueError(f"TRUNCATED_OR_DISAGREEING_RESPONSE count={count} rows={len(d['data'])}")
    return d,url,hashlib.sha256(content).hexdigest()
def clean(d,reporter,partner,year,source_url,sha):
    records=d["data"]
    if not records:return dict(reporter=reporter,partner=partner,year=year,observed=False,
                               amount_usd=np.nan,reason="No returned bilateral row, not assumed zero",
                               raw_sha256=sha,source_url=source_url)
    vals=[]
    for record in records:
        if int(record["reporterCode"])!=ISO_M49[reporter]:raise ValueError("Reporter code mismatch")
        if int(record["partnerCode"])!=ISO_M49[partner]:raise ValueError("Partner code mismatch")
        if int(record.get("refYear",record.get("period",year)))!=year:raise ValueError("Year mismatch")
        if str(record["cmdCode"])!="85":raise ValueError("Product mismatch")
        if str(record["flowCode"]).upper()!="M":raise ValueError("Not imports")
        if str(record.get("classificationCode","H5"))!="H5":raise ValueError("Not HS2017")
        value=float(record["primaryValue"])
        if not np.isfinite(value) or value<0:raise ValueError("Invalid observed import USD")
        vals.append(value)
    if len(vals)!=1:raise ValueError("Unexpected multiple aggregate records: would double count")
    return dict(reporter=reporter,partner=partner,year=year,observed=True,
                amount_usd=vals[0],reason="",raw_sha256=sha,source_url=source_url)
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    df=pd.read_excel(RAW)
    assert len(df)==846 and df.ISO3.nunique()==47
    rows=[];failures=[]
    for year in YEARS:
        for reporter in ISO_M49:
            for partner in ISO_M49:
                if reporter==partner:continue
                try:
                    data,url,sha=fetch(reporter,partner,year)
                    rec=clean(data,reporter,partner,year,url,sha)
                    rows.append(rec)
                    print("REAL_COMTRADE",year,reporter,"<",partner,rec["amount_usd"],"observed",rec["observed"],flush=True)
                except Exception as exc:
                    failures.append(dict(reporter=reporter,partner=partner,year=year,error=str(exc)))
                    print("PILOT_SOURCE_BLOCKED",year,reporter,partner,str(exc),flush=True)
                time.sleep(.4)
    trades=pd.DataFrame(rows)
    trades.to_csv(OUT/"real_observed_comtrade_hs85_pairs.csv",index=False)
    exposes=[]
    for (reporter,year),sub in trades.groupby(["reporter","year"]) if len(trades) else []:
        if not sub.observed.all() or len(sub)!=2:
            continue
        # t-1 (prior-year partner R&D), not same-year partners; missing RnD FAILS.
        partner_rnd=df.loc[(df.Year==year-1)&(df.ISO3.isin(sub.partner)),["ISO3","RnD"]]
        if len(partner_rnd)!=2:continue
        tmp=sub.merge(partner_rnd,left_on="partner",right_on="ISO3",validate="one_to_one")
        w=tmp.amount_usd/to_sum if (to_sum:=tmp.amount_usd.sum())>0 else np.nan
        if not np.isfinite(w).all():continue
        exposes.append(dict(reporter=reporter,year=year,partner_count=2,
                            hs85_partner_import_USD=float(to_sum),
                            potential_peer_RnD_percent_GDP=float((w*tmp.RnD).sum()),
                            warning="Coverage ONLY 2 pilot partner countries, not whole-world shares; NOT valid causal estimand"))
    pd.DataFrame(exposes).to_csv(OUT/"pilot_peer_rnd_exposure_DO_NOT_ESTIMATE.csv",index=False)
    expected=len(YEARS)*len(ISO_M49)*(len(ISO_M49)-1)
    manifest=dict(source="United Nations Comtrade public preview",source_url=API,
       fetched_at_utc=datetime.now(timezone.utc).isoformat(),product="HS2017 chapter 85",
       product_note="Broad electrical/electronic goods, NOT an observed technology transfer",
       reporter_countries=list(ISO_M49),partner_countries=list(ISO_M49),
       requested_pair_years=expected,observed_pair_years=int(trades.observed.sum()) if len(trades) else 0,
       returned_pairs=int(len(trades)),failed_requests=failures,
       exposure_records=len(exposes),
       status="PILOT_INCOMPLETE" if failures or len(trades)!=expected or not trades.observed.all() else "PILOT_OBSERVED_NOT_CAUSAL",
       gate="No panel spillover regression permitted from 2-year 3-country pilot; cannot call data complete; no missing-value-to-zero conversion")
    (OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf8")
    print("PHASE_B_OFFICIAL_PILOT",json.dumps(manifest,ensure_ascii=False),flush=True)
    # Exit nonzero if API inaccessible or schema invalid; always persist audit artifact.
    if manifest["status"]!="PILOT_OBSERVED_NOT_CAUSAL":raise SystemExit("Pilot source incomplete; NO scientific inference")
if __name__=="__main__":main()
