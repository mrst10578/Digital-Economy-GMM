"""Independent science QA for real two-step Difference GMM cross-section & country checks.

Validates that fixed 5 leave-one-country-out cases were selected from PREVIOUS
one-step full-country jackknife, not via current results. Does not execute Stata.
No acceptance of conditional or causal GMM exogeneity is inferred.
"""
from __future__ import annotations
import csv, hashlib, json, re
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/"evidence/scientific-gates-2026-10-16"
OLD=ROOT/"evidence/tablet-stata-2026-10-16"
CD=E/"difference_l23_twostep_residual_cd.csv"
LOO=E/"difference_l23_twostep_five_country_influence.csv"
LOG=E/"difference_l23_twostep_cd_five_country_real_stata.log"
SCRIPT=ROOT/"stata/tablet_diagnostics/23_difference_l23_twostep_cd_influence.do"
BASE=E/"difference_gmm_l23_two_primary_outcomes.csv"
PREVIOUS=OLD/"loo_47x2.csv"
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
EXPECTED_HASH="474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b"

def tab(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))
def n(s):
    v=Decimal(s)
    assert v.is_finite(),s
    return v
def main():
    assert hashlib.sha256(RAW.read_bytes()).hexdigest()==EXPECTED_HASH
    script=SCRIPT.read_text(encoding="utf-8")
    assert 'local fixed_countries "AZE TUR MAC ISR KGZ"' in script
    assert "noleveleq twostep robust small artests(2)" in script
    assert script.count("lag(2 3) collapse)")>=6
    assert "predict double __gmm_resid if __gmm_sample, residuals" in script
    assert "reshape wide __gmm_resid, i(Year) j(panel_id)" in script
    assert "DIFF_L23_STRESS_COMPLETE" in script
    base={r["outcome"]:r for r in tab(BASE) if r["estimator"]=="twostep"}
    assert set(base)=={"Growth","ln_Productivity"}
    prior=tab(PREVIOUS)
    assert len(prior)==94
    full_one_step_internet={
        "Growth":Decimal("-.0097008841"),
        "ln_Productivity":Decimal("-.0005165193"),
    }
    prior_top3=set()
    for outcome,full_b in full_one_step_internet.items():
        country_rows=[r for r in prior if r["outcome"]==outcome]
        assert len(country_rows)==47 and len({r["dropped_country"] for r in country_rows})==47
        country_rows.sort(key=lambda r:abs(n(r["b_internet"])-full_b),reverse=True)
        prior_top3.update(r["dropped_country"] for r in country_rows[:3])
    expected={"AZE","TUR","MAC","ISR","KGZ"}
    assert prior_top3==expected,"Prior sensitivity country set changed"

    log=LOG.read_text(errors="replace")
    assert len(re.findall(r"^DIFF_TWOSTEP_CD_OK outcome=",log,re.M))==2
    assert len(re.findall(r"^DIFF_FIXED_INFLUENCE_OK outcome=",log,re.M))==10
    assert "DIFF_TWOSTEP_CD_FAILURES=0" in log
    assert "DIFF_FIXED_INFLUENCE_FAILURES=0" in log
    assert "DIFF_FIXED_INFLUENCE_TOTAL_COUNT=10" in log
    assert "DIFF_L23_STRESS_COMPLETE" in log
    assert not re.search(r"(?im)^\s*Warning:|^r\(\d+\);|^DIFF_TWOSTEP_CD_PREDICT_FAILED|^DIFF_TWOSTEP_CD_EST_FAILED|^DIFF_FIXED_INFLUENCE_FAILED|covariance matrix of moments is singular",log)

    cds=tab(CD)
    assert len(cds)==2 and {r["outcome"] for r in cds}==set(base)
    result_cd={}
    for r in cds:
        assert r["rc"]=="0"
        assert (int(r["groups"]),int(r["years"]),int(r["pairs"]))==(47,16,1081)
        for k in ("cd_stat","cd_p"):n(r[k])
        assert 0<=n(r["cd_p"])<=1
        assert n(r["cd_p"])>=Decimal(".05")
        result_cd[r["outcome"]]={"cd_z":r["cd_stat"],"two_sided_p":r["cd_p"],
                                 "independence_proven":False}
    loo=tab(LOO)
    assert len(loo)==10 and {(r["outcome"],r["omitted_iso"]) for r in loo}=={(o,c) for o in base for c in expected}
    result_loo={}
    for outcome in base:
        selected=[r for r in loo if r["outcome"]==outcome]
        flips=0
        n_ar1_significant=0
        for r in selected:
            assert r["rc"]=="0"
            assert (int(r["N"]),int(r["groups"]),int(r["instruments"]))==(736,46,30)
            for k in ("internet_b","internet_se","internet_p","lag_b","hansen_p","sargan_p","ar1_p","ar2_p"):
                n(r[k])
            for k in ("internet_p","hansen_p","sargan_p","ar1_p","ar2_p"):
                assert 0<=n(r[k])<=1
            assert n(r["internet_se"])>0
            assert n(r["internet_p"])>Decimal(".05"),"No evidence digital Internet under prespecified country omission"
            assert n(r["hansen_p"])>Decimal(".05")
            assert n(r["sargan_p"])>Decimal(".05")
            assert n(r["ar2_p"])>Decimal(".05")
            if n(r["ar1_p"])<Decimal(".05"):n_ar1_significant+=1
            if n(r["internet_b"])*n(base[outcome]["b_internet"])<0:flips+=1
        result_loo[outcome]={
            "five_prior_influential_countries_count":5,
            "number_sign_changes_vs_full_twostep":flips,
            "number_AR1_rejections_at_5pct":n_ar1_significant,
            "minimum_hansen_p":str(min(n(r["hansen_p"]) for r in selected)),
            "minimum_ar2_p":str(min(n(r["ar2_p"]) for r in selected)),
            "all_internet_p_above_5pct":True
        }
    assert result_loo["Growth"]["number_sign_changes_vs_full_twostep"]==0
    assert result_loo["ln_Productivity"]["number_sign_changes_vs_full_twostep"]==3
    assert result_loo["Growth"]["number_AR1_rejections_at_5pct"]==1
    assert result_loo["ln_Productivity"]["number_AR1_rejections_at_5pct"]==1

    report={
       "audit":"PASS: genuine 2 native two-step GMM Pesaran CD and 10 prespecified prior-country reruns",
       "original_source_sha256":EXPECTED_HASH,
       "stata_run_in_ci":False,
       "difference_GMM_is_original_system_GMM":False,
       "cross_section_residual_CD":result_cd,
       "five_country_two_step_sensitivity":result_loo,
       "no_causal_identification_accepted":True,
       "scientific_limitations":[
         "Pesaran CD non-rejection does not prove cross-sectional independence.",
         "Influential countries were prespecified from earlier full one-step jackknife; only 5 countries rerun here, not a 47x2 two-step leave-one-out.",
         "Internet sign for productivity remains sensitive and all nominal Internet p-values >5%.",
         "AR1 is sensitive to Macau omission for both outcomes and generally not rejected under two-step robust.",
         "Overidentification non-rejection alone cannot establish exogeneity or non-weak instruments."
       ],
    }
    dest=ROOT/"outputs/professor_diff_twostep_stress_audit"
    dest.mkdir(parents=True,exist_ok=True)
    (dest/"latest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
