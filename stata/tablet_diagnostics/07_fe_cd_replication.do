* Independent Pesaran (2004) CD diagnostic on exactly balanced FE residuals.
* Pairwise correlation average with time dimension 17/18 and 47 countries.
* Exploratory crosscheck of plm::pcdtest, NOT a replacement for GMM diagnostics.
version 16.0
clear all
set more off
cd "D:/Digital_Economy_Stata_Ready"
capture mkdir "outputs/diagnostics"
capture log close _all
log using "outputs/diagnostics/FE_CD_REPLICATION.log", text replace
use "data/processed/stata_ready.dta", clear
capture confirm variable panel_id
if _rc encode ISO3, gen(panel_id)
xtset panel_id Year
postfile cdp str36 model double N years groups cd_stat cd_p b_internet using "outputs/diagnostics/fe_cd_repl.dta", replace
capture program drop _fe_cd
program define _fe_cd
    version 16.0
    syntax, OUTCOME(name) DYNAMIC(integer)
    preserve
    local rhs ""
    if `dynamic' == 1 local rhs "L.`outcome'"
    quietly regress `outcome' `rhs' Internet Broadband ICT_Exports Unemployment Inflation RnD i.panel_id i.Year
    local num_obs = e(N)
    local beta = _b[Internet]
    gen byte __cd_in = e(sample)
    predict double __cd_r if __cd_in, residuals
    keep if __cd_in
    keep Year panel_id __cd_r
    reshape wide __cd_r, i(Year) j(panel_id)
    quietly ds __cd_r*
    local vars `r(varlist)'
    mata: X = st_data(., tokens(st_local("vars")))
    mata: CC = correlation(X)
    mata: NN = cols(X)
    mata: TT = rows(X)
    mata: sumrho = (sum(vec(CC))-NN)/2
    mata: zcd = sqrt(2*TT/(NN*(NN-1))) * sumrho
    mata: st_numscalar("__cd_z", zcd)
    mata: st_numscalar("__cd_p", 2*normal(-abs(zcd)))
    mata: st_numscalar("__cd_N", NN)
    mata: st_numscalar("__cd_T", TT)
    local label "static"
    if `dynamic' == 1 local label "dynamic"
    post cdp ("`outcome'_`label'") (`num_obs') (__cd_T) (__cd_N) (__cd_z) (__cd_p) (`beta')
    display as result "CD_ESTIMATED outcome=`outcome' model=`label' T=" __cd_T " N=" __cd_N " z=" __cd_z " p=" __cd_p " internet=" `beta'
    restore
end
foreach y in Growth ln_Productivity {
    foreach dynamic in 0 1 {
        capture noisily _fe_cd, outcome(`y') dynamic(`dynamic')
        display as result "CD_RUN_RC y=`y' dynamic=`dynamic' rc=" _rc
    }
}
postclose cdp
preserve
use "outputs/diagnostics/fe_cd_repl.dta", clear
export delimited using "outputs/diagnostics/fe_cd_repl.csv", replace
list, noobs
restore
display as result "CD_TEST_SCRIPT_COMPLETE (descriptive, no causal validation)"
log close
