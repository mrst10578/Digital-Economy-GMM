* Independent time-window sensitivity for professor's original two System GMM equations.
* Pre-pandemic 2005-2019 window is defined by calendar, never by outcomes or p-values.
* Original full 2005-2022 evidence stays unchanged.
version 16.0
clear all
set more off
cd "D:/Digital_Economy_QA_20261016"
sysdir set PLUS "D:/Digital_Economy_Stata_Ready/plus/"
capture noisily mata: mata mlib index
capture mkdir "outputs/professor"
capture log close _all
log using "outputs/professor/PROFESSOR_PREPANDEMIC_SYSTEM_GMM.log", text replace
capture noisily do "stata/01_environment_and_data.do"
local ready_rc = _rc
if `ready_rc' != 0 {
    display as error "PREPANDEMIC_PREFLIGHT_FAILED rc=`ready_rc'"
    log close
    exit `ready_rc'
}
quietly keep if Year <= 2019
isid ISO3 Year
bysort ISO3: assert _N == 15
assert _N == 705
quietly xtset panel_id Year
capture drop pyd_*
quietly tab Year, generate(pyd_)
* Same non-redundant year basis rule: 2005 base, omit 2008 alias.
global pre_years "pyd_2-pyd_3 pyd_5-pyd_15"
postfile pp str20 outcome double rc N Ng instruments lag_b lag_se internet_b internet_se internet_p sargan_p hansen_p ar1_p ar2_p diffh_dep_level_p diffh_controls_p using "outputs/professor/prepandemic_system_gmm_stats.dta", replace
display as result "PREPANDEMIC_SAMPLE=2005-2019 countries=47 raw_country_years=705"
foreach y in Growth ln_Productivity {
    display as result "PREPANDEMIC_START outcome=`y' two-step System GMM, fixed lag(2 2) collapsed"
    capture noisily xtabond2 `y' L.`y' Internet Broadband ICT_Exports Unemployment Inflation RnD $pre_years, gmmstyle(`y', lag(2 2) collapse split) gmmstyle(Internet Broadband ICT_Exports RnD, lag(2 2) collapse) gmmstyle(Unemployment Inflation, lag(2 2) collapse) ivstyle($pre_years) twostep robust small artests(2)
    local rc = _rc
    if `rc' == 0 {
        local n = e(N)
        local ng = e(N_g)
        local j = e(j)
        local bl = _b[L.`y']
        local sl = _se[L.`y']
        local bi = _b[Internet]
        local si = _se[Internet]
        local pi = 2*ttail(`ng'-1,abs(`bi'/`si'))
        local sg = e(sarganp)
        local ha = e(hansenp)
        local a1 = e(ar1p)
        local a2 = e(ar2p)
        local dhy = .
        local dhc = .
        capture matrix __dh = e(diffsargan)
        if _rc == 0 {
            if rowsof(__dh)>=5 & colsof(__dh)>=4 {
                local dhy = el(__dh,5,3)
                local dhc = el(__dh,5,4)
            }
        }
        post pp ("`y'") (0) (`n') (`ng') (`j') (`bl') (`sl') (`bi') (`si') (`pi') (`sg') (`ha') (`a1') (`a2') (`dhy') (`dhc')
        display as result "PREPANDEMIC_OK outcome=`y' N=`n' Ng=`ng' instruments=`j' bInternet=`bi' Hansen=`ha' AR1=`a1' AR2=`a2' DHlevel=`dhy'"
    }
    else {
        post pp ("`y'") (`rc') (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.)
        display as error "PREPANDEMIC_FAILED outcome=`y' rc=`rc'"
    }
}
postclose pp
preserve
use "outputs/professor/prepandemic_system_gmm_stats.dta", clear
export delimited using "outputs/professor/prepandemic_system_gmm_stats.csv", replace
count if rc != 0
display as result "PREPANDEMIC_FAILURE_COUNT=" r(N)
count
display as result "PREPANDEMIC_TOTAL_COUNT=" r(N)
list, noobs abbreviate(20)
restore
display as result "PREPANDEMIC_RUN_COMPLETE: model sensitivity only, not proof of valid instruments or spillovers"
log close
