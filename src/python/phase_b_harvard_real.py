"""HARVARD HS92 verified original bilateral partner GOODS imports x original WDI 47-country panel.
Country clustered TWO-WAY FE benchmarks only. NO causal GMM/IV or verified tech flows.
Fixed >=80% full-world import coverage, >=400 obs, >=30 countries, >=12 years.
Never replace missing trade with invented zeros or change gates for desired p-values.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT=Path(__file__).resolve().parents[2]
XLSX=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
TRADE=ROOT/"outputs/harvard_verified/hs92_country_country_year.csv"
OUT=ROOT/"outputs/harvard_spillover"
XLSX_SHA="474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b"
TRADE_SHA="9f3e6ed88e3cf751cd8e7ab3b939c9fb216bec0944ed4add0cb8473a8013fda2"
TRADE_MD5="9c39659168dd5212f745572ba35b2a5c"
WCOL="peer_Internet_allgoods_lag1"
RCOL="peer_RnD_allgoods_lag1"
X=["Internet","Broadband","ICT_Exports","Unemployment","Inflation","RnD"]

def hashfile(path,algorithm="sha256"):
    h=hashlib.new(algorithm)
    with path.open("rb") as fd:
        for buf in iter(lambda:fd.read(1048576),b""):h.update(buf)
    return h.hexdigest()

def trade_quality(t):
    assert len(t)==879014 and t.year.min()==1995 and t.year.max()==2024
    assert list(t.columns)==["country_id","country_iso3_code","partner_country_id",
           "partner_iso3_code","year","export_value","import_value"]
    assert not t.duplicated(["country_iso3_code","partner_iso3_code","year"]).any()
    assert t.notna().all().all()
    assert (t.country_iso3_code!=t.partner_iso3_code).all()
    neg=t.loc[(t.import_value<0)|(t.export_value<0)]
    neg.to_csv(OUT/"source_negative_trade_rows.csv",index=False)
    mirror=t[["country_iso3_code","partner_iso3_code","year","import_value","export_value"]].rename(columns={
       "country_iso3_code":"partner_iso3_code","partner_iso3_code":"country_iso3_code",
       "import_value":"reverse_import","export_value":"reverse_export"})
    z=t.merge(mirror,on=["country_iso3_code","partner_iso3_code","year"],how="left",validate="one_to_one",indicator=True)
    assert z._merge.eq("both").all()
    assert z.import_value.eq(z.reverse_export).all()
    assert z.export_value.eq(z.reverse_import).all()
    quality=dict(original_rows=len(t),years=[int(t.year.min()),int(t.year.max())],
       country_codes=int(t.country_iso3_code.nunique()),
       partner_codes=int(t.partner_iso3_code.nunique()),
       original_negative_rows=int(len(neg)),pairs_mirrored_without_disagreement=True,
       negative_rows_policy="Source negative values documented; none in selected original 47 recipient sample",
       source_sha256=TRADE_SHA,source_md5=TRADE_MD5)
    (OUT/"source_quality.json").write_text(json.dumps(quality,indent=2,ensure_ascii=False))
    return quality

def exposure(panel,t):
    sample=set(panel.ISO3)
    q=t.loc[t.year.between(2005,2021)&t.country_iso3_code.isin(sample)&
            (t.country_iso3_code!=t.partner_iso3_code)].copy()
    assert len(q)==153522 and q.country_iso3_code.nunique()==47
    assert (q.import_value>=0).all(),"Negative import in original 47 recipient sample"
    pairs=["country_iso3_code","year"]
    total=q.groupby(pairs).import_value.sum().rename("all_observed_import_USD")
    assert (total>0).all()
    peer=panel[["ISO3","Year","Internet","RnD"]].rename(columns={
       "ISO3":"partner_iso3_code","Year":"year",
       "Internet":"foreign_Internet_pct","RnD":"foreign_RnD_pctGDP"})
    q=q.merge(peer,on=["partner_iso3_code","year"],how="left",validate="many_to_one")
    k=q.loc[q.partner_iso3_code.isin(sample)&q.foreign_Internet_pct.notna()&q.foreign_RnD_pctGDP.notna()].copy()
    k["weighted_internet"]=k.import_value*k.foreign_Internet_pct
    k["weighted_rnd"]=k.import_value*k.foreign_RnD_pctGDP
    a=k.groupby(pairs).agg(known_peer_import_USD=("import_value","sum"),
            wi=("weighted_internet","sum"),wr=("weighted_rnd","sum"),
            eligible_peer_count=("partner_iso3_code","nunique"))
    v=a.join(total,how="outer")
    v["known_peer_import_USD"]=v.known_peer_import_USD.fillna(0)
    v["coverage"]=v.known_peer_import_USD/v.all_observed_import_USD
    assert v.coverage.between(0,1+1e-9).all()
    v["pass_80pct"]=v.coverage.ge(.80)
    v[WCOL]=np.where(v.pass_80pct,v.wi/v.known_peer_import_USD,np.nan)
    v[RCOL]=np.where(v.pass_80pct,v.wr/v.known_peer_import_USD,np.nan)
    v=v.reset_index().rename(columns={"country_iso3_code":"ISO3","year":"trade_year"})
    v["Year"]=v.trade_year+1
    assert len(v)==799 and int(v.pass_80pct.sum())==481
    assert v.loc[v.pass_80pct,"ISO3"].nunique()==35
    v.to_csv(OUT/"real_harvard_country_year_trade_exposures.csv",index=False)
    v.groupby("ISO3").agg(eligible_years=("pass_80pct","sum"),
         observed_years=("coverage","size"),mean_coverage=("coverage","mean"),
         min_coverage=("coverage","min"),max_coverage=("coverage","max")).to_csv(OUT/"coverage_by_country.csv")
    v.groupby("trade_year").agg(eligible_receivers=("pass_80pct","sum"),
         total_receivers=("coverage","size"),median_coverage=("coverage","median")).to_csv(OUT/"coverage_by_trade_year.csv")
    excluded=sorted(sample-set(v.loc[v.pass_80pct,"ISO3"]))
    stat=dict(trade_rows_for_47=int(len(q)),trade_country_years=int(len(v)),
       eligible_country_years=int(v.pass_80pct.sum()),
       excluded_country_years=int((~v.pass_80pct).sum()),
       eligible_countries=int(v.loc[v.pass_80pct,"ISO3"].nunique()),
       eligible_years=int(v.loc[v.pass_80pct,"trade_year"].nunique()),
       coverage_median=float(v.coverage.median()),
       excluded_countries_entirely=excluded,
       warnings="Not random country inclusion; excludes China/Japan/etc; 80% ORIGINAL prespecified for trade weights, cannot generalize to all 47")
    (OUT/"country_year_coverage.json").write_text(json.dumps(stat,indent=2,ensure_ascii=False))
    return v,stat

def regress(df,dep,dynamic,scenario,exclude=""):
    d=df if not exclude else df.loc[df.ISO3!=exclude]
    d=d.dropna(subset=[dep,"lag_y",WCOL,RCOL]+X)
    assert len(d)>=400 and d.ISO3.nunique()>=30 and d.Year.nunique()>=12,"Coverage gate failed; no estimation"
    rhs=(["lag_y"] if dynamic else [])+X+[WCOL,RCOL]
    fm=dep+" ~ "+" + ".join(rhs)+" + C(ISO3) + C(Year)"
    fit=smf.ols(fm,data=d).fit(cov_type="cluster",
         cov_kwds={"groups":d.ISO3,"use_correction":True})
    results=[]
    for term in [WCOL,RCOL,"Internet","RnD"]:
        b=float(fit.params[term]);se=float(fit.bse[term]);p=float(fit.pvalues[term])
        assert np.isfinite([b,se,p]).all()
        results.append(dict(outcome=dep,model="dynamic_FE" if dynamic else "static_FE",
          scenario=scenario,excluded_country=exclude,term=term,
          coefficient=b,cluster_country_se=se,cluster_country_p=p,
          ci95_lower=b-1.96*se,ci95_upper=b+1.96*se,
          nobs=int(fit.nobs),n_countries=d.ISO3.nunique(),n_years=d.Year.nunique(),
          condition_number=float(fit.condition_number)))
    return results

def models(panel,trade_index):
    dat=panel.sort_values(["ISO3","Year"]).copy()
    dat["ln_Productivity"]=np.log(dat.Productivity)
    dat=dat.merge(trade_index[["ISO3","Year",WCOL,RCOL]],on=["ISO3","Year"],
                  how="left",validate="one_to_one")
    assert dat[WCOL].notna().sum()==481
    out=[]
    for dep in ["Growth","ln_Productivity"]:
        base=dat.copy()
        base["lag_y"]=base.groupby("ISO3")[dep].shift(1)
        for dyn in [False,True]:
            out+=regress(base,dep,dyn,"primary_80pct_2006_2022")
            out+=regress(base.loc[base.Year!=2020],dep,dyn,"predeclared_drop_2020")
            for c in sorted(base.loc[base[WCOL].notna(),"ISO3"].unique()):
                out+=regress(base,dep,dyn,"leave_one_country_out",c)
    d=pd.DataFrame(out)
    assert len(d)==4*4*(2+35)==592
    d.to_csv(OUT/"full_model_coefficients_AND_leave_one_out.csv",index=False)
    main=d.loc[d.scenario=="primary_80pct_2006_2022"]
    assert len(main)==16
    main.to_csv(OUT/"MAIN_four_real_FE_models_NONCAUSAL.csv",index=False)
    loo=[]
    for (dep,method,term),group in d.loc[d.scenario=="leave_one_country_out"].groupby(["outcome","model","term"]):
        b=main.loc[(main.outcome==dep)&(main.model==method)&(main.term==term)].iloc[0]
        loo.append(dict(outcome=dep,model=method,term=term,base_coef=b.coefficient,
          base_cluster_p=b.cluster_country_p,n_leave_out=len(group),
          min_coefficient=group.coefficient.min(),max_coefficient=group.coefficient.max(),
          n_sign_flips=int((np.sign(group.coefficient)!=np.sign(b.coefficient)).sum())))
    pd.DataFrame(loo).to_csv(OUT/"leave_one_country_out_summary.csv",index=False)
    print("HARVARD_PHASEB_REAL_MAIN",main[["outcome","model","term","coefficient","cluster_country_p","nobs","n_countries"]].to_json(orient="records"),flush=True)
    return len(d)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=dict(source="Harvard Growth Lab Atlas HS92 country-country-year international all-goods trade",
        doi="10.7910/DVN/T4CHWJ",harvard_file_id=13685107,
        sha256=TRADE_SHA,md5=TRADE_MD5,original_wdi_sha256=XLSX_SHA,
        requested_coverage=.80,models="Static/Dynamic two-way FE, country-clustered",
        estimator_scope="DESCRIPTIVE ONLY, not causal GMM / IV",
        warning="All-goods imports are not observed technology transfer; trade endogeneity, common shocks, Nickell bias, nonrandom coverage",
        generated_utc=datetime.now(timezone.utc).isoformat(),status="BLOCKED")
    try:
        assert hashfile(XLSX)==XLSX_SHA,"Original WDI spreadsheet changed"
        assert TRADE.stat().st_size==30767251,"Wrong Harvard source file size"
        assert hashfile(TRADE)==TRADE_SHA and hashfile(TRADE,"md5")==TRADE_MD5,"Wrong Harvard source hash"
        p=pd.read_excel(XLSX)
        assert len(p)==846 and p.ISO3.nunique()==47
        t=pd.read_csv(TRADE)
        source_stats=trade_quality(t)
        z,coverage=exposure(p,t)
        manifest.update(source_audit=source_stats,coverage_audit=coverage)
        assert coverage["eligible_country_years"]>=400 and coverage["eligible_countries"]>=30 and coverage["eligible_years"]>=12
        model_rows=models(p,z)
        manifest.update(status="EXECUTED_REAL_HARVARD_DESCRIPTIVE_NONCAUSAL",
          number_model_specs=4,reported_coefficient_rows=model_rows,scientifically_accepted_gmm_models=0)
    except Exception as e:
        manifest["blocked_reason"]=str(e)
        print("HARVARD_REAL_ANALYSIS_FAILED",str(e),flush=True)
        raise
    finally:
        (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False,default=str),encoding="utf8")
    print("HARVARD_REAL_PHASEB_COMPLETE",json.dumps({"status":manifest["status"],"coverage":manifest["coverage_audit"],"coefficient_rows":model_rows},ensure_ascii=False),flush=True)

if __name__=="__main__": main()
