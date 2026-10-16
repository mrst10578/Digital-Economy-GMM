"""Independent Fisher aggregation of fixed-lag country ADF p-values.
Predefined intercept/trend, level/difference specifications; not a CIPS test.
Expected deviations from Stata: finite-sample/p-value MacKinnon conventions possible.
"""
from __future__ import annotations
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd
from scipy.stats import chi2
from statsmodels.tsa.stattools import adfuller
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
OUT=ROOT/"outputs/python_adf"
VARIABLES=["Growth","ln_Productivity","Internet","Broadband","ICT_Exports",
           "Unemployment","Inflation","RnD"]
def run():
    OUT.mkdir(parents=True,exist_ok=True)
    df=pd.read_excel(SOURCE).sort_values(["ISO3","Year"]).copy()
    assert len(df)==846 and df.ISO3.nunique()==47 and not df.duplicated(["ISO3","Year"]).any()
    df["ln_Productivity"]=np.log(df["Productivity"])
    assert np.isfinite(df[VARIABLES]).all().all()
    results=[];countries=[]
    for var in VARIABLES:
        for trans in ["level","first_difference"]:
            for reg in ["c","ct"]:
                pvals=[]
                for iso,block in df.groupby("ISO3"):
                    sample=block[var].to_numpy(dtype=float)
                    if trans=="first_difference": sample=np.diff(sample)
                    try:
                        stat,pval,*_=adfuller(sample,maxlag=1,autolag=None,regression=reg)
                        pvals.append(float(pval))
                        countries.append(dict(variable=var,transform=trans,deterministics=reg,country=iso,
                                              adf_statistic=float(stat),adf_p_value=float(pval),status="OK"))
                    except Exception as exc:
                        countries.append(dict(variable=var,transform=trans,deterministics=reg,country=iso,
                                              adf_statistic=np.nan,adf_p_value=np.nan,status="FAILED:"+str(exc)))
                fisher=-2*float(np.log(pvals).sum()) if pvals else np.nan
                p_comb=float(chi2.sf(fisher,df=2*len(pvals))) if pvals else np.nan
                results.append(dict(variable=var,transform=trans,deterministics=reg,
                                    fixed_country_ADF_lags=1,
                                    N_countries_tested=len(pvals),Fisher_chi2=fisher,
                                    chi2_df=2*len(pvals),Fisher_p=p_comb,
                                    assumptions="country-independence; NOT appropriate as sole inference with Pesaran CD"))
                print("INDEPENDENT_ADF_FISHER",var,trans,reg,"countries",len(pvals),"chi2",fisher,"p",p_comb,flush=True)
    pd.DataFrame(results).to_csv(OUT/"fisher_sensitivity.csv",index=False)
    pd.DataFrame(countries).to_csv(OUT/"country_adf.csv",index=False)
    ref=next(x for x in results if x["variable"]=="ln_Productivity"
             and x["transform"]=="level" and x["deterministics"]=="c")
    assert ref["N_countries_tested"]==47
    # Data-defined FISHER result checked against Stata's actual p≈0.483515; this is an assertion of
    # cross-software reproducibility, NOT a claim of stationarity.
    assert abs(ref["Fisher_p"]-0.483515)<0.0004,ref["Fisher_p"]
    (OUT/"manifest.json").write_text(json.dumps({
      "source_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
      "specification":"statsmodels country ADF regression c or ct, fixed maxlag=1, autolag=None; Fisher chi2 aggregation",
      "independence_warning":"strong country CD violates usual asymptotic Fisher assumptions",
      "independent_crosscheck_of_Stata_Fisher_ln_Productivity_intercept":ref["Fisher_p"]
    },indent=2,ensure_ascii=False),encoding="utf8")
    print("ADF_REPLICATION_PASSED; specifications reported transparently")
if __name__=="__main__":run()
