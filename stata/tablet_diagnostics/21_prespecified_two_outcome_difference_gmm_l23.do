* Ex-ante identification repair trial, not a search over GMM lags.
* Two original professor outcome DEFINITIONS unchanged: Growth, ln_Productivity.
* Remove potentially invalid System level equation; difference-only, lag(2 3)
* and same endogenous variable groups as the professor's System GMM baseline.
* This overidentified lag(2 3) comparison was prefigured in 04_productivity_models.do
* as a ONE-step preliminary, now test one- and two-step with identical instruments.
* Never replace original specification based on Hansen or significance alone.
version 16.0
clear all
set more off
cd "D:/Digital_Economy_QA_20261016"
sysdir set PLUS "D:/Digital_Economy_Stata_Ready/plus/"
capture noisily mata: mata mlib index
capture mkdir "outputs/professor"
capture log close _all
log using "outputs/professor/DIFFERENCE_GMM_OVERIDENTIFIED_L23_BOTH_MODELS.log", text replace
capture noisily do "stata/01_environment_and_data.do"
local preflight=_rc
if `preflight' {
 display as error "DIFF_REPAIR_PREFLIGHT_FAILED rc=`preflight'"
 log close
 exit `preflight'
}
postfile v str20 outcome str10 estimator double rc N Ng instruments b_lag se_lag b_internet se_internet p_internet joint_p hansen_p sargan_p ar1_p ar2_p using "outputs/professor/diff_l23_two_outcomes_stats.dta", replace
foreach y in Growth ln_Productivity {
 foreach estimator in twostep onestep {
  display as result "DIFF_REPAIR_START outcome=`y' estimator=`estimator' lag2_3_only"
  if "`estimator'"=="twostep" {
   capture noisily xtabond2 `y' L.`y' Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies_diff, gmmstyle(`y', lag(2 3) collapse) gmmstyle(Internet Broadband ICT_Exports RnD, lag(2 3) collapse) gmmstyle(Unemployment Inflation, lag(2 3) collapse) ivstyle($digital_year_dummies_diff, equation(diff)) noleveleq twostep robust small artests(2)
  }
  else {
   capture noisily xtabond2 `y' L.`y' Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies_diff, gmmstyle(`y', lag(2 3) collapse) gmmstyle(Internet Broadband ICT_Exports RnD, lag(2 3) collapse) gmmstyle(Unemployment Inflation, lag(2 3) collapse) ivstyle($digital_year_dummies_diff, equation(diff)) noleveleq robust small artests(2)
  }
  local rc=_rc
  if `rc'==0 {
   local n=e(N)
   local ng=e(N_g)
   local j=e(j)
   local lagb=_b[L.`y']
   local lagse=_se[L.`y']
   local internet=_b[Internet]
   local ise=_se[Internet]
   local ip=2*ttail(`ng'-1,abs(`internet'/`ise'))
   local jp=.
   capture noisily test Internet Broadband ICT_Exports
   if _rc==0 local jp=r(p)
   local hp=e(hansenp)
   local sp=e(sarganp)
   local a1=e(ar1p)
   local a2=e(ar2p)
   post v ("`y'") ("`estimator'") (0) (`n') (`ng') (`j') (`lagb') (`lagse') (`internet') (`ise') (`ip') (`jp') (`hp') (`sp') (`a1') (`a2')
   display as result "DIFF_REPAIR_OK outcome=`y' estimator=`estimator' N=`n' groups=`ng' instruments=`j' Hansen=`hp' Sargan=`sp' AR1=`a1' AR2=`a2' InternetP=`ip' JointDigitalP=`jp'"
  }
  else {
   post v ("`y'") ("`estimator'") (`rc') (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.)
   display as error "DIFF_REPAIR_FAILED outcome=`y' estimator=`estimator' rc=`rc'"
  }
 }
}
postclose v
preserve
use "outputs/professor/diff_l23_two_outcomes_stats.dta", clear
export delimited using "outputs/professor/diff_l23_two_outcomes_stats.csv", replace
count if rc!=0
display as result "DIFF_REPAIR_FAILURES=" r(N)
count
display as result "DIFF_REPAIR_TOTAL_COUNT=" r(N)
list, noobs abbreviate(18)
restore
display as result "DIFF_REPAIR_COMPLETE: original professor outcome preserved; extra instruments tested; no automatic scientific validation"
log close
