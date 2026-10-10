"""Full-sample, fail-closed BACI HS2002 partner exposure engine (2006-2022).
Real bilateral data REQUIRED. No fake observations. Estimator is descriptive FE,
not a causal GMM, and proxy is import-weighted foreign digital capability,
NOT verified patent/knowledge transfer.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd
import pycountry
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
SRC_SHA="474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b"
YEARS=tuple(range(2005,2022))    # prior-year weights for 2006...2022 outcomes
MIN_COVERAGE=.80                   # prespecified: known partner share of world HS85 flows
MIN_COUNTRIES=30
MIN_YEARS=12
MIN_OBS=400
def source_files(root):
    files={}
    for year in YEARS:
        matches=list(root.glob(f"BACI_HS02_Y{year}_V*.csv"))
        if len(matches)!=1:
            raise FileNotFoundError(f"Exactly one authentic BACI_HS02_Y{year}_V*.csv required, found {len(matches)}")
        files[year]=matches[0]
    rev={re.search(r"_V([^/]+)\.csv$",p.name).group(1) for p in files.values()}
    if len(rev)!=1:raise ValueError("Mixed BACI release vintages forbidden")
    return files,rev.pop()
def country_m49(countries):
    # World Bank ISO3 to ISO3166 numeric; unsupported matches MUST fail rather than guess.
    output={}
    for iso in countries:
        row=pycountry.countries.get(alpha_3=iso)
        if row is None:raise ValueError(f"Unsupported ISO3 {iso}; explicit audited crosswalk required")
        output[iso]=int(row.numeric)
    if len(set(output.values()))!=len(output):raise ValueError("Duplicate M49 codes")
    return output
def read_baci_hs85(files,importer_codes):
    # BACI HS02 standard columns: t year, i exporter, j importer, k HS6, v trade value in 1000 USD.
    obs=[];hashes={}
    for year,path in sorted(files.items()):
        hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        parts=[]
        for ch in pd.read_csv(path,dtype={"k":str},chunksize=200000,
                              usecols=["t","i","j","k","v"]):
            x=ch.loc[(ch.t==year)&ch.j.isin(importer_codes)&
                     ch.k.str.startswith("85",na=False)].copy()
            if not len(x):continue
            if (x.v<0).any() or not np.isfinite(x.v).all():raise ValueError("Invalid BACI values")
            x=x.loc[x.i!=x.j]
            x=x.loc[(x.i>0)&(x.j>0)]
            parts.append(x.groupby(["i","j"],as_index=False)["v"].sum())
        if not parts:raise ValueError(f"No valid HS85 import flows in year {year}")
        merged=pd.concat(parts).groupby(["i","j"],as_index=False)["v"].sum()
        merged["year"]=year
        obs.append(merged.rename(columns={"i":"exporter_m49","j":"importer_m49","v":"value_thousand_usd"}))
        print("BACI_REAL_YEAR",year,"pairs",len(merged),"value_kUSD",merged.v.sum(),flush=True)
    return pd.concat(obs,ignore_index=True),hashes
def create_exposures(trade,panel,crosswalk,min_coverage=MIN_COVERAGE):
    mapping={v:k for k,v in crosswalk.items()}
    x=trade.copy()
    req={"year","importer_m49","exporter_m49","value_thousand_usd"}
    assert req.issubset(x.columns)
    x["receiver"]=x.importer_m49.map(mapping)
    x["source_iso"]=x.exporter_m49.map(mapping)
    if x.receiver.isna().any():raise ValueError("Trade pairs contain unexpected importer outside target")
    if not np.isfinite(x.value_thousand_usd).all() or (x.value_thousand_usd<0).any():
        raise ValueError("Bad trade value")
    x=x.loc[x.exporter_m49!=x.importer_m49].copy()
    if x.duplicated(["year","importer_m49","exporter_m49"]).any():raise ValueError("Duplicate trade network edge")
    den=x.groupby(["receiver","year"]).value_thousand_usd.sum().rename("all_observed_hs85_imports_kUSD")
    # Foreign capabilities observed only for original 47 countries, no imputation for rest of world.
    peer=panel.loc[:,["ISO3","Year","Internet","RnD"]].rename(
        columns={"ISO3":"source_iso","Year":"year",
                 "Internet":"foreign_Internet_percent","RnD":"foreign_RnD_percent_GDP"})
    x=x.merge(peer,on=["source_iso","year"],how="left",validate="many_to_one")
    x["eligible"]=(x.source_iso.notna()&
                   x.foreign_Internet_percent.notna()&x.foreign_RnD_percent_GDP.notna())
    m=x.loc[x.eligible].copy()
    num=m.groupby(["receiver","year"]).value_thousand_usd.sum().rename("known_peer_hs85_imports_kUSD")
    stats=pd.concat([den,num],axis=1).fillna({"known_peer_hs85_imports_kUSD":0})
    stats["coverage"]=np.where(stats.all_observed_hs85_imports_kUSD>0,
                               stats.known_peer_hs85_imports_kUSD/stats.all_observed_hs85_imports_kUSD,np.nan)
    if (stats.coverage>1.0000000001).any():raise ValueError("Coverage above 100%, duplicated trade")
    # Conditional mean renormalizes partner weights only when at least 80% of observed
    # world HS85 import value has a known source digital capability; no zeros for unavailable partners.
    m["weighted_internet"]=m.value_thousand_usd*m.foreign_Internet_percent
    m["weighted_rnd"]=m.value_thousand_usd*m.foreign_RnD_percent_GDP
    numer=m.groupby(["receiver","year"]).agg(
       sum_weighted_internet=("weighted_internet","sum"),
       sum_weighted_rnd=("weighted_rnd","sum"),
       eligible_peer_count=("source_iso","nunique"))
    stats=stats.join(numer)
    stats["foreign_Internet_tradeweighted_lag1"]=np.where(
       (stats.coverage>=min_coverage)&(stats.known_peer_hs85_imports_kUSD>0),
       stats.sum_weighted_internet/stats.known_peer_hs85_imports_kUSD,np.nan)
    stats["foreign_RnD_tradeweighted_lag1"]=np.where(
       (stats.coverage>=min_coverage)&(stats.known_peer_hs85_imports_kUSD>0),
       stats.sum_weighted_rnd/stats.known_peer_hs85_imports_kUSD,np.nan)
    stats=stats.reset_index().rename(columns={"year":"trade_year"})
    stats["Year"]=stats.trade_year+1   # lag weights + lag foreign indicators
    stats["ISO3"]=stats.receiver
    cols=["ISO3","Year","trade_year","coverage","eligible_peer_count",
          "all_observed_hs85_imports_kUSD","known_peer_hs85_imports_kUSD",
          "foreign_Internet_tradeweighted_lag1","foreign_RnD_tradeweighted_lag1"]
    return stats[cols]
def run_model(panel,expo,out):
    import statsmodels.formula.api as smf
    dat=panel.merge(expo,on=["ISO3","Year"],how="left",validate="one_to_one")
    dat=dat.sort_values(["ISO3","Year"])
    dat["ln_Productivity"]=np.log(dat.Productivity)
    rows=[]
    for dep in ["Growth","ln_Productivity"]:
        dat["lag_y"]=dat.groupby("ISO3")[dep].shift(1)
        d=dat.dropna(subset=[dep,"lag_y","Internet","Broadband","ICT_Exports",
              "Unemployment","Inflation","RnD","foreign_Internet_tradeweighted_lag1",
              "foreign_RnD_tradeweighted_lag1"]).copy()
        if d.ISO3.nunique()<MIN_COUNTRIES or d.Year.nunique()<MIN_YEARS or len(d)<MIN_OBS:
            rows.append({"outcome":dep,"status":"BLOCKED_INSUFFICIENT_COVERAGE",
                         "N":len(d),"countries":d.ISO3.nunique(),"years":d.Year.nunique()})
            continue
        formula=dep+" ~ lag_y + Internet + Broadband + ICT_Exports + Unemployment + Inflation + RnD + foreign_Internet_tradeweighted_lag1 + foreign_RnD_tradeweighted_lag1 + C(ISO3) + C(Year)"
        fit=smf.ols(formula,data=d).fit(cov_type="cluster",
              cov_kwds={"groups":d.ISO3,"use_correction":True})
        for v in ["foreign_Internet_tradeweighted_lag1","foreign_RnD_tradeweighted_lag1"]:
            rows.append({"outcome":dep,"status":"EXPLORATORY_FE_ONLY",
                         "term":v,"coef":float(fit.params[v]),"se":float(fit.bse[v]),
                         "p":float(fit.pvalues[v]),"N":int(fit.nobs),
                         "countries":d.ISO3.nunique(),"years":d.Year.nunique(),
                         "limitation":"Trade weights endogenous; lagged dependent FE biased; missing foreign RnD; cross-section common shocks; neither GMM nor IV"})
    pd.DataFrame(rows).to_csv(out/"exploratory_trade_exposure_FE_NOT_CAUSAL.csv",index=False)
    return rows
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--baci-dir",type=Path,default=ROOT/"data/raw/baci_hs02_202601")
    parser.add_argument("--out",type=Path,default=ROOT/"outputs/phase_b_full")
    args=parser.parse_args()
    out=args.out;out.mkdir(parents=True,exist_ok=True)
    manifest={"source_sha256_expected":SRC_SHA,"BACI_folder":str(args.baci_dir),
       "BACI_upstream":"CEPII BACI 202601 HS02 bilateral HS6 original CSV",
       "source_url":"https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37",
       "years_trade":list(YEARS),"years_outcome":[2006,2022],
       "HS2_filter":"85 (all electrical/electronic goods, not a pure high-tech category)",
       "unit":"thousand USD in BACI input","min_partner_share_coverage":MIN_COVERAGE,
       "min_obs_for_exploratory":MIN_OBS,"min_countries":MIN_COUNTRIES,"min_years":MIN_YEARS,
       "no_causal_claim":True,"status":"BLOCKED"}
    try:
        if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SRC_SHA:raise ValueError("Original source hash mismatch")
        panel=pd.read_excel(SOURCE)
        assert len(panel)==846 and panel.ISO3.nunique()==47
        cw=country_m49(set(panel.ISO3))
        files,release=source_files(args.baci_dir)
        trade,hashes=read_baci_hs85(files,set(cw.values()))
        expo=create_exposures(trade,panel,cw)
        expo.to_csv(out/"real_bilateral_trade_weighted_exposure.csv",index=False)
        result=run_model(panel,expo,out)
        manifest.update(BACI_release=release,sha256_by_file=hashes,
            trade_country_years=len(expo),coverage_eligible=int(expo.foreign_Internet_tradeweighted_lag1.notna().sum()),
            model_rows=result,status="PROXY_BUILT_NOT_CAUSAL")
    except Exception as e:
        manifest["block_reason"]=str(e)
        print("PHASE_B_FAIL_CLOSED",str(e),flush=True)
    finally:
        manifest["generated_at_utc"]=datetime.now(timezone.utc).isoformat()
        (out/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False,default=str),encoding="utf8")
    print("PHASE_B_FULL",json.dumps({"status":manifest["status"],"reason":manifest.get("block_reason"),"eligible":manifest.get("coverage_eligible")}))
    if manifest["status"]=="BLOCKED":raise SystemExit(2)
if __name__=="__main__":main()
