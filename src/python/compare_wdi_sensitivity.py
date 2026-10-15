"""Compare original and updated-WDI Stata executions without selecting models by p-values."""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,json,re
from pathlib import Path
from decimal import Decimal
FIELDS=("N","Ng","instruments","sargan_p","hansen_p","ar1_p","ar2_p")
def table(path):
    with open(path,encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    return {r["model"]:r for r in rows}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",required=True)
    ap.add_argument("--revised",required=True)
    ap.add_argument("--log",required=True)
    ap.add_argument("--out",required=True)
    opt=ap.parse_args()
    base=table(opt.base);revised=table(opt.revised)
    assert len(base)==6 and set(base)==set(revised)
    evidence=[]
    for model,b in base.items():
        x=revised[model]
        delta={}
        threshold_crossings=[]
        for field in FIELDS:
            a=Decimal(b[field]);c=Decimal(x[field])
            delta[field]={"historical":str(a),"current_WDI":str(c),"difference":str(c-a)}
            if field.endswith("_p") and (a<Decimal(".05"))!=(c<Decimal(".05")):
                threshold_crossings.append(field)
        evidence.append({"model":model,"historical_rc":int(b["rc"]),"wdi_rc":int(x["rc"]),
                         "historical_verdict":b["status"],"wdi_verdict":x["status"],
                         "changes":delta,"p_threshold_crossings":threshold_crossings})
    text=Path(opt.log).read_text(errors="replace")
    warnings=len(re.findall(r"^Warning: Two-step estimated covariance matrix of moments is singular\.",text,re.M))
    omissions=re.findall(r"^(yd_\d+ dropped due to collinearity)$",text,re.M)
    complete="RUN_ALL_SCRIPT_COMPLETED" in text
    result={"timestamp_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
            "model_count":len(evidence),"original_models_failed":sum(x["historical_rc"]!=0 for x in evidence),
            "wdi_models_failed":sum(x["wdi_rc"]!=0 for x in evidence),
            "current_WDI_log_sha256":hashlib.sha256(Path(opt.log).read_bytes()).hexdigest(),
            "full_stata_pipeline_finished":complete,"singular_covariance_warnings":warnings,
            "year_dummy_collinearity_omissions":omissions,"model_comparisons":evidence,
            "status":"COMPUTATIONAL_COMPLETE_WITH_SCIENTIFIC_CAVEATS" if complete and not any(x["wdi_rc"] for x in evidence) else "INCOMPLETE_OR_FAILED",
            "science_note":"Diagnostic warnings, causal identification and peer review matter; never choose a specification because a p-value improves."}
    dest=Path(opt.out)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("WDI_REESTIMATION_COMPARISON",json.dumps({"status":result["status"],
       "models":result["model_count"],"singular_warnings":warnings,
       "omitted_year_dummies":len(omissions),"crossed_5pct":{r["model"]:r["p_threshold_crossings"] for r in evidence if r["p_threshold_crossings"]}},
       ensure_ascii=False))
    for r in evidence:
        print("COMPARISON",r["model"],"p-values",[(k,r["changes"][k]["historical"],r["changes"][k]["current_WDI"]) for k in ("hansen_p","sargan_p","ar1_p","ar2_p")])
if __name__=="__main__":
    main()
