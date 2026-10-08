* Stata scaffold: not a finished estimand or validated GMM specification.
version 16.0
set more off
capture mkdir "outputs"
capture log close _all
log using "outputs/stata_preflight.log", text replace
display as result "STATA_RUNTIME=" c(stata_version)
capture confirm file "data/processed/stata_ready.dta"
if _rc {
    display as error "Missing audited data/processed/stata_ready.dta; run conversion only after data audit."
    log close
    exit 601
}
use "data/processed/stata_ready.dta", clear
capture isid ISO3 Year
if _rc {
    display as error "Panel keys ISO3 and Year are not unique. Stop."
    log close
    exit 459
}
capture which xtabond2
if _rc {
    display as error "xtabond2 not installed: run official SSC install after verifying network and compatibility."
    display as text "ssc install xtabond2, replace"
    log close
    exit 499
}
display as result "Preflight complete. Model specification requires scientific review."
log close
do "stata/02_models.do"
