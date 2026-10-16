* Preregistered mechanical lag-window stress test, not model selection.
* Root-relative paths, source workbook and pre-existing models unchanged.
version 16.0
clear all
set more off
cd "D:/Digital_Economy_Stata_Ready"
sysdir set PLUS "D:/Digital_Economy_Stata_Ready/plus/"
capture noisily mata: mata mlib index
capture log close _all
capture mkdir "outputs/diagnostics"
log using "outputs/diagnostics/LAG_WINDOW_STRESS.log", text replace
which xtabond2
use "data/processed/stata_ready.dta", clear
isid ISO3 Year
capture confirm variable panel_id
if _rc encode ISO3, generate(panel_id)
xtset panel_id Year
capture drop yd_*
quietly tab Year, generate(yd_)
global digital_year_dummies "yd_2-yd_18"
postfile stress str30 model double rc N Ng instruments sargan_p hansen_p ar1_p ar2_p b_internet using "outputs/diagnostics/stress_status.dta", replace
foreach y in Growth ln_Productivity {
    foreach lag in 2 3 {
        display "STRESS_START outcome=`y' lag=`lag':`lag' diff GMM, one-step, collapse, robust, 17 time dummies"
        capture noisily xtabond2 `y' L.`y' Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies, gmmstyle(`y' Internet Broadband ICT_Exports Unemployment Inflation RnD, lag(`lag' `lag') collapse) ivstyle($digital_year_dummies, equation(diff)) noleveleq robust small artests(2)
        local err = _rc
        if `err' == 0 {
            post stress ("`y'_DIFF_L`lag'") (0) (e(N)) (e(N_g)) (e(j)) (e(sarganp)) (e(hansenp)) (e(ar1p)) (e(ar2p)) (_b[Internet])
            display "STRESS_ESTIMATED outcome=`y' lag=`lag' N=" e(N) " instruments=" e(j)
        }
        else {
            post stress ("`y'_DIFF_L`lag'") (`err') (.) (.) (.) (.) (.) (.) (.) (.)
            display as error "STRESS_FAILED outcome=`y' lag=`lag' rc=`err'"
        }
    }
}
postclose stress
preserve
use "outputs/diagnostics/stress_status.dta", clear
export delimited using "outputs/diagnostics/stress_status.csv", replace
list, noobs abbreviate(18)
restore
display "STRESS_TEST_COMPLETE: exploratory sensitivity only; no causal validation"
log close
