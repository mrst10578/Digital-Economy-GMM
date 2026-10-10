# Reproduce documented old R MadWu discrepancy. Comparison configurations do not justify
# choosing favorable p-values; all tests assume cross-section independence.
dir.create("outputs/r_fisher_forensics",recursive=TRUE,showWarnings=FALSE)
suppressPackageStartupMessages(library(plm))
suppressPackageStartupMessages(library(readxl))
d=as.data.frame(readxl::read_xlsx("data/raw/Balanced_Panel_Data.xlsx"))
d=d[order(d$ISO3,d$Year),]
d$ln_Productivity=log(d$Productivity)
p=plm::pdata.frame(d,index=c("ISO3","Year"))
cat("R",R.version.string,"plm",as.character(packageVersion("plm")),"urca_installed",requireNamespace("urca",quietly=TRUE),"\n")
out=data.frame()
for(spec in c("package_default","MacKinnon1994","MacKinnon1996")){
  tryCatch({
    if(spec=="package_default"){
      fit=plm::purtest(p[["ln_Productivity"]],test="madwu",exo="intercept",lags=1)
    } else {
      fit=plm::purtest(p[["ln_Productivity"]],test="madwu",exo="intercept",
                      lags=1,p.approx=spec)
    }
    val=as.numeric(fit$statistic$statistic)
    prob=as.numeric(fit$statistic$p.value)
    # htest may be in fit$statistic, directly exposing p.value
    if(!length(val)) val=as.numeric(fit$statistic)[1]
    if(!length(prob)) prob=fit$statistic$p.value
    cat("R_FISHER_VARIANT",spec,"statistic",val,"p",prob,"\n")
    cat("R_IDRES_FIELD_NAMES",spec,paste(names(fit$idres),collapse=","),"\n")
    out=rbind(out,data.frame(spec=spec,p_value=prob,statistic=val,status="OK",message="47 countries, intercept, fixed lag=1"))
  },error=function(e){
    cat("R_FISHER_VARIANT_FAILED",spec,conditionMessage(e),"\n")
    out=rbind(out,data.frame(spec=spec,p_value=NA_real_,statistic=NA_real_,
                status="FAILED",message=conditionMessage(e)))
  })
}
write.csv(out,"outputs/r_fisher_forensics/package_approximation_variants.csv",row.names=FALSE)
print(out)
if(sum(out$status=="OK")==0)stop("All forensic R Fisher comparisons failed")
