# Install matrix and reproducibility

Research scope: **digital only**. This is not a shared multi-study runner.

## GitHub Actions (recommended for Android-only access)
- Python 3.11 on `ubuntu-24.04`; `pip install -r requirements-python.txt` (pandas, numpy, scipy, statsmodels, linearmodels, openpyxl, pytest).
- R: `sudo apt-get install -y r-base r-cran-plm r-cran-lmtest r-cran-sandwich`; `plm::pgmm`, `plm::mtest`, `plm::sargan`, `plm::purtest` are intended for subsequent empirical scripts. The `pdynmc` package is **optional** and must be version-tested before adoption.
- gretl: `sudo apt-get install -y gretl`; verify `gretlcli`, then use `dpanel` only once estimator/instruments are agreed.
- Stata is proprietary; NOT installed here. Use a licensed Windows/Linux/Mac installation tomorrow, and install `xtabond2` from SSC when available.

## Termux controller (optional)
```sh
pkg update
pkg install git python
# Use your GitHub web app or an authorized gh CLI to dispatch workflows.
# Actual R/gretl number-crunching stays in GitHub Actions.
```
Do not assume the Android Termux ARM packages work the same as Ubuntu runner builds.

## Reproducibility policy
Currently CI validates only software availability and synthetic scaffold tests. Do not label status=waiting_for_source_files as a successful data audit. Save library versions, dataset checksum (not dataset itself in public), exact specifications and failed runs when real analyses start. Do not manufacture Stata output.

## Data privacy
Repository visibility is currently PUBLIC. All supplied Word/Excel research materials and email attachments stay out of Git history. Keep `data/raw/`, `data/processed/` and `outputs/` ignored. Prefer a private repository before adding non-public data and never use public CI artifacts for confidential datasets.
