"""Predeclared sensitivity checks on EXACT original 47-country workbook.
NOT a new causal estimator; never select significant specifications ex post.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
OUT=ROOT/"outputs/phase_a"
SOURCE_SHA="474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b"
X=["Internet","Broadband","ICT_Exports","Unemployment","Inflation","RnD"]
OUTCOMES=["Growth","ln_Productivity"]
# Ex ante windows: no post-2020 outcome truncation chosen by sign/p-value.
WINDOWS={
    "all_2005_2022":lambda x:np.ones(len(x),dtype=bool),
    "pre_2020_2005_2019":lambda x:x.Year<=2019,
    "post_2010_2011_2022":lambda x:x.Year>=2011,
    "drop_2020_only":lambda x:x.Year!=2020,
    "drop_MAC_2020":lambda x:~((x.ISO3=="MAC")&(x.Year==2020)),
}
def fit(df,dep,dynamic,label,drop_country=None):
    sub=df if drop_country is None else df.loc[df.ISO3!=drop_country]
    sub=sub.dropna(subset=([f"lag_{dep}"] if dynamic else []) + X+[dep])
    if len(sub)<100 or sub.ISO3.nunique()<30 or sub.Year.nunique()<8:
        raise ValueError("Insufficient panel coverage for prespecified sensitivity")
    rhs=([f"lag_{dep}"] if dynamic else [])+X
    formula=dep+" ~ "+" + ".join(rhs)+" + C(ISO3) + C(Year)"
    model=smf.ols(formula,data=sub).fit(cov_type="cluster",
                                       cov_kwds={"groups":sub.ISO3,"use_correction":True})
    return dict(label=label,outcome=dep,dynamic_FE=dynamic,removed_country=drop_country or "",
                countries=int(sub.ISO3.nunique()),years=int(sub.Year.nunique()),N=int(model.nobs),
                internet_beta=float(model.params["Internet"]),
                internet_SE_cluster_country=float(model.bse["Internet"]),
                internet_p_cluster_country=float(model.pvalues["Internet"]),
                broadband_beta=float(model.params["Broadband"]),
                broadband_p_cluster_country=float(model.pvalues["Broadband"]),
                lag_y_beta=float(model.params[f"lag_{dep}"]) if dynamic else np.nan,
                model_note="Two-way FE cluster(country); dynamic FE has Nickell bias at T=18; descriptive NOT identification")
def main():
    assert hashlib.sha256(RAW.read_bytes()).hexdigest()==SOURCE_SHA,"Original source changed: BLOCK"
    OUT.mkdir(parents=True,exist_ok=True)
    df=pd.read_excel(RAW).sort_values(["ISO3","Year"]).copy()
    assert len(df)==846 and df.ISO3.nunique()==47
    assert df.Year.min()==2005 and df.Year.max()==2022
    assert not df.duplicated(["ISO3","Year"]).any()
    assert (df.Productivity>0).all()
    df["ln_Productivity"]=np.log(df.Productivity)
    for y in OUTCOMES:df["lag_"+y]=df.groupby("ISO3")[y].shift(1)
    results=[]
    for y in OUTCOMES:
        for dyn in [False,True]:
            for name,rule in WINDOWS.items():
                results.append(fit(df.loc[rule(df)],y,dyn,name))
            for country in sorted(df.ISO3.unique()):
                results.append(fit(df,y,dyn,"leave_one_country_out",country))
    table=pd.DataFrame(results)
    table.to_csv(OUT/"all_prespecified_sensitivity_models.csv",index=False)
    overview=[]
    for (y,dyn),ss in table.groupby(["outcome","dynamic_FE"],sort=True):
        base=ss.loc[ss.label=="all_2005_2022"].iloc[0]
        loo=ss.loc[ss.label=="leave_one_country_out"]
        overview.append(dict(outcome=y,dynamic_FE=dyn,
          full_beta=float(base.internet_beta),full_p=float(base.internet_p_cluster_country),
          loo_runs=len(loo),loo_beta_min=float(loo.internet_beta.min()),
          loo_beta_max=float(loo.internet_beta.max()),
          loo_sign_reversals=int((np.sign(loo.internet_beta)!=np.sign(base.internet_beta)).sum()),
          loo_p_lt_005=int((loo.internet_p_cluster_country<.05).sum()),
          note="Sensitivity counts do NOT validate or invalidate GMM; no multiplicity-adjusted significance claims"))
    pd.DataFrame(overview).to_csv(OUT/"leave_one_country_out_summary.csv",index=False)
    issues={
      "source_sha256":SOURCE_SHA,"planned_models":4*(len(WINDOWS)+47),
      "executed_models":len(table),"non_causal":True,
      "eligibility":"Original file untouched; macro outcomes no partner-flow variables; no external technological spillover estimand identified",
      "pre_registered_exclusions":list(WINDOWS),
      "interpretation":"Country-clustered two-way FE, dynamic versions biased in short T. Shock windows and LOO are not identification.",
      "panels":{"countries":47,"start":2005,"end":2022,"observations":846}
    }
    assert len(table)==issues["planned_models"]
    (OUT/"manifest.json").write_text(json.dumps(issues,indent=2,ensure_ascii=False),encoding="utf8")
    print("PHASE_A_COMPLETED",json.dumps(issues))
    print("PHASE_A_SENSITIVITY",pd.DataFrame(overview).to_json(orient="records"))
if __name__=="__main__":main()
