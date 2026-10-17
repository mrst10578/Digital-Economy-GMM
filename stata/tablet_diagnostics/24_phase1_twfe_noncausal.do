version 16.0
clear all
set more off
cd "D:/Digital_Economy_Phase1_Method_20261017"
sysdir set PLUS "D:/Digital_Economy_Stata_Ready/plus/"
capture mkdir "outputs"
capture log close _all
log using "outputs/STATA_TWFE_INDEPENDENT.log", text replace
capture noisily do "stata/01_environment_and_data.do"
local rc_pre=_rc
if `rc_pre' != 0 {
 display as error "TWFE_PREFLIGHT_FAILED"
 log close
 exit `rc_pre'
}
foreach v in ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD {
 generate double D_`v'=D.`v'
}
postfile results str22 model str24 term double rc N Ng b se p joint_p using "outputs/STATA_TWFE_COUNTRY_CLUSTER.dta", replace
foreach y in Growth ln_Productivity D_ln_Productivity {
 if "`y'"=="D_ln_Productivity" {
  local regressors "D_Internet D_Broadband D_ICT_Exports D_Unemployment D_Inflation D_RnD"
  local digital "D_Internet D_Broadband D_ICT_Exports"
 }
 else {
  local regressors "Internet Broadband ICT_Exports Unemployment Inflation RnD"
  local digital "Internet Broadband ICT_Exports"
 }
 display as result "TWFE_START model=`y'"
 capture noisily xtreg `y' `regressors' i.Year, fe vce(cluster panel_id)
 local result_rc=_rc
 if `result_rc' !=0 {
  post results ("`y'") ("FAIL") (`result_rc') (.) (.) (.) (.) (.) (.)
  display as error "TWFE_FAIL model=`y' rc=`result_rc'"
 }
 else {
  local n=e(N)
  local ng=e(N_g)
  local joint=.
  capture noisily test `digital'
  if _rc==0 local joint=r(p)
  foreach v of local regressors {
   local b=_b[`v']
   local se=_se[`v']
   local p=2*ttail(e(df_r),abs(`b'/`se'))
   post results ("`y'") ("`v'") (0) (`n') (`ng') (`b') (`se') (`p') (`joint')
   display as result "TWFE_TERM model=`y' var=`v' b=" %18.12g `b' " se=" %18.12g `se' " p=" %18.12g `p'
  }
  display as result "TWFE_OK model=`y' N=`n' groups=`ng' joint_cluster_p=`joint'"
 }
}
postclose results
preserve
use "outputs/STATA_TWFE_COUNTRY_CLUSTER.dta",clear
export delimited using "outputs/STATA_TWFE_COUNTRY_CLUSTER.csv",replace
count if rc!=0
display as result "TWFE_FAIL_COUNT=" r(N)
count
display as result "TWFE_TOTAL_TERM_ROWS=" r(N)
restore
display as result "TWFE_REESTIMATION_COMPLETED_NO_CAUSAL_CLAIM"
log close
