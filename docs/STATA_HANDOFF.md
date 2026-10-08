# Stata handoff (tomorrow 08:00)

**Status: scaffold only, not ready for a final GMM run.** The new chat must lock model and instrument specifications and fill `stata/02_models.do` after scientific review.

1. Obtain and install licensed Stata on the laptop, verify actual version and Internet availability for SSC.
2. From project root, after audited Excel is securely available at `data/raw/Balanced_Panel_Data.xlsx`, run `python -m src.python.preflight` and `python -m src.python.to_stata`.
3. In Stata, set working directory to project root and run `do stata/RUN_ALL.do`.
4. On a first installation, manually run `ssc install xtabond2, replace` using official SSC if required. Check any associated package dependencies and report errors.
5. Capture genuine `.log`, Hansen/Sargan/AR and instrument counts after successful execution. Existing placeholder code deliberately exits with error 459 until specification is approved.

Never submit Python/R or invented logs as actual Stata output. All model results currently pending.
