"""Build the nutrition research brief from committed aggregate evidence, never refit models."""
from __future__ import annotations
import csv
import hashlib
import html
import json
from pathlib import Path
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/"projects/nutrition-machine-learning"
NAVY="#183247"; TEAL="#007f78"; MUTED="#61717d"; PALE="#eef5f5"
URL="https://github.com/mjeans/public-health-methods-lab/tree/main/projects/nutrition-machine-learning"
LABELS={"mean":"Development-mean baseline","elastic":"Elastic net","forest":"Random forest","boost":"Gradient boosting"}
INPUTS=["outputs/test-metrics.csv","outputs/dietary-comparisons.csv","outputs/selection.json","config/analysis-plan.json","outputs/cohort-flow.csv"]

def read_rows(name):
    with (PROJECT/"outputs"/name).open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def label(key):
    fs,family=key.split(":")
    return LABELS[family]+(" + diet" if fs=="diet" else " | base" if family!="mean" else "")

def paragraph(c,text,y,size=10.5,leading=15,color=NAVY,x=44,width=524,bold=False):
    style=ParagraphStyle("brief",fontName="Helvetica-Bold" if bold else "Helvetica",
                         fontSize=size,leading=leading,textColor=HexColor(color))
    p=Paragraph(text,style)
    _,height=p.wrap(width,1000)
    if y-height<45:
        raise ValueError(f"Brief text would overflow: {text[:60]}")
    p.drawOn(c,x,y-height)
    return y-height-10

def page(c,number,kicker):
    c.setFillColor(HexColor(TEAL));c.rect(0,780,612,12,fill=1,stroke=0)
    c.setFont("Helvetica-Bold",9);c.setFillColor(HexColor(TEAL));c.drawString(44,752,kicker.upper())
    c.setStrokeColor(HexColor("#d5e0e4"));c.line(44,40,568,40)
    c.setFont("Helvetica",8);c.setFillColor(HexColor(MUTED))
    c.drawString(44,26,"Matthew Jeans, PhD, PMP | Research portfolio analysis")
    c.drawRightString(568,26,f"{number} / 3")

def model_chart(c,rows,top):
    left,right=210,507;low,high=.75,1.05
    scale=lambda v:left+(float(v)-low)/(high-low)*(right-left)
    for tick in [.75,.85,.95,1.05]:
        x=scale(tick);c.setStrokeColor(HexColor("#e5ebed"));c.line(x,top-176,x,top+10)
        c.setFillColor(HexColor(MUTED));c.setFont("Helvetica",8);c.drawCentredString(x,top-192,f"{tick:.2f}")
    for i,r in enumerate(sorted(rows,key=lambda r:float(r["rmse"]),reverse=True)):
        y=top-i*27;color=TEAL if r["model"].startswith("diet:") else NAVY
        c.setFont("Helvetica",8.5);c.setFillColor(HexColor(NAVY));c.drawString(44,y-3,label(r["model"]))
        c.setStrokeColor(HexColor(color));c.setLineWidth(2)
        c.line(scale(r["rmse_lower"]),y,scale(r["rmse_upper"]),y)
        c.setFillColor(HexColor(color));c.circle(scale(r["rmse"]),y,3,fill=1,stroke=0)
        c.setFont("Helvetica",8.5);c.drawRightString(568,y-3,f'{float(r["rmse"]):.4f}')
    c.setFont("Helvetica",9);c.setFillColor(HexColor(MUTED));c.drawCentredString(355,top-211,"Weighted RMSE (HbA1c percentage points)")
    return top-230

