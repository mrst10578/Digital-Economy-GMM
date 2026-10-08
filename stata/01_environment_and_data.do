* Study-specific Stata preflight; run from repo root.
capture confirm file "data/processed/stata_ready.dta"
if _rc {
 display as error "Download audited .dta artifact first."
 exit 601
}
capture which xtabond2
if _rc {
 display as error "Install xtabond2 using: ssc install xtabond2"
 exit 499
}
use "data/processed/stata_ready.dta", clear
isid ISO3 Year
assert inrange(Year,2005,2022)
assert !missing(Growth,Productivity,Internet,Broadband,ICT_Exports,Unemployment,Inflation,RnD)
assert Productivity>0
gen double ln_Productivity=ln(Productivity)
encode ISO3, gen(panel_id)
xtset panel_id Year
tab Year, gen(yd_)
global digital_year_dummies "yd_2-yd_18"
display as result "STATA_PREFLIGHT_OK; this is not estimation."
