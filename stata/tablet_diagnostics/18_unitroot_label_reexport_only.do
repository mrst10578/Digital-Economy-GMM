version 16.0
set more off
cd "D:/Digital_Economy_QA_20261016"
capture log close _all
log using "outputs/professor/UNITROOT_LABEL_CORRECTION.log", replace text
use "outputs/professor/productivity_unitroot_grid.dta", clear
assert _N == 16
recast str12 form
quietly count if form == "differen"
assert r(N) == 8
replace form = "difference" if form == "differen"
assert form == "level" | form == "difference"
export delimited using "outputs/professor/productivity_unitroot_grid.csv", replace
display "UNITROOT_FORMAT_FIXED=1"
display "UNITROOT_RECORDS_PRESERVED=" _N
log close
