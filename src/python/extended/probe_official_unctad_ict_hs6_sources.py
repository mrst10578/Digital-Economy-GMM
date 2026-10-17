#!/usr/bin/env python3
"""Test ONLY official public ICT-HS classification assets with immutable hashes.

Zero guessed goods; download statuses distinguish 403, true PDF, XLS and error.
Raw official assets are retained in short-lived Actions artifacts, not committed.
"""
from __future__ import annotations
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs/extended/official_ict_hs6_probe"
HOST = "https://unctadstat.unctad.org/EN/Classifications/"
URLS = {
    **{f"UNCTAD_HS{rev}_PDF": HOST + f"DimHS{rev}Products_Ict_Hierarchy.pdf"
       for rev in (1992, 1996, 2002, 2007, 2012, 2017, 2022)},
    "EUROSTAT_HS2017_XLS": "https://ec.europa.eu/eurostat/cache/metadata/"
                          "Annexes/isoc_it_ict_esmsip2_an_ICT_goods_categories_and_compo.xls",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; academic-ICT-research-audit/1.0)",
           "Accept": "application/pdf,application/vnd.ms-excel,application/octet-stream,*/*"}
MAX_BYTES = 8_000_000


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    statuses = []
    for name, url in URLS.items():
        entry = {"name": name, "url": url, "status": "ERROR", "http_code": None,
                 "size_bytes": 0, "sha256": None, "file_kind_verified": "NONE",
                 "stored_relpath": "", "error": ""}
        for attempt in range(2):
            try:
                with urlopen(Request(url, headers=HEADERS), timeout=26) as stream:
                    response_code = stream.getcode()
                    content_type = stream.headers.get("Content-Type", "")
                    content = stream.read(MAX_BYTES + 1)
                entry["http_code"] = response_code
                if len(content) > MAX_BYTES:
                    raise ValueError("Response exceeds source download bound")
                is_pdf = content[:5] == b"%PDF-"
                is_xls = content[:8] == bytes.fromhex("D0CF11E0A1B11AE1")
                if name.endswith("_PDF") and not is_pdf:
                    raise ValueError(f"Not PDF: head={content[:20]!r} content-type={content_type}")
                if name.endswith("_XLS") and not is_xls:
                    raise ValueError(f"Not legacy XLS: head={content[:20]!r} content-type={content_type}")
                ext = ".pdf" if is_pdf else ".xls"
                target = OUT / (name + ext)
                target.write_bytes(content)
                entry.update(status="VALID_SOURCE_BYTES", size_bytes=len(content),
                             sha256=hashlib.sha256(content).hexdigest(),
                             file_kind_verified=ext.lstrip("."),
                             stored_relpath=target.name)
                break
            except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                entry["http_code"] = getattr(exc, "code", None)
                entry["error"] = f"{type(exc).__name__}: {str(exc)[:240]}"
                if isinstance(exc, HTTPError) and exc.code in (403, 404, 400):
                    break
                if attempt == 0:
                    time.sleep(1)
        statuses.append(entry)
        print("OFFICIAL_ICT_SOURCE_PROBE", name, entry["status"], entry["http_code"],
              entry["size_bytes"], entry["error"], flush=True)
    summary = {
        "phase": "EXTENDED_DATA_EXPERIMENTAL",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sources": statuses,
        "available_valid_sources": sum(x["status"] == "VALID_SOURCE_BYTES" for x in statuses),
        "no_HS6_codes_inferred_or_invented": True,
        "not_yet_approved_ICT_goods_basket": True,
        "no_Stata_or_original_professor_data_change": True,
    }
    (OUT / "SOURCE_ACCESS_PROBE.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("OFFICIAL_ICT_SOURCE_PROBE_COMPLETE", summary["available_valid_sources"],
          "of", len(statuses), flush=True)


if __name__ == "__main__":
    main()
