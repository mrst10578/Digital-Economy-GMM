* These are execution statuses only. None of the numeric diagnostics proves validity.
version 16.0
postclose digital_post
preserve
use "outputs/stata/model_status.dta", clear
sort model
export delimited using "outputs/stata/model_status.csv", replace
list, noobs abbreviate(20)
restore
display as result "STATA_STATUS_EXPORT_OK: outputs/stata/model_status.csv"
display as text "Always inspect full RUN_ALL_REAL_STATA.log for warnings, instrument categories, and the real Difference-in-Hansen table."
