# SECOND-WAVE, PREDECLARED ROBUSTNESS TESTS; NO GMM MODEL SELECTION.
# Executable with apt r-cran-plm/readxl/lmtest/sandwich. Every failure logged.
dir.create("outputs/r_robustness",recursive=TRUE,showWarnings=FALSE)
log_file=file("outputs/r_robustness/run.log",open="wt")
sink(log_file,split=TRUE)
on.exit <- function() {while(sink.number()>0) sink();close(log_file)}
suppressPackageStartupMessages(library(plm))
suppressPackageStartupMessages(library(readxl))
suppressPackageStartupMessages(library(lmtest))
suppressPackageStartupMessages(library(sandwich))
cat("TEST_DESIGN_FROZEN BEFORE RESULTS: CIPS drift/trend with lags1/2, level & first difference; two-way-FE DK SE and residual CD; CCE static pooled/mean-group as exploratory only.\n")
cat("R",R.version.string,"PLM",as.character(packageVersion("plm")),"\n")
d=as.data.frame(readxl::read_xlsx("data/raw/Balanced_Panel_Data.xlsx"))
d=d[order(d$ISO3,d$Year),]
stopifnot(nrow(d)==846,length(unique(d$ISO3))==47,!anyDuplicated(d[c("ISO3","Year")]))
stopifnot(all(d$Productivity>0))
d$ln_Productivity=log(d$Productivity)
dependent=c("Growth","ln_Productivity")
vars=c(dependent,"Internet","Broadband","ICT_Exports","Unemployment","Inflation","RnD")
xs=c("Internet","Broadband","ICT_Exports","Unemployment","Inflation","RnD")
for(v in vars){
  d[[paste0("D_",v)]]=ave(d[[v]],d$ISO3,FUN=function(x)c(NA_real_,diff(x)))
}
pdata=plm::pdata.frame(d,index=c("ISO3","Year"),drop.index=FALSE)
unit_tests=data.frame()
for(v in vars){
  for(level in c("level","first_difference")){
    cname=if(level=="level")v else paste0("D_",v)
    for(type in c("drift","trend")){
      for(lag_n in c(1L,2L)){
        label=paste(v,level,type,paste0("lag",lag_n),sep="_")
        result=tryCatch({
          x=plm::cipstest(pdata[[cname]],lags=lag_n,type=type,model="cmg")
          pval=as.numeric(x$p.value)
          stat=as.numeric(x$statistic)[1]
          cat("CIPS_RESULT",label,stat,pval,"\n")
          data.frame(variable=v,transformation=level,test="CIPS",type=type,
                 lags=lag_n,statistic=stat,p_value=pval,
                 status="OK",message="CIPS p may be truncated at table bounds")
        },error=function(e){
          cat("CIPS_FAILURE",label,conditionMessage(e),"\n")
          data.frame(variable=v,transformation=level,test="CIPS",type=type,
                 lags=lag_n,statistic=NA_real_,p_value=NA_real_,
                 status="FAILED",message=conditionMessage(e))
        })
        unit_tests=rbind(unit_tests,result)
      }
    }
  }
}
write.csv(unit_tests,"outputs/r_robustness/cips_level_and_differences.csv",row.names=FALSE)
f_baseline=function(dep,dynamic){
  rhs=if(dynamic)paste(c(paste0("lag(",dep,",1)"),xs),collapse="+")
      else paste(xs,collapse="+")
  as.formula(paste(dep,"~",rhs))
}
diagnostics=data.frame()
for(dep in dependent){
  for(dynamic in c(FALSE,TRUE)){
    label=paste(dep,if(dynamic)"lagged_two_way_FE" else "static_two_way_FE",sep="_")
    tryCatch({
      m=plm::plm(f_baseline(dep,dynamic),data=pdata,model="within",effect="twoways")
      tab=lmtest::coeftest(m,vcov.=plm::vcovSCC(m,type="HC1",maxlag=2))
      write.csv(data.frame(term=rownames(tab),as.data.frame(unclass(tab)),check.names=FALSE),
              paste0("outputs/r_robustness/",label,"_driscoll_kraay.csv"),row.names=FALSE)
      cd=plm::pcdtest(m,test="cd")
      selected=which(rownames(tab)=="Internet")
      intern=if(length(selected)==1L)as.numeric(tab[selected,1]) else NA_real_
      ip=if(length(selected)==1L)as.numeric(tab[selected,4]) else NA_real_
      diagnostics=rbind(diagnostics,data.frame(model=label,method="two-way FE, Driscoll-Kraay SE; descriptive, NOT GMM",
                         sample_n=length(stats::residuals(m)),internet_coef=intern,internet_p=ip,
                         pesaran_CD_stat=as.numeric(cd$statistic),pesaran_CD_p=cd$p.value,status="OK",
                         warning=if(dynamic)"Dynamic FE biased when T limited; DK adjusts uncertainty only"
                           else "Static FE omits dynamic adjustment; DK SE do not resolve endogeneity"))
      cat("FE_DK_REAL",label,"N",length(stats::residuals(m)),
         "Internet",intern,"p",ip,"CD",as.numeric(cd$statistic),"CDp",cd$p.value,"\n")
    },error=function(e){
      cat("FE_DK_FAILED",label,conditionMessage(e),"\n")
      diagnostics=rbind(diagnostics,data.frame(model=label,method="FE DK",sample_n=NA_real_,
                  internet_coef=NA_real_,internet_p=NA_real_,pesaran_CD_stat=NA_real_,
                  pesaran_CD_p=NA_real_,status="FAILED",warning=conditionMessage(e)))
    })
  }
  for(ce in c("p","mg")){
    label=paste(dep,"CCE_static",ce,sep="_")
    tryCatch({
      m=plm::pcce(as.formula(paste(dep,"~",paste(xs,collapse="+"))),
                  data=pdata,model=ce)
      sm=summary(m)
      cf=as.matrix(sm$coefficients)
      write.csv(data.frame(term=rownames(cf),as.data.frame(cf),check.names=FALSE),
                paste0("outputs/r_robustness/",label,"_coefficients.csv"),row.names=FALSE)
      ind=which(rownames(cf)=="Internet")
      beta=if(length(ind)==1L)as.numeric(cf[ind,1]) else NA_real_
      pv=if(length(ind)==1L && ncol(cf)>=4)as.numeric(cf[ind,4]) else NA_real_
      cat("CCE_STATIC",label,"Internet",beta,"p",pv,"\n")
      diagnostics=rbind(diagnostics,data.frame(model=label,method="Common correlated effects STATIC; descriptive, not comparable with dynamic GMM",
                         sample_n=nrow(d),internet_coef=beta,internet_p=pv,
                         pesaran_CD_stat=NA_real_,pesaran_CD_p=NA_real_,status="OK",
                         warning="T=18 and N=47; CCE static is no causal identification or long-run proof"))
    },error=function(e){
      cat("CCE_FAILED",label,conditionMessage(e),"\n")
      diagnostics=rbind(diagnostics,data.frame(model=label,method="CCE static",
                    sample_n=NA_real_,internet_coef=NA_real_,internet_p=NA_real_,
                    pesaran_CD_stat=NA_real_,pesaran_CD_p=NA_real_,status="FAILED",warning=conditionMessage(e)))
    })
  }
}
write.csv(diagnostics,"outputs/r_robustness/robustness_models.csv",row.names=FALSE)
cat("SECOND_WAVE_FINISHED testrows",nrow(unit_tests),"success_cips",sum(unit_tests$status=="OK"),
    "models",nrow(diagnostics),"success_models",sum(diagnostics$status=="OK"),"\n")
if(sum(unit_tests$status=="OK")==0)stop("No new unit root test succeeded")
if(sum(diagnostics$status=="OK")==0)stop("No new robust baseline succeeded")
