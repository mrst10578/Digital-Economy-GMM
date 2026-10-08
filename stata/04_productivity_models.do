* ln(Productivity) is logged, predictors are in levels (semi-elasticities, not elasticities).
capture noisily xtabond2 ln_Productivity L.ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies, gmmstyle(ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD, lag(2 3) collapse) ivstyle($digital_year_dummies, equation(diff)) noleveleq robust small
if !_rc {
 estimates store DIG_PRODUCTIVITY_DIF
 display as result "PRODUCTIVITY_DIFFERENCE_GMM estimated; review diagnostics"
 ereturn list
}
else display as error "PRODUCTIVITY_DIFFERENCE_GMM_FAILED"
capture noisily xtabond2 ln_Productivity L.ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies, gmmstyle(ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD, lag(2 3) collapse) ivstyle($digital_year_dummies) twostep robust small
if !_rc {
 estimates store DIG_PRODUCTIVITY_SYS
 display as result "PRODUCTIVITY_SYSTEM_GMM estimated; review diagnostics"
 ereturn list
}
else display as error "PRODUCTIVITY_SYSTEM_GMM_FAILED"
