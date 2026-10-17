#!/usr/bin/env python3
"""Extract exact six-digit ICT goods rows from real SHA-verified UNCTAD PDFs.

Edition-specific catalogs are source observations, NOT a reconciled economic
series. In particular, current HS2017 PDF has 92 extracted distinct rows vs
general overview claiming 93; flag for independent Eurostat comparison.
Never invent missing codes, use guessed year-to-edition mappings, or join to
the professor's data.
"""
from __future__ import annotations
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import fitz

ROOT=Path(__file__).resolve().parents[3]
DIR=ROOT/"outputs/extended/official_ict_hs6_probe"
OUT=ROOT/"data/extended/official_ict_hs6"
INFO=DIR/"SOURCE_ACCESS_PROBE.json"
EXPECTED={2002:108,2007:93,2012:91,2017:92,2022:107}
HSCODE=re.compile(r"^\s*(\d{6})\s+(.+?)\s*$")
CATCODE=re.compile(r"^\s*(ICT0[1-5])\s+(.+?)\s*$")
SIXDIGIT=re.compile(r"(?<!\d)\d{6}(?!\d)")
FIELDS=["HS_edition","Comtrade_classificationCode","ICT_group","ICT_group_label",
        "HS6","description_as_published","UNCTAD_source_url","UNCTAD_pdf_sha256",
        "page_index_first_seen","official_code_observed","cross_edition_harmonized",
        "FTECH_ready"]


def skip_line(line):
    s=line.strip()
    return (not s or s.startswith("ICT goods categories and composition")
            or s.startswith("/Total ICT goods")
            or s.startswith("Code      Label")
            or s.startswith("Code  Label")
            or s.startswith("Generation date:")
            or re.match(r"^Page \d+ of \d+",s) is not None)


def extract_pdf(path, year, url, digest):
    pdf=fitz.open(path)
    rows=[]
    category=""
    category_label=""
    current=None
    raw_count=0

    def seal():
        nonlocal current
        if current is not None:
            current["description_as_published"]=" ".join(current["description_as_published"].split())
            assert current["description_as_published"] and len(current["description_as_published"])>6
            rows.append(current)
            current=None

    for page_no,page in enumerate(pdf,1):
        txt=page.get_text("text",sort=True)
        raw_count+=len(SIXDIGIT.findall(txt))
        for raw_line in txt.splitlines():
            line=raw_line.strip()
            if skip_line(line): continue
            cc=CATCODE.match(line)
            if cc:
                seal()
                category=cc.group(1)
                category_label=cc.group(2)
                continue
            if line.startswith("ICT00"):
                seal()
                continue
            goods=HSCODE.match(line)
            if goods:
                seal()
                if not category:
                    raise ValueError(f"Uncategorized official HS6 code in {year}:{page_no}")
                current={
                  "HS_edition":f"HS{year}",
                  "Comtrade_classificationCode":{2002:"H2",2007:"H3",2012:"H4",2017:"H5",2022:"H6"}[year],
                  "ICT_group":category,"ICT_group_label":category_label,
                  "HS6":goods.group(1),"description_as_published":goods.group(2),
                  "UNCTAD_source_url":url,"UNCTAD_pdf_sha256":digest,
                  "page_index_first_seen":page_no,"official_code_observed":"TRUE",
                  "cross_edition_harmonized":"FALSE","FTECH_ready":"FALSE"}
            elif current is not None:
                # A continuation line for the previously printed 6-digit row.
                current["description_as_published"]+=" "+line
            else:
                raise ValueError(f"Unexpected text before first ICT good: {year} page{page_no} {line[:60]!r}")
    seal()
    assert len(rows)==raw_count, (
        f"Parser missed a 6-digit code in HS{year}: parsed={len(rows)} pdf={raw_count}"
    )
    assert len({x["HS6"] for x in rows})==len(rows),f"Duplicate HS6 in HS{year}"
    assert set(x["ICT_group"] for x in rows)=={f"ICT0{i}" for i in range(1,6)}
    assert len(rows)==EXPECTED[year],f"Unexpected code cardinality HS{year}"
    return rows, len(pdf)


