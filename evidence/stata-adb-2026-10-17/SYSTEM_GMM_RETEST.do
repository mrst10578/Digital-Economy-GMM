* Two professor-required System GMM equations (authoritative 2-step)
* Plus 1-step sensitivity with IDENTICAL moments, lag2 collapsed, year basis.
* 1-step is NOT replacing professor's 2-step. Never auto-select favorable p.
version 16.0
clear all
set more off
cd "D:/Digital_Economy_Phase1_Retest_20261017"
sysdir set PLUS "D:/Digital_Economy_Stata_Ready/plus/"
capture noisily mata: mata mlib index
capture mkdir "outputs/professor"
capture log close _all
log using "outputs/professor/PROFESSOR_SYSTEM_GMM_FOUR_RUNS.log", text replace
display as result "PROFESSOR_GMM_SOURCE=research/digital-economy-estimation-audit-20261008"
display as result "PROFESSOR_GMM_DATA=original_846_observations_not_WDI_revised"
capture noisily do "stata/01_environment_and_data.do"
if _rc {
    display as error "PROFESSOR_PREFLIGHT_FAILED"
    log close
    exit 459
}
postfile prof str20 outcome str10 method double rc N Ng instruments b_lag se_lag b_internet se_internet p_internet b_broadband se_broadband b_ict se_ict sargan_p hansen_p ar1_p ar2_p diffh_dep_level_p diffh_ctrl_p using "outputs/professor/professor_system_gmm_stats.dta", replace
foreach y in Growth ln_Productivity {
    foreach mode in twostep onestep {
        display as result "PROFESSOR_START outcome=`y' method=`mode'"
        if "`mode'" == "twostep" {
            capture noisily xtabond2 `y' L.`y' Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies_sys, gmmstyle(`y', lag(2 2) collapse split) gmmstyle(Internet Broadband ICT_Exports RnD, lag(2 2) collapse) gmmstyle(Unemployment Inflation, lag(2 2) collapse) ivstyle($digital_year_dummies_sys) twostep robust small artests(2)
        }
        else {
            capture noisily xtabond2 `y' L.`y' Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies_sys, gmmstyle(`y', lag(2 2) collapse split) gmmstyle(Internet Broadband ICT_Exports RnD, lag(2 2) collapse) gmmstyle(Unemployment Inflation, lag(2 2) collapse) ivstyle($digital_year_dummies_sys) robust small artests(2)
        }
        local rc = _rc
        if `rc' == 0 {
            local n = e(N)
            local ng = e(N_g)
            local j = e(j)
            local sarg = e(sarganp)
            local hans = e(hansenp)
            local ar1 = e(ar1p)
            local ar2 = e(ar2p)
            local lag_b = _b[L.`y']
            local lag_se = _se[L.`y']
            local internet_b = _b[Internet]
            local internet_se = _se[Internet]
            local broadband_b = _b[Broadband]
            local broadband_se = _se[Broadband]
            local ict_b = _b[ICT_Exports]
            local ict_se = _se[ICT_Exports]
            local t_internet = `internet_b' / `internet_se'
            local p_internet = 2*ttail(e(N_g)-1, abs(`t_internet'))
            local diffh_dep_level = .
            local diffh_ctrl = .
            capture matrix __prof_dh = e(diffsargan)
            if _rc == 0 {
                if rowsof(__prof_dh) >= 5 & colsof(__prof_dh) >= 4 {
                    local diffh_dep_level = el(__prof_dh,5,3)
                    local diffh_ctrl = el(__prof_dh,5,4)
                }
            }
            post prof ("`y'") ("`mode'") (0) (`n') (`ng') (`j') (`lag_b') (`lag_se') (`internet_b') (`internet_se') (`p_internet') (`broadband_b') (`broadband_se') (`ict_b') (`ict_se') (`sarg') (`hans') (`ar1') (`ar2') (`diffh_dep_level') (`diffh_ctrl')
            capture estimates save "outputs/professor/`y'_`mode'.ster", replace
            display as result "PROFESSOR_OK outcome=`y' method=`mode' N=`n' instruments=`j' Hansen=`hans' AR1=`ar1' AR2=`ar2' DHlevel=`diffh_dep_level'"
        }
        else {
            post prof ("`y'") ("`mode'") (`rc') (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.) (.)
            display as error "PROFESSOR_FAILED outcome=`y' method=`mode' rc=`rc'"
        }
    }
}
postclose prof
preserve
use "outputs/professor/professor_system_gmm_stats.dta", clear
sort outcome method
export delimited using "outputs/professor/professor_system_gmm_stats.csv", replace
list, noobs abbreviate(18)
count if rc!=0
display as result "PROFESSOR_FAILED_COUNT=" r(N)
count
display as result "PROFESSOR_TOTAL_MODELS=" r(N)
restore
display as result "PROFESSOR_GMM_RUN_COMPLETED: two-step primary, one-step sensitivity, no causal acceptance"
log close
