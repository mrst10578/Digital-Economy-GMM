"""Export actual Markdown research reports as editable HTML and tagged PDFs.
Run in GitHub Actions; output is an artifact, not an estimated model.
"""
from pathlib import Path
from markdown import markdown
from weasyprint import HTML

css="""
@page { size: A4; margin: 18mm 16mm 17mm 16mm; @bottom-center {content: counter(page); font-size:9pt; color:#57616f;} }
html { direction: rtl; lang: fa; }
body { font-family:'Noto Naskh Arabic','DejaVu Sans',sans-serif; direction:rtl;
       color:#1b2738; font-size:10pt; line-height:1.65; }
h1,h2,h3 { color:#18466c; break-after:avoid; font-weight:700; }
h1 {font-size:18pt;border-bottom:2px solid #b9cad6;padding-bottom:7px}
h2 {font-size:13pt;margin-top:14pt;border-bottom:1px solid #e2e8ef;}
h3 {font-size:11pt;}
p {margin:6px 0;text-align:justify}
table { width:100%; border-collapse:collapse; margin:9px 0; font-size:7.7pt; }
thead { display:table-header-group; }
th,td {border:1px solid #c9d5df;padding:3px 5px;vertical-align:top;word-break:break-word}
th {background:#e8f0f5; color:#17324b;}
tr {break-inside:avoid;}
code {font-family:'DejaVu Sans Mono',monospace;direction:ltr;unicode-bidi:embed;font-size:8pt}
pre {white-space:pre-wrap;direction:ltr;unicode-bidi:embed;background:#eff3f5;padding:7px}
strong {color:#102a3f}
"""
Path("reports").mkdir(exist_ok=True)
for name in ["FINAL_REPORT_FA","FINAL_SCIENTIFIC_VERDICT_FA","STATA_REAL_RESULTS_AUDIT_FA","DEFENSE_GUIDE_FA","CHEATSHEET_FA"]:
    src=Path("docs")/(name+".md")
    assert src.is_file(),src
    body=markdown(src.read_text(encoding="utf-8"),extensions=["tables","fenced_code"])
    output=f'<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><style>{css}</style></head><body>{body}</body></html>'
    html=Path("reports")/(name+".html")
    html.write_text(output,encoding="utf-8")
    result=Path("reports")/(name+".pdf")
    HTML(string=output,base_url=str(Path.cwd())).write_pdf(str(result))
    assert result.stat().st_size>2000
    print(name,"PDF_BYTES",result.stat().st_size,"HTML_BYTES",html.stat().st_size,flush=True)