def main():
    manifest=json.loads(INFO.read_text(encoding="utf-8"))
    byname={r["name"]:r for r in manifest["sources"]}
    all_rows=[]
    edition_stats=[]
    sets={}
    for year in sorted(EXPECTED):
        src=byname[f"UNCTAD_HS{year}_PDF"]
        assert src["status"]=="VALID_SOURCE_BYTES" and src["file_kind_verified"]=="pdf"
        original=DIR/src["stored_relpath"]
        assert hashlib.sha256(original.read_bytes()).hexdigest()==src["sha256"]
        goods,npages=extract_pdf(original,year,src["url"],src["sha256"])
        codes={r["HS6"] for r in goods}
        sets[year]=codes
        groups=Counter(r["ICT_group"] for r in goods)
        stats={
          "edition":f"HS{year}","Comtrade_classificationCode":goods[0]["Comtrade_classificationCode"],
          "official_source_url":src["url"],"official_source_sha256":src["sha256"],
          "pages":npages,"distinct_six_digit_codes":len(codes),
          "category_counts":dict(sorted(groups.items())),
          "completeness_against_current_pdf":"ALL_PDF_SIX_DIGIT_ROWS_EXTRACTED",
          "cross_edition_mapping_verified":False}
        edition_stats.append(stats)
        all_rows.extend(goods)
        print("OFFICIAL_UNCTAD_ICT_HS6_EXTRACTED",year,len(goods),dict(groups),flush=True)

    assert len(all_rows)==sum(EXPECTED.values())==491
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/"unctad_ict_goods_official_hs6_2002_2007_2012_2017_2022.csv"
    with path.open("w",newline="",encoding="utf-8") as fp:
        writer=csv.DictWriter(fp,fieldnames=FIELDS,lineterminator="\n")
        writer.writeheader();writer.writerows(all_rows)
    shifts=[]
    for earlier,later in zip(sorted(EXPECTED)[:-1],sorted(EXPECTED)[1:]):
        previous=sets[earlier];after=sets[later]
        shifts.append({
            "from_HS_edition":f"HS{earlier}",
            "to_HS_edition":f"HS{later}",
            "identical_six_digit_strings":len(previous&after),
            "only_earlier_strings":len(previous-after),
            "only_later_strings":len(after-previous),
            "UNSD_split_merge_concordance_performed":"FALSE",
        })
    with (OUT/"edition_code_token_overlap_not_concordance.csv").open(
            "w",newline="",encoding="utf-8") as fp:
        w=csv.DictWriter(fp,fieldnames=list(shifts[0]),lineterminator="\n")
        w.writeheader();w.writerows(shifts)
    meta={
        "phase":"EXTENDED_DATA_EXPERIMENTAL",
        "source":"UNCTAD Data Hub official ICT categories and HS edition catalogs",
        "source_files_verified_sha256":len(EXPECTED),
        "total_official_HS6_entries":len(all_rows),
        "editions":edition_stats,
        "HS2017_current_pdf_rows":len(sets[2017]),
        "HS2017_website_descriptive_count":93,
        "HS2017_discrepancy_with_website_UNRESOLVED":len(sets[2017])!=93,
        "independent_eurostat_HS2017_crosscheck_required":True,
        "raw_HS6_editions_never_assumed_interchangeable":True,
        "HS6_partner_trade_data_yet_downloaded":False,
        "trade_weight_data_quality_yet_validated":False,
        "final_FTECH_or_GMM_approved":False,
        "professor_original_dataset_changed":False,
    }
    (OUT/"PROVENANCE_AND_SCIENTIFIC_LIMITS.json").write_text(
        json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("OFFICIAL_UNCTAD_HS6_CATALOG_ARCHIVED",len(all_rows),
          "entries; 2017 source inconsistency pending crosscheck",flush=True)


if __name__=="__main__":main()
