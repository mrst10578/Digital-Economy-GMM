#!/usr/bin/env python3
"""Validate/retain original Comtrade partner evidence for 3 other receivers.

Read only known successful GHA artifact run 39017650352. Validate 18 raw JSON
SHA-256s, normalized 773 partners, 3×6 world-aggregate coverage and strict
no-zero imputation. Publish raw-normalized research CSVs only on Phase B.

These are provisional 2005-2007 origins and weight components, NOT a complete
ICT basket, network-wide FTECH, external IV, or causal estimate.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
ART=ROOT/"outputs/extended/artefact_run_39017650352"
OUT=ROOT/"data/extended/comtrade"
LOCK=ROOT/"config/extended/phase2_original_47_country_sample_lock.json"
RAW=ROOT/"data/raw/Balanced_Panel_Data.xlsx"
DEST=("KGZ","MDA","PAN")
HS=("8471","8517")
YEARS=(2005,2006,2007)
RUN=39017650352

def read_csv(p):
    with p.open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))
def write_csv(p,rows):
    assert rows
    with p.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)

def main():
    lock=json.loads(LOCK.read_text(encoding="utf-8"))
    sha=hashlib.sha256(RAW.read_bytes()).hexdigest()
    assert sha==lock["original_data_sha256"]
    allowed=set(lock["iso3_to_original_country_name"])
    rows=read_csv(ART/"three_country_2005_2007_partners.csv")
    cover=read_csv(ART/"three_country_18_annual_source_coverage.csv")
    table=read_csv(ART/"three_country_preperiod_weight_feasibility.csv")
    summary=json.loads((ART/"summary.json").read_text(encoding="utf-8"))
    assert (len(rows),len(cover),len(table))==(773,18,3)
    assert not summary["bad_queries"] and summary["valid_headings"]==18
    assert set(r["destination_ISO3"] for r in table)==set(DEST)
    group=defaultdict(dict)
    for r in rows:
        dest=r["destination_ISO3"];y=int(r["Year"]);hs=r["HS4"]
        partner=int(r["origin_M49"]);src=r["origin_ISO3_in_original_47"]
        value=float(r["value_nominal_USD"])
        assert dest in DEST and y in YEARS and hs in HS
        assert not src or src in allowed
        assert math.isfinite(value) and value>=0 and partner>=0
        key=(dest,y,hs)
        assert partner not in group[key],"duplicate reporting partner code"
        group[key][partner]=(value,src)
    assert set(group)=={(dest,y,hs) for dest in DEST for y in YEARS for hs in HS}
    for r in cover:
        dest=r["destination_ISO3"];y=int(r["Year"]);h=r["HS4"]
        assert r["status"]=="VALID_PREVIEW"
        g=group[dest,y,h]
        assert len(g)==int(r["preview_rows"])
        assert 0 in g
        world=g[0][0]
        sub=sum(v for _,(v,src) in g.items() if src and src!=dest)
        assert math.isclose(world,float(r["world_reported_USD"]),rel_tol=1e-10)
        assert math.isclose(sub,float(r["reported_original_47_source_USD"]),rel_tol=1e-10,abs_tol=0.01)
        raw=(ART/"raw_api"/f"{dest}_{y}_HS{h}.json").read_bytes()
        assert hashlib.sha256(raw).hexdigest()==r["raw_response_sha256"]
    weight_rows=[]
    for dest in DEST:
        entry=next(x for x in table if x["destination_ISO3"]==dest)
        world=sum(group[dest,y,h][0][0] for y in YEARS for h in HS)
        original=sum(v for y in YEARS for h in HS for _,(v,src) in group[dest,y,h].items() if src and src!=dest)
        assert math.isclose(world,float(entry["world_total_USD_2005_2007_2_HS4"]),rel_tol=1e-10)
        assert math.isclose(original,float(entry["observed_origins_value_USD"]),rel_tol=1e-10,abs_tol=.01)
        supported=0;full=0
        for src in sorted(allowed-{dest}):
            observed=[]
            for year in YEARS:
                for h in HS:
                    for p,(value,code) in group[dest,year,h].items():
                        if code==src:
                            observed.append(value)
            n=len(observed)
            supported+=n>0;full+=n==6
            weight_rows.append({
                "destination_ISO3":dest,"origin_ISO3":src,
                "base_years":"2005-2007","HS_headings":"8471+8517",
                "observed_year_heading_cells_of_6":n,
                "reporting_value_nominal_USD":sum(observed) if n else "",
                "partial_observed_trade_share_of_world":sum(observed)/world if n else "",
                "usable_as_final_weight":False,
                "missing_is_not_zero":True,
                "causal_spillover_validated":False,
            })
        assert supported==int(entry["observed_source_countries_in_original_47"])
        assert full==int(entry["source_countries_with_six_reported_cells"])
    assert len(weight_rows)==3*46
    OUT.mkdir(parents=True,exist_ok=True)
    for name,origin in [
        ("KGZ_MDA_PAN_2005_2007_all_partner_values.csv","three_country_2005_2007_partners.csv"),
        ("KGZ_MDA_PAN_2005_2007_six_heading_coverage.csv","three_country_18_annual_source_coverage.csv"),
        ("KGZ_MDA_PAN_2005_2007_preperiod_weight_quality.csv","three_country_preperiod_weight_feasibility.csv")]:
        (OUT/name).write_bytes((ART/origin).read_bytes())
    write_csv(OUT/"KGZ_MDA_PAN_2005_2007_observed_only_country_weight_screen.csv",weight_rows)
    prov={
       "phase":"EXTENDED_DATA_EXPERIMENTAL",
       "source_run":RUN,
       "original_professor_sha256":sha,
       "raw_API_payloads_verified":18,
       "all_partner_records":len(rows),
       "all_year_heading_summary_rows":len(cover),
       "receiver_countries":list(DEST),
       "source_country_weight_rows":len(weight_rows),
       "missing_cell_count_never_filled_zero":True,
       "raw_API_json_in_30_day_actions_artifact":True,
       "world_M49_0_only_denominator_not_source":True,
       "HS8471_8517_only_not_full_ICT_basket":True,
       "weights_partial_not_identified_for_causal_models":True,
       "Stata_executed":False,
       "phase_A_modified":False,
       "redistribution_source":"UN Comtrade",
       "data_policy":"https://uncomtrade.org/docs/re-dissemination-of-data/"
    }
    (OUT/"KGZ_MDA_PAN_2005_2007_PROVENANCE.json").write_text(json.dumps(prov,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("THREE_RECIPIENT_ARCHIVE_PASS",len(rows),"reported partner values",len(cover),"source headings",len(weight_rows),"candidate original-source cells")
    print("PROFESSOR_DATA_UNCHANGED_AND_NOT_CAUSAL=TRUE")

if __name__=="__main__":
    main()
