#!/usr/bin/env python3
"""Check whether true Comtrade historical classifications align with UNCTAD ICT catalogs.

Audit 8 reporters × 15 years × 2 trial headings. This is revision selection
evidence only, not harmonization or cross-border technology exposure.
"""
from __future__ import annotations
import csv,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
LOCK=ROOT/"config/extended/phase2_original_47_country_sample_lock.json"
REVISIONS=ROOT/"data/extended/comtrade/oecd_missing_hs4_2008_2022/source_classification_revisions_2008_2022.csv"
CAT=ROOT/"data/extended/official_ict_hs6/unctad_ict_goods_official_hs6_1992_to_2022.csv"
OUT=ROOT/"evidence/extended/COMTRADE_8_RECEIVER_HS_REVISION_VS_UNCTAD_CATALOG_2026-10-17.json"
M49={"H0":"HS1992","H1":"HS1996","H2":"HS2002","H3":"HS2007",
     "H4":"HS2012","H5":"HS2017","H6":"HS2022"}
COUNTRIES={"KGZ","MAC","MDA","MKD","MNG","PAN","TTO","URY"}
def read(path):
    with path.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def main():
    lock=json.loads(LOCK.read_text(encoding="utf-8"))
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==lock["original_data_sha256"]
    goods=read(CAT);rev=read(REVISIONS)
    assert len(goods)==691 and len(rev)==240
    hs6=defaultdict(set)
    for good in goods:
        k=good["Comtrade_classificationCode"]
        assert k in M49 and good["HS_edition"]==M49[k]
        code=good["HS6"];assert len(code)==6 and code.isdigit()
        assert code not in hs6[k]
        hs6[k].add(code)
    assert len(hs6)==7
    yearly=defaultdict(dict);source_counts=Counter()
    for row in rev:
        country,year,heading=row["reporter_ISO3"],int(row["Year"]),row["HS4"]
        assert country in COUNTRIES and 2008<=year<=2022 and heading in ("8471","8517")
        key=(country,year)
        assert heading not in yearly[key]
        orig=row["observed_classificationCode_values"]
        flag=row["revision_established_from_metadata_not_year"]
        if flag=="TRUE":
            assert orig in M49 and orig in hs6
            assert row["unambiguous_HS_revision_if_reported"]==M49[orig]
            status="VERIFIED_EDITION_IN_CATALOG"
            source_counts[orig]+=1
        else:
            assert orig=="" and row["unambiguous_HS_revision_if_reported"]==""
            status="NO_SOURCE_RECORD_TO_ESTABLISH_EDITION"
            source_counts["MISSING"]+=1
        yearly[key][heading]=(orig,status)
    assert len(yearly)==120
    receiver_summary=[]
    mixed=[]
    for country in sorted(COUNTRIES):
        codes=Counter();transitions=[];previous=None;with_revision=0
        for year in range(2008,2023):
            pair=yearly[country,year]
            assert set(pair)=={"8471","8517"}
            left,right=pair["8471"][0],pair["8517"][0]
            if left!=right:
                mixed.append({"country":country,"year":year,"8471":left,"8517":right})
                codes["MIXED"]+=1
                continue
            code=left if left else "MISSING"
            codes[code]+=1
            if left:
                with_revision+=1
                if previous and previous!=left:
                    transitions.append({"year":year,"from":previous,"to":left})
                previous=left
        receiver_summary.append({
            "receiver_ISO3":country,"years":15,
            "years_two_headings_same_revision_with_observed_data":with_revision,
            "edition_counts_by_year":dict(codes),
            "observed_revision_transitions":transitions,
        })
    summary={
        "phase":"EXTENDED_DATA_EXPERIMENTAL",
        "observed_source_year_hs4_slices":len(rev),
        "eight_country_year_pairs":len(yearly),
        "verified_code_source_rows":sum(v for k,v in source_counts.items() if k!="MISSING"),
        "missing_classification_source_rows":source_counts["MISSING"],
        "edition_source_heading_counts":dict(source_counts),
        "mixed_revision_in_one_country_year":mixed,
        "country_results":receiver_summary,
        "all_seven_UNCTAD_editions_catalog_verified":True,
        "cross_edition_economic_comparability_not_proven":True,
        "final_ICT_goods_HS6_trade_value_not_downloaded":True,
        "no_FTECH_GMM_or_stata":True,
        "baseline_sha256_verified":lock["original_data_sha256"],
    }
    assert summary["verified_code_source_rows"]==230
    assert summary["missing_classification_source_rows"]==10
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PHASE2_COMTRADE_HS_EDITION_SOURCE_ALIGNMENT_PASS",230,"verified headings",
          "10 missing", "country-year-mixed",len(mixed),flush=True)
if __name__=="__main__":main()
