# Digital Economy and Technology Spillovers

Independent research repository. This project must **not** import data, scripts, estimates, outputs or issue workflows from the other study or Shakhsi2/3/4.

## Current state
**SCAFFOLD ONLY.** No source dataset, R/Gretl/Stata estimates, p-values, Hansen/AR tests or verified findings have been generated here. The original research Excel/Word documents must be supplied in the new chat and audited before estimation.

## Project scope
Country panels, 2005–2022; outcomes GDP growth and labour productivity. Expected 47 countries / 846 rows (verify from source, not guaranteed).

Expected outcomes: `Growth`, `Productivity`. Expected predictors: `Internet`, `Broadband`, `ICT_Exports`, `Unemployment`, `Inflation`, `RnD`.

## Quick start
1. Read the separate **MASTER_PROMPT** supplied with this study's research ZIP.
2. Place the source Excel files under `data/raw/` **locally**, or use a private controlled artifact store. **This GitHub repository is public. Never commit raw source workbooks or personal emails.**
3. Run the Python verification and inspect `outputs/preflight_status.json`.
4. GitHub Actions workflows provide independent environment checks for Python, R, and gretl. Environment checks are **not** econometric estimation.
5. A real licensed Stata session is needed tomorrow for `xtabond2` confirmation and authentic `.log` outputs. Stata results remain pending until executed.

## Install/runtime
- GitHub Actions: Ubuntu runner, Python 3.11, R via apt `r-base r-cran-plm r-cran-lmtest r-cran-sandwich`, and `gretl` via apt. `pdynmc` is optional only after compatibility checks.
- Python: `python -m pip install -r requirements-python.txt`.
- Termux is a controller; commands run through GitHub Actions. Do **not** assume R/Gretl on Android ARM is equivalent to tested Linux CI.

See `docs/ENVIRONMENT.md`, `docs/PROJECT_STATUS.md` and `docs/STATA_HANDOFF.md` before taking any estimates as final.
