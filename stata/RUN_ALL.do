* Digital economy real-data Stata run, on a licensed compatible computer only.
version 16.0
clear all
set more off
capture mkdir "outputs"
capture mkdir "outputs/stata"
capture log close _all
log using "outputs/stata/RUN_ALL_REAL_STATA.log", text replace
display as text "PROJECT=Digital Economy; Stata " c(stata_version)
do "stata/01_environment_and_data.do"
do "stata/02_pre_estimation.do"
do "stata/03_growth_models.do"
do "stata/04_productivity_models.do"
display as result "STATA_SCRIPT_FINISHED: inspect diagnostics and failed model markers"
log close
