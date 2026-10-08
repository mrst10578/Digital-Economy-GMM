* Growth: one-step difference 2-3; two-step system lags 2 only primary sensitivity.
* Third specification 2-3 is an AUDIT comparison, not a p-value optimization.
version 16.0
capture noisily xtabond2 Growth L.Growth Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies, gmmstyle(Growth Internet Broadband ICT_Exports Unemployment Inflation RnD, lag(2 3) collapse) ivstyle($digital_year_dummies, equation(diff)) noleveleq robust small artests(2)
local modelrc = _rc
if `modelrc' == 0 {
    digital_success, name(GROWTH_DIFF_L23)
}
else {
    digital_failure, name(GROWTH_DIFF_L23) rc(`modelrc')
}
* Split dependent-variable moment group to request valid subset difference-in-Hansen
* when xtabond2's Mata estimator can actually calculate it.
capture noisily xtabond2 Growth L.Growth Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies, gmmstyle(Growth, lag(2 2) collapse split) gmmstyle(Internet Broadband ICT_Exports RnD, lag(2 2) collapse) gmmstyle(Unemployment Inflation, lag(2 2) collapse) ivstyle($digital_year_dummies) twostep robust small artests(2)
local modelrc = _rc
if `modelrc' == 0 {
    digital_success, name(GROWTH_SYS_L22)
}
else {
    digital_failure, name(GROWTH_SYS_L22) rc(`modelrc')
}
capture noisily xtabond2 Growth L.Growth Internet Broadband ICT_Exports Unemployment Inflation RnD $digital_year_dummies, gmmstyle(Growth, lag(2 3) collapse split) gmmstyle(Internet Broadband ICT_Exports RnD, lag(2 3) collapse) gmmstyle(Unemployment Inflation, lag(2 3) collapse) ivstyle($digital_year_dummies) twostep robust small artests(2)
local modelrc = _rc
if `modelrc' == 0 {
    digital_success, name(GROWTH_SYS_L23_AUDIT)
}
else {
    digital_failure, name(GROWTH_SYS_L23_AUDIT) rc(`modelrc')
}
