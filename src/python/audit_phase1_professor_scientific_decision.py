"""Phase 1 professor-only scientific decision gate.

Checks archived real Stata results and original workbook; never estimates models,
never tunes p-values, and never classifies Hansen non-rejection as proof of exogeneity.
Run: python -m src.python.audit_phase1_professor_scientific_decision
"""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/"evidence"
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
EXPECTED_HASH="474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b"

def read_csv(rel):
    with (E/rel).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def row(data,field,val,extra=None):
    found=[x for x in data if x[field]==val and (extra is None or all(x[k]==v for k,v in extra.items()))]
    assert len(found)==1,(field,val,extra,len(found))
    return found[0]

def check():
    assert hashlib.sha256(RAW.read_bytes()).hexdigest()==EXPECTED_HASH
    gmm=read_csv("stata-adb-2026-10-17/professor_system_gmm_stats.csv")
    difference=read_csv("stata-adb-2026-10-17/diff_l23_two_outcomes_stats.csv")
    annual=read_csv("scientific-gates-2026-10-16/theory_led_productivity_growth_system_gmm_stats.csv")
    twfe=read_csv("phase1-robust-2026-10-17/twfe_r_diagnostics.csv")
    assert len(gmm)==4 and len(difference)==4 and len(annual)==2 and len(twfe)==3
    for x in gmm:
        assert x["rc"]=="0" and int(x["N"])==799 and int(x["Ng"])==47 and int(x["instruments"])==31
    for x in difference:
        assert x["rc"]=="0" and int(x["N"])==752 and int(x["Ng"])==47 and int(x["instruments"])==30
    for x in annual:
        assert x["rc"]=="0" and int(x["N"])==752 and int(x["Ng"])==47 and int(x["instruments"])==30
    gr=row(gmm,"outcome","Growth",{"method":"twostep"})
    pr=row(gmm,"outcome","ln_Productivity",{"method":"twostep"})
    pr1=row(gmm,"outcome","ln_Productivity",{"method":"onestep"})
    pd=row(difference,"outcome","ln_Productivity",{"estimator":"twostep"})
    annual2=row(annual,"method","twostep")
    levels=row(twfe,"model","ln_Productivity")
    changes=row(twfe,"model","D_ln_Productivity")
    assert float(pr["hansen_p"])<0.05 and float(pr["diffh_dep_level_p"])<0.01
    assert float(pr["diffh_ctrl_p"])<0.05
    assert float(pr1["hansen_p"])<0.05
    assert float(pr["b_lag"])>0.98
    assert float(gr["sargan_p"])<0.00001 and float(gr["hansen_p"])>0.05
    assert float(pd["hansen_p"])>0.05 and float(pd["ar2_p"])>0.05
    assert float(annual2["sargan_p"])<0.05 and float(annual2["hansen_p"])>0.05
    assert float(annual2["ar1_p"])>0.05
    assert float(levels["residual_cd_p"])<0.05
    assert float(changes["joint_p_cluster"])>0.05 and float(changes["joint_p_dk_lag2"])<0.05
    log=(E/"stata-adb-2026-10-17/PROFESSOR_SYSTEM_GMM_FOUR_RUNS.log").read_text(errors="replace")
    assert "GMM instruments for levels" in log and "Hansen test excluding group:     chi2(0)" in log
    assert "PROFESSOR_FAILED_COUNT=0" in log
    audit=(ROOT/"docs/PHASE1_FINAL_STRICT_SCIENTIFIC_AUDIT_2026-10-17_FA.md").read_text(encoding="utf-8")
    assert "درجه آزادی صفر" in audit and "۰٫۰۰۰۷۹۴" in audit
    decision={
      "audit":"PASS","raw_source":"original_professor_workbook_only",
      "source_sha256":EXPECTED_HASH,"new_data_used":False,
      "fresh_stata_run_in_this_gate":False,
      "growth_system_gmm":"REPORTABLE_WITH_MAJOR_LIMITATIONS_NOT_CAUSAL",
      "productivity_level_system_gmm":"REJECT_FOR_CAUSAL_INFERENCE_WITH_CURRENT_MOMENTS",
      "productivity_difference_gmm":"SENSITIVITY_ONLY_NOT_PROOF_OF_VALID_IV",
      "productivity_annual_growth_gmm":"DIFFERENT_ESTIMAND_EXPLORATORY_NOT_REPLACEMENT",
      "two_way_fixed_effects":"DESCRIPTIVE_CHECKS_NOT_CAUSAL",
      "cross_country_spillovers":"NOT_IDENTIFIED_BY_INTERNAL_DIGITAL_INDICATORS",
      "model_selection":"NO_POST_HOC_P_VALUE_OPTIMIZATION",
      "professor_action":"CLARIFY_ACCEPTABILITY_OF_NONCAUSAL_FINDINGS_AND_REDEFINED_ESTIMAND",
      "phase1_conclusion":"DO_NOT_CERTIFY_CAUSAL_PROOF"
    }
    print(json.dumps(decision,ensure_ascii=False,indent=2))
    return decision

if __name__=="__main__":
    check()
