dir.create("outputs", showWarnings = FALSE)
stopifnot(requireNamespace("plm", quietly=TRUE))
txt <- c(
  paste0("R_VERSION=", R.version.string),
  paste0("PLM_VERSION=", as.character(packageVersion("plm"))),
  paste0("PDYNMC_AVAILABLE=", requireNamespace("pdynmc", quietly=TRUE)),
  "STATUS=runtime_check_only; NO_ESTIMATES_COMPUTED"
)
writeLines(txt, "outputs/r_environment.txt")
cat(paste(txt, collapse="\n"), "\n")
