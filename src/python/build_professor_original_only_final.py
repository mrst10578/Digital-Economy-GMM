"""Build the professor's original-data-only PDF/DOCX/ZIP from checked repository evidence.

DOES NOT run or refit Stata. The numerical content comes from genuine archived
Stata output audited by src.python.audit_professor_final_primary_delivery.
The DTA is regenerated ONLY from the original SHA-pinned historical XLSX.
Explicit allowlist prevents accidentally bundling updated WDI/Harvard/new data.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Cm, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/professor_original_only_final"
REPORT = ROOT / "docs/PROFESSOR_ORIGINAL_DATA_ONLY_HANDOFF_REPORT_2026-10-16_FA.md"
FILENAME = "PROFESSOR_ORIGINAL_DATA_ONLY_2026-10-16"
RAW = ROOT / "data/raw/Balanced_Panel_Data.xlsx"
RAW_SHA = "474d5525a37ecfbb424c9dd25d832a9ffa6eed1942bd4f4900454204810d215b"

REQUIRED = (
    "data/raw/Balanced_Panel_Data.xlsx",
    "data/processed/stata_ready.dta",
    "config/project.json",
    "stata/RUN_ALL.do",
    "stata/00_model_helpers.do",
    "stata/01_environment_and_data.do",
    "stata/02_pre_estimation.do",
    "stata/03_growth_models.do",
    "stata/04_productivity_models.do",
    "stata/05_post_estimation_and_export.do",
    "stata/tablet_diagnostics/11_professor_system_gmm_two_equations.do",
    "stata/tablet_diagnostics/13_professor_joint_digital_and_persistence.do",
    "stata/tablet_diagnostics/17_professor_exogeneity_relevance_and_unit_root.do",
    "stata/tablet_diagnostics/19_professor_final_coefficient_export.do",
    "stata/tablet_diagnostics/21_prespecified_two_outcome_difference_gmm_l23.do",
    "evidence/tablet-stata-2026-10-16/professor_system_gmm_stats.csv",
    "evidence/tablet-stata-2026-10-16/professor_system_gmm_native_stata.log",
    "evidence/tablet-stata-2026-10-16/professor_joint_restrictions.csv",
    "evidence/scientific-gates-2026-10-16/professor_two_primary_system_gmm_full_coefficients.csv",
    "evidence/scientific-gates-2026-10-16/professor_full_coefficient_export_real_stata.log",
    "evidence/scientific-gates-2026-10-16/productivity_unitroot_grid_stata.csv",
    "evidence/scientific-gates-2026-10-16/cips_full_64_original_r_workflow14.csv",
    "evidence/scientific-gates-2026-10-16/difference_gmm_l23_two_primary_outcomes.csv",
    "evidence/scientific-gates-2026-10-16/diff_gmm_joint_lag2_3_47_country_oos_predictive.csv",
    "docs/PROFESSOR_ORIGINAL_DATA_ONLY_HANDOFF_REPORT_2026-10-16_FA.md",
    "docs/PROFESSOR_ORIGINAL_REQUIREMENTS_AUDIT_FA.md",
    "docs/PROFESSOR_FINAL_IDENTIFICATION_FEASIBILITY_DECISION_2026-10-16_FA.md",
    "docs/PROFESSOR_NO_NEW_DATA_HARD_CONSTRAINT_2026-10-16_FA.md",
    "src/python/to_stata.py",
    "src/python/audit_professor_final_primary_delivery.py",
)
BLOCKED = (
    "harvard", "uncomtrade", "bilateral", "wdi_revision",
    "wdi_sensitivity", "extended", "phase_b", "peer_matching",
)

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require_sources() -> None:
    assert sha256(RAW) == RAW_SHA, "Original historical source SHA mismatch"
    assert REPORT.is_file() and REPORT.stat().st_size > 3000
    s=REPORT.read_text(encoding="utf-8")
    for marker in ("ORIGINAL_DATA_ONLY", "Hansen", "Sargan", "Difference-in-Hansen",
                   "۰٫۰۳۵۴۵", "۰٫۰۰۰۷۹۴", "۴۷ کشور", "داده جدید"):
        assert marker in s, f"Missing scientific disclosure {marker!r}"
    with (ROOT/"evidence/scientific-gates-2026-10-16/professor_two_primary_system_gmm_full_coefficients.csv").open(newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==14
    assert {(r["outcome"],r["term"]) for r in rows}=={
        (y, v) for y in ("Growth","ln_Productivity")
        for v in (f"L.{y}","Internet","Broadband","ICT_Exports",
                  "Unemployment","Inflation","RnD")
    }
    assert all((r["N"],r["countries"],r["instruments"])==("799","47","31") for r in rows)
    subprocess.run([sys.executable, "-m", "src.python.audit_professor_final_primary_delivery"],
                   cwd=ROOT,check=True)

def qt(parent, tag: str) -> None:
    if parent.find(qn(tag)) is None:
        parent.append(OxmlElement(tag))

def bidi_paragraph(p) -> None:
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    qt(p._p.get_or_add_pPr(),"w:bidi")
    for r in p.runs:
        r.font.name="Noto Naskh Arabic"
        r.font.size=Pt(10)
        rPr=r._r.get_or_add_rPr()
        qt(rPr,"w:rtl")
        rf=rPr.rFonts
        if rf is None:
            rf=OxmlElement("w:rFonts"); rPr.insert(0,rf)
        for a in ("w:ascii","w:hAnsi","w:cs","w:eastAsia"):
            rf.set(qn(a),"Noto Naskh Arabic")

def word_styles(path:Path) -> None:
    doc=Document(path)
    section=doc.sections[0]
    section.page_width=Cm(21)
    section.page_height=Cm(29.7)
    section.top_margin=Cm(1.85)
    section.bottom_margin=Cm(1.7)
    section.left_margin=Cm(1.65)
    section.right_margin=Cm(1.65)
    # Explicit RTL for body and tables, not just apparent alignment.
    normal=doc.styles["Normal"]
    normal.font.name="Noto Naskh Arabic"
    normal.font.size=Pt(10)
    normal.paragraph_format.space_after=Pt(4)
    normal.paragraph_format.line_spacing=1.20
    for stylename,size in (("Title",16),("Heading 1",15),("Heading 2",13),("Heading 3",11)):
        try:
            st=doc.styles[stylename]
            st.font.name="Noto Naskh Arabic"
            st.font.size=Pt(size)
            st.font.bold=True
            st.paragraph_format.keep_with_next=True
        except KeyError:
            pass
    for p in doc.paragraphs:
        bidi_paragraph(p)
        if p.style.name.startswith("Heading"):
            p.paragraph_format.space_before=Pt(11)
            p.paragraph_format.space_after=Pt(5)
    for table in doc.tables:
        table.alignment=WD_TABLE_ALIGNMENT.CENTER
        # Use the available A4 text width: keep 95% confidence intervals on
        # ONE line, rather than splitting each CI into stacked fragments.
        # Verified against actual 5-column regression tables in rendered PDF.
        ncols=len(table.columns)
        if ncols == 5:
            widths_cm=(3.2,2.6,2.65,2.45,6.8)
        elif ncols == 4:
            widths_cm=(5.2,3.7,3.7,5.1)
        elif ncols == 2:
            widths_cm=(8.8,8.9)
        else:
            widths_cm=tuple(17.7/ncols for _ in table.columns)
        table.autofit=False
        for column,w in zip(table.columns,widths_cm):
            column.width=Cm(w)
        for row in table.rows:
            for cell,w in zip(row.cells,widths_cm):
                cell.width=Cm(w)
        tblPr=table._tbl.tblPr
        qt(tblPr,"w:bidiVisual")
        for row_i,row in enumerate(table.rows):
            if row_i==0:
                qt(row._tr.get_or_add_trPr(),"w:tblHeader")
            for cell in row.cells:
                for p in cell.paragraphs:
                    bidi_paragraph(p)
                    for run in p.runs:
                        run.font.size=Pt(8.2)
                        if row_i==0:run.font.bold=True
    header=section.header.paragraphs[0]
    header.text="پژوهش اقتصاد دیجیتال | نسخه مخصوص استاد، فقط داده اولیه"
    bidi_paragraph(header)
    for run in header.runs:
        run.font.size=Pt(8)
    footer=section.footer.paragraphs[0]
    footer.text="ORIGINAL_DATA_ONLY | بدون ادعای اعتبار علّی تأییدشده"
    bidi_paragraph(footer)
    for run in footer.runs:
        run.font.size=Pt(8)
    doc.core_properties.title="گزارش اقتصاد دیجیتال، فقط داده اولیه استاد"
    doc.core_properties.subject="دو مدل اصلی System GMM رشد و بهره‌وری"
    doc.core_properties.author="پروژه اقتصاد دیجیتال"
    doc.save(path)

def make_documents() -> tuple[Path,Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    word=OUT/f"{FILENAME}.docx"
    pdf=OUT/f"{FILENAME}.pdf"
    subprocess.run(["pandoc",str(REPORT),"-f","gfm","-t","docx",
                   "--standalone","--metadata=lang:fa","-o",str(word)],check=True)
    word_styles(word)
    with tempfile.TemporaryDirectory(prefix="libreoffice_original_") as profile:
        subprocess.run(["libreoffice",f"-env:UserInstallation=file://{profile}",
                        "--headless","--convert-to","pdf:writer_pdf_Export",
                        "--outdir",str(OUT),str(word)],check=True,timeout=180)
    assert word.exists() and word.stat().st_size>8000
    assert pdf.exists() and pdf.stat().st_size>12000
    import subprocess as sp
    # PDFs can differ in how they Unicode-normalize Persian glyphs. Verify via extraction.
    text=sp.run(["pdftotext","-layout",str(pdf),"-"],capture_output=True,check=True).stdout.decode("utf-8",errors="replace")
    assert len(text)>2800, ("PDF has too little extractable content",len(text))
    assert "System GMM" in text and "Hansen" in text and "Internet" in text
    info=sp.run(["pdfinfo",str(pdf)],capture_output=True,check=True,text=True).stdout
    pages=int(next(x.split(":",1)[1].strip() for x in info.splitlines() if x.startswith("Pages:")))
    assert 4<=pages<=26,pages
    print(f"RTL_DOCUMENT_QA_OK pages={pages} pdf_bytes={pdf.stat().st_size} docx_bytes={word.stat().st_size}")
    return word,pdf

def create_data_and_zip(word:Path,pdf:Path)->Path:
    subprocess.run([sys.executable,"-m","src.python.to_stata"],cwd=ROOT,check=True)
    dta=ROOT/"data/processed/stata_ready.dta"
    assert dta.exists() and dta.stat().st_size>10000
    import pandas as pd
    reread=pd.read_stata(dta)
    assert len(reread)==846
    assert set(reread["ISO3"].astype(str)) and reread["Year"].nunique()==18
    assert not reread.duplicated(["ISO3","Year"]).any()
    assert len(set(reread["ISO3"]))==47
    for relative in REQUIRED:
        p=ROOT/relative
        assert p.is_file() and p.stat().st_size>0,relative
        assert not any(word in relative.lower() for word in BLOCKED), f"Blocked external data: {relative}"
        # no symlink, including parent components
        assert not p.is_symlink(),relative
    # Professor original instructions are documentation (not another dataset).
    originals=list((ROOT/"sources").glob("بررسی اثر سرریز فناوری*.docx"))
    assert len(originals)==1,originals
    allowed={Path(p) for p in REQUIRED}
    allowed.add(originals[0].relative_to(ROOT))
    readme=OUT/"README_ORIGINAL_DATA_ONLY_FA.txt"
    readme.write_text(
       "بسته نهایی فاز اول | فقط فایل تاریخی ۴۷ کشور ۲۰۰۵ تا ۲۰۲۲\n"
       "تنها منبع خام برآورد: data/raw/Balanced_Panel_Data.xlsx\n"
       "فایل DTA فقط از همین Excel مشتق شده و داده خارجی ندارد.\n"
       "دو مدل مرجع استاد System GMM هستند. Difference GMM فقط تحلیل حساسیت است.\n"
       "مدل بهره‌وری محدودیت مهم اعتبار ابزار دارد؛ گزارش PDF/Word باید کامل خوانده شود.\n"
       "این بسته اثبات اثر علّی یا تأیید قطعی فرضیه سرریز خارجی را ادعا نمی‌کند.\n"
       "RUN_ALL.do برای استفاده با مسیر صحیح محیط و افزونه xtabond2 نیاز به تنظیم دارد.\n"
       "لطفاً به هیچ وجه نتایج فاز پژوهش توسعه‌یافته را با این تحویل مخلوط نکنید.\n",
       encoding="utf-8"
    )
    files=[
      (ROOT/relative,Path(relative)) for relative in sorted(allowed)
    ]+[(word,Path(word.name)),(pdf,Path(pdf.name)),(readme,Path(readme.name))]
    manifest={
        "package":"ORIGINAL_DATA_ONLY",
        "branch":"research/digital-economy-estimation-audit-20261008",
        "only_original_dataset":True,
        "raw_source":"data/raw/Balanced_Panel_Data.xlsx",
        "raw_sha256":RAW_SHA,
        "raw_rows":846,
        "countries":47,
        "period":[2005,2022],
        "models":["Growth / System GMM twostep","ln_Productivity / System GMM twostep"],
        "scientific_causal_identification_status":"NOT_VERIFIED",
        "do_not_mix_with_extended_data":True,
        "entries": [
           {"path":str(arc),"bytes":p.stat().st_size,"sha256":sha256(p)}
           for p,arc in files
        ]
    }
    manifestpath=OUT/"MANIFEST_ORIGINAL_DATA_ONLY.json"
    manifestpath.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    output=OUT/f"{FILENAME}_FINAL.zip"
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for p,arc in files:z.write(p,str(arc))
        z.write(manifestpath,manifestpath.name)
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        names=z.namelist()
        assert "data/raw/Balanced_Panel_Data.xlsx" in names
        assert "data/processed/stata_ready.dta" in names
        assert len(names)==len(set(names))
        assert not any(any(block in n.lower() for block in BLOCKED) for n in names)
        raw=z.read("data/raw/Balanced_Panel_Data.xlsx")
        assert hashlib.sha256(raw).hexdigest()==RAW_SHA
        assert z.read("MANIFEST_ORIGINAL_DATA_ONLY.json")
    (OUT/"BUILD_RESULT_ORIGINAL_DATA_ONLY.json").write_text(json.dumps({
       "status":"PASS",
       "archive":output.name,
       "zip_entries":len(files)+1,
       "original_dataset_sha256":RAW_SHA,
       "pdf":pdf.name,
       "docx":word.name,
       "no_new_data":True,
       "causal_validity_claimed":False,
       },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"ORIGINAL_DATA_ONLY_PACKAGE_QA_PASS archive={output} bytes={output.stat().st_size} files={len(files)+1}")
    return output

def main():
    require_sources()
    word,pdf=make_documents()
    create_data_and_zip(word,pdf)

if __name__=="__main__":main()
