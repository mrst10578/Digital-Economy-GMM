* Registers real outcomes only. Models are NEVER marked scientifically accepted here.
capture program drop digital_success
program define digital_success
    version 16.0
    syntax , NAME(string)
    local inst = e(j)
    local groups = e(N_g)
    local verdict "DIAGNOSTIC_HOLD"
    if missing(`inst') | missing(`groups') {
        local verdict "MISSING_INSTRUMENT_DIAGNOSTIC"
    }
    if !missing(`inst') & !missing(`groups') {
        if `inst' >= `groups' local verdict "INSTRUMENTS_GE_GROUPS"
    }
    post digital_post ("`name'") ("`verdict'") (0) (e(N)) (e(N_g)) (e(j)) (e(sarganp)) (e(hansenp)) (e(ar1p)) (e(ar2p))
    display as result "STATA_MODEL_ESTIMATED=`name' status=`verdict' instruments=" e(j) " groups=" e(N_g)
    display as text "Sargan p=" e(sarganp) " Hansen p=" e(hansenp) " AR1 p=" e(ar1p) " AR2 p=" e(ar2p)
    capture noisily estimates store `name'
    capture noisily estimates save "outputs/stata/`name'.ster", replace
    capture noisily matrix list e(diffsargan)
end
capture program drop digital_failure
program define digital_failure
    version 16.0
    syntax , NAME(string) RC(integer)
    post digital_post ("`name'") ("FAILED_EXECUTION") (`rc') (.) (.) (.) (.) (.) (.) (.)
    display as error "STATA_MODEL_FAILED=`name' return_code=`rc'"
end
