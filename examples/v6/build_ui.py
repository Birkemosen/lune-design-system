#!/usr/bin/env python3
"""
Lune V6 web-UI — referenceimplementering af Lune Design System 2.
Bygger dashboardet med build-time i18n oven på dist/v6/lune-ui.css.

    python build_ui.py                       # standard: --langs en,da
    python build_ui.py --langs de,en         # vælg sprog ved compile
    LUNE_UI_LANGS=da python build_ui.py      # eller via miljøvariabel (fx fra PlatformIO)

Output (i --out, standard ./dist):
    lune-ui.css(.gz)              fælles stylesheet
    <lang>/index.html(.gz)        én færdigoversat side pr. sprog
    web_ui.h                      gzip-bytes som C-arrays + sprogtabel til firmwaren

Første sprog i listen er standard/fallback. Mangler en nøgle i et katalog,
bruges engelsk (eller første sprog), og buildet advarer. Med ét sprog
udelades sprogvælgeren helt.

Sprogskift kræver ingen JavaScript: vælgeren er almindelige links til
/en/ og /da/. Firmwaren serverer "/" ud fra cookie → Accept-Language →
standardsprog (se lune_ui_pick() i web_ui.h).
"""
import argparse, gzip, json, math, os, random, sys, pathlib
FORMS_JS = (pathlib.Path(__file__).resolve().parent.parent.parent/"js"/"lune-forms.js").read_text(encoding="utf-8")
LDS_DEFS = (pathlib.Path(__file__).resolve().parent.parent.parent/"css"/"lds-svg-defs.html").read_text(encoding="utf-8")  # lds-svg-defs

ROOT = pathlib.Path(__file__).parent

# ---------------------------------------------------------------- katalog --
class Cat:
    def __init__(self, lang, fallback):
        self.d = json.load(open(ROOT / "i18n" / f"{lang}.json", encoding="utf-8"))
        self.fb = fallback
        self.missing = set()
    def __call__(self, k, **kw):
        if k in self.d: s = self.d[k]
        elif self.fb and k in self.fb.d:
            self.missing.add(k); s = self.fb.d[k]
        else:
            raise KeyError(f"Mangler i18n-nøgle: {k}")
        return s.format(**kw) if kw else s
    def num(self, x, dec=1):
        return f"{x:.{dec}f}".replace(".", self.d["_dec"])
    def meta(self, k): return self.d[k]

# ---------------------------------------------------------------- data -----
# Eksempeldata til preview. I firmwaren erstattes værdierne af binderen
# (data-bind*) eller ved server-side rendering.
Z = [
 (1,"Josephine",21.4,22.0,"calling",62,29.1,None,"sw","ble",12.0,150,"PEX 16mm"),
 (2,"Laura",20.8,21.0,"idle",18,28.2,None,"ne","ble",11.0,150,"PEX 16mm"),
 (3,"Toilet",22.6,22.0,"idle",6,28.9,None,"","probe",4.5,100,"PEX 16mm"),
 (4,"Stue rum 1",21.1,21.5,"calling",54,28.4,"primary","s","probe",22.0,150,"PEX 16mm"),
 (5,"Stue rum 2",21.0,21.5,"calling",54,28.5,"member","sw","probe",18.0,150,"PEX 16mm"),
 (6,"Soveværelse",17.8,19.0,"fault",0,22.1,None,"n","ble",14.0,200,"ALUPEX 16mm"),
]
PIPES=["PEX 12mm","PEX 14mm","PEX 16mm","PEX 17mm","PEX 18mm","PEX 20mm","ALUPEX 16mm","ALUPEX 20mm","Unknown"]
def level(z): return 0 if z[4] in ("fault","off") else max(1, math.ceil(z[5]/10))   # 10 segmenter á 10 %
def tid(z): return "Z4–5" if z[7]=="primary" else f"Z{z[0]}"
def rid(z): return "Z5" if z[7]=="member" else tid(z)

def history(z):
    random.seed(z[0]*7)
    i,n,t,tg,st=z[:5]; tgt=[]; tmp=[]; cur=tg-0.6
    for k in range(48):
        h=(k/2+10)%24; night=(h>=22 or h<6)
        g=tg-(1.5 if (night and i in (2,6)) else 0.5 if night else 0)
        tgt.append(g); cur+=(g-cur)*0.18+random.uniform(-.08,.08)
        if st=="fault" and k>=42: cur-=0.28
        tmp.append(cur)
    d=t-tmp[-1]
    for j in range(8): tmp[-8+j]+=d*(j+1)/8
    return tgt,tmp


def zone_series(z):
    """Eksempeldata til zonegrafen: 48 halvtimer bagud (fra kl. 14 i går) + 12 halvtimer frem (til kl. 20).
    Returnerer (temp, mål, ventil%, preload-flag) for fortiden og (prognose, lav, høj, planlagt mål) for fremtiden."""
    random.seed(z[0]*13)
    i,n,t,tg,st=z[:5]
    temp=[];sp=[];valve=[];pre=[]; cur=tg-0.4
    for k in range(48):
        h=(14+k/2)%24; night=(h>=22 or h<6)
        p = (i in (1,5)) and (12 <= k < 34)             # preload i går kl. 20 → i dag kl. 07
        g = tg - (1.5 if (night and i in (2,6)) else 0.5 if night else 0) + (0.4 if p else 0)
        sp.append(g); pre.append(p)
        cur += (g-cur)*0.16 + random.uniform(-.07,.07)
        if st=="fault" and k>=38: cur -= 0.22
        temp.append(cur)
        v = 0 if (st=="fault" and k>=36) else max(0, min(100, (g-cur)*140 + 25 + random.uniform(-6,6)))
        valve.append(v)
    d=t-temp[-1]
    for j in range(8): temp[-8+j]+=d*(j+1)/8
    fut,lo,hi = project(temp, [tg]*12)
    psp=[tg]*12
    return temp,sp,valve,pre,fut,lo,hi,psp

def project(temp, sp_plan, n=8, phi=0.85):
    """Dæmpet lineær fremskrivning (DESIGN.md 5.9): mindste kvadrater over de seneste n halvtimer,
    hældningen dæmpes med phi pr. halvtime, klippes til [mål−3,0 ; mål+1,5], bånd ±(σ·√k + 0,05)."""
    ys=temp[-n:]; xs=list(range(n)); mx=sum(xs)/n; my=sum(ys)/n
    b=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sum((x-mx)**2 for x in xs)
    a=my-b*mx; res=[y-(a+b*x) for x,y in zip(xs,ys)]
    sigma=max((sum(r*r for r in res)/(n-2))**0.5, 0.05)
    fut=[];lo=[];hi=[]; acc=0.0; now=temp[-1]
    for k in range(1,13):
        acc+=phi**k; v=now+b*acc
        v=min(max(v, sp_plan[k-1]-3.0), sp_plan[k-1]+1.5)
        u=sigma*k**0.5+0.05
        fut.append(v); lo.append(v-u); hi.append(v+u)
    return fut,lo,hi

