* Pre-estimation Stata-native tests. Errors logged but no test fabricated.
version 16.0
xtdescribe
summarize Growth Productivity ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD, detail
pwcorr Growth ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD, sig
regress Growth Internet Broadband ICT_Exports Unemployment Inflation RnD
estat vif
regress ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD
estat vif
* VIF conditioning on country and year indicators is not the same as pooled VIF.
regress Growth Internet Broadband ICT_Exports Unemployment Inflation RnD i.panel_id i.Year
estat vif
* Keep full variable-by-test status. IPS and Fisher assume cross-sectional independence.
foreach v in Growth ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD {
    capture noisily xtunitroot ips `v', lags(1)
    local ipserr = _rc
    display as result "STATA_TEST_STATUS IPS `v' rc=`ipserr'"
    capture noisily xtunitroot fisher `v', dfuller lags(1)
    local fisherr = _rc
    display as result "STATA_TEST_STATUS FISHER `v' rc=`fisherr'"
}
display as text "Cross-sectional dependence/CIPS estimates already run in R. Do NOT mislabel IPS/Fisher as cross-sectionally robust."
