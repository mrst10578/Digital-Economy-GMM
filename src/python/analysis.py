"""Independent, reproducible data audit and transparent OLS/FE benchmarks.
This module does NOT estimate or label anything as GMM or Stata output.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import zscore
import statsmodels.formula.api as smf
from statsmodels.stats.outliers_influence import variance_inflation_factor
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
ORIG=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
OUT=ROOT/"outputs/python"
VARS=["Growth","Productivity","Internet","Broadband","ICT_Exports","Unemployment","Inflation","RnD"]
X=["Internet","Broadband","ICT_Exports","Unemployment","Inflation","RnD"]

def jsonify(obj):
    if isinstance(obj,dict): return {str(k):jsonify(v) for k,v in obj.items()}
    if isinstance(obj,(list,tuple)): return [jsonify(x) for x in obj]
    if isinstance(obj,(np.integer,)): return int(obj)
    if isinstance(obj,(np.floating,)): return float(obj) if np.isfinite(obj) else None
    return obj

def dump(name,data):
    (OUT/name).write_text(json.dumps(jsonify(data),ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")

def vif_frame(a):
    z=a.dropna().astype(float).to_numpy()
    if np.any(np.std(z,axis=0)==0): return {"status":"constant regressors"}
    return {name:round(float(variance_inflation_factor(z,i)),4)
            for i,name in enumerate(a.columns)}

def baseline(df,dependent,formula_label,trim=False):
    x=df.copy()
    if trim:
        x=x.loc[~((x.ISO3=="MAC") & (x.Year==2020))].copy()
    x["lag_y"]=x.groupby("ISO3")[dependent].shift(1)
    x=x.dropna(subset=["lag_y",dependent]+X)
    rhs="lag_y + "+" + ".join(X)
    results=[]
    for type_,fx in [("pooled", ""),("two_way_FE"," + C(ISO3) + C(Year)")]:
        model=smf.ols(dependent+" ~ "+rhs+fx,data=x).fit(
            cov_type="cluster", cov_kwds={"groups":x.ISO3})
        results.append(dict(model=formula_label,method=type_,exclude_MAC_2020=trim,
                            obs=int(model.nobs),countries=int(x.ISO3.nunique()),r2=float(model.rsquared),
                            coefficients={v:{"coef":float(model.params[v]),
                                             "se_cluster":float(model.bse[v]),
                                             "p":float(model.pvalues[v])}
                                          for v in ["lag_y"]+X}))
    return results

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    df=pd.read_excel(ORIG,engine="openpyxl").sort_values(["ISO3","Year"]).reset_index(drop=True)
    assert len(df)==846 and df.ISO3.nunique()==47
    assert not df.duplicated(["ISO3","Year"]).any()
    assert not df[VARS].isna().any().any()
    assert (df["Productivity"]>0).all()
    sha=hashlib.sha256(ORIG.read_bytes()).hexdigest()
    df["ln_Productivity"]=np.log(df["Productivity"])
    df["country_id"]=pd.factorize(df["ISO3"],sort=True)[0]+1
    df.to_csv(ROOT/"data/processed/panel_for_models.csv",index=False,float_format="%.13g")
    df.to_stata(ROOT/"data/processed/stata_ready.dta",version=118,write_index=False)
    reread=pd.read_stata(ROOT/"data/processed/stata_ready.dta")
    assert (df.ISO3.astype(str).to_numpy()==reread.ISO3.astype(str).to_numpy()).all()
    assert (df.Year.to_numpy()==reread.Year.to_numpy()).all()
    for v in VARS+["ln_Productivity"]:
        assert np.allclose(df[v],reread[v],rtol=1e-10,atol=1e-8)
    audit={
        "raw_sha256":sha,"rows":len(df),"countries":df.ISO3.nunique(),"years":sorted(df.Year.unique().tolist()),
        "unique_keys":True,"balanced":df.groupby("ISO3").Year.nunique().eq(18).all().item(),
        "raw_missing":df[VARS].isna().sum().to_dict(),
        "negative_or_zero":(df[VARS]<=0).sum().to_dict(),
        "descriptive":df[VARS+["ln_Productivity"]].describe().round(6).to_dict(),
        "pairwise_correlations":df[X+["Growth","ln_Productivity"]].corr().round(6).to_dict(),
        "dta_roundtrip_verified":True,
        "provenance":"workbook values; WDI per-country per-year verification not independently completed",
        "interpretation_warning":"Neither source dictionary nor balanced panel implies authentic WDI values or causal spillovers."
    }
    dump("data_audit.json",audit)
    df[VARS+["ln_Productivity"]].describe().T.to_csv(OUT/"descriptives.csv")
    df[X+["Growth","ln_Productivity"]].corr().to_csv(OUT/"correlations.csv")
    pooled=df[X].copy(); pooled=pooled-pooled.mean()
    by_country=df.groupby("ISO3")[X].transform("mean")
    by_year=df.groupby("Year")[X].transform("mean")
    twoway=df[X]-by_country-by_year+df[X].mean()
    dump("vif.json",{
        "pooled_centered":vif_frame(pooled),
        "within_two_way_demeaned":vif_frame(twoway),
        "note":"Two-way demeaning equals residualization against country and year indicators for balanced data; this is NOT a panel unit-root test."
    })
    results=[]
    for y in ["Growth","ln_Productivity"]:
        results+=baseline(df,y,y,False)
        results+=baseline(df,y,y,True)
    dump("ols_fe_benchmarks.json",results)
    trends=df.groupby("Year")[["Growth","ln_Productivity","Internet","Broadband"]].mean()
    trends.to_csv(OUT/"annual_means.csv")
    for series in trends:
        plt.figure(figsize=(8,4))
        trends[series].plot(marker="o")
        plt.xlabel("Year");plt.ylabel(series);plt.title("Across-country mean: "+series)
        plt.grid(alpha=0.2);plt.tight_layout()
        plt.savefig(OUT/("trend_"+series+".png"),dpi=160);plt.close()
    summary={"data_audit":audit["raw_sha256"],"corr_Internet_Broadband":float(df.Internet.corr(df.Broadband)),
             "vif":json.loads((OUT/"vif.json").read_text()),
             "baseline_models":results}
    dump("SUMMARY.json",summary)
    print("PYTHON_REAL_ANALYSIS_COMPLETE",json.dumps(jsonify({
        "raw_sha256":sha,"n":len(df),"n_countries":df.ISO3.nunique(),"corr_I_B":summary["corr_Internet_Broadband"],
        "vif":summary["vif"],"benchmarks":results
    }),ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