def pair_chart(c,rows,top):
    left,right=210,545;low,high=-.018,.003
    scale=lambda v:left+(float(v)-low)/(high-low)*(right-left)
    for tick in [-.015,-.010,-.005,0]:
        x=scale(tick);c.setStrokeColor(HexColor("#e5ebed"));c.line(x,top-95,x,top+12)
        c.setFillColor(HexColor(MUTED));c.setFont("Helvetica",8);c.drawCentredString(x,top-111,f"{tick:.3f}")
    c.setDash(3,3);c.setStrokeColor(HexColor(MUTED));c.line(scale(0),top-95,scale(0),top+12);c.setDash()
    for i,r in enumerate(rows):
        y=top-i*29;name="Selected pipelines" if i==0 else LABELS[r["comparison"]]
        c.setFont("Helvetica",9);c.setFillColor(HexColor(NAVY));c.drawString(44,y-3,name)
        c.setStrokeColor(HexColor(TEAL));c.setLineWidth(2);c.line(scale(r["lower"]),y,scale(r["upper"]),y)
        c.setFillColor(HexColor(TEAL));c.circle(scale(r["rmse_difference"]),y,3,fill=1,stroke=0)
    c.setFont("Helvetica",9);c.setFillColor(HexColor(MUTED));c.drawCentredString(365,top-130,"RMSE with diet minus RMSE without diet")
    return top-148

