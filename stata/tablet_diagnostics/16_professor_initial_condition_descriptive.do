* Descriptive INITIAL LEVEL vs mean annual within-country change (2005-22).
* This is NOT an econometric test of Blundell-Bond level moment exogeneity,
* nor a proper panel unit-root test. It diagnoses patterns relevant to initial conditions.
version 16.0
clear all
set more off
cd "D:/Digital_Economy_QA_20261016"
sysdir set PLUS "D:/Digital_Economy_Stata_Ready/plus/"
capture noisily mata: mata mlib index
capture mkdir "outputs/professor"
capture log close _all
log using "outputs/professor/PROFESSOR_INITIAL_CONDITION_DESCRIPTIVE.log", text replace
capture noisily do "stata/01_environment_and_data.do"
local pre_rc=_rc
if `pre_rc' {
    display as error "INITIAL_CONDITION_PREFLIGHT_FAILED rc=`pre_rc'"
    log close
    exit `pre_rc'
}
postfile init str20 outcome double rc countries periods slope se p r2 mean_annual_change sd_annual_change share_positive_change using "outputs/professor/initial_condition_descriptives.dta", replace
foreach y in Growth ln_Productivity {
    preserve
    bysort panel_id (Year): generate double initial_y = `y'[1]
    bysort panel_id (Year): generate double annual_dy = `y'-`y'[_n-1] if _n>1
    bysort panel_id: egen double mean_dy = mean(annual_dy)
    bysort panel_id (Year): keep if _n==1
    isid panel_id
    assert _N==47
    quietly summarize mean_dy
    local mu=r(mean)
    local sd=r(sd)
    quietly count if mean_dy>0
    local share=r(N)/47
    capture noisily regress mean_dy initial_y, vce(robust)
    local rc=_rc
    if `rc'==0 {
        local slope=_b[initial_y]
        local se=_se[initial_y]
        local p=2*ttail(e(df_r),abs(`slope'/`se'))
        local r2=e(r2)
        post init ("`y'") (0) (47) (17) (`slope') (`se') (`p') (`r2') (`mu') (`sd') (`share')
        display as result "INITIAL_DESCRIPTIVE_OK outcome=`y' slope=`slope' p=`p' r2=`r2' share_positive=`share'"
    }
    else {
        post init ("`y'") (`rc') (.) (.) (.) (.) (.) (.) (.) (.) (.)
        display as error "INITIAL_DESCRIPTIVE_FAILED outcome=`y' rc=`rc'"
    }
    restore
}
postclose init
preserve
use "outputs/professor/initial_condition_descriptives.dta", clear
export delimited using "outputs/professor/initial_condition_descriptives.csv", replace
count if rc!=0
display as result "INITIAL_DESCRIPTIVE_FAILURES=" r(N)
list, noobs abbreviate(20)
restore
display as result "INITIAL_DESCRIPTIVE_COMPLETE: descriptive association only; does not identify unobserved country effects"
log close
