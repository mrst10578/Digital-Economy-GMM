* Source DTA comes from this repository's audited workbook.
version 16.0
capture confirm file "data/processed/stata_ready.dta"
if _rc {
    display as error "Missing data/processed/stata_ready.dta. Extract full handoff ZIP first."
    exit 601
}
capture which xtabond2
if _rc {
    display as error "xtabond2 is missing. In licensed Stata: ssc install xtabond2, replace"
    exit 499
}
which xtabond2
use "data/processed/stata_ready.dta", clear
isid ISO3 Year
assert inrange(Year, 2005, 2022)
foreach v of varlist Growth Productivity Internet Broadband ICT_Exports Unemployment Inflation RnD {
    assert !missing(`v')
}
assert Productivity > 0
capture confirm variable ln_Productivity
if _rc {
    generate double ln_Productivity = ln(Productivity)
}
else {
    assert !missing(ln_Productivity)
    assert abs(ln_Productivity - ln(Productivity)) < 1e-7
}
capture confirm variable panel_id
if _rc {
    encode ISO3, generate(panel_id)
}
capture confirm numeric variable panel_id
if _rc {
    display as error "panel_id should be numeric."
    exit 109
}
bysort ISO3: assert _N == 18
xtset panel_id Year
capture drop yd_*
quietly tabulate Year, generate(yd_)
global digital_year_dummies "yd_2-yd_18"
display as result "STATA_DATA_PREFLIGHT_OK n=" _N
display as text "The raw data and two-way time indicators passed structure checks; no GMM was fitted yet."
