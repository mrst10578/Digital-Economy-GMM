# Digital Economy & Technology Spillovers

**One research project per repository.** This repo is dedicated exclusively to GDP growth and labor productivity (47 expected countries, 2005–2022; verify before estimation). It is independent of the other study and of Shakhsi2/3/4.

## Original source package imported from Dropbox

The full ZIP is committed at [research-packages/Digital_Economy_Ready_Package.zip](research-packages/Digital_Economy_Ready_Package.zip). All eight source package files have been unpacked. The original Word manuscript, Excel workbook and dictionary, instructor screenshots, extra email note and SHA256 manifest are in [sources/](sources/). The full instruction prompt is in the repository root (MASTER_PROMPT*.md). The workbook is also at [data/raw/Balanced_Panel_Data.xlsx](data/raw/) for automated checks.

**Public repository:** these supplied research inputs were explicitly authorized for publication by the user. Do not add personal credentials, hidden API keys, or licensing information.

## Current workflow state

- Python, R/plm and gretl installation/runtime checks were configured separately in GitHub Actions.
- [Validate imported research dataset and build Stata DTA](.github/workflows/05-validate-research-data.yml) checks the real input and creates a `stata_ready.dta` downloadable artifact (if successful).
- Original data are present; **Python OLS/FE, R IPS/Fisher/CIPS/CD + Difference/System GMM, and gretl dpanel were actually executed and audited**. Multiple specification diagnostics remain unfavorable or inconclusive. **Difference-in-Hansen and licensed Stata estimates have NOT been completed**, and no causal interpretation has been accepted.
- The original Stata placeholder has been replaced by staged xtabond2 do-files, but **the code has not yet been executed on Stata**. Use the GitHub Actions one-click laptop handoff ZIP.

## Tools

Python: `pip install -r requirements-python.txt`. R: `r-base r-cran-plm r-cran-lmtest r-cran-sandwich`; gretl: `gretl`. The GitHub Actions workflows test the tools on Ubuntu without requiring a PC or Android installation.

## Continue in a new chat

Start with [MASTER_PROMPT](./) and the study's `sources/` folder; audit independently, build appropriate estimators, and preserve all unsuccessful and incompatible model specifications in reports. See `docs/STATA_HANDOFF.md`. Never mislabel R/Python results as authentic Stata output.

## Research outputs (branch only)

See [Persian final report](docs/FINAL_REPORT_FA.md), [full defense guide](docs/DEFENSE_GUIDE_FA.md), [model pre-specification](docs/MODEL_SPECIFICATION.md), [Iran-peers design](docs/IRAN_PEERS_FA.md), and [current project status](docs/PROJECT_STATUS.md). New Actions workflows 06-12 produce source review logs, actual Python/R/gretl statistical outputs, WDI comparisons, Persian report PDF/HTML files and a one-click Stata laptop ZIP. **No claim is made that the GMM diagnostics establish a valid causal model or that Stata has been run.**