def forecast_data():
    random.seed(11); temp=[]; wind=[]
    for h in range(73):
        hod=h%24; day=min(h//24,2)
        t=[11.5,12.5,10.5][day]+[4.5,3.0,2.5][day]*math.sin((hod-9)/24*2*math.pi)+random.uniform(-.25,.25)
        w=4.5+1.5*math.sin(h/9)+random.uniform(-.4,.4)
        if 18<=h<=32: w+=5.5*math.sin((h-18)/14*math.pi)
        if h>52: w-=1.5
        temp.append(t); wind.append(max(.5,w))
    return temp,wind
def cond(h):
    hod=h%24
    if 21<=h<=29: return "rain"
    if h in (44,47,50): return "cloud"
    if hod<6 or hod>=20: return "moon"
    if hod in (9,12,15) and h<24: return "sun"
    if hod in (12,15): return "partly"
    return "cloud"

# ---------------------------------------------------------------- render ---
def render(T, langs, lang_urls, css_href, inline_css=None, dev=False):
    ST={k:T(f"state.{k}") for k in ("calling","idle","fault","off")}
    H=T.meta("_h")

    def stepper(name,val,mn,mx,step,unit,label,dec=1,disabled=False):
        d=" disabled" if disabled else ""
        return (f'<div class="stepper"><button type="button" data-step="-1" aria-label="{T("common.decrease",x=label.lower())}"{d}>−</button>'
                f'<span class="value"><input type="number" inputmode="decimal" id="{name}" name="{name}" value="{val:.{dec}f}" min="{mn}" max="{mx}" step="{step}"{d}><span class="unit">{unit}</span></span>'
                f'<button type="button" data-step="1" aria-label="{T("common.increase",x=label.lower())}"{d}>+</button></div>')
    def switch(name,t,sub,on):
        return f'<label class="switch"><span class="switch-text"><b>{t}</b>{f"<small>{sub}</small>" if sub else ""}</span><input type="checkbox" role="switch" name="{name}"{" checked" if on else ""}></label>'
    def seg(name,opts,sel,label):
        return f'<div class="seg" role="radiogroup" aria-label="{label}">'+"".join(f'<label><input type="radio" name="{name}" value="{v}"{" checked" if v==sel else ""}><span>{t}</span></label>' for v,t in opts)+'</div>'
    def row(id_,label,control): return f'<div class="field row"><label for="{id_}">{label}</label>{control}</div>'
    def rstep(id_,label,*a,**k): return row(id_,label,stepper(id_,*a,label=label,**k))
    def probes(sel,name): return f'<select class="select" id="{name}" name="{name}">'+"".join(f'<option value="{k}"{" selected" if k==sel else ""}>{T("csys.probe",n=k)}</option>' for k in range(1,9))+'</select>'
    def metric(label,val,unit,bind=""):
        b=f' data-bind="{bind}"' if bind else ""
        return f'<div class="metric"><dt>{label}</dt><dd{b}>{val} <small>{unit}</small></dd></div>'
    def title(z): return f"{tid(z)} {z[1]}"

    # ---- grupperede lister, ark og gem-bjælke (DESIGN.md 15)
    def lab(id_,text): return f'<label for="{id_}">{text}</label>'
    def srow(label,control,hint="",cls=""):
        h=f"<small>{hint}</small>" if hint else ""
        return f'<div class="setting{(" "+cls) if cls else ""}"><div class="setting-label">{label}{h}</div><div class="setting-control">{control}</div></div>'
    def sstep(id_,label,*a,hint="",**k): return srow(lab(id_,label),stepper(id_,*a,label=label,**k),hint)
    def sswitch(name,t,sub,on):
        return (f'<label class="setting switch"><span class="setting-label"><b>{t}</b>{f"<small>{sub}</small>" if sub else ""}</span>'
                f'<input type="checkbox" role="switch" name="{name}"{" checked" if on else ""}></label>')
    def group(title,rows,extra="",pre=""): return f'<section class="setting-group"><h4>{title}</h4>{pre}<div class="setting-list">{rows}</div>{extra}</section>'
    def ggroup(title,sw,rows,extra="",pre=""):
        return f'<section class="setting-group"><h4>{title}</h4>{pre}<div class="setting-list gated">{sw}<div class="gated-body">{rows}</div></div>{extra}</section>'
    def subpage(label,value,body):
        return (f'<details class="subpage"><summary class="setting"><span class="sub-back">{T("common.back")}</span>'
                f'<span class="setting-label"><span>{label}</span></span><span class="setting-control"><span class="muted">{value}</span></span></summary>'
                f'<div class="subpage-body">{body}</div></details>')
    def savebar(fid):
        return (f'<footer class="savebar"><span class="save-status" id="ss-{fid}" aria-live="polite"></span>'
                f'<button type="reset" class="btn">{T("common.undo")}</button><button class="btn primary" type="submit">{T("common.save")}</button></footer>')
    def sheet(sid,hashv,icon,tone,head,status,overview,history,settings):
        tabs=[("o","overview"),("h","history"),("s","settings")]
        radios="".join(f'<input class="state tab" type="radio" name="tab-{sid}" id="t-{sid}-{k}" value="{v}" data-hash="{T("hash."+v)}" aria-label="{T("tab."+v)}"{" checked" if k=="o" else ""}>' for k,v in tabs)
        labels="".join(f'<label for="t-{sid}-{k}" data-tab="{v}">{T("tab."+v)}</label>' for k,v in tabs)
        return f'''
  <div id="sheet-{sid}" popover class="sheet" role="dialog" aria-labelledby="sheet-{sid}-t" data-hash="{hashv}">
    {radios}
    <header class="sheet-head">
      <span class="chip-icon"{f' data-tone="{tone}"' if tone else ""} aria-hidden="true">{icon}</span>
      <div><h2 id="sheet-{sid}-t">{head}</h2><p>{status}</p></div>
      <button class="sheet-close" type="button" popovertarget="sheet-{sid}" popovertargetaction="hide" aria-label="{T("sheet.close")}">×</button>
      <nav class="tabs" aria-label="{T("sheet.tabs")}">{labels}</nav>
    </header>
    <div class="sheet-body">
      <section class="tab-panel" data-tab="overview">{overview}</section>
      <section class="tab-panel" data-tab="history">{history}</section>
      <section class="tab-panel" data-tab="settings">{settings}</section>
    </div>
  </div>'''
    I_ROOM='<svg viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="3"/><path d="M4 12h8V4"/></svg>'
    I_MANI='<svg viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16"/><path d="M8 7v10M16 7v10"/></svg>'
    CL='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14"/></svg>'          # minus
    CR='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>'  # plus
    def confirm(pid, open_label, title, body, act_label, value, extra_style=""):
        """Bekræftelses-popover (LDS 5.16). Ligger i formularen, så Nulstil sender den med name=action."""
        return (f'<button class="btn danger" type="button" popovertarget="{pid}"{extra_style}>{open_label}</button>'
                f'<div id="{pid}" popover class="confirm-pop" role="alertdialog" aria-labelledby="{pid}-t" aria-describedby="{pid}-d">'
                f'<h4 id="{pid}-t">{title}</h4><p id="{pid}-d">{body}</p>'
                f'<div class="actions"><button class="btn" type="button" popovertarget="{pid}" popovertargetaction="hide" autofocus>{T("common.cancel")}</button>'
                f'<button class="btn danger-solid" type="submit" name="action" value="{value}">{act_label}</button></div></div>')

    # ---- strimmel
    def dev_chip(z):
        """Afvigelse fra mål som chip i 5 trin (scale-cold-warm): ≤−1, ≤−0,3, ±0,3, <+1, ≥+1."""
        if z[4]=="fault": return ""
        d=z[2]-z[3]; k=1 if d<=-1 else 2 if d<=-0.3 else 3 if d<0.3 else 4 if d<1 else 5
        sign="+" if d>0.05 else "−" if d<-0.05 else "±"
        return f'<span class="tile-dev" data-dev="{k}" data-bind="z{z[0]}.dev">{sign}{T.num(abs(d))}°</span>'
    tiles="".join(f'''
          <button class="tile" type="button" popovertarget="sheet-z{z[0]}" data-state="{z[4]}" data-level="{level(z)}"{f' data-group="{z[7]}"' if z[7] else ''}>
            <span class="lvl" aria-hidden="true">{"<i></i>"*10}</span>
            <span class="tile-pct" data-bind="z{z[0]}.valve">{0 if z[4] in ("fault","off") else z[5]} %</span>
            <span class="tile-id">{tid(z)}</span>
            <span class="tile-name" data-bind="z{z[0]}.name">{z[1]}</span>
            {dev_chip(z)}
            <span class="tile-val" data-bind="z{z[0]}.temp">{T("tile.fault") if z[4]=="fault" else T.num(z[2])+"°"}</span>
          </button>''' for z in Z)
    strip=f'''<nav class="strip" aria-label="{T("strip.label")}">
          <button class="tile tile-sys" type="button" popovertarget="sheet-manifold">
            <b>{T("scope.manifold")}</b>
            <span class="big" data-bind="manifold.flowret">{T.num(34.2)}° / {T.num(29.8)}°</span>
            <small data-bind="manifold.dtstate">{T("sys.dtstate",dt=T.num(4.4))}</small>
          </button>{tiles}
        </nav>'''

    # ---- grafer
    def spark(z):
        tgt,tmp=history(z)
        lo=min(min(tgt),min(tmp)); hi=max(max(tgt),max(tmp)); mid=(lo+hi)/2; span=max(hi-lo+.6,3.0)
        lo,hi=mid-span/2,mid+span/2; W,Hh=240,40
        X=lambda k: round(k*W/47,1); Y=lambda v: round(Hh-(v-lo)/(hi-lo)*Hh,1)
        tp=" ".join(f"{X(k)},{Y(v)}" for k,v in enumerate(tmp)); gp=[]
        for k,v in enumerate(tgt):
            if k and v!=tgt[k-1]: gp.append(f"{X(k)},{Y(tgt[k-1])}")
            gp.append(f"{X(k)},{Y(v)}")
        return f'<svg class="spark" viewBox="0 0 {W} {Hh}" preserveAspectRatio="none" aria-hidden="true" data-bind-spark="z{z[0]}"><polygon class="a" points="{tp} {" ".join(reversed(gp))}"/><polyline class="g" points="{" ".join(gp)}"/><polyline class="t" points="{tp}"/></svg>'
    def trend():
        random.seed(3); W,Hh=240,80; f=[];r=[]; cf=33; cr=29
        for k in range(48):
            h=(k/2+10)%24; night=(h>=22 or h<6)
            cf+=((36.5 if night else 33.5)-cf)*0.2+random.uniform(-.3,.3); cr+=((30.5 if night else 29.2)-cr)*0.2+random.uniform(-.2,.2)
            f.append(cf); r.append(cr)
        X=lambda k: round(k*W/47,1); Y=lambda v: round(Hh-(v-26)/13*Hh,1)
        pf=" ".join(f"{X(k)},{Y(v)}" for k,v in enumerate(f)); pr=" ".join(f"{X(k)},{Y(v)}" for k,v in enumerate(r))
        return f'<svg class="trend" viewBox="0 0 {W} {Hh}" preserveAspectRatio="none" role="img" aria-label="{T("trend.aria")}" data-bind-trend="manifold"><polygon class="dt" points="{pf} {" ".join(reversed(pr.split()))}"/><polyline class="f" points="{pf}"/><polyline class="r" points="{pr}"/></svg>'

    def forecast_panel():
        temp,wind=forecast_data(); W=720; X=lambda h: round(h*W/72,1)
        Yt=lambda v: round(100-(v-6)/14*100,1); Yw=lambda v: round(60-v/14*60,1)
        tp=" ".join(f"{X(h)},{Yt(v)}" for h,v in enumerate(temp)); wp=" ".join(f"{X(h)},{Yw(v)}" for h,v in enumerate(wind))
        NOW=14; now=X(NOW); p0,p1=X(20),X(31)
        gl=lambda ys: "".join(f'<line class="gl" x1="0" x2="{W}" y1="{y}" y2="{y}"/>' for y in ys)
        days="".join(f'<line class="day" x1="{X(d)}" x2="{X(d)}" y1="0" y2="100%"/>' for d in (24,48))
        thr=Yw(8)
        icons="".join(f'<svg class="ic {cond(h)}"><use href="#i-{cond(h)}"/></svg>' for h in range(0,72,3))
        dn=T.meta("_days"); labels=[dn[0],"06","12","18",dn[1],"06","12","18",dn[2],"06","12","18",""]
        xl="".join(f'<span{" class=d" if l in dn else ""}>{l}</span>' for l in labels)
        return f'''        <section class="panel">
          <header class="panel-head"><h3>{T("fc.title")}</h3><p>{T("fc.sub",model="DMI HARMONIE",time="14:05")}</p><span class="badge info">{T("fc.badge",v=T.num(0.4))}</span></header>
          <dl class="metrics">
            {metric(T("fc.now"),T.num(13.4),"°C","forecast.temp")}
            <div class="metric"><dt>{T("fc.wind")}</dt><dd class="c-info" data-bind="forecast.wind">6 <small>m/s</small> <svg class="dir" viewBox="0 0 16 16" style="--deg:296deg" aria-label="{T("fc.windFrom",dir=T.meta("_dir_ese"))}"><path d="M8 2v12M8 2l-4 4M8 2l4 4"/></svg><small>{T.meta("_dir_ese")}</small></dd></div>
            {metric(T("fc.windMax"),"11","m/s","forecast.windmax")}
            {metric(T("fc.tempMin"),T.num(6.8),"°C","forecast.tmin")}
          </dl>
          <p class="msg info"><span><b>{T("fc.msgStrong")}</b> {T("fc.msg")}</span></p>
          <div class="fc" style="--now:{NOW/72*100:.3f}%">
            <div class="fc-icons" aria-hidden="true">{icons}</div>
            <div class="fc-y"><span>20°</span><span>13°</span><span>6°</span></div>
            <div class="fc-plot fc-temp" role="img" aria-label="{T("fc.tempAria")}">
              <span class="fc-now">{T("fc.now")}</span>
              <svg viewBox="0 0 {W} 100" preserveAspectRatio="none" data-bind-fc="temp">{gl((0,50,100))}{days}<rect class="pre" x="{p0}" y="0" width="{p1-p0}" height="100"/><polyline class="tl" points="{tp}"/><rect class="past" x="0" y="0" width="{now}" height="100"/><line class="now" x1="{now}" x2="{now}" y1="0" y2="100"/></svg>
            </div>
            <div class="fc-y"><span>14</span><span>7</span><span>0</span></div>
            <div class="fc-plot fc-wind" role="img" aria-label="{T("fc.windAria")}">
              <svg viewBox="0 0 {W} 60" preserveAspectRatio="none" data-bind-fc="wind">{gl((0,30,60))}{days}<rect class="pre" x="{p0}" y="0" width="{p1-p0}" height="60"/><polygon class="wa" points="0,60 {wp} {W},60"/><polyline class="wl" points="{wp}"/><line class="thr" x1="0" x2="{W}" y1="{thr}" y2="{thr}"/><rect class="past" x="0" y="0" width="{now}" height="60"/><line class="now" x1="{now}" x2="{now}" y1="0" y2="60"/></svg>
            </div>
            <div class="fc-x" aria-hidden="true">{xl}</div>
          </div>
          <div class="fc-legend" aria-hidden="true"><span><i class="lt"></i>{T("fc.lTemp")}</span><span><i class="lw"></i>{T("fc.lWind")}</span><span><i class="lthr"></i>{T("fc.lThr")}</span><span><i class="lpre"></i>{T("fc.lPre")}</span></div>
        </section>'''

    # ---- dashboard: manifold
    comfort="".join(f'''
            <button type="button" popovertarget="sheet-z{z[0]}" data-state="{z[4]}">
              <span class="id">{rid(z)}</span>
              <span class="name">{z[1]}</span>
              <span class="val">{f'<b class="bad">{ST["fault"]}</b>' if z[4]=='fault' else f'<b class="{"c-warn" if z[3]-z[2]>0.5 else ""}">{T.num(z[2])}°</b> / {T.num(z[3])}°'}</span>
              {spark(z)}
            </button>''' for z in Z)
    balrows=[("1,00","1,08","1,08"),("0,85","0,81","0,81"),("0,40","0,44","0,44"),("1,00","0,97","0,97"),("1,00","0,97","0,97"),("0,85","—","0,85")]
    bal="".join(f'<tr><td>{rid(z)}</td>'+"".join(f'<td class="num{" c-violet" if j==1 else ""}">{v.replace(",",T.meta("_dec"))}</td>' for j,v in enumerate(r))+'</tr>' for z,r in zip(Z,balrows))
    faultz=Z[5]
    home=f'''
      <section class="view" id="v-home-sys" aria-labelledby="h-home">
        <header class="view-head"><h2 id="h-home">{T("scope.manifold")}</h2><p>{T("dash.sys.sub",zones=6,calling=3,faults=1)}</p></header>

        <div class="panel alert">
          <div class="panel-head"><h3>{T("alert.zoneFault",zone=title(faultz))}</h3></div>
          <p class="note">{T("alert.zoneFaultBody")}</p>
          <div class="panel-foot"><button class="btn" type="button" popovertarget="sheet-z6">{T("common.open",x="Z6")}</button></div>
        </div>

        <section class="panel c5">
          <header class="panel-head"><h3>{T("heat.title")}</h3><span class="badge hot">{T("badge.calling")}</span></header>
          <dl class="metrics">
            {metric(T("m.supply"),T.num(34.2),"°C","manifold.flow")}
            {metric(T("m.return"),T.num(29.8),"°C","manifold.return")}
            {metric(T("m.dt"),T.num(4.4),"K","manifold.dt")}
            {metric(T("m.opening"),"32","%","manifold.opening")}
          </dl>
          <div class="bar" style="--v:32%" role="meter" aria-valuenow="32" aria-valuemin="0" aria-valuemax="100" aria-label="{T("m.openingAria")}"><i></i></div>
          <div class="sub trend-wrap">
            <h4>{T("trend.title")} <span class="legend"><i class="lf"></i>{T("m.supply")}<i class="lr"></i>{T("m.return")}</span></h4>
            {trend()}
            <div class="axis" aria-hidden="true"><span>−24 {H}</span><span>−12 {H}</span><span>{T("trend.now")}</span></div>
          </div>
          <footer class="panel-foot"><button class="btn" type="button" popovertarget="sheet-manifold">{T("home.openManifold")}</button></footer>
        </section>

        <section class="panel c7">
          <header class="panel-head"><h3>{T("comfort.title")}</h3><p>{T("trend.title")}</p><span class="legend" aria-hidden="true"><i class="lt"></i>{T("legend.temp")}<i class="lg"></i>{T("legend.target")}</span></header>
          <div class="comfort">{comfort}
          </div>
        </section>

{forecast_panel()}
      </section>'''


    def zone_chart(z):
        temp,sp,valve,pre,fut,lo,hi,psp = zone_series(z)
        W,Hh = 600,120; N=60                          # 30 timer á 20 px; nu ved x=480
        X=lambda k: round(k*W/N,1)
        allv = temp+sp+fut+lo+hi+psp
        lo_,hi_ = min(allv), max(allv); mid=(lo_+hi_)/2; span=max(hi_-lo_+0.4, 3.0)
        ymin, ymax = mid-span/2, mid+span/2
        Y=lambda v: round(Hh-(v-ymin)/(ymax-ymin)*Hh,1)
        def step(vals, k0):
            pts=[]
            for j,v in enumerate(vals):
                k=k0+j
                if j and v!=vals[j-1]: pts.append(f"{X(k)},{Y(vals[j-1])}")
                pts.append(f"{X(k)},{Y(v)}")
            return pts
        tp=[f"{X(k)},{Y(v)}" for k,v in enumerate(temp)]
        spp=step(sp,0)
        dev=" ".join(tp)+" "+" ".join(reversed(spp))
        now=X(47)
        fp=[f"{now},{Y(temp[-1])}"]+[f"{X(47+k)},{Y(v)}" for k,v in enumerate(fut,1)]
        band=" ".join([f"{now},{Y(temp[-1])}"]+[f"{X(47+k)},{Y(v)}" for k,v in enumerate(hi,1)]+[f"{X(47+k)},{Y(v)}" for k,v in reversed(list(enumerate(lo,1)))])
        pspp=step([sp[-1]]+psp,47)
        # preload-bånd (fortid)
        bands=""; k=0
        while k<48:
            if pre[k]:
                k0=k
                while k<48 and pre[k]: k+=1
                bands+=f'<rect class="pre" x="{X(k0)}" y="0" width="{X(k)-X(k0)}" height="{Hh}"/>'
            k+=1
        grid="".join(f'<line class="gl" x1="0" x2="{W}" y1="{y}" y2="{y}"/>' for y in (0,Hh/2,Hh))
        days=f'<line class="day" x1="{X(20)}" x2="{X(20)}" y1="0" y2="{Hh}"/>'   # midnat
        svg=(f'<svg viewBox="0 0 {W} {Hh}" preserveAspectRatio="none" data-bind-zchart="z{z[0]}">'
             f'{grid}{days}{bands}<rect class="future" x="{now}" y="0" width="{W-now}" height="{Hh}"/>'
             f'<polygon class="dev" points="{dev}"/>'
             f'<polygon class="band" points="{band}"/>'
             f'<polyline class="sp" points="{" ".join(spp)}"/>'
             f'<polyline class="sp plan" points="{" ".join(pspp)}"/>'
             f'<polyline class="t" points="{" ".join(tp)}"/>'
             f'<polyline class="fc" points="{" ".join(fp)}"/>'
             f'<line class="now" x1="{now}" x2="{now}" y1="0" y2="{Hh}"/></svg>')
        vbars="".join(f'<rect x="{X(k)+1}" y="{round(18-v/100*18,1)}" width="{round(W/N-2,1)}" height="{round(v/100*18,1)}"/>' for k,v in enumerate(valve))
        vsvg=f'<svg viewBox="0 0 {W} 18" preserveAspectRatio="none" class="zc-valve-svg" aria-hidden="true">{vbars}</svg>'
        devs=[a-b for a,b in zip(temp,sp)]; avg=sum(devs)/len(devs)
        under=sum(1 for d in devs if d<-0.3)*0.5
        hh=int(under); mm=int(round((under-hh)*60))
        Hs=T.meta("_h")
        ylab="".join(f"<span>{T.num(v)}°</span>" for v in (ymax, (ymax+ymin)/2, ymin))
        xl=[f"−24 {Hs}","−18","−12","−6",T("zchart.now"),f"+6 {Hs}"]
        xpos=[round(max(0,47-48+k*12)/N*100,2) for k in range(4)] + [round(47/N*100,2), round(59/N*100,2)]   # følger datapunkterne: nu = punkt 47
        xlab="".join(f'<span style="left:{p}%"{" class=n" if j==4 else ""}>{l}</span>' for j,(l,p) in enumerate(zip(xl,xpos)))
        fault=z[4]=="fault"
        sgn=lambda v: ("+" if v>0.05 else "−" if v<-0.05 else "")+T.num(abs(v))
        return f'''
        <section class="sub" data-state="{z[4]}" aria-labelledby="zc-h-{z[0]}">
          <h4 id="zc-h-{z[0]}">{T("zchart.sub")}</h4>
          <dl class="metrics">
            {metric(T("zchart.avgDev"), sgn(avg), "°C")}
            {metric(T("zchart.under"), f"{hh} {Hs} {mm:02d}", "min")}
            {metric(T("zchart.expected",time="20:00"), T.num(fut[-1]), "°C")}
            {metric(T("zchart.valveAvg"), str(round(sum(valve)/len(valve))), "%")}
          </dl>
          <div class="zc">
            <div class="zc-y" aria-hidden="true">{ylab}</div>
            <div class="zc-plot" role="img" aria-label="{T("zchart.aria", avg=sgn(avg), exp=T.num(fut[-1]))}">{svg}</div>
            <div class="zc-vlabel" aria-hidden="true">{T("zchart.valve")}</div>
            <div class="zc-valve">{vsvg}</div>
            <div class="zc-x" aria-hidden="true">{xlab}</div>
          </div>
          <div class="fc-legend" aria-hidden="true">
            <span><i class="lt"></i>{T("legend.temp")}</span>
            <span><i class="lsp"></i>{T("legend.target")}</span>
            <span><i class="lfc"></i>{T("zchart.lForecast")}</span>
            <span><i class="lpre"></i>{T("fc.lPre")}</span>
            <span><i class="lvalve"></i>{T("zchart.valve")}</span>
          </div>
          <p class="note">{T("zchart.projHint")}</p>
          {f'<p class="msg bad"><span><b>{T("zchart.faultStrong")}</b> {T("zchart.fault")}</span></p>' if fault else ''}
        </section>'''

    # ---- Hjem → zone-ark (DESIGN.md 15.3)
    WL=T.meta("_walls"); WF=T.meta("_walls_full")
    def compass(i,walls):
        return f'<div class="compass inline" role="group" aria-label="{T("cz.walls")}"><i class="c"></i>'+"".join(f'<label data-wall="{k}"><input type="checkbox" name="z{i}_wall" value="{k}"{" checked" if k in walls else ""} aria-label="{WF[k]}"><span>{WL[k]}</span></label>' for k in "nesw")+'</div>'
    def zone_sheet(z):
        i,n,t,tg,st,fl,ret,grp,walls,src,area,sp,pipe=z
        member=grp=="member"; fault=st=="fault"; zid=f"Z{i}"
        status=T("sheet.zoneStatus",id=tid(z),temp=T.num(t),open=0 if fault else fl,state=ST[st])
        # Overblik
        alert=f'''
        <form class="panel alert" data-save="zone/{i}/recovery">
          <div class="panel-head"><h3>{T("zdash.faultTitle")}</h3></div>
          <p class="note">{T("zdash.faultBody")}</p>
          <div class="panel-foot"><button class="btn" type="submit" name="action" value="reset_fault">{T("common.resetFault")}</button></div>
        </form>''' if fault else ""
        dis=' disabled' if member else ''
        ta=T("zdash.targetAria")
        lead=(f'<p class="msg violet"><span><b>{T("cz.memberStrong",p="Z4")}</b> {T("zdash.memberNote",m=zid,p="Z4")}</span></p>'
              f'<div class="actions"><button class="btn" type="button" popovertarget="sheet-z4">{T("common.open",x="Z4–5")}</button></div>') if member else ""
        pre=f'<p class="msg info"><span><b>{T("zdash.preloadStrong")}</b> {T("zdash.preload")}</span></p>' if i in (1,5) else ""
        overview=f'''{alert}{lead}
        <form data-save="zone/{i}/target">
          <div class="climate">
            <div class="now" data-bind="z{i}.temp">{T.num(t)}<small>°C</small></div>
            <div class="target">
              <button type="button" data-step="-1" aria-label="{T("common.decrease",x=ta)}"{dis}>{CL}</button>
              <label class="value"><small>{T("zdash.target")}</small><input type="number" inputmode="decimal" name="z{i}_target" value="{tg:.1f}" min="16" max="28" step="0.5"{dis}></label>
              <button type="button" data-step="1" aria-label="{T("common.increase",x=ta)}"{dis}>{CR}</button>
            </div>
          </div>
          <p class="autosave" aria-live="polite"></p>
        </form>
        {pre}
        <dl class="metrics">
          {metric(T("zdash.opening"),0 if fault else fl,"%",f"z{i}.flow")}
          {metric(T("m.return"),T.num(ret),"°C",f"z{i}.return")}
        </dl>
        <div class="bar" style="--v:{0 if fault else fl}%" aria-hidden="true"><i></i></div>
        <dl class="kv">
          <div><dt>{T("zdash.motor")}</dt><dd class="{'c-warn' if fault else 'c-ok'}">{T("common.needsLearning") if fault else T("common.learned")}</dd></div>
          <div><dt>{T("zdash.offsetNow")}</dt><dd class="{'c-info' if i in (1,5) else ''}">{"+"+T.num(0.4) if i in (1,5) else T.num(0.0)} °C</dd></div>
          <div><dt>{T("zdash.tempFrom")}</dt><dd class="c-info">{T("src.ble") if src=="ble" else T("src.probe")}</dd></div>
        </dl>'''
        # Indstillinger
        merge=f'<option value="">{T("common.none")}</option>'+"".join(f'<option value="{y[0]}"{" selected" if (i==5 and y[0]==4) else ""}>Z{y[0]} {y[1]}</option>' for y in Z if y[0]!=i)
        pipes="".join(f'<option{" selected" if p==pipe else ""}>{p}</option>' for p in PIPES)
        L=(T("common.needsLearning"),"—","—",T.num(0,2),T("cz.endstopTimeout")) if fault else (T("common.learned"),"412 / 398",f"{T.num(0.96,2)} / {T.num(1.04,2)}",T.num(0.35,2),T("common.none"))
        motor_body=group(T("cz.motor"),
            srow(f'<span>{T("cz.ripples")}</span>',f'<span>{L[1]}</span>')+srow(f'<span>{T("cz.factors")}</span>',f'<span>{L[2]}</span>')+
            srow(f'<span>{T("zdash.preheatAdv")}</span>',f'<span>{L[3]} °C</span>')+srow(f'<span>{T("cz.lastFault")}</span>',f'<span class="{"c-bad" if fault else ""}">{L[4]}</span>'),
            f'<div class="actions"><button class="btn primary" type="submit" name="action" value="reset_fault">{T("common.resetFault")}</button></div>' if fault else "")
        group_body=group(T("zs.grouping"),srow(lab(f"z{i}_merge",T("cz.group")),f'<select class="select" id="z{i}_merge" name="z{i}_merge">{merge}</select>',T("cz.groupHint")))
        settings=f'''
        <form data-save="zone/{i}">
          {group(T("zs.comfort"),
                 sswitch(f"z{i}_enabled",T("cz.enabled"),"",st!="off")+
                 srow(lab(f"z{i}_target_s",T("legend.target")),stepper(f"z{i}_target_s",tg,16,28,0.5,"°C",ta,disabled=member).replace(f'name="z{i}_target_s"',f'name="z{i}_target"'),T("zs.memberTarget",p="Z4") if member else T("zs.targetHint")))}
          {group(T("cz.room"),
                 srow(lab(f"z{i}_name",T("cz.name")),f'<input class="input w-sm" id="z{i}_name" name="z{i}_name" value="{n}" maxlength="24">')+
                 sstep(f"z{i}_area",T("cz.area"),area,0,200,0.5,"m²")+
                 srow(f'<span>{T("cz.tempFrom")}</span>',seg(f"z{i}_src",[("probe",T("cz.probe")),("ble",T("cz.ble"))],src,T("cz.tempFrom")))+
                 srow(lab(f"z{i}_ble",T("cz.bleMac")),f'<input class="input w-md" id="z{i}_ble" name="z{i}_ble" placeholder="AA:BB:CC:DD:EE:FF" pattern="^([0-9A-Fa-f]{{2}}:){{5}}[0-9A-Fa-f]{{2}}$" autocomplete="off" spellcheck="false"><button type="button" class="btn" data-action="ble-scan" data-zone="{i}">{T("cz.scan")}</button>',T("cz.bleHint").replace("&","&amp;"))+
                 srow(lab(f"z{i}_ret",T("cz.returnSensor")),probes(i,f"z{i}_ret")))}
          {group(T("zs.weather"),
                 srow(f'<span>{T("cz.walls")}</span>',compass(i,walls),T("zs.wallsHint"))+
                 sstep(f"z{i}_wind",T("cz.wind"),1.0 if walls else 0.0,0,2,0.1,"×")+
                 sstep(f"z{i}_solar",T("cz.solar"),0.6 if "s" in walls else 0.2,0,2,0.1,"×"))}
          {group(T("zs.floor"),
                 sstep(f"z{i}_spacing",T("cz.spacing"),sp,50,300,25,"mm",dec=0)+
                 srow(lab(f"z{i}_pipe",T("cz.pipeType")),f'<select class="select" id="z{i}_pipe" name="z{i}_pipe">{pipes}</select>')+
                 sstep(f"z{i}_lead",T("cz.lead"),3.0,0,12,0.5,H))}
          {group(T("zs.advanced"),
                 subpage(T("zs.motorCal"),L[0],motor_body)+subpage(T("zs.grouping"),"Z4" if i==5 else T("common.none"),group_body),
                 f'<p class="note">{T("zs.advancedNote")}</p>')}
          <div class="actions">{confirm(f"cf-relearn-{i}", T("cz.relearn"), T("cz.relearnConfirm",z=zid)+"?", T("cz.relearnNote",z=zid), T("cz.relearnConfirm",z=zid), "reset_relearn")}</div>
          {savebar(f"zone-{i}")}
        </form>'''
        return sheet(f"z{i}",f"z{i}",I_ROOM,"",n,status,overview,zone_chart(z),settings)

    # ---- manifold-ark
    def manifold_sheet():
        status=T("sheet.manifoldStatus",flow=T.num(34.2),ret=T.num(29.8),dt=T.num(4.4),open=32)
        overview=f'''
        <dl class="metrics">
          {metric(T("m.supply"),T.num(34.2),"°C","manifold.flow")}
          {metric(T("m.return"),T.num(29.8),"°C","manifold.return")}
          {metric(T("m.dt"),T.num(4.4),"K","manifold.dt")}
          {metric(T("m.opening"),"32","%","manifold.opening")}
        </dl>
        <div class="bar" style="--v:32%" role="meter" aria-valuenow="32" aria-valuemin="0" aria-valuemax="100" aria-label="{T("m.openingAria")}"><i></i></div>
        <div class="sub"><h4>{T("bal.title")} <span class="badge violet">{T("bal.adaptive")}</span></h4>
          <div class="table-wrap"><table class="table">
            <thead><tr><th>{T("bal.zone")}</th><th class="num">{T("bal.prior")}</th><th class="num">{T("bal.learned")}</th><th class="num">{T("bal.effective")}</th></tr></thead>
            <tbody>{bal}</tbody>
          </table></div></div>'''
        history=f'''
        <div class="sub trend-wrap">
          <h4>{T("trend.title")} <span class="legend"><i class="lf"></i>{T("m.supply")}<i class="lr"></i>{T("m.return")}</span></h4>
          {trend()}
          <div class="axis" aria-hidden="true"><span>−24 {H}</span><span>−12 {H}</span><span>{T("trend.now")}</span></div>
        </div>'''
        settings=f'''
        <form data-save="regulation">
          {group(T("csys.heating"),
                 srow(f'<span>{T("csys.heatMode")}</span>',seg("heat_mode",[("normal",T("csys.heatNormal")),("heat_pump",T("csys.heatPump"))],"heat_pump",T("csys.heatMode")))+
                 sstep("heat_min_open",T("csys.minOpening"),0,0,100,1,"%",dec=0))}
          <section class="setting-group hp-limits"><h4>{T("csys.heatPumpLimits")}</h4><div class="setting-list">
                 {sstep("hp_demand",T("csys.hpDemand"),80,30,100,1,"%",dec=0)}
                 {sstep("hp_base",T("csys.hpBase"),60,30,100,1,"%",dec=0)}
                 {sstep("hp_overheat",T("csys.hpOverheat"),1.0,0.3,3.0,0.1,"°C")}
                 {sstep("hp_trim",T("csys.hpTrim"),35,0,100,1,"%",dec=0)}</div></section>
          {group(T("csys.balancing"),
                 srow(f'<span>{T("csys.mode")}</span>',seg("bal_mode",[("static",T("csys.static")),("adaptive",T("csys.adaptive"))],"adaptive",T("csys.mode")))+
                 sstep("bal_interval",T("csys.interval"),300,60,3600,60,"s",dec=0)+
                 sstep("bal_step",T("csys.step"),0.02,0.01,0.2,0.01,"",dec=2)+
                 sstep("bal_min",T("csys.minFactor"),0.3,0.1,1,0.05,"",dec=2)+
                 sstep("bal_max",T("csys.maxFactor"),1.5,1,3,0.05,"",dec=2))}
          {ggroup(T("csys.preheat"),sswitch("preheat_enabled",T("csys.absorb"),T("csys.absorbSub"),False),
                  sstep("ph_band",T("csys.band"),0.5,0.1,3,0.1,"°C")+sstep("ph_delta",T("csys.delta"),0.3,0.1,2,0.1,"°C"))}
          {ggroup(T("csys.weather"),sswitch("forecast_enabled",T("csys.windPreload"),T("csys.windPreloadSub"),True),
                  srow(lab("fc_model",T("csys.model")),'<select class="select" id="fc_model" name="fc_model"><option>DMI HARMONIE</option><option>ICON-EU</option><option>ECMWF IFS</option></select>')+
                  sstep("fc_thr",T("csys.loadThr"),0.5,0,2,0.05,"",dec=2)+
                  sstep("fc_max",T("csys.maxOffset"),1.5,0,4,0.1,"°C")+
                  srow(f'<span>{T("ms.forecast")}</span>',f'<button class="btn" type="submit" name="action" value="fetch">{T("csys.fetchNow")}</button>',T("csys.fetched",time="14:05")))}
          <div class="actions">{confirm('cf-bal', T("csys.resetBal"), T("csys.resetBalConfirm")+'?', T("csys.resetBalNote"), T("csys.resetBalConfirm"), 'reset_balancing')}</div>
          {savebar("regulation")}
        </form>'''
        return sheet("manifold",T("hash.manifold"),I_MANI,"",T("scope.manifold"),status,overview,history,settings)

    # ---- System (DESIGN.md 15.4)
    zone_opts="".join(f'<option value="{z[0]}">Z{z[0]} {z[1]}</option>' for z in Z)
    def syscat(cat,title,body,badge=""):
        return (f'<section class="sys-cat" data-cat="{cat}" aria-labelledby="h-c-{cat}"><label class="sys-back" for="c-none">{T("sys.title")}</label>'
                f'<header><div><small>{T("sys.title")}</small><h2 id="h-c-{cat}">{title}</h2></div>{badge}</header>{body}</section>')
    CATS=[("device",T("cat.device"),'<path d="M4 11l8-7 8 7v9H4z"/>'),
          ("manifold",T("csys.mm"),'<path d="M4 7h16M4 12h16M4 17h16"/>'),
          ("connections",T("cat.connections"),'<path d="M9 15l6-6M7 13l-2 2a3 3 0 0 0 4 4l2-2M17 11l2-2a3 3 0 0 0-4-4l-2 2"/>'),
          ("firmware",T("cat.firmware"),'<path d="M12 4v10M8 10l4 4 4-4M5 19h14"/>'),
          ("service",T("csys.service"),'<path d="M14 6a4 4 0 0 0-5 5l-5 5 3 3 5-5a4 4 0 0 0 5-5l-2 2-3-3z"/>')]
    if dev: CATS.append(("motorlab",T("cat.motorlab"),'<circle cx="12" cy="12" r="7"/><path d="M12 8v4l3 2"/>'))
    cats_html=[]
    cats_html.append(syscat("device",T("cat.device"),f'''
      <form data-save="device">
        {group(T("dev.identity"),srow(lab("device_name",T("dev.name")),'<input class="input w-sm" id="device_name" name="device_name" value="Stueetage" maxlength="24">'))}
        {group(T("dev.location"),
               srow(lab("fc_lat",T("csys.lat")),'<input class="input w-sm" id="fc_lat" name="fc_lat" type="number" inputmode="decimal" step="0.0001" min="-90" max="90" value="55.2700">')+
               srow(lab("fc_lon",T("csys.lon")),'<input class="input w-sm" id="fc_lon" name="fc_lon" type="number" inputmode="decimal" step="0.0001" min="-180" max="180" value="9.9000">'),
               f'<p class="note">{T("dev.locationNote")}</p>')}
        {group(T("dev.bleClock"),sswitch("ble_clock",T("dev.bleClockSw"),T("dev.bleClockSub"),True))}
        {savebar("device")}
      </form>'''))
    cats_html.append(syscat("manifold",T("csys.mm"),f'''
      <form data-save="manifold">
        {group(T("csys.manifold"),
               srow(f'<span>{T("csys.valveType")}</span>',seg("manifold_type",[("no",T("csys.no")),("nc",T("csys.nc"))],"nc",T("csys.valveType")))+
               srow(lab("probe_flow",T("csys.supplyProbe")),probes(7,"probe_flow"))+
               srow(lab("probe_return",T("csys.returnProbe")),probes(8,"probe_return")))}
        {ggroup(T("csys.motors"),sswitch("motor_drivers",T("csys.drivers"),T("csys.driversSub"),True),
                srow(lab("motor_type",T("csys.motorType")),'<select class="select" id="motor_type" name="motor_type"><option>Generic</option><option selected>HmIP VdMot</option></select>')+
                sstep("m_runtime",T("csys.maxRun"),45,10,120,5,"s",dec=0))}
        {group(T("zs.advanced"),
               subpage(T("csys.closeStop"),"180 mA",group(T("csys.closeStop"),
                   sstep("m_cthr",T("csys.threshold"),180,50,500,10,"mA",dec=0)+sstep("m_cslope",T("csys.slope"),12,1,50,1,"",dec=0)+sstep("m_cfloor",T("csys.slopeFloor"),4,0,20,1,"",dec=0)))+
               subpage(T("csys.openStop"),"160 mA",group(T("csys.openStop"),
                   sstep("m_othr",T("csys.threshold"),160,50,500,10,"mA",dec=0)+sstep("m_oslope",T("csys.slope"),10,1,50,1,"",dec=0)+sstep("m_ofloor",T("csys.slopeFloor"),4,0,20,1,"",dec=0)+sstep("m_ripple",T("csys.ripple"),600,100,2000,50,"",dec=0)))+
               subpage(T("csys.relearn"),T("sys.relearnVal",n=200),group(T("csys.relearn"),
                   sstep("m_relmov",T("csys.afterMoves"),200,10,2000,10,"",dec=0)+sstep("m_relh",T("csys.afterHours"),168,1,720,1,H,dec=0)+sstep("m_minsamp",T("csys.minSamples"),3,1,20,1,"",dec=0)+sstep("m_maxdev",T("csys.maxDev"),0.15,0.01,1,0.01,"",dec=2))),
               f'<p class="note">{T("csys.limitsMsg")}</p>')}
        {savebar("manifold")}
      </form>'''))
    cats_html.append(syscat("connections",T("cat.connections"),f'''
      <form data-save="connections" data-state="approved">
        {group(T("conn.touch"),
               srow(f'<span>{T("conn.state")}</span>',f'<span class="badge ok">{T("conn.approved")}</span>')+
               srow(f'<span>{T("conn.provides")}</span>',f'<span>{T("conn.providesVal")}</span>')+
               srow(f'<span>{T("conn.host")}</span>','<span class="mono">192.168.20.186</span>'),
               f'<p class="note" data-show-when="unpaired">{T("conn.unpairedNote")}</p>')}
        <div class="actions">
          <button class="btn primary" type="submit" name="action" value="approve_touch" data-show-when="unpaired">{T("conn.approve")}</button>
          <span data-show-when="approved error">{confirm("cf-touch", T("conn.disconnect"), T("conn.disconnectConfirm")+"?", T("conn.disconnectNote"), T("conn.disconnectConfirm"), "disconnect_touch")}</span>
        </div>
      </form>'''))
    cats_html.append(syscat("firmware",T("cat.firmware"),f'''
      <form data-save="firmware">
        {group(T("fw.firmware"),
               srow(f'<span>{T("fw.version")}</span>','<span>6.4.2</span>')+srow('<span>ESPHome</span>','<span>2026.9.1</span>')+
               srow(f'<span>{T("fw.ip")}</span>','<span class="mono">192.168.20.106</span>')+
               srow(f'<span>{T("fw.update")}</span>',f'<button class="btn" type="submit" name="action" value="ota_check">{T("fw.check")}</button>'))}
        {group(T("fw.backup"),
               srow(f'<span>{T("fw.download")}</span>',f'<button class="btn" type="submit" name="action" value="backup_download">{T("fw.downloadBtn")}</button>',T("fw.downloadHint"))+
               srow(lab("backup_file",T("fw.restoreFile")),f'<label class="input file w-md" for="backup_file"><input class="sr-only" type="file" id="backup_file" name="backup_file" accept=".json"><span class="file-pick">{T("fw.pick")}</span><span class="file-name">{T("fw.noFile")}</span></label>'))}
        <div class="actions">{confirm("cf-restore", T("fw.restore"), T("fw.restoreConfirm")+"?", T("fw.restoreNote"), T("fw.restoreConfirm"), "backup_restore")}</div>
      </form>'''))
    cats_html.append(syscat("service",T("csys.service"),f'''
      <form data-save="service">
        {group(T("svc.diag"),
               srow('<span>Wi-Fi</span>','<span data-bind="wifi.rssi">−58 dBm</span>')+
               srow(f'<span>{T("dev.uptime")}</span>',f'<span data-bind="sys.uptime">6 {T("common.days")}</span>')+
               srow(f'<span>{T("csys.tasks")}</span>',f'<button class="btn" type="submit" name="action" value="dump_tasks">{T("svc.toLog")}</button>'),
               f'''<pre class="log" data-bind="log" aria-live="polite" lang="en">14:05  <span class="info">forecast</span> fetched, max wind 11 m/s
14:05  <span class="violet">balancing</span> Z3 0.42 → 0.44
14:06  <span class="bad">motor Z6</span> end-stop timeout (45 s)
14:06  <span class="bad">zone Z6</span> FAULT, valve closed</pre>''')}
        {ggroup(T("csys.manual"),sswitch("manual_mode",T("csys.manualMode"),T("svc.manualSub"),False),
                srow(lab("man_zone",T("csys.motor")),f'<select class="select" id="man_zone" name="man_zone">{zone_opts}</select>')+
                sstep("man_target",T("csys.motorTarget"),50,0,100,5,"%",dec=0)+
                srow(f'<span>{T("svc.manualRun")}</span>',f'<button class="btn" type="submit" name="action" value="stop">{T("csys.stop")}</button><button class="btn" type="submit" name="action" value="move">{T("csys.move")}</button>'),
                pre=f'<p class="msg warn"><span>{T("csys.manualMsg")}</span></p>')}
        <div class="actions">
          {confirm('cf-probes', T("csys.resetProbes"), T("csys.resetProbesConfirm")+'?', T("csys.resetProbesNote"), T("csys.resetProbesConfirm"), 'reset_probe_map')}
          {confirm('cf-restart', T("csys.restart"), T("csys.restartConfirm")+'?', T("csys.restartNote"), T("csys.restartConfirm"), 'restart')}
        </div>
      </form>'''))
    if dev:
        cats_html.append(syscat("motorlab",T("cat.motorlab"),f'<p class="msg warn"><span>{T("motorlab.note")}</span></p>'))
    sys_radios=f'<input class="state" type="radio" name="syscat" id="c-none" checked aria-label="{T("sys.cats")}">'+"".join(
        f'<input class="state" type="radio" name="syscat" id="c-{c}" data-hash="{T("hash."+c)}" aria-label="{t}">' for c,t,_ in CATS)
    sys_nav="".join(f'<label for="c-{c}"><svg viewBox="0 0 24 24" aria-hidden="true">{ic}</svg>{t}</label>' for c,t,ic in CATS)
    sys_view=f'''
      <section class="view" id="v-sys" aria-labelledby="h-sys">
        <h2 class="sr-only" id="h-sys">{T("sys.title")}</h2>
        {sys_radios}
        <div class="sys">
          <nav class="sys-nav" aria-label="{T("sys.cats")}">{sys_nav}</nav>
          <div class="sys-main">{"".join(cats_html)}</div>
        </div>
      </section>'''

    views=home+sys_view
    sheets=manifold_sheet()+"".join(zone_sheet(z) for z in Z)

    # ---- sprogvælger (kun hvis >1 sprog)
    cur=T.meta("_lang")
    if len(langs)>1:
        links="".join(f'<a href="{lang_urls[c.meta("_lang")]}" hreflang="{c.meta("_lang")}" lang="{c.meta("_lang")}" title="{c.meta("_name")}"{" aria-current=\"true\"" if c.meta("_lang")==cur else ""}>{c.meta("_short")}</a>' for c in langs)
        langnav=f'<nav class="lang" aria-label="{T("lang.label")}">{links}</nav>'
    else:
        langnav=""

    # Dynamiske strenge til binderen (statusser, relative tider, gem-beskeder)
    rt={k:T(k) for k in ("state.calling","state.idle","state.fault","state.off","tile.fault","rt.savedOk","rt.saveFailed","rt.secondsAgo","rt.minutesAgo","rt.offline","common.learned","common.needsLearning",
                          "rt.unsaved.one","rt.unsaved.other","rt.saving","rt.nothingToSave","rt.leaveUnsaved","rt.autoSaving","rt.autoSaved","rt.autoFailed","rt.retry")}
    rt["_dec"]=T.meta("_dec"); rt["_lang"]=cur
    rt_json=json.dumps(rt,ensure_ascii=False,separators=(",",":"))

    LOGO='<svg class="logo" viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="15" fill="var(--fg)"/><path d="M10 22V12M14 22V10M18 22V13M22 22V11" stroke="var(--accent)" stroke-width="2.4" stroke-linecap="round"/></svg>'
    I_HOME='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 11l8-7 8 7v9h-5v-6H9v6H4z"/></svg>'
    I_CONF='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/></svg>'
    css_tag=f"<style>\n{inline_css}\n</style>" if inline_css else f'<link rel="stylesheet" href="{css_href}">'
    # lune-forms.js: egen fil (fælles for alle sprog, caches); inline kun i preview-filerne.
    js_tag=f"<script>\n{FORMS_JS}</script>" if inline_css else '<script src="/lune-forms.js" defer></script>'
    others="".join(f'<link rel="alternate" hreflang="{c.meta("_lang")}" href="{lang_urls[c.meta("_lang")]}">' for c in langs if c.meta("_lang")!=cur) if len(langs)>1 else ""

    return f'''<!doctype html>
<html lang="{cur}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" media="(prefers-color-scheme: light)" content="#f5f5f0">
<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#121210">
<title>{T("doc.title")}</title>
{others}
{css_tag}
</head>
<body>

<!-- TILSTAND — før .app. Rækkefølge: tilstand → omfang → tema -->
<input class="state" type="radio" name="mode" id="m-home" checked aria-label="{T("nav.home")}">
<input class="state" type="radio" name="mode" id="m-sys" data-hash="{T("hash.system")}" aria-label="{T("nav.system")}">
<input class="state" type="radio" name="scope" id="s-sys" checked aria-label="{T("scope.manifold")}">
<input class="state" type="checkbox" id="theme" aria-label="{T("theme.toggle")}">

<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <symbol id="i-sun" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"/></symbol>
  <symbol id="i-moon" viewBox="0 0 24 24"><path d="M19 14.5A7.5 7.5 0 1 1 9.5 5a6 6 0 0 0 9.5 9.5z"/></symbol>
  <symbol id="i-cloud" viewBox="0 0 24 24"><path d="M7 18h10a4 4 0 0 0 0-8 5.5 5.5 0 0 0-10.6 1.5A3.3 3.3 0 0 0 7 18z"/></symbol>
  <symbol id="i-partly" viewBox="0 0 24 24"><path d="M8 5V3.5M3.5 8H2M4.6 4.6l-1-1M11.4 4.6l1-1"/><path d="M5.4 10.4A3.5 3.5 0 0 1 11 6.6"/><path d="M9 19h8a3.5 3.5 0 0 0 0-7 4.8 4.8 0 0 0-9.2 1.3A2.9 2.9 0 0 0 9 19z"/></symbol>
  <symbol id="i-rain" viewBox="0 0 24 24"><path d="M7 14h10a4 4 0 0 0 0-8 5.5 5.5 0 0 0-10.6 1.5A3.3 3.3 0 0 0 7 14z"/><path d="M8 17l-1 3M12 17l-1 3M16 17l-1 3"/></symbol>
</svg>

<div class="app">
{LDS_DEFS}
  <div class="navbar-wrap wrap">
      <header class="header">
        <details class="device">
          <summary>{LOGO}<span class="name"><b>Lune V6</b><small data-bind="device.name">{T("device.sample")}</small></span><span class="caret" aria-hidden="true"></span></summary>
          <nav class="device-menu" aria-label="{T("nav.devices")}">
            <a href="http://192.168.20.106/" aria-current="page"><i></i>Lune V6<small>192.168.20.106 · {T("device.this")}</small></a>
            <a href="http://192.168.20.186/"><i></i>Lune Touch<small>192.168.20.186</small></a>
          </nav>
        </details>

        <nav class="mode" aria-label="{T("nav.label")}">
          <label for="m-home">{I_HOME}{T("nav.home")}</label>
          <label for="m-sys">{I_CONF}{T("nav.system")}</label>
        </nav>

        <div class="tools">
          {langnav}
          <label class="icon-btn theme-btn" for="theme" title="{T("theme.toggle")}">
            <svg class="i-sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M5 19l1.5-1.5M17.5 6.5 19 5"/></svg>
            <svg class="i-moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg>
            <span class="sr-only">{T("theme.toggle")}</span>
          </label>
        </div>
      </header>
  </div>
  <div class="top">
    <div class="wrap">
      {strip}
    </div>
  </div>

  <main class="content wrap">{views}
  </main>
{sheets}
</div>

<!-- Strenge til binderen: statusser og beskeder der skrives ved runtime -->
<script type="application/json" id="i18n">{rt_json}</script>

<!-- VALGFRI progressive enhancement: +/−, luk enhedsmenu. Gem/ugemt, autogem, ark og deep links: lune-forms.js -->
<script>
document.addEventListener('click',function(e){{var b=e.target.closest('[data-step]');
if(b&&!b.disabled){{var i=b.parentNode.querySelector('input');b.dataset.step>0?i.stepUp():i.stepDown();i.dispatchEvent(new Event('change',{{bubbles:true}}));}}
var d=document.querySelector('.device[open]');if(d&&!d.contains(e.target))d.open=false;}});
document.addEventListener('change',function(e){{var f=e.target;if(f.type==='file'){{var n=f.closest('label').querySelector('.file-name');if(n)n.textContent=f.files.length?f.files[0].name:n.dataset.empty||n.textContent;}}}});
</script>
{js_tag}
</body>
</html>
'''

# ---------------------------------------------------------------- C-header -
def c_array(name, data):
    lines=[",".join(f"0x{b:02x}" for b in data[i:i+20]) for i in range(0,len(data),20)]
    return f"static const uint8_t {name}[{len(data)}] PROGMEM = {{\n  " + ",\n  ".join(lines) + "\n};\n"

def write_header(out, css_gz, js_gz, pages):
    langs=[l for l,_ in pages]
    h=["// Genereret af build_ui.py — redigér ikke. Sprog: " + ",".join(langs),
       "#pragma once", "#include <stdint.h>", "#include <stddef.h>", "#include <string.h>",
       "#ifndef PROGMEM", "#define PROGMEM", "#endif", ""]
    h.append(c_array("LUNE_UI_CSS_GZ", css_gz))
    h.append("// /lune-forms.js (Content-Encoding: gzip) — fælles for alle sprog")
    h.append(c_array("LUNE_UI_JS_GZ", js_gz))
    for l,gz in pages: h.append(c_array(f"LUNE_UI_{l.upper()}_GZ", gz))
    h.append("struct LuneUiPage { const char *lang; const uint8_t *gz; size_t len; };")
    h.append("static const LuneUiPage LUNE_UI_PAGES[] = {")
    for l,gz in pages: h.append(f'  {{"{l}", LUNE_UI_{l.upper()}_GZ, sizeof(LUNE_UI_{l.upper()}_GZ)}},')
    h.append("};")
    h.append(f"static const size_t LUNE_UI_PAGE_COUNT = {len(pages)};")
    h.append(r'''
// Vælg side til "/": 1) cookie "lune_lang=xx", 2) første match i
// Accept-Language (i header-rækkefølge), 3) første sprog i buildet.
// Sæt cookien, når brugeren besøger /xx/ — så huskes valget uden JS.
static inline const LuneUiPage *lune_ui_find(const char *lang) {
  for (size_t i = 0; i < LUNE_UI_PAGE_COUNT; i++)
    if (lang && strncmp(lang, LUNE_UI_PAGES[i].lang, 2) == 0) return &LUNE_UI_PAGES[i];
  return nullptr;
}
static inline const LuneUiPage *lune_ui_pick(const char *cookie, const char *accept_language) {
  if (cookie) { const char *c = strstr(cookie, "lune_lang=");
    if (c) { const LuneUiPage *p = lune_ui_find(c + 10); if (p) return p; } }
  if (accept_language) {
    const char *best = nullptr; const LuneUiPage *bp = nullptr;
    for (size_t i = 0; i < LUNE_UI_PAGE_COUNT; i++) {
      const char *hit = strstr(accept_language, LUNE_UI_PAGES[i].lang);
      if (hit && (!best || hit < best)) { best = hit; bp = &LUNE_UI_PAGES[i]; }
    }
    if (bp) return bp;
  }
  return &LUNE_UI_PAGES[0];
}''')
    (out/"web_ui.h").write_text("\n".join(h), encoding="utf-8")

# ---------------------------------------------------------------- main -----
def main():
    ap=argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--langs", default=os.environ.get("LUNE_UI_LANGS","en,da"), help="kommasepareret, første = standard (default en,da)")
    ap.add_argument("--out", default="dist")
    ap.add_argument("--css", default=str(ROOT.parent.parent/"dist"/"v6"/"lune-ui.css"),
                    help="projekt-CSS bygget af tools/lds_build.py config/v6.json")
    ap.add_argument("--preview", action="store_true", help="byg også selvstændige preview-<lang>.html med inline CSS")
    ap.add_argument("--dev", action="store_true", help="dev-build: Motorlab sidst på System")
    ap.add_argument("--preview-urls", default="", help="lang=url,... til sprogvælgeren i preview-filerne")
    a=ap.parse_args()

    codes=[c.strip() for c in a.langs.split(",") if c.strip()]
    avail=sorted(p.stem for p in (ROOT/"i18n").glob("*.json"))
    for c in codes:
        if c not in avail: sys.exit(f"Ukendt sprog '{c}'. Tilgængelige: {', '.join(avail)}")
    base=Cat("en",None) if "en" in avail else None
    cats=[Cat(c, None if c=="en" else base) for c in codes]

    out=pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cssp=pathlib.Path(a.css)
    if not cssp.exists(): sys.exit(f"Mangler {cssp}. Kør først: python tools/lds_build.py config/v6.json")
    css=cssp.read_text(encoding="utf-8")
    (out/"lune-ui.css").write_text(css, encoding="utf-8")
    css_gz=gzip.compress(css.encode(), 9, mtime=0)
    (out/"lune-ui.css.gz").write_bytes(css_gz)
    (out/"lune-forms.js").write_text(FORMS_JS, encoding="utf-8")
    js_gz=gzip.compress(FORMS_JS.encode(), 9, mtime=0)
    (out/"lune-forms.js.gz").write_bytes(js_gz)

    urls={c.meta("_lang"): f"/{c.meta('_lang')}/" for c in cats}
    pages=[]
    for c in cats:
        html=render(c, cats, urls, "/lune-ui.css", dev=a.dev)
        d=out/c.meta("_lang"); d.mkdir(exist_ok=True)
        (d/"index.html").write_text(html, encoding="utf-8")
        gz=gzip.compress(html.encode(), 9, mtime=0); (d/"index.html.gz").write_bytes(gz)
        pages.append((c.meta("_lang"), gz))
        if c.missing: print(f"ADVARSEL: {c.meta('_lang')} mangler {len(c.missing)} nøgler (bruger engelsk): {', '.join(sorted(c.missing))}")
    write_header(out, css_gz, js_gz, pages)

    if a.preview:
        purls=dict(urls)
        for kv in filter(None, a.preview_urls.split(",")):
            k,v=kv.split("=",1); purls[k]=v
        for c in cats:
            (out/f"preview-{c.meta('_lang')}.html").write_text(render(c, cats, purls, None, inline_css=css, dev=a.dev), encoding="utf-8")

    total=len(css_gz)+len(js_gz)+sum(len(g) for _,g in pages)
    print(f"Byggede {', '.join(codes)} → {out}/  (flash: {total/1024:.1f} kB gzip i alt: css {len(css_gz)/1024:.1f} kB + js {len(js_gz)/1024:.1f} kB + " +
          " + ".join(f"{l} {len(g)/1024:.1f} kB" for l,g in pages) + ")")

if __name__=="__main__":
    main()
