* Ex ante predictive-relevance stress test for already frozen lag(2 3) Diff-GMM
* outcomes and all six regressors; separate cluster-robust OLS proxy tests.
* This is NOT a formal GMM weak-instrument/rank test; never infer exogeneity.
version 16.0
clear all
set more off
cd "D:/Digital_Economy_QA_20261016"
sysdir set PLUS "D:/Digital_Economy_Stata_Ready/plus/"
capture log close _all
log using "outputs/professor/DIFF_L23_LAG_RELEVANCE_REAL_STATA.log", text replace
do "stata/01_environment_and_data.do"
postfile q str22 variable str24 target double rc N countries coefficient_l2 coefficient_l3 joint_F joint_p r2 using "outputs/professor/diff_l23_lag_relevance.dta", replace
foreach v in Growth ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD {
  local target "D.`v'"
  if inlist("`v'","Growth","ln_Productivity") local target "D.L.`v'"
  display as result "DIFF_RELEVANCE_START v=`v' target=`target'"
  capture noisily regress `target' L2.`v' L3.`v' i.Year, vce(cluster panel_id)
  local rc = _rc
  if `rc' == 0 {
    local n=e(N)
    local ncountry=e(N_clust)
    local b2=_b[L2.`v']
    local b3=_b[L3.`v']
    local r2=e(r2)
    capture noisily test L2.`v' L3.`v'
    local testrc=_rc
    local f=.
    local p=.
    if `testrc'==0 {
       local f=r(F)
       local p=r(p)
    }
    post q ("`v'") ("`target'") (0) (`n') (`ncountry') (`b2') (`b3') (`f') (`p') (`r2')
    display as result "DIFF_RELEVANCE_OK v=`v' N=`n' groups=`ncountry' F=`f' p=`p'"
  }
  else {
    post q ("`v'") ("`target'") (`rc') (.) (.) (.) (.) (.) (.) (.)
    display as error "DIFF_RELEVANCE_FAILED v=`v' rc=`rc'"
  }
}
postclose q
preserve
use "outputs/professor/diff_l23_lag_relevance.dta", clear
export delimited using "outputs/professor/diff_l23_lag_relevance.csv", replace
count if rc!=0
display as result "DIFF_RELEVANCE_FAILURES=" r(N)
count
display as result "DIFF_RELEVANCE_COUNT=" r(N)
restore
display as result "DIFF_RELEVANCE_COMPLETE: descriptive predictive checks only, not GMM instrument validity"
log close
