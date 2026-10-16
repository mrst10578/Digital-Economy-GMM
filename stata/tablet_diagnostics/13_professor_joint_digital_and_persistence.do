* Professor original System GMM: joint digital effects & lag persistence restrictions.
* No parameter search. Two original lag(2 2) twostep specifications only.
version 16.0
clear all
set more off
cd "D:/Digital_Economy_QA_20261016"
sysdir set PLUS "D:/Digital_Economy_Stata_Ready/plus/"
capture noisily mata: mata mlib index
capture mkdir "outputs/professor"
capture log close _all
log using "outputs/professor/PROFESSOR_JOINT_DIGITAL_AND_PERSISTENCE.log", text replace
capture noisily do "stata/01_environment_and_data.do"
local ready_rc = _rc
if `ready_rc' {
  display as error "JOINT_PREFLIGHT_FAILED rc=`ready_rc'"
  log close
  exit `ready_rc'
}
postfile pp str20 outcome double rc N Ng instruments lag_coef lag_se joint_rc joint_F joint_p persistence_rc persistence_F persistence_p hansen_p ar1_p ar2_p using "outputs/professor/professor_joint_restrictions.dta", replace
foreach y in Growth ln_Productivity {
  display as result "JOINT_ESTIMATION_START outcome=`y'"
  capture noisily xtabond2 `y' L.`y' Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies_sys, gmmstyle(`y', lag(2 2) collapse split) gmmstyle(Internet Broadband ICT_Exports RnD, lag(2 2) collapse) gmmstyle(Unemployment Inflation, lag(2 2) collapse) ivstyle($digital_year_dummies_sys) twostep robust small artests(2)
  local rc = _rc
  if `rc' == 0 {
    local n = e(N)
    local ng = e(N_g)
    local j = e(j)
    local b = _b[L.`y']
    local se = _se[L.`y']
    local ha = e(hansenp)
    local a1 = e(ar1p)
    local a2 = e(ar2p)
    display as result "TEST_DIGITAL_JOINT outcome=`y': H0 Internet=Broadband=ICT_Exports=0"
    capture noisily test Internet Broadband ICT_Exports
    local jr = _rc
    local jf = .
    local jp = .
    if `jr' == 0 {
      local jf = r(F)
      local jp = r(p)
      display as result "TEST_DIGITAL_JOINT_RESULT outcome=`y' F=`jf' p=`jp'"
    }
    display as result "TEST_LAG_EQUAL_ONE outcome=`y': H0 coefficient(L.`y')=1 (NOT formal unit root test)"
    capture noisily test L.`y' = 1
    local pr = _rc
    local pf = .
    local ppv = .
    if `pr' == 0 {
      local pf = r(F)
      local ppv = r(p)
      display as result "TEST_LAG_EQUAL_ONE_RESULT outcome=`y' F=`pf' p=`ppv'"
    }
    post pp ("`y'") (0) (`n') (`ng') (`j') (`b') (`se') (`jr') (`jf') (`jp') (`pr') (`pf') (`ppv') (`ha') (`a1') (`a2')
    display as result "JOINT_MODEL_OK outcome=`y'"
  }
  else {
    post pp ("`y'") (`rc') (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.)
    display as error "JOINT_MODEL_FAILED outcome=`y' rc=`rc'"
  }
}
postclose pp
preserve
use "outputs/professor/professor_joint_restrictions.dta", clear
export delimited using "outputs/professor/professor_joint_restrictions.csv", replace
count if rc != 0
display as result "JOINT_MODEL_FAILURES=" r(N)
count if joint_rc != 0 | persistence_rc != 0
display as result "JOINT_RESTRICTION_FAILURES=" r(N)
list, noobs abbreviate(16)
restore
display as result "JOINT_TESTS_COMPLETE: no selection; joint Wald significance is conditional on unproven instrument validity"
log close
