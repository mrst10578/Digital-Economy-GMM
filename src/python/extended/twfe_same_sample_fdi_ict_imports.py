#!/usr/bin/env python3
"""Phase B prespecified descriptive TWFE A/B comparison on exactly same 840 keys.

This DOES NOT replicate professor's dynamic System GMM. FDI and ICT imports are
potentially endogenous; statistical significance DOES NOT confer causality.
Use raw historical source read-only. The sample is determined only by joint
WDI availability, before fitting, and is frozen for all four specifications.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS
from openpyxl import load_workbook

from pilot_wdi_coverage import LOCK, OUT, ROOT, SOURCE

FDI="BX.KLT.DINV.WD.GD.ZS"
ICT="TM.VAL.ICTG.ZS.UN"
DIGITAL=("Internet","Broadband","ICT_Exports")
CONTROLS=("Unemployment","Inflation","RnD")
BASE=(*DIGITAL,*CONTROLS)
EXTRA={"FDI_inflow_percent_GDP":FDI,"ICT_imports_percent_goods":ICT}
TERMS=("Growth","ln_Productivity")
EST=OUT/"twfe_comparison"
LOG_SRC=OUT/"wdi_pilot_original_country_years.csv"

def load_historical():
    wb=load_workbook(SOURCE,read_only=True,data_only=True)
    r=wb.active.iter_rows(values_only=True)
    headers=list(next(r))
    need=["ISO3","Year","Growth","Productivity",*BASE]
    assert all(k in headers for k in need)
    rows=[dict(zip(headers,values)) for values in r if values and any(v is not None for v in values)]
    assert len(rows)==846
    frame=pd.DataFrame(rows)
    frame["ln_Productivity"]=np.log(pd.to_numeric(frame["Productivity"]))
    assert np.isfinite(frame["ln_Productivity"]).all()
    return frame

def load_wdi():
    with LOG_SRC.open(encoding="utf-8",newline="") as fp:
        rows=list(csv.DictReader(fp))
    assert len(rows)==846
    df=pd.DataFrame(rows)
    df["Year"]=df["Year"].astype(int)
    for friendly,src in EXTRA.items():
        df[friendly]=pd.to_numeric(df[src],errors="coerce")
        # Count nonmissing via source, never silently coerce malformed nonempty strings.
        assert int(df[friendly].notna().sum())==(846 if src==FDI else 840)
    return df[["ISO3","Year",*EXTRA]]

def save_csv(filename,records):
    assert records
    with (EST/filename).open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)

def model(df,y,predictors,tag):
    model=PanelOLS(df[y],df[list(predictors)],entity_effects=True,time_effects=True,
                   drop_absorbed=False,check_rank=True)
    # Driscoll-Kraay cross-sectional/time robust approximation; T=18 is limited.
    fit=model.fit(cov_type="kernel",kernel="bartlett",bandwidth=2)
    allparams=fit.params
    assert set(allparams)==set(predictors)
    assert fit.nobs==840
    assert fit.resids.notna().all()
    return fit

def main():
    lock=json.loads(LOCK.read_text(encoding="utf-8"))
    original_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert original_hash==lock["original_data_sha256"]
    EST.mkdir(parents=True,exist_ok=True)
    original=load_historical()
    external=load_wdi()
    assert original[["ISO3","Year"]].duplicated().sum()==0
    assert external[["ISO3","Year"]].duplicated().sum()==0
    assert set(map(tuple,original[["ISO3","Year"]].itertuples(index=False,name=None)))==set(map(tuple,external[["ISO3","Year"]].itertuples(index=False,name=None)))
    m=original.merge(external,on=["ISO3","Year"],validate="one_to_one",indicator=True)
    assert m["_merge"].eq("both").all()
    predictors_extended=(*BASE,*EXTRA)
    assert m[list(BASE)+list(TERMS)].notna().all().all()
    matched=m.dropna(subset=list(EXTRA)).copy()
    assert len(matched)==840
    assert matched["ISO3"].nunique()==47 and matched["Year"].nunique()==18
    assert matched[["ISO3","Year"]].duplicated().sum()==0
    assert matched[list(predictors_extended)+list(TERMS)].notna().all().all()
    # Single predeclared matched dataset used for all 4 regressions.
    matched=matched.set_index(["ISO3","Year"]).sort_index()
    rows=[]
    comparisons=[]
    fits={}
    for target in TERMS:
        for label,predictors in (("baseline_matched_840",BASE),("expanded_matched_840",predictors_extended)):
            fit=model(matched,target,predictors,label)
            fits[(target,label)]=fit
            assert fit.nobs==840
            print(f"TWFE_PASS outcome={target} model={label} n={fit.nobs} countries=47 within_R2={fit.rsquared_within:.7f}",flush=True)
            for variable in predictors:
                conf=fit.conf_int().loc[variable]
                rows.append({
                    "dependent":target,
                    "specification":label,
                    "coefficient_name":variable,
                    "coefficient":float(fit.params[variable]),
                    "robust_std_error":float(fit.std_errors[variable]),
                    "p_value":float(fit.pvalues[variable]),
                    "CI95_lower":float(conf["lower"]),
                    "CI95_upper":float(conf["upper"]),
                    "n_obs":fit.nobs,
                    "n_countries":47,"year_range":"2005-2022",
                    "entity_and_year_FE":True,
                    "covariance":"Driscoll-Kraay Bartlett bandwidth 2",
                    "causal_inference":False,
                })
            with (EST/f"{target}_{label}.txt").open("w",encoding="utf-8") as f:
                f.write(str(fit.summary)+"\n")
        baseline=fits[(target,"baseline_matched_840")]
        extended=fits[(target,"expanded_matched_840")]
        for term in DIGITAL:
            comparisons.append({
                "dependent":target,"term":term,
                "baseline_beta":float(baseline.params[term]),
                "baseline_p":float(baseline.pvalues[term]),
                "expanded_beta":float(extended.params[term]),
                "expanded_p":float(extended.pvalues[term]),
                "beta_change":float(extended.params[term]-baseline.params[term]),
                "same_matched_country_year_keys":True,
                "same_840_observations":True,
                "model_type":"static two-way fixed effects, NOT professor dynamic GMM",
                "causal":False,
            })
    save_csv("twfe_all_coefficients.csv",rows)
    save_csv("twfe_digital_coefficient_comparison.csv",comparisons)
    sample_records=[]
    for iso,year in matched.index:
        sample_records.append({"ISO3":iso,"Year":int(year)})
    save_csv("frozen_matched_sample_keys_840.csv",sample_records)
    report={
        "phase":"EXTENDED_DATA_EXPERIMENTAL",
        "status":"TWFE_DESCRIPTIVE_FOUR_MODELS_COMPLETED",
        "original_file_hash":original_hash,
        "original_file_modified":False,
        "new_data_used_in_professor_phase":False,
        "same_sample_all_four_models":True,
        "n_observations_each":840,
        "countries":47,
        "years":18,
        "outcomes":list(TERMS),
        "model_type":"static two-way fixed-effects exploratory comparison",
        "baseline_terms":list(BASE),
        "extended_additions":EXTRA,
        "new_covariates_chosen_prior_to_significance_by_mechanism_and_coverage":True,
        "standard_errors":"Driscoll-Kraay (Bartlett bandwidth=2; T=18 caveat)",
        "not_professor_System_GMM":True,
        "no_lagged_dependent_variable":True,
        "no_claim_of_exogeneity_or_causality":True,
        "joint_digitals":comparisons,
        "warnings":[
            "Adding potentially endogenous FDI and ICT import share does not identify technology spillovers.",
            "Static two-way FE with DK errors is NOT the original dynamic System GMM requested by the professor.",
            "All four models use exactly the same original 47-country and 840 country-year keys.",
            "With 18 years, large-T asymptotics for Driscoll-Kraay standard errors are limited.",
            "Significant or insignificant coefficients should not drive later specification or sample choices.",
        ]
    }
    (EST/"methods_and_results.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("TWFE_COMPLETE: 4 descriptive models on identical 840 keys; no GMM, no causal claims, no changes to Phase A",flush=True)

if __name__=="__main__":
    main()
