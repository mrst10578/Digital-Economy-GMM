# Runtime and installation

This repository contains the complete original research files imported from Dropbox into `sources/` and `data/raw/`. Public availability of these specific research inputs was authorized. Do not commit credentials or license information.

## GitHub Actions
1. `01-python-qa.yml`: Python 3.11, pandas/numpy/scipy/statsmodels/linearmodels/openpyxl/pytest and synthetic scaffold tests.
2. `02-r-environment.yml`: Ubuntu apt installs `r-base r-cran-plm r-cran-lmtest r-cran-sandwich`; checks `plm`. Optional `pdynmc` requires separate compatibility testing.
3. `03-gretl-environment.yml`: Ubuntu apt installs `gretl`; verifies `gretlcli`.
4. `05-validate-research-data.yml`: verifies genuine input Excel schema/keys and generates Stata `.dta` artifact.

The `stata_ready.dta` export is a format conversion, not a completed statistical model. GMM packages and settings must be selected based on source-specific methodology and then run and verified independently.

## Android / Termux
```sh
pkg update
pkg install git python
```
Use Termux to control GitHub, not as the primary statistical runtime. Do not assume Linux-x86 builds can be installed into Android ARM. Actual Stata requires a licensed supported host OS.
