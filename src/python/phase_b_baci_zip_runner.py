"""Direct official CEPII BACI 202601 HS02 zip ingest, streaming HS85 per year.
Source data MUST be real. Records only research proxy; no causal inference.
"""
from __future__ import annotations
import hashlib,json,re,zipfile,urllib.request,shutil,os,sys
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from phase_b_baci_exposure import ROOT,SOURCE,SRC_SHA,YEARS,country_m49,create_exposures,run_model,MIN_COVERAGE
ARCHIVE="https://www.cepii.fr/DATA_DOWNLOAD/baci/data/BACI_HS02_V202601.zip"
OUT=ROOT/"outputs/phase_b_cepii_direct"
CACHE=ROOT/"_external_baci_download"
MAX_DOWNLOAD=1_500_000_000    # safety/resource cap; never quietly substitute partial dataset.
def download_archive():
    CACHE.mkdir(parents=True,exist_ok=True)
    path=CACHE/"BACI_HS02_V202601.zip"
    h=hashlib.sha256();n=0
    req=urllib.request.Request(ARCHIVE,headers={"User-Agent":"AcademicMethodsAudit/1.0","Accept":"application/zip"})
    with urllib.request.urlopen(req,timeout=120) as remote, path.open("wb") as file:
        if remote.status!=200:raise RuntimeError(f"HTTP {remote.status}")
        size=remote.headers.get("Content-Length")
        print("CEPII_OFFICIAL_RESPONSE","content_length",size,flush=True)
        if size is not None and int(size)>MAX_DOWNLOAD:raise RuntimeError("Official archive exceeds 1.5GB safety cap")
        while True:
            chunk=remote.read(1_048_576)
            if not chunk:break
            n+=len(chunk)
            if n>MAX_DOWNLOAD:raise RuntimeError("Download size exceeded safe cap")
            h.update(chunk);file.write(chunk)
            if n%(100*1_048_576)<1_048_576:print("DOWNLOAD_MIB",n//1_048_576,flush=True)
    if n<10000:raise RuntimeError("Unexpectedly small official ZIP")
    return path,h.hexdigest(),n
def filter_network(archive,importer_codes):
    results=[];meta={}
    with zipfile.ZipFile(archive) as z:
        names={}
        for item in z.infolist():
            fname=Path(item.filename).name
            match=re.fullmatch(r"BACI_HS02_Y(\d{4})_V202601\.csv",fname)
            if match:
                yr=int(match.group(1))
                if yr in names:raise RuntimeError("Duplicate year entries in archive")
                names[yr]=item
        missing=sorted(set(YEARS)-set(names))
        if missing:raise RuntimeError(f"Official ZIP lacks needed years: {missing}")
        for year in YEARS:
            member=names[year]
            if member.file_size>2_000_000_000:raise RuntimeError("Unsafe member inflated size")
            if ".." in Path(member.filename).parts:raise RuntimeError("Unexpected path traversal")
            # Only HS2002 "85xxxx" imported products, exporter i -> importer j.
            summed={}
            n_hs85=0
            with z.open(member) as source:
                for chunk in pd.read_csv(source,chunksize=180000,dtype={"k":str},usecols=["t","i","j","k","v"]):
                    x=chunk.loc[chunk.j.isin(importer_codes)&
                        (chunk.t==year)&chunk.k.str.startswith("85",na=False)]
                    if not len(x):continue
                    if not np.isfinite(x.v).all() or (x.v<0).any():raise ValueError("Invalid BACI values")
                    x=x.loc[(x.i!=x.j)&(x.i>0)&(x.j>0)]
                    n_hs85+=len(x)
                    g=x.groupby(["i","j"]).v.sum()
                    for key,val in g.items():
                        summed[key]=summed.get(key,0.)+float(val)
            if not summed:raise ValueError(f"Year {year} has no valid HS85 pairs")
            row=pd.DataFrame([(year,int(i),int(j),v) for (i,j),v in summed.items()],
                 columns=["year","exporter_m49","importer_m49","value_thousand_usd"])
            results.append(row)
            meta[year]={"original_csv":member.filename,"uncompressed_bytes":member.file_size,
                        "CRC32":member.CRC,"hs85_rows":n_hs85,"aggregated_pairs":len(row)}
            print("OFFICIAL_BACI_YEAR",year,"sample_pairs",len(row),"HS85_ROWS",n_hs85,flush=True)
    return pd.concat(results,ignore_index=True),meta
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=dict(source=ARCHIVE,upstream="CEPII BACI 202601 HS02",
         source_url="https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37",
         source_license="Etalab 2.0 per CEPII official page",
         status="BLOCKED",source_ISO3_sample="47 original countries",
         trade_years=[min(YEARS),max(YEARS)],outcome_years=[2006,2022],
         product="HS02 heading 85, broad electrical machinery, NOT observed patent/knowledge flows",
         inferences="No causal model validation; only descriptive country clustered FE if eligible",
         min_eligible_share=MIN_COVERAGE)
    try:
        if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SRC_SHA:raise RuntimeError("Original workbook changed")
        panel=pd.read_excel(SOURCE)
        assert len(panel)==846 and panel.ISO3.nunique()==47
        cw=country_m49(set(panel.ISO3))
        archive,sha,size=download_archive()
        manifest.update(zip_sha256=sha,zip_size_bytes=size)
        trade,years=filter_network(archive,set(cw.values()))
        manifest["file_metadata"]=years
        trade.to_csv(OUT/"BACI_real_HS85_aggregated_edges.csv",index=False)
        expo=create_exposures(trade,panel,cw)
        expo.to_csv(OUT/"potential_peer_tech_exposure.csv",index=False)
        # Means of partner RnD and Internet are import-share exposure PROXIES,
        # not bilateral observed technology spillovers.
        eligible=int(expo.foreign_RnD_tradeweighted_lag1.notna().sum())
        stats=dict(candidate_country_years=len(expo),eligible_country_years=eligible,
                   eligible_countries=int(expo.loc[expo.foreign_RnD_tradeweighted_lag1.notna(),"ISO3"].nunique()),
                   coverage_median=float(expo.coverage.median()),
                   coverage_min=float(expo.coverage.min()),
                   coverage_max=float(expo.coverage.max()))
        manifest["coverage"]=stats
        print("REAL_NETWORK_COVERAGE",json.dumps(stats),flush=True)
        res=run_model(panel,expo,OUT)
        manifest["model_results"]=res
        manifest["status"]="REAL_BACI_PROXY_BUILT_NOT_CAUSAL"
        if not any(row["status"]=="EXPLORATORY_FE_ONLY" for row in res):
            manifest["status"]="REAL_BACI_PROXY_BUILT_BUT_REGRESSION_BLOCKED_COVERAGE"
    except Exception as exc:
        manifest["blocking_exception"]=str(exc)
        print("OFFICIAL_BACI_BLOCKED",str(exc),flush=True)
    finally:
        manifest["generated_utc"]=datetime.now(timezone.utc).isoformat()
        (OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2,default=str),encoding="utf8")
    print("OFFICIAL_BACI_STATUS",manifest["status"],flush=True)
    if manifest["status"]=="BLOCKED":raise SystemExit(2)
if __name__=="__main__":main()
