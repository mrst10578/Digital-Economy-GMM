* Integrate recently committed production do-files without repeating prior IPS/Fisher.
* All 16 original and revised WDI pretests were already run in real Stata.
version 16.0
clear all
set more off
cd "D:/Digital_Economy_Stata_Integrated_FullRank"
sysdir set PLUS "D:/Digital_Economy_Stata_Ready/plus/"
capture noisily mata: mata mlib index
capture mkdir "outputs"
capture mkdir "outputs/stata"
capture log close _all
log using "outputs/stata/FULL_RANK_INTEGRATION_REAL.log", text replace
display "INTEGRATION_RESEARCH_BRANCH=research/digital-economy-estimation-audit-20261008"
capture noisily do "stata/01_environment_and_data.do"
local preflight_rc=_rc
if `preflight_rc'!=0 {
    display as error "INTEGRATION_DATA_PREFLIGHT_FAILED rc=`preflight_rc'"
    log close
    exit `preflight_rc'
}
do "stata/00_model_helpers.do"
postfile digital_post str32 model str32 status double rc N Ng instruments sargan_p hansen_p ar1_p ar2_p using "outputs/stata/model_status.dta", replace
capture noisily do "stata/03_growth_models.do"
local growth_rc=_rc
capture noisily do "stata/04_productivity_models.do"
local prod_rc=_rc
do "stata/05_post_estimation_and_export.do"
display "INTEGRATION_GROWTH_SCRIPT_RC=" `growth_rc'
display "INTEGRATION_PROD_SCRIPT_RC=" `prod_rc'
display "INTEGRATION_FULL_RANK_EXECUTION_COMPLETED"
log close
