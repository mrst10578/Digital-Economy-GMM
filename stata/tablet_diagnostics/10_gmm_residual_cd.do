* Native Stata residual dependence diagnostic after real Difference GMM.
* For both original outcomes, use the same full-rank time-basis & lagged internal IVs.
* This probes residual dependence; not proof of instrument exogeneity or causality.
version 16.0
clear all
set more off
cd "D:/Digital_Economy_QA_20261016"
sysdir set PLUS "D:/Digital_Economy_Stata_Ready/plus/"
capture noisily mata: mata mlib index
capture mkdir "outputs/scientific"
capture log close _all
log using "outputs/scientific/GMM_RESIDUAL_CD.log", replace text
do "stata/01_environment_and_data.do"
postfile cdx str20 outcome double rc N groups years cd_stat cd_p using "outputs/scientific/gmm_residual_cd.dta", replace
foreach y in Growth ln_Productivity {
    display "GMM_RESID_CD_START outcome=`y'"
    capture noisily xtabond2 `y' L.`y' Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies_diff, gmmstyle(`y' Internet Broadband ICT_Exports Unemployment Inflation RnD, lag(2 3) collapse) ivstyle($digital_year_dummies_diff, equation(diff)) noleveleq robust small artests(2)
    local rc = _rc
    if `rc' == 0 {
        preserve
        quietly generate byte __sample = e(sample)
        capture noisily predict double __err if __sample, residuals
        local predict_rc = _rc
        if `predict_rc' == 0 {
            quietly keep if __sample & !missing(__err)
            quietly keep Year panel_id __err
            quietly reshape wide __err, i(Year) j(panel_id)
            quietly ds __err*
            local vars `r(varlist)'
            mata: X = st_data(., tokens(st_local("vars")))
            mata: R = correlation(X)
            mata: N = cols(X)
            mata: T = rows(X)
            mata: cdstat = sqrt(2*T/(N*(N-1))) * (sum(vec(R))-N)/2
            mata: st_numscalar("__gmcd_stat", cdstat)
            mata: st_numscalar("__gmcd_p", 2*normal(-abs(cdstat)))
            mata: st_numscalar("__gmcd_n", N)
            mata: st_numscalar("__gmcd_t", T)
            post cdx ("`y'") (0) (__gmcd_n*__gmcd_t) (__gmcd_n) (__gmcd_t) (__gmcd_stat) (__gmcd_p)
            display as result "GMM_RESID_CD_OK outcome=`y' N=" __gmcd_n " T=" __gmcd_t " statistic=" __gmcd_stat " p=" __gmcd_p
        }
        else {
            post cdx ("`y'") (`predict_rc') (.) (.) (.) (.) (.)
            display as error "GMM_RESID_CD_PREDICT_FAILED outcome=`y' rc=`predict_rc'"
        }
        restore
    }
    else {
        post cdx ("`y'") (`rc') (.) (.) (.) (.) (.)
        display as error "GMM_RESID_CD_EST_FAILED outcome=`y' rc=`rc'"
    }
}
postclose cdx
preserve
use "outputs/scientific/gmm_residual_cd.dta", clear
export delimited using "outputs/scientific/gmm_residual_cd.csv", replace
list, noobs
restore
display "GMM_RESIDUAL_CD_COMPLETE: descriptive diagnostic only"
log close
