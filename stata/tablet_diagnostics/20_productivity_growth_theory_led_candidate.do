* THEORY-LED ALTERNATIVE: annual productivity growth (D.ln_Productivity).
* Not the professor's original dependent variable ln_Productivity in levels.
* Pre-specified all six x as annual changes, fixed endogenous GMM groups,
* collapsed lag(2 2), 2-step primary and 1-step weighting sensitivity.
* Don't select models or lags based on p-values. The source remains unchanged.
version 16.0
clear all
set more off
cd "D:/Digital_Economy_QA_20261016"
sysdir set PLUS "D:/Digital_Economy_Stata_Ready/plus/"
capture noisily mata: mata mlib index
capture mkdir "outputs/professor"
capture log close _all
log using "outputs/professor/THEORY_LED_PRODUCTIVITY_GROWTH_SYSTEM_GMM.log", text replace
capture noisily do "stata/01_environment_and_data.do"
local pre=_rc
if `pre' {
  display as error "ALTERNATIVE_PREFLIGHT_FAILED rc=`pre'"
  log close
  exit `pre'
}
generate double Productivity_Growth = D.ln_Productivity
foreach v in Internet Broadband ICT_Exports Unemployment Inflation RnD {
  generate double d_`v' = D.`v'
}
* Year 2005 is undefined for growth; omit 2005, 2006, 2008 as time bases.
global alt_productivity_years "yd_3 yd_5-yd_18"
postfile a str20 method double rc N Ng instruments b_lag se_lag b_internet se_internet internet_p hansen_p sargan_p ar1_p ar2_p diffh_dep_level_p diffh_controls_p using "outputs/professor/theory_led_productivity_growth_stats.dta", replace
foreach method in twostep onestep {
  display as result "ALTERNATIVE_START method=`method'"
  if "`method'"=="twostep" {
    capture noisily xtabond2 Productivity_Growth L.Productivity_Growth d_Internet d_Broadband d_ICT_Exports d_Unemployment d_Inflation d_RnD $alt_productivity_years, gmmstyle(Productivity_Growth, lag(2 2) collapse split) gmmstyle(d_Internet d_Broadband d_ICT_Exports d_RnD, lag(2 2) collapse) gmmstyle(d_Unemployment d_Inflation, lag(2 2) collapse) ivstyle($alt_productivity_years) twostep robust small artests(2)
  }
  else {
    capture noisily xtabond2 Productivity_Growth L.Productivity_Growth d_Internet d_Broadband d_ICT_Exports d_Unemployment d_Inflation d_RnD $alt_productivity_years, gmmstyle(Productivity_Growth, lag(2 2) collapse split) gmmstyle(d_Internet d_Broadband d_ICT_Exports d_RnD, lag(2 2) collapse) gmmstyle(d_Unemployment d_Inflation, lag(2 2) collapse) ivstyle($alt_productivity_years) robust small artests(2)
  }
  local rc=_rc
  if `rc'==0 {
    local n=e(N)
    local ng=e(N_g)
    local j=e(j)
    local bl=_b[L.Productivity_Growth]
    local sl=_se[L.Productivity_Growth]
    local bi=_b[d_Internet]
    local si=_se[d_Internet]
    local pi=2*ttail(`ng'-1,abs(`bi'/`si'))
    local hp=e(hansenp)
    local sp=e(sarganp)
    local a1=e(ar1p)
    local a2=e(ar2p)
    local dh=.
    local ctrl=.
    capture matrix __d=e(diffsargan)
    if _rc==0 {
      if rowsof(__d)==5 & inlist(colsof(__d),3,4) {
        local k=colsof(__d)
        local dh=el(__d,5,`k'-1)
        local ctrl=el(__d,5,`k')
      }
    }
    post a ("`method'") (0) (`n') (`ng') (`j') (`bl') (`sl') (`bi') (`si') (`pi') (`hp') (`sp') (`a1') (`a2') (`dh') (`ctrl')
    display as result "ALTERNATIVE_OK method=`method' N=`n' groups=`ng' instruments=`j' Hansen=`hp' AR1=`a1' AR2=`a2' DHlevel=`dh' InternetP=`pi'"
  }
  else {
    post a ("`method'") (`rc') (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.)
    display as error "ALTERNATIVE_FAILED method=`method' rc=`rc'"
  }
}
postclose a
preserve
use "outputs/professor/theory_led_productivity_growth_stats.dta", clear
export delimited using "outputs/professor/theory_led_productivity_growth_stats.csv", replace
count if rc != 0
display as result "ALTERNATIVE_FAILED_COUNT=" r(N)
count
display as result "ALTERNATIVE_TOTAL_COUNT=" r(N)
restore
display as result "ALTERNATIVE_COMPLETED: new research estimand, not causal acceptance"
log close
