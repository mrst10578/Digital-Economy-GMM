* Execute from root of extracted Digital_Economy_Stata_Ready directory.
version 16.0
clear all
set more off
capture mkdir "outputs"
capture mkdir "outputs/stata"
capture log close _all
log using "outputs/stata/RUN_ALL_REAL_STATA.log", text replace
display as text "PROJECT Digital-Economy-GMM; REAL STATA VERSION " c(stata_version)
capture noisily do "stata/01_environment_and_data.do"
local preflight_rc = _rc
if `preflight_rc' != 0 {
    display as error "PREFLIGHT_FAILED rc=`preflight_rc' : no regression attempted."
    log close
    exit `preflight_rc'
}
do "stata/00_model_helpers.do"
postfile digital_post str32 model str32 status double rc N Ng instruments sargan_p hansen_p ar1_p ar2_p using "outputs/stata/model_status.dta", replace
capture noisily do "stata/02_pre_estimation.do"
local pretests_rc = _rc
display as result "STATA_PRETEST_SCRIPT_RETURN_CODE=" `pretests_rc'
capture noisily do "stata/03_growth_models.do"
local growth_rc = _rc
if `growth_rc' != 0 {
    display as error "GROWTH_SCRIPT_INTERNAL_FAILURE rc=`growth_rc'"
}
capture noisily do "stata/04_productivity_models.do"
local productivity_rc = _rc
if `productivity_rc' != 0 {
    display as error "PRODUCTIVITY_SCRIPT_INTERNAL_FAILURE rc=`productivity_rc'"
}
do "stata/05_post_estimation_and_export.do"
display as result "RUN_ALL_SCRIPT_COMPLETED. This does not mean GMM is scientifically valid."
display as result "CHECK model_status.csv and the full Stata log before reporting any model."
log close
