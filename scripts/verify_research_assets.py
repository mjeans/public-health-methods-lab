"""Verify research assets and citation consistency without recomputing the NHANES model."""
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
ML=ROOT/"projects/nutrition-machine-learning"
SIM=ROOT/"projects/methods-stress-test"

def main():
    manifest=json.loads((ML/"outputs/brief-provenance.json").read_text())
    assert manifest["models_refitted"] is False
    for path,expected in manifest["inputs"].items():
        actual=hashlib.sha256((ML/path).read_bytes().replace(b"\r\n",b"\n")).hexdigest()
        assert actual==expected, f"Brief input drift: {path}"
    pdf=PdfReader(ML/"output/pdf/nutrition-ml-research-brief.pdf")
    assert len(pdf.pages)==3
    text="\n".join(page.extract_text() for page in pdf.pages)
    for page in pdf.pages:
        assert len(page.extract_text())>500
        assert float(page.mediabox.width)==612 and float(page.mediabox.height)==792
    for value in ["3,999","3,947","0.8637","0.8642","-0.0004","-0.0016","+0.0008","not a peer-reviewed"]:
        assert value in text, f"Missing brief content: {value}"
    html=(ML/"outputs/research-brief.html").read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>") and '<html lang="en">' in html
    assert "<script" not in html.lower() and html.count("<svg")==2
    for name in ["measurement-error","missingness","clustering"]:
        ET.parse(SIM/f"assets/{name}.svg")
    with (SIM/"outputs/summary.csv").open(newline="") as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==68 and len({r["scenario"] for r in rows})==23
    for row in rows:
        assert int(row["attempted"])==2000 and int(row["failed"])==0
        for metric in ["coverage","reject_zero"]:
            assert 0 <= float(row[metric+"_lower"]) <= float(row[metric]) + 1e-10
            assert float(row[metric]) <= float(row[metric+"_upper"])+1e-10 <= 1+1e-9
    meta=json.loads((ROOT/".zenodo.json").read_text())
    cff=(ROOT/"CITATION.cff").read_text()
    assert meta["title"]=="Public Health Methods Lab"
    assert meta["creators"][0]["orcid"]=="0000-0002-1140-3185"
    assert meta["license"]=="mit" and "license: MIT" in cff
    assert meta["creators"][0]["orcid"] in cff and meta["title"] in cff
    assert "doi" not in meta, "Only add an actual verified archive DOI."
    print("Verified: three-page PDF, self-contained HTML, input hashes, three SVGs, 68 simulation rows, citation metadata.")

if __name__=="__main__":
    main()
