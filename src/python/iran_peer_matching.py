"""Retrospective Iran-peer feasibility on VERIFIED 47-country DIGITAL ECONOMY panel.

Date of actual implementation: Oct 2026, AFTER original GMM estimation.
NOT a preregistered pre-estimation peer set; never use outcomes or GMM p-values
to select peers. Do not confuse '30 countries' from email with this 47-sample.

World Bank API original country-specific fields, 2005-2007 baseline.
Five conceptual dimensions with equal weight 0.20:
income(log PPP real GDP per cap), production (two sector shares each .10),
resource rents (log1p), trade openness(log1p), internet penetration(log1p).
No rescaling chosen after inspecting ranking. No mean imputation or zero fill.
"""
from __future__ import annotations
import hashlib,json,time,ssl,urllib.parse,urllib.request
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
SHA="474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b"
OUT=ROOT/"outputs/iran_peers"
PERIOD=[2005,2006,2007]
INDICATORS={
"gdp_ppp_real_pc":"NY.GDP.PCAP.PP.KD",
"industry_pct_gdp":"NV.IND.TOTL.ZS",
"services_pct_gdp":"NV.SRV.TOTL.ZS",
"natural_resource_rents_pct_gdp":"NY.GDP.TOTL.RT.ZS",
"trade_pct_gdp":"NE.TRD.GNFS.ZS",
"internet_users_pct":"IT.NET.USER.ZS",
}
# Sum = 1. Income .20; production structure .20; rents .20; trade .20; digital .20.
WEIGHTS={"gdp_ppp_real_pc":.2,"industry_pct_gdp":.1,
         "services_pct_gdp":.1,"natural_resource_rents_pct_gdp":.2,
         "trade_pct_gdp":.2,"internet_users_pct":.2}
LOG1P={"natural_resource_rents_pct_gdp","trade_pct_gdp","internet_users_pct"}
MIN_BASE_YEARS=2
DESCRIPTIVE_TOP_K=10
def get_official(indicator):
    url="https://api.worldbank.org/v2/country/all/indicator/"+indicator+"?"+urllib.parse.urlencode({
        "format":"json","date":"2005:2007","per_page":25000})
    last=None
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Digital-Economy-Iran-Peer-Audit/1.0"})
            with urllib.request.urlopen(req,timeout=55,context=ssl.create_default_context()) as x:
                payload=json.load(x)
            if not isinstance(payload,list) or len(payload)!=2 or not isinstance(payload[1],list):
                raise ValueError("WDI wrong response type")
            if int(payload[0].get("pages",1))!=1:
                raise ValueError("WDI pagination not complete")
            z={}
            for row in payload[1]:
                if row is None or row.get("value") is None:continue
                k=(row.get("countryiso3code"),int(row["date"]))
                if not k[0] or k[1] not in PERIOD:continue
                val=float(row["value"])
                if not np.isfinite(val):continue
                if k in z:raise ValueError(f"Duplicate WDI country-year {k}")
                z[k]=val
            return z,url
        except Exception as err:
            last=err
            if attempt<2:time.sleep(3*(attempt+1))
    raise RuntimeError(f"WDI retrieval blocked: {indicator}: {last}")

def prepare(panel):
    country_ids=sorted(set(panel.ISO3)|{"IRN"})
    # Never query only presumed 'similar' countries; take original 47 + Iran.
    cols=[]
    lineage={}
    for name,code in INDICATORS.items():
        data,url=get_official(code)
        lineage[name]={"WDI_indicator":code,"retrieved_from":url,
          "available_country_year_keys":len(data),"minimum_baseline_years":MIN_BASE_YEARS}
        for c in country_ids:
            vals=[data.get((c,y)) for y in PERIOD]
            ok=[x for x in vals if x is not None]
            cols.append(dict(ISO3=c,indicator=name,n_baseline_years=len(ok),
               mean_2005_2007=float(np.mean(ok)) if len(ok)>=MIN_BASE_YEARS else np.nan,
               source_code=code,year_2005=vals[0],year_2006=vals[1],year_2007=vals[2]))
        print("IRAN_WDI_GOT",name,len(data),"IRAN_2005",data.get(("IRN",2005)),flush=True)
        time.sleep(.3)
    raw=pd.DataFrame(cols)
    raw.to_csv(OUT/"wdi_indicators_47_plus_iran_2005_2007.csv",index=False)
    matrix=raw.pivot(index="ISO3",columns="indicator",values="mean_2005_2007")
    return matrix,lineage,raw

