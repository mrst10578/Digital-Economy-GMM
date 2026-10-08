* Productivity: logged outcome, level regressors; X coefficients are semi-elasticities.
* High lag persistence makes System initial-conditions assumptions especially important.
version 16.0
capture noisily xtabond2 ln_Productivity L.ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies, gmmstyle(ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD, lag(2 3) collapse) ivstyle($digital_year_dummies, equation(diff)) noleveleq robust small artests(2)
local modelrc = _rc
if `modelrc' == 0 {
    digital_success, name(PROD_DIFF_L23)
}
else {
    digital_failure, name(PROD_DIFF_L23) rc(`modelrc')
}
capture noisily xtabond2 ln_Productivity L.ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies, gmmstyle(ln_Productivity, lag(2 2) collapse split) gmmstyle(Internet Broadband ICT_Exports RnD, lag(2 2) collapse) gmmstyle(Unemployment Inflation, lag(2 2) collapse) ivstyle($digital_year_dummies) twostep robust small artests(2)
local modelrc = _rc
if `modelrc' == 0 {
    digital_success, name(PROD_SYS_L22)
}
else {
    digital_failure, name(PROD_SYS_L22) rc(`modelrc')
}
capture noisily xtabond2 ln_Productivity L.ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies, gmmstyle(ln_Productivity, lag(2 3) collapse split) gmmstyle(Internet Broadband ICT_Exports RnD, lag(2 3) collapse) gmmstyle(Unemployment Inflation, lag(2 3) collapse) ivstyle($digital_year_dummies) twostep robust small artests(2)
local modelrc = _rc
if `modelrc' == 0 {
    digital_success, name(PROD_SYS_L23_AUDIT)
}
else {
    digital_failure, name(PROD_SYS_L23_AUDIT) rc(`modelrc')
}
