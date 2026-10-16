* Final professor-ready full variable coefficient table from archived ORIGINAL
* two-step System GMM .ster estimates, with no re-fitting or changing inputs.
* Archive saved by Stata/MP 17 on 2026-10-16 under outputs/professor.
version 16.0
clear all
set more off
cd "D:/Digital_Economy_QA_20261016"
capture mkdir "outputs/professor"
capture log close _all
log using "outputs/professor/PROFESSOR_FULL_COEFFICIENT_EXPORT.log", text replace
postfile coefs str20 outcome str26 term double estimate robust_se t_stat p_value ci95_low ci95_high N countries instruments using "outputs/professor/professor_two_system_full_coefficients.dta", replace
foreach y in Growth ln_Productivity {
    display as result "FINAL_STER_LOAD_START outcome=`y'"
    capture noisily estimates use "outputs/professor/`y'_twostep.ster"
    local readrc=_rc
    if `readrc' {
        display as error "FINAL_STER_LOAD_FAILED outcome=`y' rc=`readrc'"
        postclose coefs
        log close
        exit `readrc'
    }
    local n=e(N)
    local ng=e(N_g)
    local instr=e(j)
    local df=`ng'-1
    assert `n'==799
    assert `ng'==47
    assert `instr'==31
    local critical=invttail(`df', .025)
    display as result "FINAL_STER_LOADED outcome=`y' N=`n' Ng=`ng' instruments=`instr' critical=`critical'"
    foreach v in L.`y' Internet Broadband ICT_Exports Unemployment Inflation RnD {
        local b=_b[`v']
        local se=_se[`v']
        if missing(`b',`se') | `se'<=0 {
           display as error "FINAL_COEFFICIENT_ERROR outcome=`y' term=`v'"
           postclose coefs
           log close
           exit 459
        }
        local t=`b'/`se'
        local p=2*ttail(`df', abs(`t'))
        local low=`b'-`critical'*`se'
        local high=`b'+`critical'*`se'
        post coefs ("`y'") ("`v'") (`b') (`se') (`t') (`p') (`low') (`high') (`n') (`ng') (`instr')
        display as result "FINAL_COEFFICIENT_OK outcome=`y' term=`v' estimate=`b' se=`se' p=`p'"
    }
}
postclose coefs
preserve
use "outputs/professor/professor_two_system_full_coefficients.dta", clear
isid outcome term
count
assert r(N)==14
count if missing(estimate) | missing(robust_se) | missing(p_value) | missing(ci95_low) | missing(ci95_high)
assert r(N)==0
count if p_value<0 | p_value>1 | ci95_low>estimate | ci95_high<estimate
assert r(N)==0
export delimited using "outputs/professor/professor_two_system_full_coefficients.csv", replace
display as result "FINAL_FULL_TABLE_ROWS=" _N
list outcome term estimate robust_se p_value ci95_low ci95_high, noobs abbreviate(22)
restore
display as result "FINAL_FULL_COEFFICIENT_EXPORT_COMPLETED: archived original models only; no new fitting and no causal approval"
log close
