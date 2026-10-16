"""Read *this repository's* original source manuscripts, dictionary, and workbook.
No estimation takes place in this step. Emits an auditable source digest in CI logs.
"""
from pathlib import Path
import hashlib, json, zipfile
import xml.etree.ElementTree as ET
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "sources"
WNS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

def docx_text(path):
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
        for p in root.iter(WNS+"p"):
            text = "".join(t.text or "" for t in p.iter(WNS+"t"))
            if text.strip():
                yield text.strip()

def main():
    print("SOURCE_REVIEW_VERSION=2026-10-08-1", flush=True)
    paths = [
        *SRC.glob("*.docx"),
        SRC/"Balanced_Panel_Data.xlsx",
        ROOT/"data/raw/Balanced_Panel_Data.xlsx",
        SRC/"Data_Dictionary.xlsx",
        SRC/"01_Pre_estimation_2026-10-07.png",
        SRC/"02_Post_estimation_2026-10-07.png",
        SRC/"EMAIL_NOTE_2026-09-30.txt",
        ROOT/"research-packages/Digital_Economy_Ready_Package.zip",
    ]
    for p in paths:
        print("FILE", json.dumps({"path":str(p.relative_to(ROOT)),
                  "available":p.is_file(), "size":p.stat().st_size if p.is_file() else None,
                  "sha256":hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None},
                  ensure_ascii=False), flush=True)
    docs = list(SRC.glob("*.docx"))
    if len(docs)!=1:
        raise RuntimeError(f"Expected one study Word document; found {len(docs)}")
    print("WORD_TEXT_BEGIN", flush=True)
    for i,p in enumerate(docx_text(docs[0]),1):
        print(f"P{i:04d}: {p}",flush=True)
    print("WORD_TEXT_END", flush=True)
    book = SRC/"Data_Dictionary.xlsx"
    for sh in pd.ExcelFile(book).sheet_names:
        data=pd.read_excel(book,sheet_name=sh)
        print("DICTIONARY",sh,"SHAPE",data.shape,flush=True)
        print(data.to_string(index=False,max_rows=150,max_cols=30),flush=True)
    df=pd.read_excel(ROOT/"data/raw/Balanced_Panel_Data.xlsx")
    print("DATA_SHEETS",pd.ExcelFile(ROOT/"data/raw/Balanced_Panel_Data.xlsx").sheet_names,flush=True)
    print("DATA_DTYPES",df.dtypes.astype(str).to_json(),flush=True)
    print("DATA_COLUMNS",list(df.columns),flush=True)
    print("DATA_SHAPE",df.shape,flush=True)
    print("DATA_HEAD",df.head(4).to_string(index=False),flush=True)
    print("DATA_COUNTRIES",sorted(df.ISO3.astype(str).unique()),flush=True)
    print("YEAR_RANGE",df.Year.min(),df.Year.max(),"YEARS",sorted(df.Year.unique()),flush=True)
    print("KEY_DUPLICATES",int(df.duplicated(["ISO3","Year"]).sum()),flush=True)
    print("COUNTRY_YEAR_COUNT",df.groupby("ISO3").Year.nunique().to_json(),flush=True)
    print("MISSING_BY_COLUMN",df.isna().sum().to_json(),flush=True)
    numeric=df.select_dtypes(include="number")
    print("NUMERIC_DESCRIBE",numeric.describe().to_string(),flush=True)
    print("NONPOSITIVE", (numeric<=0).sum().to_json(),flush=True)
    print("CORRELATION",numeric.corr().round(3).to_string(),flush=True)
    for k in ["Growth","Productivity","Internet","Broadband","ICT_Exports","Unemployment","Inflation","RnD"]:
        if k in df:
            print("EXTREMES",k,"MIN",df.nsmallest(5,k)[["ISO3","Year",k]].to_json(orient="records"),
                  "MAX",df.nlargest(5,k)[["ISO3","Year",k]].to_json(orient="records"),flush=True)
    print("SOURCE_REVIEW_COMPLETED=YES", flush=True)

if __name__=="__main__":
    main()
