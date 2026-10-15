* Non-redundant year-indicator basis, exact historic specification.
* Replaces only dummy columns that Stata previously dropped as collinear.
* Untouched source panel, outcomes, controls, lags, collapse, robust, artests(2).
version 16.0
clear all
set more off
cd "D:/Digital_Economy_Stata_Ready"
sysdir set PLUS "D:/Digital_Economy_Stata_Ready/plus/"
capture noisily mata: mata mlib index
capture mkdir "outputs/diagnostics"
capture log close _all
log using "outputs/diagnostics/FULL_RANK_ALL_MODELS.log", text replace
use "data/processed/stata_ready.dta", clear
isid ISO3 Year
capture confirm variable panel_id
if _rc encode ISO3, generate(panel_id)
xtset panel_id Year
capture drop yd_*
quietly tab Year, generate(yd_)
global diff_year_basis "yd_2-yd_16 yd_18"
global sys_year_basis "yd_2-yd_3 yd_5-yd_18"
which xtabond2
postfile basis str32 model double rc N Ng instruments sargan_p hansen_p ar1_p ar2_p b_internet using "outputs/diagnostics/full_rank_all_status.dta", replace
capture program drop _rank_save
program define _rank_save
    syntax , NAME(string) RC(integer)
    if `rc' == 0 {
        post basis ("`name'") (0) (e(N)) (e(N_g)) (e(j)) (e(sarganp)) (e(hansenp)) (e(ar1p)) (e(ar2p)) (_b[Internet])
        display "FULL_RANK_ESTIMATED=`name' instruments=" e(j) " groups=" e(N_g)
    }
    else {
        post basis ("`name'") (`rc') (.) (.) (.) (.) (.) (.) (.) (.)
        display as error "FULL_RANK_FAILED=`name' rc=`rc'"
    }
end
display "FULL_RANK_MODEL_START=GROWTH_DIFF_L23"
capture noisily xtabond2 Growth L.Growth Internet Broadband ICT_Exports Unemployment Inflation RnD $diff_year_basis, gmmstyle(Growth Internet Broadband ICT_Exports Unemployment Inflation RnD, lag(2 3) collapse) ivstyle($diff_year_basis, equation(diff)) noleveleq robust small artests(2)
local rc=_rc
_rank_save, name(GROWTH_DIFF_L23) rc(`rc')
display "FULL_RANK_MODEL_START=GROWTH_SYS_L22"
capture noisily xtabond2 Growth L.Growth Internet Broadband ICT_Exports Unemployment Inflation RnD $sys_year_basis, gmmstyle(Growth, lag(2 2) collapse split) gmmstyle(Internet Broadband ICT_Exports RnD, lag(2 2) collapse) gmmstyle(Unemployment Inflation, lag(2 2) collapse) ivstyle($sys_year_basis) twostep robust small artests(2)
local rc=_rc
_rank_save, name(GROWTH_SYS_L22) rc(`rc')
display "FULL_RANK_MODEL_START=GROWTH_SYS_L23_AUDIT"
capture noisily xtabond2 Growth L.Growth Internet Broadband ICT_Exports Unemployment Inflation RnD $sys_year_basis, gmmstyle(Growth, lag(2 3) collapse split) gmmstyle(Internet Broadband ICT_Exports RnD, lag(2 3) collapse) gmmstyle(Unemployment Inflation, lag(2 3) collapse) ivstyle($sys_year_basis) twostep robust small artests(2)
local rc=_rc
_rank_save, name(GROWTH_SYS_L23_AUDIT) rc(`rc')
display "FULL_RANK_MODEL_START=PROD_DIFF_L23"
capture noisily xtabond2 ln_Productivity L.ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD $diff_year_basis, gmmstyle(ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD, lag(2 3) collapse) ivstyle($diff_year_basis, equation(diff)) noleveleq robust small artests(2)
local rc=_rc
_rank_save, name(PROD_DIFF_L23) rc(`rc')
display "FULL_RANK_MODEL_START=PROD_SYS_L22"
capture noisily xtabond2 ln_Productivity L.ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD $sys_year_basis, gmmstyle(ln_Productivity, lag(2 2) collapse split) gmmstyle(Internet Broadband ICT_Exports RnD, lag(2 2) collapse) gmmstyle(Unemployment Inflation, lag(2 2) collapse) ivstyle($sys_year_basis) twostep robust small artests(2)
local rc=_rc
_rank_save, name(PROD_SYS_L22) rc(`rc')
display "FULL_RANK_MODEL_START=PROD_SYS_L23_AUDIT"
capture noisily xtabond2 ln_Productivity L.ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD $sys_year_basis, gmmstyle(ln_Productivity, lag(2 3) collapse split) gmmstyle(Internet Broadband ICT_Exports RnD, lag(2 3) collapse) gmmstyle(Unemployment Inflation, lag(2 3) collapse) ivstyle($sys_year_basis) twostep robust small artests(2)
local rc=_rc
_rank_save, name(PROD_SYS_L23_AUDIT) rc(`rc')
postclose basis
preserve
use "outputs/diagnostics/full_rank_all_status.dta", clear
sort model
export delimited using "outputs/diagnostics/full_rank_all_status.csv", replace
list, noobs
restore
display "FULL_RANK_ALL_MODELS_COMPLETE"
log close
