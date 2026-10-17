#!/usr/bin/env Rscript
# Phase 1, independent noncausal complementary estimates; historical workbook only.
# No data augmentation, no specification selection by statistical significance.
suppressPackageStartupMessages({library(readxl);library(plm)})
root <- normalizePath(getwd())
raw <- file.path(root, "data/raw/Balanced_Panel_Data.xlsx")
expected <- "474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b"
actual <- unname(tools::md5sum(raw)) # not source evidence: authoritative SHA checked by the driver and log
stopifnot(file.exists(raw))
x <- as.data.frame(readxl::read_excel(raw))
stopifnot(nrow(x)==846,nrow(unique(x[,c("ISO3","Year")]))==846,length(unique(x$ISO3))==47,length(unique(x$Year))==18,all(x$Productivity>0))
x <- x[order(x$ISO3,x$Year),]
x$ln_Productivity <- log(x$Productivity)
for (v in c("ln_Productivity","Internet","Broadband","ICT_Exports","Unemployment","Inflation","RnD")) {
  x[[paste0("D_",v)]] <- ave(x[[v]],x$ISO3,FUN=function(y) c(NA_real_,diff(y)))
}
designs <- list(
  Growth = c("Internet","Broadband","ICT_Exports","Unemployment","Inflation","RnD"),
  ln_Productivity = c("Internet","Broadband","ICT_Exports","Unemployment","Inflation","RnD"),
  D_ln_Productivity = c("D_Internet","D_Broadband","D_ICT_Exports","D_Unemployment","D_Inflation","D_RnD")
)
out <- "outputs/phase1_robust_twfe_20261017"
dir.create(out,recursive=TRUE,showWarnings=FALSE)
coefs <- list(); summary <- list()
for (label in names(designs)) {
  terms <- designs[[label]]
  m <- plm(as.formula(paste0(label,"~",paste(terms,collapse="+"))),data=x,index=c("ISO3","Year"),model="within",effect="twoways",na.action=na.omit)
  b <- coef(m)
  stopifnot(length(b)==6,all(terms %in% names(b)))
  covs <- list()
  for(k in c(1L,2L,3L)) {
    covs[[paste0("dk",k)]] <- vcovSCC(m,type="HC1",maxlag=k,inner="cluster")
  }
  covs$cluster <- vcovHC(m,method="arellano",type="HC1",cluster="group")
  p_c <- function(est,se) 2*pt(-abs(est/se),df=46)
  cd <- tryCatch(pcdtest(m,test="cd"),error=function(e) NULL)
  wald <- function(v) {
    if(any(!is.finite(v))) return(NA_real_)
    z <- b[terms[1:3]]
    V <- v[terms[1:3],terms[1:3],drop=FALSE]
    stat <- as.numeric(t(z)%*%solve(V,z))
    pchisq(stat,df=3,lower.tail=FALSE)
  }
  for (term in terms) {
    row <- data.frame(model=label,term=term,b=unname(b[[term]]),
      se_cluster=sqrt(covs$cluster[term,term]),
      p_cluster=p_c(b[[term]],sqrt(covs$cluster[term,term])),
      se_dk_lag1=sqrt(covs$dk1[term,term]),
      p_dk_lag1=2*pnorm(-abs(b[[term]]/sqrt(covs$dk1[term,term]))),
      se_dk_lag2=sqrt(covs$dk2[term,term]),
      p_dk_lag2=2*pnorm(-abs(b[[term]]/sqrt(covs$dk2[term,term]))),
      se_dk_lag3=sqrt(covs$dk3[term,term]),
      p_dk_lag3=2*pnorm(-abs(b[[term]]/sqrt(covs$dk3[term,term])))
    )
    coefs[[length(coefs)+1L]] <- row
  }
  # CD is descriptive: its distribution under short T and two-way within adjustment is limited.
  stat <- if(is.null(cd)) NA_real_ else unname(cd$statistic)
  cd_p <- if(is.null(cd)) NA_real_ else unname(cd$p.value)
  summary[[length(summary)+1L]] <- data.frame(model=label,N=nobs(m),countries=47,source_start=2005,
    source_end=2022,within_r2=unname(summary(m)$r.squared[1]),
    joint_p_cluster=wald(covs$cluster),joint_p_dk_lag1=wald(covs$dk1),
    joint_p_dk_lag2=wald(covs$dk2),joint_p_dk_lag3=wald(covs$dk3),
    residual_cd_stat=stat,residual_cd_p=cd_p)
  cat(sprintf("TWFE_OK model=%s N=%s CD=%.7g CDp=%.7g WaldDK2p=%.7g\n",label,nobs(m),stat,cd_p,wald(covs$dk2)))
}
coeff <- do.call(rbind,coefs)
summ <- do.call(rbind,summary)
stopifnot(nrow(coeff)==18,nrow(summ)==3,all(is.finite(coeff$b)),all(is.finite(coeff$se_dk_lag2)))
write.csv(coeff,file.path(out,"TWFE_3_MODELS_COEFFICIENTS.csv"),row.names=FALSE,na="")
write.csv(summ,file.path(out,"TWFE_3_MODELS_DIAGNOSTICS.csv"),row.names=FALSE,na="")
cat("TWFE_PHASE1_ORIGINAL_DATA_NO_CAUSAL_VALIDATION_PASS\n")
