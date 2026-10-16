* Prespecified follow-up to DIFFERENCE-GMM lag(2 3) two-step with original
* Growth and ln_Productivity outcomes, 47 countries and historical sample.
* New checks: residual Pesaran CD on the REAL two-step fits; and 5 high-influence
* countries from EARLIER, independently saved one-step 47x2 jackknife.
* Country union from top 3 original one-step Internet slope changes per outcome:
* Growth AZE TUR MAC; productivity ISR TUR KGZ -> AZE TUR MAC ISR KGZ.
* These are vulnerability diagnostics, NOT a hypothesis-search or causal proof.
version 16.0
clear all
set more off
cd "D:/Digital_Economy_QA_20261016"
sysdir set PLUS "D:/Digital_Economy_Stata_Ready/plus/"
capture noisily mata: mata mlib index
capture mkdir "outputs/professor"
capture log close _all
log using "outputs/professor/DIFF_GMM_L23_TWO_STEP_CD_AND_INFLUENCE.log", text replace
capture noisily do "stata/01_environment_and_data.do"
local pre=_rc
if `pre' {
 display as error "DIFF_STRESS_PREFLIGHT_FAILED rc=`pre'"
 log close
 exit `pre'
}
local fixed_countries "AZE TUR MAC ISR KGZ"
display as result "INFLUENCE_FIXED_BEFORE_ESTIMATION: `fixed_countries'"
postfile cd str20 outcome double rc groups years pairs cd_stat cd_p using "outputs/professor/diff_l23_twostep_residual_cd.dta", replace
foreach y in Growth ln_Productivity {
 display as result "DIFF_TWOSTEP_CD_START outcome=`y'"
 capture noisily xtabond2 `y' L.`y' Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies_diff, gmmstyle(`y', lag(2 3) collapse) gmmstyle(Internet Broadband ICT_Exports RnD, lag(2 3) collapse) gmmstyle(Unemployment Inflation, lag(2 3) collapse) ivstyle($digital_year_dummies_diff, equation(diff)) noleveleq twostep robust small artests(2)
 local est_rc=_rc
 if `est_rc'==0 {
  preserve
  quietly generate byte __gmm_sample=e(sample)
  capture noisily predict double __gmm_resid if __gmm_sample, residuals
  local pred_rc=_rc
  if `pred_rc'==0 {
   quietly keep if __gmm_sample & !missing(__gmm_resid)
   quietly keep Year panel_id __gmm_resid
   quietly reshape wide __gmm_resid, i(Year) j(panel_id)
   quietly ds __gmm_resid*
   local cols `r(varlist)'
   mata: __X=st_data(.,tokens(st_local("cols")))
   mata: __R=correlation(__X)
   mata: __N=cols(__X)
   mata: __T=rows(__X)
   mata: __CD=sqrt(2*__T/(__N*(__N-1)))*(sum(vec(__R))-__N)/2
   mata: st_numscalar("__cd_n",__N)
   mata: st_numscalar("__cd_t",__T)
   mata: st_numscalar("__cd_z",__CD)
   local pairs=scalar(__cd_n)*(scalar(__cd_n)-1)/2
   local p=2*normal(-abs(scalar(__cd_z)))
   post cd ("`y'") (0) (__cd_n) (__cd_t) (`pairs') (__cd_z) (`p')
   display as result "DIFF_TWOSTEP_CD_OK outcome=`y' groups=" __cd_n " years=" __cd_t " pairs=`pairs' CD=" __cd_z " p=`p'"
  }
  else {
   post cd ("`y'") (`pred_rc') (.) (.) (.) (.) (.)
   display as error "DIFF_TWOSTEP_CD_PREDICT_FAILED outcome=`y' rc=`pred_rc'"
  }
  restore
 }
 else {
  post cd ("`y'") (`est_rc') (.) (.) (.) (.) (.)
  display as error "DIFF_TWOSTEP_CD_EST_FAILED outcome=`y' rc=`est_rc'"
 }
}
postclose cd
preserve
use "outputs/professor/diff_l23_twostep_residual_cd.dta",clear
export delimited using "outputs/professor/diff_l23_twostep_residual_cd.csv",replace
count if rc!=0
display as result "DIFF_TWOSTEP_CD_FAILURES=" r(N)
restore

postfile lo str20 outcome str3 omitted_iso double rc N groups instruments internet_b internet_se internet_p lag_b hansen_p sargan_p ar1_p ar2_p using "outputs/professor/diff_l23_twostep_fixed_country_sensitivity.dta", replace
foreach y in Growth ln_Productivity {
 foreach iso of local fixed_countries {
  preserve
  quietly drop if ISO3=="`iso'"
  quietly xtset panel_id Year
  display as result "DIFF_FIXED_INFLUENCE_START outcome=`y' omitted=`iso'"
  capture noisily xtabond2 `y' L.`y' Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies_diff, gmmstyle(`y', lag(2 3) collapse) gmmstyle(Internet Broadband ICT_Exports RnD, lag(2 3) collapse) gmmstyle(Unemployment Inflation, lag(2 3) collapse) ivstyle($digital_year_dummies_diff, equation(diff)) noleveleq twostep robust small artests(2)
  local rc=_rc
  if `rc'==0 {
   local n=e(N)
   local ng=e(N_g)
   local j=e(j)
   local b=_b[Internet]
   local se=_se[Internet]
   local pi=2*ttail(`ng'-1,abs(`b'/`se'))
   local lagb=_b[L.`y']
   local ha=e(hansenp)
   local sa=e(sarganp)
   local a1=e(ar1p)
   local a2=e(ar2p)
   post lo ("`y'") ("`iso'") (0) (`n') (`ng') (`j') (`b') (`se') (`pi') (`lagb') (`ha') (`sa') (`a1') (`a2')
   display as result "DIFF_FIXED_INFLUENCE_OK outcome=`y' omitted=`iso' Internet=`b' InternetP=`pi' Hansen=`ha' AR1=`a1' AR2=`a2'"
  }
  else {
   post lo ("`y'") ("`iso'") (`rc') (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.)
   display as error "DIFF_FIXED_INFLUENCE_FAILED outcome=`y' omitted=`iso' rc=`rc'"
  }
  restore
 }
}
postclose lo
preserve
use "outputs/professor/diff_l23_twostep_fixed_country_sensitivity.dta",clear
sort outcome omitted_iso
export delimited using "outputs/professor/diff_l23_twostep_fixed_country_sensitivity.csv",replace
count if rc!=0
display as result "DIFF_FIXED_INFLUENCE_FAILURES=" r(N)
count
display as result "DIFF_FIXED_INFLUENCE_TOTAL_COUNT=" r(N)
restore
display as result "DIFF_L23_STRESS_COMPLETE: fixed original sample, preselected prior-impact countries, no significance screening"
log close