def main():
    rows=read_rows("test-metrics.csv");pairs=read_rows("dietary-comparisons.csv")
    selection=json.loads((PROJECT/"outputs/selection.json").read_text())
    plan=json.loads((PROJECT/"config/analysis-plan.json").read_text())
    primary=pairs[0];scores={r["model"]:r for r in rows}
    base=scores[selection["champions"]["base"]];diet=scores[selection["champions"]["diet"]]
    dn=selection["development_n"];tn=int(diet["n"])
    d=float(primary["rmse_difference"]);lo=float(primary["lower"]);hi=float(primary["upper"])
    takeaway=(f"Adding diet changed weighted RMSE by {d:+.4f} HbA1c percentage points "
              f"(approximate conditional 95% interval {lo:+.4f} to {hi:+.4f}).")
    conclusion="The interval includes zero; this comparison does not establish an improvement." if lo<=0<=hi else "Read the direction and uncertainty of this contrast alongside the full report."
    abstract=(f"This benchmark asks whether two-day dietary summaries improve prediction of contemporaneously measured HbA1c beyond demographic and body measurements. "
              f"Models were developed in {dn:,} eligible adults from NHANES 2015-2016 and tested in a separate 2017-2018 sample of {tn:,} adults. "
              f"Training-only preprocessing and {plan['cv_folds']}-fold PSU-grouped cross-validation selected {label(selection['champions']['diet'])} for the dietary pipeline. "
              f"Its weighted RMSE was {float(diet['rmse']):.4f}, versus {float(base['rmse']):.4f} for the selected base pipeline. "
              f"{takeaway} {conclusion}")
    (PROJECT/"output/pdf").mkdir(parents=True,exist_ok=True)
    pdf=PROJECT/"output/pdf/nutrition-ml-research-brief.pdf"
    c=Canvas(str(pdf),pagesize=(612,792),invariant=1,pageCompression=1)
    c.setTitle("Does diet improve prediction of measured HbA1c?")
    c.setAuthor("Matthew Jeans")
    c.setSubject("Reproducible NHANES nutrition machine-learning portfolio benchmark")
    page(c,1,"Nutrition / Machine learning / Research brief")
    y=paragraph(c,"Does diet improve prediction<br/>of measured HbA1c?",719,26,30,bold=True)
    y=paragraph(c,"Independent NHANES survey cycles, transparent model selection, and a result that keeps uncertainty visible.",y,12,17,color=MUTED)
    y=paragraph(c,"Matthew Jeans, PhD, PMP | ORCID 0000-0002-1140-3185",y,9,13)
    y=paragraph(c,"ABSTRACT",y-5,10,14,color=TEAL,bold=True)
    y=paragraph(c,abstract,y,10.5,15)
    y=paragraph(c,"STUDY DESIGN",y-7,10,14,color=TEAL,bold=True)
    cards=[("DEVELOP",f"{dn:,} adults","2015-2016","30 masked PSUs"),
           ("SELECT","Training data only",f"{plan['cv_folds']}-fold grouped CV","Freeze model choices"),
           ("EVALUATE",f"{tn:,} adults","2017-2018","No test-driven selection")]
    top=y
    for i,(title,a,b,e) in enumerate(cards):
        x=44+i*179;c.setFillColor(HexColor(PALE));c.roundRect(x,top-90,166,90,6,fill=1,stroke=0)
        paragraph(c,title,top-10,9,12,TEAL,x+10,146,True)
        paragraph(c,a,top-30,11,14,NAVY,x+10,146,True)
        paragraph(c,b+"<br/>"+e,top-49,9,13,MUTED,x+10,146)
        if i<2:
            c.setStrokeColor(HexColor(TEAL));c.line(x+168,top-44,x+176,top-44)
    y=top-113
    y=paragraph(c,"WHAT THE RESULT MEANS",y,10,14,color=TEAL,bold=True)
    y=paragraph(c,"These dietary summaries did not clearly improve the selected pipeline. That does not show that nutrition is unimportant: predictive value, measurement quality, and causal dietary effects are different questions.",y,11,16)
    paragraph(c,"Scope: a reproducible portfolio analysis, not a peer-reviewed paper, clinical model, or forecast of future diabetes.",y,9,13,color=MUTED)
    c.showPage()

    page(c,2,"Results / Compare models and added value")
    y=paragraph(c,"More complexity was not the<br/>development-selected answer.",719,23,28,bold=True)
    y=paragraph(c,"Both selected pipelines use elastic net. The dietary random forest had the lowest observed test RMSE, but test performance did not replace the model selected during development.",y,10.5,15)
    y=model_chart(c,rows,y-9)
    y=paragraph(c,"Teal adds dietary features. Lines are approximate conditional 95% intervals from stratified masked-PSU resampling; they hold the fitted models fixed.",y,9,13,color=MUTED)
    y=paragraph(c,"PAIRED DIETARY ADDED VALUE",y-5,10,14,color=TEAL,bold=True)
    y=pair_chart(c,pairs,y-9)
    paragraph(c,"Negative values favor diet. Comparisons use the same test participants and the same bootstrap resamples. Family-specific rows select tuning separately for each feature set. Only the first row is the primary selected-pipeline comparison.",y,9,13,color=MUTED)
    c.showPage()

    page(c,3,"Methods / Limits / Reproduction")
    y=paragraph(c,"What makes the comparison auditable?",719,23,28,bold=True)
    sections=[
        ("Cohort and measurement","Adults aged 20 or older; not known pregnant (unknown retained); two reliable dietary recalls, positive WTDR2D, measured HbA1c, survey-design fields, and positive energy intake. Both predictor sets use identical cohorts. HbA1c is never imputed."),
        ("Predictors and training","Base: age, recorded sex, income ratio, BMI, and waist circumference. Diet adds energy and fiber, sugars, saturated fat, protein, and sodium density per 1,000 kcal. Medians, missingness indicators, and scaling are learned within training folds; laboratory outcomes and diabetes-specific variables are excluded from predictors."),
        ("Evaluation and uncertainty",f"WTDR2D weights enter fitting and evaluation. Model selection uses grouped development CV; {plan['bootstrap_replicates']:,} stratified masked-PSU bootstrap resamples quantify approximate conditional test uncertainty. These intervals exclude training/model-selection uncertainty and are not individual prediction intervals."),
        ("Limits that affect interpretation","Two recalls do not measure usual intake without error. The samples are independent cross-sections, not longitudinal follow-up. Missing HbA1c and eligibility restrictions can alter representativeness; weighting does not repair every selection process. Diagnosis and treatment may change both diet and HbA1c. Subgroup checks do not establish fairness or safety."),
        ("Reproduce and inspect","The source repository provides verified CDC file hashes, pinned dependencies, 19 unit tests, all aggregate tables, the fixed analysis plan, and numeric reference checks. Reproduction reruns the same frozen holdout; it is not a new independent validation study."),
    ]
    for title,body in sections:
        y=paragraph(c,title.upper(),y,9.5,13,color=TEAL,bold=True)
        y=paragraph(c,body,y,9.7,13.4)
    y=paragraph(c,"CODE, DATA SOURCES, AND USE",y,9.5,13,color=TEAL,bold=True)
    y=paragraph(c,f'<a href="{URL}" color="{TEAL}">Open the full project and executed results</a><br/>'
        '<a href="https://wwwn.cdc.gov/nchs/nhanes/tutorials/weighting.aspx" color="#007f78">CDC/NCHS NHANES weighting guidance</a><br/>'
        '<a href="https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/GHB_J.htm" color="#007f78">NHANES 2017-2018 glycohemoglobin documentation</a>',y,9,13)
    paragraph(c,"Code and documentation: MIT. CDC/NCHS public-use inputs remain governed by their source terms. No respondent-level records or fitted models are republished.",y,8.8,12,color=MUTED)
    c.save()

    figures=[]
    for name in ["model-comparison","dietary-added-value"]:
        svg=(PROJECT/f"assets/{name}.svg").read_text(encoding="utf-8")
        figures.append(svg[svg.index("<svg"):])
    style="body{font:17px/1.6 system-ui,sans-serif;color:#183247;background:#f4f7f8;margin:0}main{max-width:960px;margin:auto;background:white;padding:48px}h1{font-size:40px;line-height:1.15}h2{color:#007f78;margin-top:2em}a{color:#007f78}.note{background:#eef5f5;padding:18px;border-left:4px solid #007f78}svg{width:100%;height:auto}.flow{display:flex;gap:12px}.flow div{flex:1;background:#eef5f5;padding:15px}footer{font-size:14px;color:#61717d}@media(max-width:600px){main{padding:22px}h1{font-size:30px}.flow{display:block}}@media print{body{background:white}main{padding:0}svg{break-inside:avoid}}"
    body=(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nutrition ML research brief</title><style>{style}</style></head><body><main>'
          '<p>NUTRITION / MACHINE LEARNING / RESEARCH BRIEF</p><h1>Does diet improve prediction of measured HbA1c?</h1>'
          '<p>Matthew Jeans, PhD, PMP | ORCID 0000-0002-1140-3185</p>'
          f'<p class="note">{html.escape(takeaway+" "+conclusion)}</p><h2>Abstract</h2><p>{html.escape(abstract)}</p>'
          '<h2>Study design</h2><div class="flow">'
          +''.join(f'<div><strong>{a}</strong><br/>{b}<br/>{d}<br/>{e}</div>' for a,b,d,e in cards)
          +'</div><h2>Model comparison</h2>'+figures[0]+'<h2>What diet adds</h2>'+figures[1]
          +''.join(f'<h2>{html.escape(t)}</h2><p>{html.escape(b)}</p>' for t,b in sections)
          +f'<p><a href="{URL}">Full code, aggregate evidence, methods, and model card</a> | <a href="../output/pdf/nutrition-ml-research-brief.pdf">Download the three-page PDF</a></p>'
          '<footer>This portfolio analysis is not peer reviewed and is not a clinical model. Code/documentation: MIT. Data source: CDC/NCHS NHANES. No row-level records are republished.</footer></main></body></html>\n')
    (PROJECT/"outputs/research-brief.html").write_text(body,encoding="utf-8",newline="\n")
    manifest={"inputs":{p:hashlib.sha256((PROJECT/p).read_bytes().replace(b"\r\n",b"\n")).hexdigest() for p in INPUTS},
              "outputs":["outputs/research-brief.html","output/pdf/nutrition-ml-research-brief.pdf"],
              "models_refitted":False,"source":"Committed aggregate evidence from the frozen cross-cycle benchmark"}
    (PROJECT/"outputs/brief-provenance.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(pdf)

if __name__=="__main__":
    main()
