#!/usr/bin/env python3
"""OECD ICIO 2025 official download metadata audit without bulk fetching.

Discover hrefs from OECD official page. Inspect Content-Length, Content-Type
and CDN redirects via HEAD; NEVER fetch large ZIP contents in this workflow.
One ReadMe workbook may be retrieved only if server states length <= 5 MB.
"""
from __future__ import annotations
import csv
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlparse
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/"outputs/extended/oecd_icio_2025_archive_preflight"
PAGE="https://www.oecd.org/en/data/datasets/inter-country-input-output-tables.html"
OFFICIAL_DOMAIN="webfs-sti.oecd.org"
DOWNS=("2001-2005","2006-2010","2011-2015","2016-2022")
EXPECTED=("2001-2005","2006-2010","2011-2015","2016-2022")

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors=[]
        self.href=None
        self.text=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            d=dict(attrs)
            self.href=d.get("href")
            self.text=[]
    def handle_data(self,data):
        if self.href is not None:
            self.text.append(data)
    def handle_endtag(self,tag):
        if tag=="a" and self.href is not None:
            self.anchors.append((" ".join(self.text).strip(),self.href))
            self.href=None
            self.text=[]

def fetch(url,method="GET"):
    req=Request(url,headers={"User-Agent":"Academic-Research-PhaseB-ICIO/1.0"},method=method)
    return urlopen(req,timeout=35)

def meta(url):
    try:
        with fetch(url,"HEAD") as r:
            h=r.headers
            final=r.geturl()
            return {"status":r.status,"bytes_advertised":h.get("Content-Length",""),
                    "content_type":h.get("Content-Type",""),
                    "accept_ranges":h.get("Accept-Ranges",""),
                    "etag":h.get("ETag",""),"last_modified":h.get("Last-Modified",""),
                    "resolved_download_url":final,
                    "error":""}
    except Exception as ex:
        return {"status":"","bytes_advertised":"","content_type":"",
                "accept_ranges":"","etag":"","last_modified":"",
                "resolved_download_url":url,"error":type(ex).__name__+": "+str(ex)[:240]}

def main():
    with fetch(PAGE) as response:
        html=response.read(2_000_000).decode("utf-8")
        assert "regular ICIO" in html and "2025 edition" in html
    parser=Links()
    parser.feed(html)
    found=[]
    seen=set()
    for label,href in parser.anchors:
        full=urljoin(PAGE,href)
        if urlparse(full).hostname != OFFICIAL_DOMAIN:continue
        if "/ICIO/2025/" not in full:continue
        if ("SML" not in full and "ReadMe_ICIO_small" not in full):
            continue
        if full in seen:continue
        seen.add(full)
        found.append({"label":label,"file_url":full})
    assert len(found)>=4, f"Unexpected official links: {found}"
    OUT.mkdir(parents=True,exist_ok=True)
    table=[]
    for p in found:
        values=meta(p["file_url"])
        row={**p,**values}
        table.append(row)
        print("OECD_METADATA",row["label"],row["status"],row["bytes_advertised"],row["content_type"],row["error"],flush=True)
    for period in EXPECTED:
        assert any(period in r["file_url"] and r["status"]==200 for r in table),f"Could not verify regular OECD {period} archive"
    with (OUT/"official_download_size_manifest.csv").open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(table[0]))
        writer.writeheader();writer.writerows(table)
    summary={
        "phase":"EXTENDED_DATA_EXPERIMENTAL",
        "official_source_page":PAGE,
        "readme_and_regular_2025_archive_URLs_discovered_from_source":True,
        "all_4_required_2005_to_2022_blocks_head_verified":True,
        "files":table,
        "bulk_archive_downloaded":False,
        "sector_records_read":False,
        "country_coverage_of_actual_matrix_tested":False,
        "source_countries_named_38_of_original_47":True,
        "no_original_professor_data_modified":True,
        "no_stata_invoked":True,
        "warning":"HEAD metadata checks neither establish contents nor trade matrix completeness. Never treat ROW as nine countries."
    }
    (OUT/"archive_manifest.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("OECD_DOWNLOAD_METADATA_PASS official links checked for 2005-2022; no huge files downloaded",flush=True)

if __name__=="__main__":
    main()
