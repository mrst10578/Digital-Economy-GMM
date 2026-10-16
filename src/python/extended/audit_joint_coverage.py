#!/usr/bin/env python3
"""Phase B only. Real joint 47×18 WDI missingness, before any estimation.

Run AFTER pilot_wdi_coverage.py downloads API snapshots. Never mutate
the professor workbook, the phase A branch or the original Stata model.
Joint coverage counts are not GMM estimation sample sizes.
"""
from __future__ import annotations
import csv
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from pilot_wdi_coverage import INDICATORS, LOCK, OUT

N_COUNTRIES = 47
YEARS = tuple(range(2005, 2023))
CODE_ORDER = (
    "BX.KLT.DINV.WD.GD.ZS",
    "TM.VAL.ICTG.ZS.UN",
    "IP.PAT.NRES",
    "IP.PAT.RESD",
    "TX.VAL.TECH.MF.ZS",
)
assert set(CODE_ORDER) == set(INDICATORS)
EXPECTED_KEYS = N_COUNTRIES * len(YEARS)

def read_csv(filename):
    with (OUT / filename).open(encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f))

def write_csv(name, rows, fields):
    with (OUT/name).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def main():
    import hashlib,json
    from pilot_wdi_coverage import ROOT,SOURCE
    from openpyxl import load_workbook
    locked=json.loads(LOCK.read_text(encoding="utf-8"))
    sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert sha == locked["original_data_sha256"]
    wb=load_workbook(SOURCE,read_only=True,data_only=True)
    raw_rows=wb.active.iter_rows(values_only=True)
    header=list(next(raw_rows))
    expected_original=["Growth","Productivity","Internet","Broadband","ICT_Exports","Unemployment","Inflation","RnD"]
    assert all(k in header for k in ["ISO3","Year",*expected_original])
    ik=header.index("ISO3");iy=header.index("Year")
    orig={}
    for row in raw_rows:
        if not row or all(v is None for v in row):
            continue
        iso,year=str(row[ik]),int(row[iy])
        assert (iso,year) not in orig
        orig[(iso,year)] = {k:row[header.index(k)] for k in expected_original}
    assert len(orig)==EXPECTED_KEYS
    rows=read_csv("wdi_pilot_original_country_years.csv")
    assert len(rows)==EXPECTED_KEYS
    isos=sorted(locked["iso3_to_original_country_name"])
    assert len(isos)==N_COUNTRIES
    keys={(iso,y) for iso in isos for y in YEARS}
    assert set(orig)==keys
    bykey={}
    for row in rows:
        k=(row["ISO3"],int(row["Year"]))
        assert k in keys and k not in bykey
        # Empty string is missing, but zero and negative are legitimate observations.
        bykey[k]={code:(None if row[code].strip()=="" else float(row[code])) for code in CODE_ORDER}
    assert set(bykey)==keys
    assert all(all(v is not None for v in r.values()) for r in orig.values()), "Original data incomplete"
    present={code:{k for k in keys if bykey[k][code] is not None} for code in CODE_ORDER}
    assert {code:len(v) for code,v in present.items()} == {
        "BX.KLT.DINV.WD.GD.ZS":846,"TM.VAL.ICTG.ZS.UN":840,
        "IP.PAT.NRES":793,"IP.PAT.RESD":789,"TX.VAL.TECH.MF.ZS":737,
    }, "Unexpected WDI revision since 2026-10-16 pilot; inspect before proceeding"
    models=[]
    for n in range(1,len(CODE_ORDER)+1):
        for seq in combinations(CODE_ORDER,n):
            complete=keys.intersection(*(present[x] for x in seq))
            by_year={y:sum((iso,y) in complete for iso in isos) for y in YEARS}
            by_iso={iso:sum((iso,y) in complete for y in YEARS) for iso in isos}
            # Conservative t,t-1,t-2,t-3 simultaneous complete-case marker.
            # Does NOT equal xtabond2's model-specific instruments/e(sample).
            lag_complete={(iso,y) for iso in isos for y in YEARS if y>=2008 and
                          all((iso,y-k) in complete for k in range(4))}
            item={
                "n_indicators":n,
                "indicators":"+".join(seq),
                "complete_rows":len(complete),
                "complete_pct":round(100*len(complete)/EXPECTED_KEYS,3),
                "missing_rows":EXPECTED_KEYS-len(complete),
                "full_18yr_countries":sum(v==18 for v in by_iso.values()),
                "countries_at_least_12yr":sum(v>=12 for v in by_iso.values()),
                "country_count_any_year":sum(v>0 for v in by_iso.values()),
                "complete_rows_2005":by_year[2005],
                "complete_rows_2022":by_year[2022],
                "lag2_and_lag3_joint_rows_2008_2022":len(lag_complete),
                "lag_screen_not_stata_e_sample":"TRUE",
                "imputed_rows":0,
                "phase_a_modified":"FALSE",
            }
            models.append(item)
    assert len(models)==31 and min(x["complete_rows"] for x in models)>0
    write_csv("joint_coverage_31_combinations.csv",models,list(models[0]))
    by_country=[]
    for iso in isos:
        group=[(iso,y) for y in YEARS]
        by_country.append({
            "ISO3":iso,
            "Country":locked["iso3_to_original_country_name"][iso],
            **{code:sum(k in present[code] for k in group) for code in CODE_ORDER},
            "all_5_joint_years":sum(all(k in present[code] for code in CODE_ORDER) for k in group)
        })
    write_csv("joint_coverage_by_country.csv",by_country,list(by_country[0]))
    by_year=[]
    for y in YEARS:
        group=[(iso,y) for iso in isos]
        by_year.append({
            "Year":y,
            **{code:sum(k in present[code] for k in group) for code in CODE_ORDER},
            "all_5_joint_countries":sum(all(k in present[code] for code in CODE_ORDER) for k in group)
        })
    write_csv("joint_coverage_by_year.csv",by_year,list(by_year[0]))
    # Per-country missingness, not imputed: rank the largest losses.
    missing_events=[]
    for iso in isos:
        for year in YEARS:
            missing_codes=[c for c in CODE_ORDER if (iso,year) not in present[c]]
            if missing_codes:
                missing_events.append({"ISO3":iso,"Year":year,
                    "missing_variable_count":len(missing_codes),
                    "missing_indicators":"+".join(missing_codes)})
    write_csv("joint_missingness_events.csv",missing_events,
              ["ISO3","Year","missing_variable_count","missing_indicators"])
    ix={r["indicators"]:r for r in models}
    core=CODE_ORDER[:2]
    both_patent=(CODE_ORDER[2],CODE_ORDER[3])
    explicit={
        "FDI_only":ix[CODE_ORDER[0]],
        "ICT_imports_only":ix[CODE_ORDER[1]],
        "patent_nonresident_only":ix[CODE_ORDER[2]],
        "patent_resident_only":ix[CODE_ORDER[3]],
        "hightech_exports_only":ix[CODE_ORDER[4]],
        "FDI_and_ICT_imports":ix["+".join(core)],
        "patents_resident_nonresident":ix["+".join(both_patent)],
        "FDI_ICT_imports_nonresident_patent":ix["+".join(CODE_ORDER[:3])],
        "all_five":ix["+".join(CODE_ORDER)],
    }
    summary={
        "phase":"EXTENDED_DATA_EXPERIMENTAL",
        "original_47x18_source_sha256":sha,
        "baseline_data_unchanged":True,
        "comparison_rows":EXPECTED_KEYS,
        "all_baseline_regressors_observed":True,
        "test_only_missingness_without_estimation":True,
        "no_new_variable_in_original_professor_model":True,
        "no_imputation":True,
        "number_of_combinations":len(models),
        "headline_scenarios":explicit,
        "scientific_cautions":[
            "Joined rows are NOT GMM estimation counts. xtabond2 also needs model-specific lags.",
            "Joint complete cases depend on covariate selection, publication revisions and country coverage.",
            "A valid GMM instrument requires exclusion restrictions, not simply high coverage.",
            "The WDI FDI and patent counts are not exogenous shocks, and nonresident patents do not identify bilateral technology transfer.",
            "Original professor workbook remains unchanged; never copy these data into the Phase A branch."
        ]
    }
    (OUT/"joint_coverage_verdict.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for name in ("FDI_and_ICT_imports","patents_resident_nonresident","FDI_ICT_imports_nonresident_patent","all_five"):
        v=explicit[name]
        print("JOINT_COVERAGE",name,"rows",v["complete_rows"],
              "fullcountries",v["full_18yr_countries"],
              "lagged_conservative",v["lag2_and_lag3_joint_rows_2008_2022"],flush=True)
    print("JOINT_COVERAGE_COMPLETE 31 nonempty combinations, 47 original countries, 18 years, no imputation or GMM",flush=True)

if __name__ == "__main__":
    main()
