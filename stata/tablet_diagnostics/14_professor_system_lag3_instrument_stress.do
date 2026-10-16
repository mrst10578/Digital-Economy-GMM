* Predeclared strict lag-3-only sensitivity for BOTH professor original System GMM equations.
* Do not change or select the original lag-2 main specifications or dataset.
* Deep lags may be weaker instruments and do not guarantee valid level moments.
version 16.0
clear all
set more off
cd "D:/Digital_Economy_QA_20261016"
sysdir set PLUS "D:/Digital_Economy_Stata_Ready/plus/"
capture noisily mata: mata mlib index
capture mkdir "outputs/professor"
capture log close _all
log using "outputs/professor/PROFESSOR_LAG3_INSTRUMENT_STRESS.log", text replace
capture noisily do "stata/01_environment_and_data.do"
local preflight_rc = _rc
if `preflight_rc' {
  display as error "LAG3_PREFLIGHT_FAILED rc=`preflight_rc'"
  log close
  exit `preflight_rc'
}
postfile p3 str20 outcome double rc N Ng instruments b_lag b_internet se_internet p_internet sargan_p hansen_p ar1_p ar2_p diffh_level_dep_p diffh_controls_p using "outputs/professor/professor_lag3_instrument_stress.dta", replace
foreach y in Growth ln_Productivity {
  display as result "LAG3_START outcome=`y': only lag 3 for all GMM-style variables"
  capture noisily xtabond2 `y' L.`y' Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies_sys, gmmstyle(`y', lag(3 3) collapse split) gmmstyle(Internet Broadband ICT_Exports RnD, lag(3 3) collapse) gmmstyle(Unemployment Inflation, lag(3 3) collapse) ivstyle($digital_year_dummies_sys) twostep robust small artests(2)
  local fitrc = _rc
  if `fitrc'==0 {
    local n=e(N)
    local ng=e(N_g)
    local j=e(j)
    local bl=_b[L.`y']
    local bi=_b[Internet]
    local si=_se[Internet]
    local pi=2*ttail(`ng'-1,abs(`bi'/`si'))
    local sp=e(sarganp)
    local hp=e(hansenp)
    local a1=e(ar1p)
    local a2=e(ar2p)
    local dhdep=.
    local dhctrl=.
    capture matrix __diffh = e(diffsargan)
    if _rc==0 {
      if rowsof(__diffh)==5 & inlist(colsof(__diffh),3,4) {
        * e(diffsargan) contains 5 statistic rows. xtabond2 may omit the
        * non-identifiable overall-level group, giving 3 instead of 4 columns.
        * In either layout, the last two columns are Y-level and controls.
        local ncols=colsof(__diffh)
        local dhdep=el(__diffh,5,`ncols'-1)
        local dhctrl=el(__diffh,5,`ncols')
        display as result "LAG3_DH_MATRIX_LAYOUT outcome=`y' columns=`ncols' dependent_level_p=`dhdep' controls_p=`dhctrl'"
      }
    }
    post p3 ("`y'") (0) (`n') (`ng') (`j') (`bl') (`bi') (`si') (`pi') (`sp') (`hp') (`a1') (`a2') (`dhdep') (`dhctrl')
    display as result "LAG3_OK outcome=`y' N=`n' instruments=`j' internet=`bi' internet_p=`pi' hansen=`hp' AR1=`a1' AR2=`a2' DHlevel=`dhdep'"
  }
  else {
    post p3 ("`y'") (`fitrc') (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.)
    display as error "LAG3_FAILED outcome=`y' rc=`fitrc'"
  }
}
postclose p3
preserve
use "outputs/professor/professor_lag3_instrument_stress.dta", clear
export delimited using "outputs/professor/professor_lag3_instrument_stress.csv", replace
count if rc!=0
display as result "LAG3_MODEL_FAILURES=" r(N)
count
display as result "LAG3_MODEL_TOTAL=" r(N)
list, noobs abbreviate(22)
restore
display as result "LAG3_SENSITIVITY_FINISHED: extra moment restrictions not scientifically accepted by default"
log close