def rank_peers(matrix):
    needed=list(INDICATORS)
    excluded=matrix.loc[matrix[needed].isna().any(axis=1)].copy()
    retained=matrix.dropna(subset=needed).copy()
    if "IRN" not in retained.index:
        raise RuntimeError("Iran missing 2+ years for at least one prespecified dimension")
    if len(retained)<12:
        raise RuntimeError(f"Too few complete countries for descriptive peer ranking ({len(retained)})")
    t=retained[needed].copy()
    if (t.gdp_ppp_real_pc<=0).any():raise ValueError("Invalid PPP GDP")
    t.gdp_ppp_real_pc=np.log(t.gdp_ppp_real_pc)
    for col in LOG1P:
        if (t[col]<0).any():raise ValueError(f"Invalid negative log1p WDI value: {col}")
        t[col]=np.log1p(t[col])
    # Compute scaling using EXCLUSIVELY WDI baseline indicators; no outcomes.
    center=t.mean(axis=0)
    sd=t.std(axis=0,ddof=0)
    if (sd<=0).any():raise ValueError("Non-variable macro similarity dimension")
    zs=(t-center)/sd
    distance=np.sqrt(((zs-zs.loc["IRN"])**2*pd.Series(WEIGHTS)).sum(axis=1))
    ranking=retained.assign(distance_to_iran=distance).drop(index="IRN").sort_values(
         ["distance_to_iran"],ascending=True)
    ranking.insert(0,"similarity_rank",np.arange(1,len(ranking)+1))
    ranking["top_5_descriptive"]=ranking.similarity_rank.le(5)
    ranking["top_10_descriptive"]=ranking.similarity_rank.le(DESCRIPTIVE_TOP_K)
    ranking.to_csv(OUT/"peer_distance_rank_ALL_eligible.csv")
    stats=dict(complete_cases_including_IRN=len(retained),eligible_original_countries=len(ranking),
       excluded_due_to_missing_baseline=sorted(excluded.index.tolist()),
       missing_baseline_dimensions_by_country={
           iso:[x for x in needed if pd.isna(matrix.loc[iso,x])] for iso in excluded.index},
       closest_5=list(ranking.head(5).index),
       closest_10=list(ranking.head(10).index),
       N_for_dynamic_GMM="Top-5/10 intentionally NOT GMM-estimated; small-N identification unreliable",
       peer_status="RETROSPECTIVE_DESCRIPTIVE_ONLY; not pre-estimation selection")
    (OUT/"peer_method_inputs.json").write_text(json.dumps({
      "prespecified_years":PERIOD,"original_47_only":True,
      "peer_target":"IRN","indicator_codes":INDICATORS,"weights":WEIGHTS,
      "transforms":{"gdp_ppp_real_pc":"ln","natural_resource_rents_pct_gdp":"log1p",
          "trade_pct_gdp":"log1p","internet_users_pct":"log1p",
          "industry_pct_gdp":"raw","services_pct_gdp":"raw"},
      "missing_policy":"at least 2 of 3 years per indicator, no imputation",
      "standardization":"population zscores of complete original 47 + Iran on 2005-07 macro features",
      "ranking_only_not_subgroup_GMM":True,
      "original_estimation_completed_before_matching":True},indent=2,ensure_ascii=False))
    return ranking,stats

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    status={"input_source":str(RAW),"sha_expected":SHA,
      "source":"World Bank WDI current API 2005-2007 baseline, 47 original ISO3 + IRN",
      "timestamp_utc":datetime.now(timezone.utc).isoformat(),
      "not_source_request":"Original 30-country fallback in sender email not assigned to this 47-country model",
      "original_gmm_validated":False,
      "status":"BLOCKED"}
    try:
        assert hashlib.sha256(RAW.read_bytes()).hexdigest()==SHA,"Original workbook has changed"
        panel=pd.read_excel(RAW)
        assert panel.ISO3.nunique()==47 and len(panel)==846
        matrix,lineage,raw=prepare(panel)
        ranking,stats=rank_peers(matrix)
        status.update(indicator_lineage=lineage,results=stats,
                      status="COMPLETED_DESCRIPTIVE_NOT_CAUSAL",
                      n_raw_wdi_rows=len(raw))
        print("IRAN_PEER_RANKING",ranking.head(15)[["similarity_rank","distance_to_iran"]].to_json(),flush=True)
    except Exception as e:
        status["block_reason"]=str(e)
        print("IRAN_PEER_SOURCE_GATE_FAILED",str(e),flush=True)
        raise
    finally:
        (OUT/"manifest.json").write_text(json.dumps(status,indent=2,ensure_ascii=False),encoding="utf8")
    print("IRAN_PEER_FINISHED",json.dumps({"status":status["status"],"results":stats},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
