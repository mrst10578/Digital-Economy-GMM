* All six X potentially endogenous: collapsed GMM instruments lags 2:3.
capture noisily xtabond2 Growth L.Growth Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies, gmmstyle(Growth Internet Broadband ICT_Exports Unemployment Inflation RnD, lag(2 3) collapse) ivstyle($digital_year_dummies, equation(diff)) noleveleq robust small
if !_rc {
 estimates store DIG_GROWTH_DIF
 display as result "GROWTH_DIFFERENCE_GMM estimated; inspect AR1 AR2 Hansen and instrument count"
 ereturn list
}
else display as error "GROWTH_DIFFERENCE_GMM_FAILED; do not invent results"
capture noisily xtabond2 Growth L.Growth Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies, gmmstyle(Growth Internet Broadband ICT_Exports Unemployment Inflation RnD, lag(2 3) collapse) ivstyle($digital_year_dummies) twostep robust small
if !_rc {
 estimates store DIG_GROWTH_SYS
 display as result "GROWTH_SYSTEM_GMM estimated, not automatically validated"
 ereturn list
}
else display as error "GROWTH_SYSTEM_GMM_FAILED; do not invent results"
