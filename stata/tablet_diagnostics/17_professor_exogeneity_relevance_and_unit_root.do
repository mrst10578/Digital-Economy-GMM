* Econometric science gate 1+2 for two original professor System GMM equations.
* Supplementary diagnostics only, not a search for valid p-values.
* Original workbook, GMM specifications, instrument lag windows, and main remain unchanged.
version 16.0
clear all
set more off
cd "D:/Digital_Economy_QA_20261016"
sysdir set PLUS "D:/Digital_Economy_Stata_Ready/plus/"
capture noisily mata: mata mlib index
capture mkdir "outputs/professor"
capture log close _all
log using "outputs/professor/INSTRUMENT_RELEVANCE_AND_PRODUCTIVITY_UNITROOT.log", text replace
do "stata/01_environment_and_data.do"
assert _N == 846
postfile relevance str24 instrument str32 diff_target double rc N groups b_lag2 se_lag2 p_lag2 F_cluster r2_year_adjusted raw_corr using "outputs/professor/lag2_descriptive_relevance.dta", replace
foreach v in Growth ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD {
    local lhs "D.`v'"
    if inlist("`v'","Growth","ln_Productivity") local lhs "D.L.`v'"
    display as result "RELEVANCE_START instrument=`v' target=`lhs' with full set of calendar indicators"
    capture noisily regress `lhs' L2.`v' i.Year, vce(cluster panel_id)
    local rc=_rc
    if `rc'==0 {
        local n=e(N)
        local b=_b[L2.`v']
        local se=_se[L2.`v']
        local r2=e(r2)
        capture noisily test L2.`v'
        local testrc=_rc
        local p=.
        local f=.
        if `testrc'==0 {
           local p=r(p)
           local f=r(F)
        }
        quietly correlate L2.`v' `lhs' if e(sample)
        local corr=r(rho)
        post relevance ("`v'") ("`lhs'") (0) (`n') (47) (`b') (`se') (`p') (`f') (`r2') (`corr')
        display as result "RELEVANCE_OK instrument=`v' n=`n' b=`b' p=`p' pair_corr=`corr'"
    }
    else {
        post relevance ("`v'") ("`lhs'") (`rc') (.) (.) (.) (.) (.) (.) (.) (.)
        display as error "RELEVANCE_FAILED instrument=`v' rc=`rc'"
    }
}
postclose relevance
preserve
use "outputs/professor/lag2_descriptive_relevance.dta", clear
export delimited using "outputs/professor/lag2_descriptive_relevance.csv", replace
count if rc!=0
display as result "RELEVANCE_FAILURE_COUNT=" r(N)
count
display as result "RELEVANCE_TOTAL=" r(N)
list, noobs abbreviate(24)
restore
display as result "RELEVANCE_DIAGNOSTICS_END: descriptive, univariate conditional on years; not a first-stage identification test"
generate double D_ln_Productivity=D.ln_Productivity
postfile ur str24 variable str12 form str6 test str8 deterministic double lag rc p1 p2 using "outputs/professor/productivity_unitroot_grid.dta", replace
foreach variable in ln_Productivity D_ln_Productivity {
    local transform "level"
    if "`variable'"=="D_ln_Productivity" local transform "difference"
    foreach lag in 1 2 {
        foreach deterministic in drift trend {
            local trendopt ""
            if "`deterministic'"=="trend" local trendopt "trend"
            display as result "UNITROOT_START variable=`variable' type=IPS deterministic=`deterministic' lags=`lag'"
            capture noisily xtunitroot ips `variable', lags(`lag') `trendopt'
            local err=_rc
            local p1=.
            local p2=.
            if `err'==0 {
                local p1=r(p_wtbar)
                local p2=r(p_tbar)
                return list
            }
            post ur ("`variable'") ("`transform'") ("IPS") ("`deterministic'") (`lag') (`err') (`p1') (`p2')
            display as result "UNITROOT_RESULT variable=`variable' test=IPS deterministic=`deterministic' lag=`lag' rc=`err' p_wtbar=`p1' p_tbar=`p2'"
            display as result "UNITROOT_START variable=`variable' type=FisherADF deterministic=`deterministic' lags=`lag'"
            capture noisily xtunitroot fisher `variable', dfuller lags(`lag') `trendopt'
            local err=_rc
            local p1=.
            local p2=.
            if `err'==0 {
                local p1=r(p_P)
                local p2=r(p_Z)
                return list
            }
            post ur ("`variable'") ("`transform'") ("Fisher") ("`deterministic'") (`lag') (`err') (`p1') (`p2')
            display as result "UNITROOT_RESULT variable=`variable' test=Fisher deterministic=`deterministic' lag=`lag' rc=`err' p_inverse_chi2=`p1' p_Z=`p2'"
        }
    }
}
postclose ur
preserve
use "outputs/professor/productivity_unitroot_grid.dta", clear
export delimited using "outputs/professor/productivity_unitroot_grid.csv", replace
count if rc!=0
display as result "UNITROOT_FAILURE_COUNT=" r(N)
count
display as result "UNITROOT_TOTAL_COUNT=" r(N)
list, noobs abbreviate(21)
restore
display as result "TWO_SCIENCE_GATES_COMPLETE: 8 instrument proxy relevance checks; 16 first-generation unit-root specifications; existing R CIPS must be interpreted separately"
log close
