* Full leave-one-country-out sensitivity: prespecified two Difference GMM outcomes
* Independent of previous model choice; NO p-value selection, causal claim or auto fixes.
version 16.0
clear all
set more off
cd "D:/Digital_Economy_QA_20261016"
sysdir set PLUS "D:/Digital_Economy_Stata_Ready/plus/"
capture noisily mata: mata mlib index
capture mkdir "outputs/scientific"
capture log close _all
log using "outputs/scientific/LOO_47X2_20261016.log", text replace
do "stata/01_environment_and_data.do"
capture confirm file "data/processed/stata_ready.dta"
if _rc exit 601
levelsof ISO3, local(countries)
local original_groups = r(r)
display "LOO_START: full deterministic 47-country jackknife, two outcomes, no case selection"
postfile loo str3 dropped_country str20 outcome double rc N Ng instruments sargan_p hansen_p ar1_p ar2_p b_internet se_internet using "outputs/scientific/loo_47x2.dta", replace
foreach y in Growth ln_Productivity {
    foreach iso of local countries {
        preserve
        quietly drop if ISO3 == "`iso'"
        quietly xtset panel_id Year
        display "LOO_RUN outcome=`y' drop=`iso'"
        capture noisily xtabond2 `y' L.`y' Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies_diff, gmmstyle(`y' Internet Broadband ICT_Exports Unemployment Inflation RnD, lag(2 3) collapse) ivstyle($digital_year_dummies_diff, equation(diff)) noleveleq robust small artests(2)
        local fit_rc = _rc
        if `fit_rc' == 0 {
            post loo ("`iso'") ("`y'") (0) (e(N)) (e(N_g)) (e(j)) (e(sarganp)) (e(hansenp)) (e(ar1p)) (e(ar2p)) (_b[Internet]) (_se[Internet])
            display as result "LOO_OK outcome=`y' drop=`iso' N=" e(N) " bInternet=" _b[Internet]
        }
        else {
            post loo ("`iso'") ("`y'") (`fit_rc') (.) (.) (.) (.) (.) (.) (.) (.) (.)
            display as error "LOO_FAILED outcome=`y' drop=`iso' return_code=`fit_rc'"
        }
        restore
    }
}
postclose loo
preserve
use "outputs/scientific/loo_47x2.dta", clear
sort outcome dropped_country
export delimited using "outputs/scientific/loo_47x2.csv", replace
tabulate outcome if rc==0
display as result "LOO_TOTAL_ROWS=" _N
count if rc!=0
display as result "LOO_TOTAL_FAILURES=" r(N)
restore
display as result "LOO_47X2_COMPLETED: not causal validity or selection of optimal models"
log close
