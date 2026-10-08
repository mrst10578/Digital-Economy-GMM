# Independent study-specific R econometric analysis (real data, not a smoke test).
# Documents failures instead of silently changing instruments to chase p-values.
dir.create("outputs/r", recursive=TRUE, showWarnings=FALSE)
sink("outputs/r/analysis.log", split=TRUE)
on.exit <- function() { while(sink.number()>0) sink() }
suppressPackageStartupMessages(library(plm))
suppressPackageStartupMessages(library(readxl))
suppressPackageStartupMessages(library(lmtest))
suppressPackageStartupMessages(library(sandwich))
cat("R_VERSION",R.version.string,"\n")
cat("PLM_VERSION",as.character(packageVersion("plm")),"\n")
cat("READXL_VERSION",as.character(packageVersion("readxl")),"\n")
cat("DESIGN_PRESPECIFIED=laged dependent and all six covariates instrumented at lags 2:3; collapsed; two-way year effects.\n")
dat=as.data.frame(readxl::read_xlsx("data/raw/Balanced_Panel_Data.xlsx"))
dat=dat[order(dat$ISO3,dat$Year),]
dat$ln_Productivity=log(dat$Productivity)
stopifnot(nrow(dat)==846, length(unique(dat$ISO3))==47, !anyNA(dat),
          !anyDuplicated(dat[c("ISO3","Year")]),all(is.finite(dat$ln_Productivity)))
p=plm::pdata.frame(dat,index=c("ISO3","Year"),drop.index=FALSE)
vars=c("Growth","ln_Productivity","Internet","Broadband","ICT_Exports",
       "Unemployment","Inflation","RnD")
test_result=data.frame(variable=character(),test=character(),statistic=double(),
                       p_value=double(),status=character(),message=character())
test_run=function(v,label,expr){
    tryCatch({
        x=expr
        cat("PRETEST",v,label,"stat",as.numeric(unlist(x$statistic))[1],"p",x$p.value,"\n")
        data.frame(variable=v,test=label,statistic=as.numeric(unlist(x$statistic))[1],
                   p_value=as.numeric(unlist(x$p.value))[1],status="RAN",message="")
    },error=function(e){
        cat("PRETEST_FAILED",v,label,conditionMessage(e),"\n")
        data.frame(variable=v,test=label,statistic=NA_real_,p_value=NA_real_,
                   status="FAILED",message=conditionMessage(e))
    })
}
for(v in vars){
    test_result=rbind(test_result,
      test_run(v,"IPS_intercept_lag1",plm::purtest(p[[v]],test="ips",exo="intercept",lags=1)),
      test_run(v,"Fisher_MadWu_intercept_lag1",plm::purtest(p[[v]],test="madwu",exo="intercept",lags=1)),
      test_run(v,"CIPS_drift_lag1",plm::cipstest(p[[v]],lags=1,type="drift",model="cmg")))
}
write.csv(test_result,"outputs/r/unit_roots.csv",row.names=FALSE)
spec_x=c("Internet","Broadband","ICT_Exports","Unemployment","Inflation","RnD")
spec_dep=c("Growth","ln_Productivity")
cd_table=data.frame()
for(dep in spec_dep){
    for(method in c("pooling","within")){
        tryCatch({
            model=plm::plm(as.formula(paste(dep,"~ lag(",dep,",1) +",paste(spec_x,collapse="+"))),
                           data=p,model=method,effect=if(method=="within")"twoways" else "individual")
            estimates=lmtest::coeftest(model,vcov.=plm::vcovHC(model,method="arellano",type="HC1",cluster="group"))
            write.csv(data.frame(term=rownames(estimates),estimates,check.names=FALSE),
                      paste0("outputs/r/",dep,"_",method,".csv"),row.names=FALSE)
            if(method=="within"){
                cd=plm::pcdtest(model,test="cd")
                cd_table=rbind(cd_table,data.frame(model=dep,test="Pesaran_CD_on_FE_residuals",
                                                  statistic=unname(cd$statistic),p_value=cd$p.value))
                cat("PESARAN_CD_FE",dep,"stat",unname(cd$statistic),"p",cd$p.value,"\n")
            }
            cat("BASELINE_SUCCESS",dep,method,"obs",nobs(model),"\n")
        },error=function(e){cat("BASELINE_ERROR",dep,method,conditionMessage(e),"\n")})
    }
}
write.csv(cd_table,"outputs/r/fe_cross_section_dependence.csv",row.names=FALSE)
gmm_tab=data.frame()
for(dep in spec_dep){
    for(lagwin in c("2:3","2:2")){
        instr=c(paste0("lag(",dep,",",lagwin,")"),
                paste0("lag(",spec_x,",",lagwin,")"))
        f=as.formula(paste(dep,"~",paste(c(paste0("lag(",dep,",1)"),spec_x),collapse="+"),
                           "|",paste(instr,collapse="+")))
        for(transf in c("d","ld")){
            for(steps in c("onestep","twosteps")){
                if(lagwin=="2:2" && (transf!="ld" || steps!="onestep")) next
                label=paste(dep,gsub(":", "-", lagwin),transf,steps,sep="_")
                tryCatch({
                    fit=plm::pgmm(f,data=p,effect="twoways",model=steps,
                                   transformation=transf,collapse=TRUE)
                    w_n=if(length(fit$W))ncol(fit$W[[1]]) else NA_integer_
                    cat("GMM_MODEL",label,"INSTRUMENT_COUNT",w_n,"GROUPS",47,"\n")
                    ss=summary(fit,robust=TRUE)
                    print(ss)
                    ab1=tryCatch(plm::mtest(fit,order=1),error=function(e)NULL)
                    ab2=tryCatch(plm::mtest(fit,order=2),error=function(e)NULL)
                    ov=tryCatch(plm::sargan(fit,weights=if(steps=="twosteps")"twosteps" else "onestep"),
                                error=function(e)NULL)
                    cfs=as.matrix(ss$coefficients)
                    write.csv(data.frame(term=rownames(cfs),cfs,check.names=FALSE),
                              paste0("outputs/r/gmm_",label,"_coefficients.csv"),row.names=FALSE)
                    gmm_tab=rbind(gmm_tab,data.frame(model=label,status="ESTIMATED",
                          instruments=w_n,groups=47,coefficients=nrow(cfs),
                          AR1_p=if(is.null(ab1))NA_real_ else ab1$p.value,
                          AR2_p=if(is.null(ab2))NA_real_ else ab2$p.value,
                          overid_plm_sargan_p=if(is.null(ov))NA_real_ else ov$p.value,
                          overid_test_name="plm::sargan; do not relabel as a separately verified Hansen test",
                          message="No independently computed Difference-in-Hansen"))
                },error=function(e){
                    cat("GMM_FAILED",label,conditionMessage(e),"\n")
                    gmm_tab=rbind(gmm_tab,data.frame(model=label,status="FAILED",
                           instruments=NA_integer_,groups=47,coefficients=NA_integer_,
                           AR1_p=NA_real_,AR2_p=NA_real_,overid_plm_sargan_p=NA_real_,
                           overid_test_name="",message=conditionMessage(e)))
                })
            }
        }
    }
}
write.csv(gmm_tab,"outputs/r/gmm_diagnostics.csv",row.names=FALSE)
cat("R_ESTIMATION_COMPLETE. SUCCESS",sum(gmm_tab$status=="ESTIMATED"),
    "FAILED",sum(gmm_tab$status=="FAILED"),"\n")
if(sum(gmm_tab$status=="ESTIMATED")==0)stop("All prespecified pgmm estimates failed; audit logs, no invented results")
