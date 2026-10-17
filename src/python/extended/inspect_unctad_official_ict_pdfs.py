#!/usr/bin/env python3
"""Inspect page text and robust 6-digit HS extraction strategy from actual PDFs."""
from __future__ import annotations
import hashlib, json, re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3]
INPUT=ROOT/"outputs/extended/official_ict_hs6_probe"
OUT=ROOT/"evidence/extended/official_ict_hs6_layout_diagnostics_2026-10-17.json"
REG=INPUT/"SOURCE_ACCESS_PROBE.json"
CODES=re.compile(r"(?<!\d)([0-9]{6})(?!\d)")
def main():
    manifest=json.loads(REG.read_text(encoding="utf-8"))
    details=[]
    for entry in manifest["sources"]:
        if entry["status"]!="VALID_SOURCE_BYTES" or not entry["name"].endswith("_PDF"): continue
        path=INPUT/entry["stored_relpath"]
        assert hashlib.sha256(path.read_bytes()).hexdigest()==entry["sha256"]
        doc=fitz.open(path)
        full=[];pages=[]
        for n,p in enumerate(doc):
            text=p.get_text("text",sort=True)
            full.append(text)
            lines=[x.strip() for x in text.splitlines() if x.strip()]
            ids=CODES.findall(text)
            pages.append({"page":n+1,"n_lines":len(lines),
                "six_digit_occurrences":len(ids),
                "first_55_lines":lines[:55] if n==0 else [],
                "first_10_lines":lines[:10],
                "first_10_codes":ids[:10],
                "raw_first_900":text[:900] if n==0 else "",
            })
        d=CODES.findall("\n".join(full))
        counts=Counter(d)
        details.append({"name":entry["name"],"sha256":entry["sha256"],
             "pages":len(doc),"six_digit_occurrences_total":len(d),
             "unique_six_digit_strings":len(counts),
             "duplicates":{k:v for k,v in counts.items() if v>1},
             "all_ict_labels_present":all(f"ICT0{i}" in "\n".join(full) for i in range(1,6)),
             "pages_detail":pages})
        print("OFFICIAL_HS6_INSPECT",entry["name"],"pages",len(doc),
              "tokens",len(d),"unique",len(counts),
              "first",d[:18],flush=True)
    OUT.parent.mkdir(exist_ok=True,parents=True)
    OUT.write_text(json.dumps({"timestamp_utc":datetime.now(timezone.utc).isoformat(),
              "sources":details,"no_goods_approved_yet":True},indent=2,
              ensure_ascii=False)+"\n",encoding="utf-8")
if __name__=="__main__":main()
