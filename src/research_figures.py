"""Accessible, data-driven SVG figures; no plotting dependencies required."""
from html import escape
from pathlib import Path

NAVY, TEAL, GRAY = "#142d42", "#087e83", "#687b89"

def text(x, y, value, size=16, color=NAVY, anchor="start", weight="400"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
            f'fill="{color}" text-anchor="{anchor}" font-weight="{weight}">{escape(str(value))}</text>')

def line(x1, y1, x2, y2, color="#dae3e9", width=1, extra=""):
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{width}" {extra}/>'

def start(title, subtitle, height, description):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>',
            '<rect width="100%" height="100%" fill="#ffffff"/>',
            '<g font-family="Arial, sans-serif">',
            text(40, 46, title, 27, weight="700"), text(40, 76, subtitle, 16, GRAY),
            line(40, 100, 960, 100)]

def save(path, parts, caption, height):
    parts.extend([text(40, height-24, caption, 14, GRAY), '</g></svg>'])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(parts)+"\n", encoding="utf-8", newline="\n")

def rates(path, rows):
    height = 490
    parts = start("What changes after age standardization?",
                  "Synthetic district surveillance | cases per 100,000 person-weeks", height,
                  "Paired crude and standardized rates. Teal horizontal intervals are approximate 95% Poisson intervals for standardized rates only.")
    left, right, maximum = 170, 610, max(r['upper_95'] for r in rows)*1.12
    scale = lambda v: left + float(v)/maximum*(right-left)
    parts += [text(670, 136, "Crude", 14, GRAY), text(765, 136, "Adjusted (95% CI)", 14, GRAY)]
    for tick in range(0, int(maximum)+1, 50):
        x=scale(tick)
        parts += [line(x, 158, x, 392), text(x, 419, tick, 14, GRAY, "middle")]
    for i, row in enumerate(rows):
        y=182+i*62
        crude, adjusted = float(row['crude_rate']), float(row['standardized_rate'])
        parts += [text(40, y+5, row['district'], 18, weight="700"),
                  line(scale(crude),y,scale(adjusted),y,GRAY,2),
                  line(scale(row['lower_95']),y,scale(row['upper_95']),y,TEAL,3),
                  f'<circle cx="{scale(crude):.1f}" cy="{y}" r="5" fill="white" stroke="{GRAY}" stroke-width="2"/>',
                  f'<circle cx="{scale(adjusted):.1f}" cy="{y}" r="6" fill="{TEAL}"/>',
                  text(670,y+5,f'{crude:.1f}'),
                  text(765,y+5,f"{adjusted:.1f} ({row['lower_95']:.1f}, {row['upper_95']:.1f})")]
    parts += [text(170,450,"Open point: crude   |   Filled point: standardized",14,GRAY)]
    save(path,parts,"Common synthetic age distribution; intervals are not tests of between-district differences.",height)

def retention(path, rows, records):
    height=700
    parts=start("Retention in care, with uncertainty",
                "Synthetic outreach groups | event: disengagement | n = 20 per group",height,
                "Kaplan-Meier step curves with pointwise Greenwood log-log 95% confidence bands, censor marks, and risk counts immediately before each displayed day.")
    left,right,top,bottom=210,950,180,470
    sx=lambda t:left+float(t)/90*(right-left)
    sy=lambda s:bottom-float(s)*(bottom-top)
    groups=list(records)
    for value in (0,.25,.5,.75,1):
        parts += [line(left,sy(value),right,sy(value)),text(left-15,sy(value)+5,f'{value:.2f}',14,GRAY,'end')]
    ticks=(0,30,60,90)
    for t in ticks:
        parts.append(text(sx(t),500,t,15,GRAY,'middle'))
    for index,group in enumerate(groups):
        color=(TEAL,NAVY)[index]
        rr=[r for r in rows if r['group']==group]
        def step(field):
            points=[(sx(0),sy(1))]
            prev=1
            for r in rr[1:]:
                points += [(sx(r['time']),sy(prev)),(sx(r['time']),sy(r[field]))]
                prev=r[field]
            return points
        upper,lower=step('upper_95'),step('lower_95')
        polygon=' '.join(f'{x:.1f},{y:.1f}' for x,y in upper+list(reversed(lower)))
        parts.append(f'<polygon points="{polygon}" fill="{color}" opacity="0.10"/>')
        points=' '.join(f'{x:.1f},{y:.1f}' for x,y in step('survival'))
        dash='stroke-dasharray="8 4"' if index else ''
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3" {dash}/>')
        for r in rr[1:]:
            if r['censored']:
                parts.append(line(sx(r['time']),sy(r['survival'])-5,sx(r['time']),sy(r['survival'])+5,color,2))
        lx=210+index*355
        parts += [line(lx,134,lx+35,134,color,3,dash),text(lx+45,140,group,16,color)]
        y=595+index*30
        parts.append(text(40,y,group,15,color))
        for t in ticks:
            count=sum(time>=t for time,event in records[group])
            parts.append(text(sx(t),y,count,16,color,'middle'))
    parts += [text(40,174,"Probability",15,GRAY),text(40,195,"retained",15,GRAY),
              text(580,532,"Days since enrollment",16,NAVY,'middle'),
              text(40,566,"Numbers at risk (just before day)",15,NAVY,weight='700'),
              text(210,653,"Shading: pointwise 95% CI   |   Small ticks: right-censoring",14,GRAY)]
    save(path,parts,"Synthetic, nonrandomized groups. Curves describe retention; they do not estimate an outreach effect.",height)

def nutrition(path, rows):
    height=510
    parts=start("Nutrient-density differences",
                "Synthetic nutrition education minus comparison | 10 participants per group",height,
                "Separate panels show fiber and sodium mean differences with illustrative normal-approximation 95% confidence intervals; the vertical line is zero.")
    for i,row in enumerate(rows):
        y=180+i*155
        low,high=float(row['lower_95']),float(row['upper_95'])
        lo,hi=min(0,low),max(0,high)
        pad=(hi-lo)*.15 or 1
        lo,hi=lo-pad,hi+pad
        sx=lambda v:300+(float(v)-lo)/(hi-lo)*590
        parts += [text(40,y-30,row['measure'],19,weight='700'),line(sx(0),y-15,sx(0),y+15,GRAY,1.5),
                  line(sx(low),y,sx(high),y,TEAL,4),
                  f'<circle cx="{sx(row["difference"]):.1f}" cy="{y}" r="7" fill="{TEAL}"/>',
                  text(40,y+8,f"{row['difference']:.2f}",24,TEAL,weight='700'),
                  text(40,y+31,f"95% CI {low:.2f} to {high:.2f}",14,GRAY)]
        for value in (lo,0,hi):
            parts.append(text(sx(value),y+44,f'{value:.1f}',14,GRAY,'middle'))
    parts.append(text(40,452,"Two-day recalls; density = mean nutrient / mean energy × 1,000.",15,GRAY))
    save(path,parts,"Illustrative normal intervals for small synthetic samples. Differences are descriptive, not causal.",height)
