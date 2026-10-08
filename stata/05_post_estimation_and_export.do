* Preserve actually estimated models for verification in licensed Stata.
* xtabond2 diagnostics are printed in the preceding estimation log.
foreach m in DIG_GROWTH_DIF DIG_GROWTH_SYS DIG_PRODUCTIVITY_DIF DIG_PRODUCTIVITY_SYS {
    capture estimates restore `m'
    if !_rc {
        display as result "RESTORED_MODEL: `m'"
        estimates save "outputs/stata/`m'.ster", replace
        ereturn list
    }
    else {
        display as error "NOT_AVAILABLE: `m'"
    }
}
display as text "Read log outputs/stata/RUN_ALL_REAL_STATA.log for Hansen, Sargan, AR(1), AR(2), instrument counts."
