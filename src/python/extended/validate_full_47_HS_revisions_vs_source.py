#!/usr/bin/env python3
"""Cross-validate 47x18 official source HS revisions against prior raw trade metadata.

Exact reporter-year logic, no calendar inference, no missing values imputed,
no modification of professor's original panel. Emits audit even on disagreement.
"""
from __future__ import annotations
import csv,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
LOCK=ROOT/"config/extended/phase2_original_47_country_sample_lock.json"
CURRENT=ROOT/"data/extended/comtrade/source_hs_revisions_47/47_country_18_year_HS_revision_2005_2022.csv"
PREV=ROOT/"data/extended/comtrade/oecd_missing_hs4_2008_2022/source_classification_revisions_2008_2022.csv"
OUT=ROOT/"evidence/extended/ALL_47_SOURCE_HS_CROSSCHECK_VS_8_REPORTERS_2026-10-17.json"
def read(p):
    with p.open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))
def main():
    lock=json.loads(LOCK.read_text(encoding="utf-8"))
    sha=hashlib.sha256(BASE.read_bytes()).hexdigest()
    assert sha==lock["original_data_sha256"]
    current=read(CURRENT);prior=read(PREV)
    assert len(current)==47*18==846 and len(prior)==240
    known_iso=set(lock["iso3_to_original_country_name"])
    observed={}
    for r in current:
        iso,year=r["ISO3"],int(r["Year"])
        assert iso in known_iso and 2005<=year<=2022
        key=(iso,year)
        assert key not in observed
        if r["status"]=="VERIFIED_SINGLE_SOURCE_REVISION":
            assert r["source_HS_edition"] in ("H0","H1","H2","H3","H4","H5","H6")
        else:
            assert r["source_HS_edition"]==""
        observed[key]=r
    assert set(observed)=={(iso,y) for iso in known_iso for y in range(2005,2023)}
    comparison=[];errors=[]
    for old in prior:
        key=(old["reporter_ISO3"],int(old["Year"]))
        new=observed[key]
        prev=old["observed_classificationCode_values"]
        code=new["source_HS_edition"]
        outcome=("MATCH" if prev and code and prev==code
            else "PREVIEW_HEADING_ABSENT_BUT_SOURCE_YEAR_KNOWN" if not prev and code
            else "BOTH_LACK_REVISION_SOURCE" if not prev and not code
            else "DISAGREEMENT_OR_MISSING_OFFICIAL_SOURCE")
        item={"ISO3":key[0],"Year":key[1],"HS4":old["HS4"],
            "preview_heading_source_revision":prev,
            "official_full_year_getDA_source_revision":code,"outcome":outcome}
        comparison.append(item)
        if outcome=="DISAGREEMENT_OR_MISSING_OFFICIAL_SOURCE":
            errors.append(item)
    country_counts=defaultdict(Counter);year_counts=defaultdict(Counter)
    for (iso,year),record in observed.items():
        country_counts[iso][record["status"]]+=1
        year_counts[year][record["status"]]+=1
    transitions={}
    for iso in sorted(known_iso):
        prev_code=None;edges=[]
        for year in range(2005,2023):
            code=observed[(iso,year)]["source_HS_edition"]
            if code and prev_code and code!=prev_code:
                edges.append({"year":year,"from":prev_code,"to":code})
            if code:prev_code=code
        transitions[iso]=edges
    report={
      "original_data_sha256":sha,"original_47_countries":47,
      "year_range":[2005,2022],"expected_country_years":846,
      "country_year_statuses":dict(Counter(x["status"] for x in current)),
      "country_statuses":{c:dict(x) for c,x in sorted(country_counts.items())},
      "year_statuses":{str(y):dict(x) for y,x in sorted(year_counts.items())},
      "observed_source_edition_transitions_not_imputed":transitions,
      "comparison_with_240_prior_8_receiver_year_hs4_slices":
         dict(Counter(x["outcome"] for x in comparison)),
      "discrepancies_requiring_review":errors,
      "prior_slice_examples_missing_trade_heading_but_year_metadata_known":[x for x in comparison
          if x["outcome"]=="PREVIEW_HEADING_ABSENT_BUT_SOURCE_YEAR_KNOWN"],
      "source_editions_never_inferred_from_calendar_year":True,
      "source_metadata_not_equivalent_to_available_trade_value":True,
      "missing_never_imputed_as_zero":True,
      "final_FTECH_GMM_approved":False,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("OFFICIAL_47_COUNTRY_18_YEAR_REVISION_AUDIT",
        report["country_year_statuses"],
        report["comparison_with_240_prior_8_receiver_year_hs4_slices"],
        "DISCREPANCIES",len(errors),flush=True)
    if errors:raise SystemExit("HS source disagreement requires review before use")
if __name__=="__main__":main()
