* Matched-moment identification stress test for the professor's TWO original System GMM outcomes.
* Fixed before estimation. Original system equations and source data never altered.
* Here only the LEVEL EQUATION is removed; lag-2 collapsed instrument categories remain.
* Two-step Diff GMM comparisons do not by themselves test all System GMM level moments.
version 16.0
clear all
set more off
cd "D:/Digital_Economy_QA_20261016"
sysdir set PLUS "D:/Digital_Economy_Stata_Ready/plus/"
capture noisily mata: mata mlib index
capture mkdir "outputs/professor"
capture log close _all
log using "outputs/professor/PROFESSOR_LEVEL_EQUATION_REMOVAL.log", text replace
capture noisily do "stata/01_environment_and_data.do"
local first_rc = _rc
if `first_rc' {
    display as error "LEVEL_REMOVAL_PREFLIGHT_FAILED rc=`first_rc'"
    log close
    exit `first_rc'
}
postfile lev str20 outcome double rc N Ng instruments lag_b lag_se internet_b internet_se internet_p hansen_p sargan_p ar1_p ar2_p using "outputs/professor/level_equation_removal_stats.dta", replace
foreach y in Growth ln_Productivity {
    display as result "LEVEL_REMOVAL_START outcome=`y' fixed collapsed lag2 two-step Difference GMM"
    capture noisily xtabond2 `y' L.`y' Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies_diff, gmmstyle(`y', lag(2 2) collapse) gmmstyle(Internet Broadband ICT_Exports RnD, lag(2 2) collapse) gmmstyle(Unemployment Inflation, lag(2 2) collapse) ivstyle($digital_year_dummies_diff, equation(diff)) noleveleq twostep robust small artests(2)
    local rc = _rc
    if `rc' == 0 {
        local n=e(N)
        local ng=e(N_g)
        local j=e(j)
        local bl=_b[L.`y']
        local sl=_se[L.`y']
        local bi=_b[Internet]
        local si=_se[Internet]
        local pi=2*ttail(`ng'-1,abs(`bi'/`si'))
        local ha=e(hansenp)
        local sa=e(sarganp)
        local a1=e(ar1p)
        local a2=e(ar2p)
        post lev ("`y'") (0) (`n') (`ng') (`j') (`bl') (`sl') (`bi') (`si') (`pi') (`ha') (`sa') (`a1') (`a2')
        display as result "LEVEL_REMOVAL_OK outcome=`y' N=`n' groups=`ng' instruments=`j' lagcoef=`bl' Internet=`bi' Hansen=`ha' AR1=`a1' AR2=`a2'"
    }
    else {
        post lev ("`y'") (`rc') (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.)
        display as error "LEVEL_REMOVAL_FAILED outcome=`y' rc=`rc'"
    }
}
postclose lev
preserve
use "outputs/professor/level_equation_removal_stats.dta", clear
export delimited using "outputs/professor/level_equation_removal_stats.csv", replace
count if rc != 0
display as result "LEVEL_REMOVAL_FAILURES=" r(N)
count
display as result "LEVEL_REMOVAL_COUNT=" r(N)
list, noobs abbreviate(20)
restore
display as result "LEVEL_REMOVAL_FINISHED: diagnostic-only, not approval of Difference/System GMM"
log close
