* Instructor's requested real panel pre-estimation checks.
xtdescribe
summ Growth Productivity ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD, detail
pwcorr Growth ln_Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD, sig
reg Growth Internet Broadband ICT_Exports Unemployment Inflation RnD
estat vif
capture noisily xtunitroot ips Growth, lags(1)
capture noisily xtunitroot fisher Growth, dfuller lags(1)
capture noisily xtunitroot ips ln_Productivity, lags(1)
capture noisily xtunitroot fisher ln_Productivity, dfuller lags(1)
capture noisily xtunitroot ips Internet, lags(1)
capture noisily xtunitroot fisher Internet, dfuller lags(1)
capture noisily xtunitroot ips Broadband, lags(1)
capture noisily xtunitroot fisher Broadband, dfuller lags(1)
capture noisily xtunitroot ips ICT_Exports, lags(1)
capture noisily xtunitroot fisher ICT_Exports, dfuller lags(1)
capture noisily xtunitroot ips Unemployment, lags(1)
capture noisily xtunitroot fisher Unemployment, dfuller lags(1)
capture noisily xtunitroot ips Inflation, lags(1)
capture noisily xtunitroot fisher Inflation, dfuller lags(1)
capture noisily xtunitroot ips RnD, lags(1)
capture noisily xtunitroot fisher RnD, dfuller lags(1)
* CD/CIPS: results from R must be cited separately, not silently substituted.
