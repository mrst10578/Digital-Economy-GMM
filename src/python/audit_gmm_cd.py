"""Validate archived native Stata GMM residual Pesaran CD tests.
This CI script does NOT run Stata, and non-rejection cannot establish independence.
"""
from __future__ import annotations
import csv
import json
import math
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/"evidence/tablet-stata-2026-10-16"
def main() -> None:
    with (E/"gmm_residual_cd.csv").open(encoding="utf-8-sig",newline="") as fh:
        rows=list(csv.DictReader(fh))
    assert len(rows)==2 and {r["outcome"] for r in rows}=={"Growth","ln_Productivity"}
    log=(E/"gmm_residual_cd.log").read_text(errors="replace")
    observations={}
    for row in rows:
        name=row["outcome"]
        assert row["rc"]=="0" and int(row["N"])==752 and int(row["groups"])==47 and int(row["years"])==16
        z=float(row["cd_stat"]); p=float(row["cd_p"])
        assert math.isfinite(z) and math.isfinite(p) and 0<=p<=1
        marker=re.search(r"^GMM_RESID_CD_OK outcome="+name+r" N=(\d+) T=(\d+) statistic=([.\d-]+) p=([.\d-]+)$",log,re.M)
        assert marker, f"Missing real output {name}"
        assert int(marker.group(1))==47 and int(marker.group(2))==16
        assert abs(z-float(marker.group(3)))<1e-6
        assert abs(p-float(marker.group(4)))<1e-6
        observations[name]={"cd_z":z,"p_value":p,"rejected_at_5pct":p<.05}
    assert "GMM_RESIDUAL_CD_COMPLETE" in log
    assert len(re.findall(r"^GMM_RESID_CD_OK",log,re.M))==2
    assert not re.search(r"(?im)^Warning:|^GMM_RESID_CD_(?:PREDICT|EST)_FAILED|^r\(\d+\);",log)
    result={
        "result":"PASS: native GMM residual CD observations verified",
        "models":observations,
        "technical_warnings":0,
        "scientific_limit":"Failure to reject CD in these two samples does not prove instrument exogeneity or full independence, nor establish technology-spillover causality.",
        "historical_FE_dependence":"Some separate two-way-FE residual CD tests rejected independence; GMM and FE residuals are distinct objects.",
        "stata_was_executed_in_ci":False
    }
    out=ROOT/"outputs/gmm_cd_audit";out.mkdir(parents=True,exist_ok=True)
    (out/"latest.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
