#!/usr/bin/env python3
"""
Lune Touch web-UI — referenceeksempel for Lune Design System 2.2 (config/touch.json).
Hjem / ark / System (DESIGN.md 15) på produktets felter (lune-coordinator/web/touch-ui).

    python build_ui.py
    python build_ui.py --langs en,da --preview --hs-type asgard

Output (i --out, standard ./dist):
    lune-ui.css(.gz)       projekt-CSS (dist/touch/lune-ui.css)
    lune-forms.js(.gz)     gem/ugemt, autogem, ark, deep links — fælles for alle sprog
    ui.js(.gz)             lille binder (varmekildens type på Varme-arket)
    <lang>/index.html(.gz) én side pr. sprog
    preview-<lang>.html    selvstændige filer med inline CSS/JS (--preview)

Eksempeldata: tre V6-styringer (Anneks er offline), én zone med motorfejl (Gang),
ét rum uden data (Lager). I produktet erstattes værdierne af binderen.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import pathlib
import random
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent
DS_ROOT = ROOT.parent.parent
LDS_DEFS = (DS_ROOT / "css" / "lds-svg-defs.html").read_text(encoding="utf-8")
FORMS_JS = (DS_ROOT / "js" / "lune-forms.js").read_text(encoding="utf-8")

# ---------------------------------------------------------------- data ----
# Styringer (V6-boards): id, navn, host, ip, online, fremløb, retur, firmware
MANIFOLDS = [
    dict(n=1, name="Teknikrum", host="lune-v6-teknik.local", ip="192.168.20.106", online=True, flow=36.0, ret=29.0, fw="6.4.2", seen=None),
    dict(n=2, name="1. sal", host="lune-v6-1sal.local", ip="192.168.20.107", online=True, flow=33.2, ret=29.6, fw="6.4.2", seen=None),
    dict(n=3, name="Anneks", host="lune-v6-anneks.local", ip="192.168.20.108", online=False, flow=30.5, ret=27.8, fw="6.4.1", seen=2),
]
# Rum: id, navn, manifold, zone, temp, mål, ventil %, tilstand, areal, cc, rør, vægge, medregn, vægt, vind, sol
# temp None = ingen data.
ROOMS = [
    ("r01", "Kontor",    1, 1, 22.9, 22.0, 18, "idle",    12.0, 150, "PEX 16 mm", "s",  True,  1.00, 0.30, 0.50),
    ("r02", "Hobbyrum",  1, 2, 23.0, 22.0, 22, "idle",    16.0, 150, "PEX 16 mm", "",   True,  1.00, 0.20, 0.20),
    ("r03", "Bryggers",  1, 3, 21.6, 21.0,  4, "idle",     8.0, 100, "PEX 16 mm", "n",  False, 0.50, 0.50, 0.00),
    ("r04", "Køkken",    1, 4, 21.7, 21.0,  0, "idle",    14.0, 150, "PEX 16 mm", "e",  True,  1.00, 0.40, 0.30),
    ("r05", "Stue",      1, 5, 21.4, 21.5, 54, "calling", 48.0, 150, "PEX 16 mm", "sw", True,  1.50, 0.60, 0.70),
    ("r06", "Josephine", 2, 1, 21.4, 22.0, 62, "calling", 12.0, 150, "PEX 16 mm", "sw", True,  1.00, 0.70, 0.40),
    ("r07", "Laura",     2, 2, 22.2, 22.0, 35, "idle",    11.0, 150, "PEX 16 mm", "ne", True,  1.00, 0.50, 0.30),
    ("r08", "Toilet",    2, 3, 22.7, 22.0, 14, "idle",     4.5, 100, "PEX 16 mm", "",   False, 0.25, 0.00, 0.00),
    ("r09", "Gang",      2, 4, 19.1, 20.0,  0, "fault",   10.0, 150, "PEX 16 mm", "n",  True,  0.75, 0.30, 0.00),
    ("r10", "Bad",       2, 5, 23.3, 22.0, 48, "idle",     8.0, 100, "ALUPEX 16 mm", "", True, 0.50, 0.00, 0.00),
    ("r11", "Værksted",  3, 1, 16.8, 18.0, 20, "idle",    22.0, 200, "PEX 20 mm", "w",  False, 0.50, 0.50, 0.20),
    ("r12", "Lager",     3, 2, None, 15.0,  0, "off",     18.0, 200, "PEX 20 mm", "",   False, 0.25, 0.30, 0.00),
]
HOUSE_TEMP, HOUSE_TARGET = 21.9, 21.0
THERMO_MIN, THERMO_MAX = 15.0, 25.0


class Cat:
    def __init__(self, lang, fallback):
        self.d = json.load(open(ROOT / "i18n" / f"{lang}.json", encoding="utf-8"))
        self.fb = fallback
        self.missing = set()

    def __call__(self, k, **kw):
        if k in self.d:
            s = self.d[k]
        elif self.fb and k in self.fb.d:
            self.missing.add(k)
            s = self.fb.d[k]
        else:
            raise KeyError(f"Mangler i18n-nøgle: {k}")
        return s.format(**kw) if kw else s

    def num(self, x, dec=1):
        return f"{x:.{dec}f}".replace(".", self.d["_dec"])

    def meta(self, k):
        return self.d[k]


def man(n):
    return next(m for m in MANIFOLDS if m["n"] == n)


def series(seed, n, base, amp, noise):
    random.seed(seed)
    return [base + amp * math.sin(k / n * 2 * math.pi - 1.2) + random.uniform(-noise, noise) for k in range(n)]


def pts(vals, w, h, lo, hi):
    return " ".join(f"{round(k * w / (len(vals) - 1), 1)},{round(h - (v - lo) / (hi - lo) * h, 1)}" for k, v in enumerate(vals))


def ensure_css(path: pathlib.Path) -> str:
    if not path.is_file():
        subprocess.run([sys.executable, str(DS_ROOT / "tools" / "lds_build.py"), str(DS_ROOT / "config" / "touch.json")], cwd=DS_ROOT, check=True)
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------- render ---
def render(T, langs, lang_urls, css_href, hs_type, inline_css=None):
    hs_type = hs_type if hs_type in ("http", "asgard") else "asgard"
    ST = {k: T(f"state.{k}") for k in ("calling", "idle", "fault", "off")}
    H = T.meta("_h")
    dash = "—"

    # ---- små byggeklodser (grupperede lister, ark, gem-bjælke)
    def stepper(name, val, mn, mx, step, unit, label, dec=1, id_=None):
        i = id_ or name
        return (f'<div class="stepper"><button type="button" data-step="-1" aria-label="{T("common.decrease", x=label.lower())}">−</button>'
                f'<span class="value"><input type="number" inputmode="decimal" id="{i}" name="{name}" value="{val:.{dec}f}" min="{mn}" max="{mx}" step="{step}">'
                f'<span class="unit">{unit}</span></span>'
                f'<button type="button" data-step="1" aria-label="{T("common.increase", x=label.lower())}">+</button></div>')

    def lab(id_, text):
        return f'<label for="{id_}">{text}</label>'

    def srow(label, control, hint="", cls=""):
        h = f"<small>{hint}</small>" if hint else ""
        return f'<div class="setting{(" " + cls) if cls else ""}"><div class="setting-label">{label}{h}</div><div class="setting-control">{control}</div></div>'

    def rrow(label, value, hint=""):  # læseværdi
        return srow(f"<span>{label}</span>", f'<span class="setting-value">{value}</span>', hint)

    def sstep(name, label, *a, hint="", id_=None, **k):
        i = id_ or name
        return srow(lab(i, label), stepper(name, *a, label=label, id_=i, **k), hint)

    def sinput(name, label, value="", cls="w-md", hint="", id_=None, typ="text", extra="", stack=False):
        i = id_ or name
        ctl = f'<input class="input {cls}" type="{typ}" id="{i}" name="{name}" value="{value}"{extra}>'
        return srow(lab(i, label), ctl, hint, cls="stack" if stack else "")

    def sswitch(name, t, sub, on, id_=None):
        return (f'<label class="setting switch"><span class="setting-label"><b>{t}</b>{f"<small>{sub}</small>" if sub else ""}</span>'
                f'<input type="checkbox" role="switch" name="{name}"{f" id={chr(34)}{id_}{chr(34)}" if id_ else ""}{" checked" if on else ""}></label>')

    def group(title, rows, extra="", pre="", attrs=""):
        return f'<section class="setting-group"{attrs}><h4>{title}</h4>{pre}<div class="setting-list">{rows}</div>{extra}</section>'

    def ggroup(title, sw, rows, extra="", pre=""):
        return f'<section class="setting-group"><h4>{title}</h4>{pre}<div class="setting-list gated">{sw}<div class="gated-body">{rows}</div></div>{extra}</section>'

    def subpage(label, value, body):
        return (f'<details class="subpage"><summary class="setting"><span class="sub-back">{T("common.back")}</span>'
                f'<span class="setting-label"><span>{label}</span></span><span class="setting-control"><span class="muted">{value}</span></span></summary>'
                f'<div class="subpage-body">{body}</div></details>')

    def savebar(fid, label=None):
        return (f'<footer class="savebar"><span class="save-status" id="ss-{fid}" aria-live="polite"></span>'
                f'<button type="reset" class="btn">{T("common.undo")}</button><button class="btn primary" type="submit">{label or T("common.save")}</button></footer>')

    def seg(name, prefix, opts, sel, label):
        """Typevalg: radioerne står før (søskende), segmentets labels peger på dem (5.18)."""
        radios = "".join(f'<input class="state" type="radio" name="{name}" id="{prefix}-{v}" value="{v}"{" checked" if v == sel else ""} aria-label="{t}">' for v, t in opts)
        labels = "".join(f'<label for="{prefix}-{v}"><span>{t}</span></label>' for v, t in opts)
        return radios, f'<div class="seg" role="radiogroup" aria-label="{label}">{labels}</div>'

    def typed(t, body):
        return f'<fieldset class="typed-fields" data-type="{t}">{body}</fieldset>'

    def confirm(pid, open_label, title, body, act_label, value=None, action=None, btn_type="submit"):
        act = f' name="action" value="{value}"' if value else ""
        da = f' data-action="{action}"' if action else ""
        return (f'<button class="btn danger" type="button" popovertarget="{pid}">{open_label}</button>'
                f'<div id="{pid}" popover class="confirm-pop" role="alertdialog" aria-labelledby="{pid}-t" aria-describedby="{pid}-d">'
                f'<h4 id="{pid}-t">{title}</h4><p id="{pid}-d">{body}</p>'
                f'<div class="actions"><button class="btn" type="button" popovertarget="{pid}" popovertargetaction="hide" autofocus>{T("common.cancel")}</button>'
                f'<button class="btn danger-solid" type="{btn_type}"{act}{da} popovertarget="{pid}" popovertargetaction="hide">{act_label}</button></div></div>')

    def metric(label, val, unit, bind="", cls=""):
        b = f' data-bind="{bind}"' if bind else ""
        c = f' class="{cls}"' if cls else ""
        return f'<div class="metric"><dt>{label}</dt><dd{b}{c}>{val} <small>{unit}</small></dd></div>'

    def kv(rows):
        return '<dl class="kv">' + "".join(f"<div><dt>{a}</dt><dd{f' class={chr(34)}{c}{chr(34)}' if c else ''}>{b}</dd></div>" for a, b, *cc in rows for c in [cc[0] if cc else ""]) + "</dl>"

    def sheet(sid, hashv, icon, tone, head, status, overview, history, settings=None):
        tabs = [("o", "overview"), ("h", "history")] + ([("s", "settings")] if settings is not None else [])
        radios = "".join(f'<input class="state tab" type="radio" name="tab-{sid}" id="t-{sid}-{k}" value="{v}" data-hash="{T("hash." + v)}" aria-label="{T("tab." + v)}"{" checked" if k == "o" else ""}>' for k, v in tabs)
        labels = "".join(f'<label for="t-{sid}-{k}" data-tab="{v}">{T("tab." + v)}</label>' for k, v in tabs)
        panels = (f'<section class="tab-panel" data-tab="overview">{overview}</section><section class="tab-panel" data-tab="history">{history}</section>'
                  + (f'<section class="tab-panel" data-tab="settings">{settings}</section>' if settings is not None else ""))
        return f'''
  <div id="sheet-{sid}" popover class="sheet" role="dialog" aria-labelledby="sheet-{sid}-t" data-hash="{hashv}">
    {radios}
    <header class="sheet-head">
      <span class="chip-icon"{f' data-tone="{tone}"' if tone else ""} aria-hidden="true">{icon}</span>
      <div><h2 id="sheet-{sid}-t">{head}</h2><p>{status}</p></div>
      <button class="sheet-close" type="button" popovertarget="sheet-{sid}" popovertargetaction="hide" aria-label="{T("sheet.close")}">×</button>
      <nav class="tabs" aria-label="{T("sheet.tabs")}">{labels}</nav>
    </header>
    <div class="sheet-body">{panels}</div>
  </div>'''

    I = {  # ikoner (stroke, currentColor)
        "heat": '<svg viewBox="0 0 24 24"><path d="M12 3c3 4 5 6.5 5 10a5 5 0 0 1-10 0c0-2 1-3.5 2-5 .5 2 1.5 3 3 3-1-3 0-6 0-8z"/></svg>',
        "plan": '<svg viewBox="0 0 24 24"><rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/></svg>',
        "wx": '<svg viewBox="0 0 24 24"><path d="M3 9h11a3 3 0 1 0-3-3M3 14h15a3 3 0 1 1-3 3M3 19h7"/></svg>',
        "pump": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="1.6"/><path d="M12 10.4c0-2.6 1.2-4.4 3.6-5M13.4 12.8c2.3 1.3 3.2 3.3 2.6 5.7M10.6 12.8c-2.3 1.3-4.5 1.2-6.2-.6"/></svg>',
        "room": '<svg viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="3"/><path d="M4 12h8V4"/></svg>',
        "mani": '<svg viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16M8 7v10M16 7v10"/></svg>',
    }

    # ---- afledte tal
    def room_dev(r):
        return None if r[4] is None else r[4] - r[5]

    def dev_chip(r, bind=""):
        d = room_dev(r)
        if d is None or r[7] in ("fault", "off"):
            return ""
        k = 1 if d <= -1 else 2 if d <= -0.3 else 3 if d < 0.3 else 4 if d < 1 else 5
        sign = "+" if d > 0.05 else "−" if d < -0.05 else "±"
        return f'<span class="tile-dev" data-dev="{k}">{sign}{T.num(abs(d))}°</span>'

    def level(r):
        """Ventilåbning i 5 trin (20 % pr. segment); 0 = lukket, fejl eller ingen data."""
        return 0 if r[7] in ("fault", "off") or r[4] is None or r[6] <= 0 else max(1, math.ceil(r[6] / 20))

    def room_val(r):
        if r[7] == "fault":
            return T("tile.fault")
        if r[4] is None:
            return dash
        return f"{T.num(r[4])}°"

    calling = sum(1 for r in ROOMS if r[7] == "calling")
    faults = [r for r in ROOMS if r[7] == "fault"]
    offline = [m for m in MANIFOLDS if not m["online"]]

    # ================================================================ HJEM
    # Varmekort: rum pr. manifold
    def room_tile(r):
        m = man(r[2])
        aria = T("tile.room.aria", name=r[1], state=ST[r[7]], temp=room_val(r))
        return f'''
            <button class="tile" type="button" popovertarget="sheet-{r[0]}" data-state="{r[7]}" data-open="{level(r)}" style="--area:{round(r[8])}" aria-label="{aria}">
              <span class="lvl" aria-hidden="true">{"<i></i>" * 5}</span>
              <span class="tile-pct">{T("tile.closed") if level(r) == 0 else T("tile.open", p=r[6])}</span>
              <span class="tile-id">Z{r[3]}</span>
              <span class="tile-name">{r[1]}</span>
              {dev_chip(r)}
              <span class="tile-val">{room_val(r)}</span>
            </button>'''

    groups = []
    for m in MANIFOLDS:
        rs = [r for r in ROOMS if r[2] == m["n"]]
        off = "" if m["online"] else " data-offline"
        note = "" if m["online"] else f'<p class="offline-note">{T("v6.offline", h=m["seen"])}</p>'
        groups.append(f'''
          <section class="room-group"{off} aria-label="{m["name"]}">
            <button class="room-group-head" type="button" popovertarget="sheet-m{m["n"]}">{m["name"]} <small>M{m["n"]} · {T.num(m["flow"])}° → {T.num(m["ret"])}°</small></button>
            {note}
            <div class="room-grid">{"".join(room_tile(r) for r in rs)}</div>
          </section>''')
    steps = [(1, f"≤−{T.num(1, 0)}"), (2, f"−{T.num(.3)}"), (3, f"±{T.num(.3)}"), (4, f"+{T.num(.3)}"), (5, f"≥+{T.num(1, 0)}")]
    legend = (f'<div class="heatmap-legend" role="group" aria-label="{T("heatmap.legendAria")}">'
              f'<ol>{"".join(f"<li data-dev={chr(34)}{k}{chr(34)}>{t}</li>" for k, t in steps)}</ol><span>{T("heatmap.legendDev")}</span>'
              f'<span><span class="lvl" aria-hidden="true">{"<i></i>" * 5}</span>{T("heatmap.legendValve")}</span></div>')
    heatmap = f'''
        <section class="panel" aria-labelledby="h-heatmap">
          <header class="heatmap-head">
            <div><small>{T("heatmap.eyebrow")}</small><h3 id="h-heatmap">{T("heatmap.title")}</h3></div>
            {legend}
          </header>
          <div class="heatmap">{"".join(groups)}</div>
          <p class="heatmap-note">{T("heatmap.note")}</p>
        </section>'''

    # Felter (maks. 4): Varme · Næste varme · Vejr · Cirkulation
    hf = series(3, 24, 34.5, 1.6, .2)
    hr = series(4, 24, 28.6, 0.8, .15)
    lo_, hi_ = 26, 38
    tile_heat = f'''
          <button class="home-tile" type="button" popovertarget="sheet-heat">
            <span class="chip-icon" aria-hidden="true">{I["heat"]}</span><b>{T("tile.heat")}</b>
            <span class="ht-status">{T("tile.heatStatus")}</span>
            <span class="ht-val">{T.num(36.0)}° → {T.num(29.0)}° <small>{T("tile.heatSub")}</small></span>
            <svg class="ht-viz" viewBox="0 0 240 64" preserveAspectRatio="none" aria-hidden="true"><path class="a" d="M0,64 L{pts(hf, 240, 64, lo_, hi_).replace(" ", " L")} L240,64Z"/><polyline class="f" points="{pts(hf, 240, 64, lo_, hi_)}"/><polyline class="r" points="{pts(hr, 240, 64, lo_, hi_)}"/></svg>
          </button>'''
    plan_kwh = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2.1, 3.4, 2.6, 0, 0, 0, 0, 0, 0, 0]
    bars = '<line class="base" x1="0" y1="63.5" x2="240" y2="63.5"/>' + "".join(f'<rect class="col on" x="{k * 10 + 2}" y="{64 - v / 3.4 * 60}" width="6" height="{v / 3.4 * 60}" rx="3"/>' for k, v in enumerate(plan_kwh) if v)
    tile_plan = f'''
          <button class="home-tile" type="button" popovertarget="sheet-plan">
            <span class="chip-icon" data-tone="violet" aria-hidden="true">{I["plan"]}</span><b>{T("tile.plan")}</b>
            <span class="ht-status">{T("tile.planStatus")}</span>
            <span class="ht-val">{T("tile.planVal", a="06", b="09")} <small>≈ {T.num(8.1)} kWh</small></span>
            <span class="ht-price">{T("tile.price", p=T.num(1.82, 2), unit=T("price.unit"))} <span class="scale-chip" data-scale="2">{T("price.scale.2")}</span></span>
            <svg class="ht-viz" viewBox="0 0 240 64" preserveAspectRatio="none" aria-hidden="true">{bars}</svg>
          </button>'''
    wx = series(7, 24, 9.5, 3.2, .3)
    tile_wx = f'''
          <button class="home-tile" type="button" popovertarget="sheet-weather">
            <span class="chip-icon" data-tone="info" aria-hidden="true">{I["wx"]}</span><b>{T("tile.weather")}</b>
            <span class="ht-status">{T("tile.weatherStatus", n=6)}</span>
            <span class="ht-val">{T.num(8.4)}° <small>{T("tile.weatherSub", w=6)}</small></span>
            <svg class="ht-viz" viewBox="0 0 240 64" preserveAspectRatio="none" aria-hidden="true"><rect class="pre" x="150" y="0" width="70" height="64"/><path class="wa" d="M0,64 L{pts(wx, 240, 64, 4, 16).replace(" ", " L")} L240,64Z"/><polyline class="t" points="{pts(wx, 240, 64, 4, 16)}"/></svg>
          </button>'''
    fl = series(9, 24, 21.5, 2.5, .4)
    tile_pump = f'''
          <button class="home-tile" type="button" popovertarget="sheet-pump">
            <span class="chip-icon" data-tone="neutral" aria-hidden="true">{I["pump"]}</span><b>{T("tile.pump")}</b>
            <span class="ht-status">{T("tile.pumpStatus")}</span>
            <span class="ht-val">{T.num(22.4)} <small>l/min · {T.num(2.9)} m · 38 W</small></span>
            <svg class="ht-viz" viewBox="0 0 240 64" preserveAspectRatio="none" aria-hidden="true"><polyline class="w" points="{pts(fl, 240, 64, 15, 28)}"/></svg>
          </button>'''

    alerts = "".join(f'''
        <div class="panel alert">
          <div class="panel-head"><h3>{T("alert.roomFault", name=r[1], m=man(r[2])["name"], z=r[3])}</h3></div>
          <p class="note">{T("alert.roomFaultBody")}</p>
          <div class="panel-foot"><button class="btn" type="button" popovertarget="sheet-{r[0]}">{T("common.open", x=r[1])}</button></div>
        </div>''' for r in faults)

    v = round((HOUSE_TARGET - THERMO_MIN) / (THERMO_MAX - THERMO_MIN) * 100)
    now = round((HOUSE_TEMP - THERMO_MIN) / (THERMO_MAX - THERMO_MIN) * 100)
    ta = T("climate.targetAria")
    home = f'''
      <section class="view" id="v-home-house" aria-labelledby="h-home">
        {alerts}
        <section class="home-hero">
          <div class="hero-text">
            <small>{T("home.greeting")}</small>
            <h2 id="h-home">{T("home.headline")} <span class="sub">{T("home.headline2")}</span></h2>
            <p>{T("home.sentence", d=T.num(HOUSE_TEMP - HOUSE_TARGET), n=calling)}</p>
            <div class="hero-facts">
              <button class="hero-fact" type="button" popovertarget="sheet-heat"><span class="chip-icon" aria-hidden="true">{I["heat"]}</span><small>{T("hero.heat")}</small><b>{T.num(36.0)}° → {T.num(29.0)}°</b><span>{T("hero.heatSub")}</span></button>
              <button class="hero-fact" type="button" popovertarget="sheet-plan"><span class="chip-icon" data-tone="violet" aria-hidden="true">{I["plan"]}</span><small>{T("tile.plan")}</small><b>{T("tile.planVal", a="06", b="09")}</b><span>≈ {T.num(8.1)} kWh</span></button>
            </div>
          </div>
          <form class="thermo" data-save="house-target">
            <div class="thermo-ring" style="--v:{v};--now:{now}" role="img" aria-label="{T("thermo.aria", t=T.num(HOUSE_TEMP), g=T.num(HOUSE_TARGET))}">
              <svg viewBox="0 0 100 100" aria-hidden="true"><circle class="trk" cx="50" cy="50" r="44" pathLength="100"/><circle class="arc" cx="50" cy="50" r="44" pathLength="100"/><circle class="tg-edge" cx="50" cy="50" r="44" pathLength="100"/><circle class="tg" cx="50" cy="50" r="44" pathLength="100"/></svg>
              <div class="thermo-val"><span>{T("thermo.house")}</span><b data-bind="house.temp">{T.num(HOUSE_TEMP)}<small>°</small></b><span>{T("thermo.outside", t=T.num(8.4))}</span></div>
            </div>
            <div class="climate">
              <div class="target">
                <button type="button" data-step="-1" aria-label="{T("common.decrease", x=ta)}">−</button>
                <label class="value"><small>{T("climate.target")}</small><input type="text" inputmode="decimal" id="house_target" name="house_target" value="{T.num(HOUSE_TARGET)}" data-min="5" data-max="30" data-step-size="0.5" autocomplete="off"><span class="unit" aria-hidden="true">°</span></label>
                <button type="button" data-step="1" aria-label="{T("common.increase", x=ta)}">+</button>
              </div>
              <p class="autosave" aria-live="polite"></p>
            </div>
          </form>
        </section>
        <header class="home-head"><small>{T("home.nowEyebrow")}</small><h3>{T("home.nowTitle")}</h3></header>
        <div class="home-tiles">{tile_heat}{tile_plan}{tile_wx}{tile_pump}</div>
        {heatmap}
      </section>'''

    # ================================================================ ARK
    # ---- Varme
    weights = [r for r in ROOMS if r[12] and r[4] is not None]
    tw = sum(r[13] * r[8] for r in weights)
    wrows = "".join(f'<tr><td>{r[1]}</td><td class="num">{T.num(r[4])} °C</td><td class="num">{T.num(r[8], 0)} m² · {round(r[13] * r[8] / tw * 100)} %</td><td class="num">{T.num(r[4] * r[13] * r[8] / tw)} °C</td></tr>' for r in weights)
    sent = f'''
        <section class="setting-group hs-type-asgard"><h4>{T("heat.sentTo", target="Asgard")}</h4>
          <div class="setting-list">
            {rrow(T("heat.weighted"), f"<b>{T.num(HOUSE_TEMP)} °C</b> · {T('rt.secondsAgo', v=12)}", "temperature_feedback_z1")}
            {rrow(T("heat.setpoint"), f"<b>{T.num(HOUSE_TARGET)} °C</b> · {T('rt.secondsAgo', v=12)}", "climate.asgard")}
          </div>
          <details class="more"><summary>{T("heat.howCalc")}</summary>
            <div class="table-wrap"><table class="table"><thead><tr><th>{T("rooms.name")}</th><th class="num">{T("heat.temp")}</th><th class="num">{T("heat.weight")}</th><th class="num">{T("heat.contrib")}</th></tr></thead><tbody>{wrows}</tbody></table></div>
            <p class="note">{T("heat.howCalcNote")}</p>
          </details>
        </section>
        <section class="setting-group hs-type-http"><h4>{T("heat.sentTo", target="HTTP")}</h4>
          <div class="setting-list">{rrow(T("heat.weighted"), f"<b>{T.num(HOUSE_TEMP)} °C</b> · {T('rt.secondsAgo', v=12)}")}</div>
        </section>'''
    heat_over = f'''
        <div data-hs-type="{hs_type}" style="display:grid;gap:var(--space-5)">
          <dl class="metrics">
            {metric(T("heat.weighted"), T.num(HOUSE_TEMP), "°C", "heat.weighted")}
            {metric(T("heat.setpoint"), T.num(HOUSE_TARGET), "°C", "heat.setpoint")}
            {metric(T("heat.hpTemps"), f"{T.num(36.0)} → {T.num(29.0)}", "°C", "heat.hp", )}
          </dl>
          {kv([(T("heat.lastPush"), T("rt.secondsAgo", v=12)), (T("heat.targetRole"), T("heat.roleTouch")), (T("heat.controlledBy"), "Odin"),
               (T("heat.odinLink"), T("status.ok"), "c-ok"), (T("heat.odinNow"), T("heat.odinNowVal", t="06"))])}
          {sent}
        </div>'''
    hist_w = series(21, 48, 21.6, 0.5, .08)
    heat_hist = f'''
        <div class="sub trend-wrap"><h4>{T("trend.title")} <span class="legend"><i class="lt"></i>{T("heat.weighted")}<i class="lg"></i>{T("heat.setpoint")}</span></h4>
          <svg class="spark" style="height:120px" viewBox="0 0 240 80" preserveAspectRatio="none" role="img" aria-label="{T("heat.histAria")}"><polyline class="g" points="0,{80 - (21 - 19.5) / 3 * 80} 240,{80 - (21 - 19.5) / 3 * 80}"/><polyline class="t" points="{pts(hist_w, 240, 80, 19.5, 22.5)}"/></svg>
          <div class="axis" aria-hidden="true"><span>−24 {H}</span><span>−12 {H}</span><span>{T("trend.now")}</span></div></div>'''
    heat_set = f'''
        <form data-save="heat_source.behavior" data-patch>
          {ggroup(T("heat.comfortSync"), sswitch("target_sync_enabled", T("heat.targetSync"), T("heat.targetSyncSub"), True),
                  sinput("climate_entity", T("heat.climateEntity"), "virtual_thermostat"))}
          {group(T("heat.odinPlan"), sswitch("odin_plan_enabled", T("heat.odinPlanSw"), T("heat.odinPlanSub"), True),
                 extra="", pre="")}
          {ggroup(T("heat.odinControl"), sswitch("odin_control_enabled", T("heat.odinControlSw"), T("heat.odinControlSub"), True),
                  sstep("odin_max_lift_c", T("heat.odinMaxLift"), 1.0, 0, 3, 0.1, "°C"))}
          <p class="note">{T("heat.connOnSystem")}</p>
          {savebar("heat-behavior")}
        </form>'''
    sheet_heat = sheet("heat", T("hash.heat"), I["heat"], "", T("tile.heat"), T("sheet.heatStatus"), heat_over, heat_hist, heat_set)

    # ---- Næste varme (Odins plan) — kun Overblik/Historik
    def plan_graph():
        bars_ = "".join(f'<i class="plan-bar" style="--v:{round(v / 3.4 * 100)}"{" data-mode=" + chr(34) + "dhw" + chr(34) if k == 15 else ""}></i>' for k, v in enumerate(plan_kwh))
        lanes = ""
        for r in ROOMS:
            if r[0] in ("r05", "r06"):
                seg_ = f'<span class="plan-seg" data-kind="charge" style="--a:3;--b:7" title="{T("plan.charge")}"></span>'
            elif r[0] == "r09":
                seg_ = f'<span class="plan-seg" data-kind="charge" data-insufficient style="--a:3;--b:8" title="{T("plan.insufficient")}"></span>'
            elif r[0] in ("r01", "r07"):
                seg_ = f'<span class="plan-seg" data-kind="preload" style="--a:12;--b:16" title="{T("plan.preload")}"></span>'
            else:
                continue
            lanes += f'<span class="plan-lab">{r[1]}</span><div class="plan-lane">{seg_}</div>'
        xs = "".join(f'<span{" class=m" if (h % 6) else ""} style="left:{h / 24 * 100:.2f}%">{(14 + h) % 24:02d}</span>' for h in range(0, 24, 3))
        return f'''<div class="plan" role="img" aria-label="{T("plan.aria")}">
          <div class="plan-lab plan-lab--y"><b>Odin</b><span class="plan-y"><i>3</i><i>0</i></span></div>
          <div class="plan-lane plan-lane--odin">{bars_}<span class="plan-lift" style="--a:13;--b:19"></span></div>
          {lanes}
          <div class="plan-x">{xs}</div></div>
        <div class="fc-legend" aria-hidden="true"><span><i class="lbar"></i>{T("plan.lHeat")}</span><span><i class="ldhw"></i>{T("plan.lDhw")}</span><span><i class="lleg"></i>{T("plan.lLeg")}</span><span><i class="llift"></i>{T("plan.lLift")}</span><span><i class="lpre"></i>{T("plan.preload")}</span><span><i class="lch"></i>{T("plan.charge")}</span><span><i class="lins"></i>{T("plan.insufficient")}</span></div>'''
    plan_over = f'''
        <dl class="metrics">
          {metric(T("plan.next"), T("tile.planVal", a="06", b="09"), "")}
          {metric(T("plan.energy"), T.num(8.1), "kWh")}
          {metric(T("plan.priceNow"), T.num(1.82, 2), T("price.unit"))}
        </dl>
        {plan_graph()}'''
    pbars = "".join(f'<div class="col"><i class="plan" style="--plan:{p}"></i><i class="act" style="--act:{a}"></i></div>' for p, a in ((40, 32), (55, 48), (70, 61), (50, 44), (35, 30), (45, 52), (30, 28), (20, 22)))
    plan_hist = f'''<div class="sub"><h4>{T("plan.vsActual")}</h4><div class="bars" style="--bars-n:8"><div class="bars-plot" role="img" aria-label="{T("plan.vsActualAria")}">{pbars}</div>
        <div class="bars-legend"><span><i class="lp"></i>{T("plan.planned")}</span><span><i class="la"></i>{T("plan.actual")}</span></div></div></div>'''
    sheet_plan = sheet("plan", T("hash.plan"), I["plan"], "violet", T("tile.plan"), T("tile.planStatus"), plan_over, plan_hist)

    # ---- Vejr
    def forecast():
        W = 720
        temp = [9 + 4 * math.sin((h - 9) / 24 * 2 * math.pi) for h in range(73)]
        wind = [4.5 + 1.5 * math.sin(h / 9) + (5 * math.sin((h - 18) / 14 * math.pi) if 18 <= h <= 32 else 0) for h in range(73)]
        X = lambda h: round(h * W / 72, 1)
        tp = " ".join(f"{X(h)},{round(100 - (t - 2) / 16 * 100, 1)}" for h, t in enumerate(temp))
        wp = " ".join(f"{X(h)},{round(60 - w / 14 * 60, 1)}" for h, w in enumerate(wind))
        days = "".join(f'<line class="day" x1="{X(d)}" x2="{X(d)}" y1="0" y2="100%"/>' for d in (10, 34, 58))
        return f'''<div class="fc" style="--now:0%">
            <div class="fc-y" aria-hidden="true"><span>18°</span><span>10°</span><span>2°</span></div>
            <div class="fc-plot fc-temp" role="img" aria-label="{T("fc.tempAria")}"><span class="fc-now">{T("fc.now")}</span>
              <svg viewBox="0 0 {W} 100" preserveAspectRatio="none">{days}<rect class="pre" x="{X(6)}" y="0" width="{X(17) - X(6)}" height="100"/><polyline class="tl" points="{tp}"/></svg></div>
            <div class="fc-y" aria-hidden="true"><span>14</span><span>7</span><span>0</span></div>
            <div class="fc-plot fc-wind" role="img" aria-label="{T("fc.windAria")}">
              <svg viewBox="0 0 {W} 60" preserveAspectRatio="none">{days}<polygon class="wa" points="0,60 {wp} {W},60"/><polyline class="wl" points="{wp}"/></svg></div>
            <div class="fc-x" aria-hidden="true"><span>{T("fc.now")}</span><span>18</span><span class="d">{T.meta("_days")[1]}</span><span>06</span><span>12</span><span>18</span><span class="d">{T.meta("_days")[2]}</span><span>12</span><span></span></div>
          </div>
          <div class="fc-legend" aria-hidden="true"><span><i class="lt"></i>{T("fc.lTemp")}</span><span><i class="lw"></i>{T("fc.lWind")}</span><span><i class="lpre"></i>{T("fc.lPre")}</span></div>'''
    wx_over = f'''
        <dl class="metrics">
          {metric(T("fc.now"), T.num(8.4), "°C", "forecast.temp")}
          {metric(T("fc.windMax"), "11", "m/s", "forecast.windmax", "c-info")}
          {metric(T("fc.tempMin"), T.num(4.9), "°C", "forecast.tmin")}
        </dl>
        <p class="msg info"><span><b>{T("fc.msgStrong")}</b> {T("fc.msg", n=6)}</span></p>
        {forecast()}'''
    wx_hist = f'''<div class="sub trend-wrap"><h4>{T("wx.past")}</h4>
          <svg class="spark" style="height:100px" viewBox="0 0 240 80" preserveAspectRatio="none" role="img" aria-label="{T("wx.pastAria")}"><polyline class="t" points="{pts(series(5, 48, 8.5, 3, .3), 240, 80, 2, 16)}"/></svg>
          <div class="axis" aria-hidden="true"><span>−24 {H}</span><span>−12 {H}</span><span>{T("trend.now")}</span></div></div>'''
    wx_set = f'''
        <form data-save="weather.boost" data-patch>
          {group(T("wx.preload"), sstep("wx_boost", T("wx.boost"), 1.5, 0, 3, 0.1, "°C", hint=T("wx.boostHint")))}
          <p class="note">{T("wx.locationOnSystem")}</p>
          {savebar("weather-boost")}
        </form>'''
    sheet_wx = sheet("weather", T("hash.weather"), I["wx"], "info", T("tile.weather"), T("tile.weatherStatus", n=6), wx_over, wx_hist, wx_set)

    # ---- Cirkulation
    dist = [("Teknikrum", 52, 11.6, 0), ("1. sal", 38, 8.5, 1), ("Anneks", 10, 2.3, 2)]
    dsegs = "".join(f'<span class="dist-seg" data-i="{i}" style="--w:{w}"></span>' for _, w, _, i in dist)
    drows = "".join(f'<i class="dist-key" data-i="{i}"></i><span class="dist-name">{n}</span><span class="num">{w} %</span><span class="num">{T.num(l)} l/min</span>' for n, w, l, i in dist)
    pump_over = f'''
        <dl class="metrics">
          {metric(T("pump.flow"), T.num(22.4), "l/min", "pump.flow")}
          {metric(T("pump.head"), T.num(2.9), "m", "pump.head")}
          {metric(T("pump.power"), "38", "W", "pump.power")}
        </dl>
        {kv([(T("pump.flowM3h"), f"{T.num(1.34, 2)} m³/h"), (T("pump.host"), "alpha2go.local")])}
        <div class="sub"><h4>{T("pump.dist")}</h4>
          <div class="dist"><div class="dist-bar" role="img" aria-label="{T("pump.distAria")}">{dsegs}</div><div class="dist-rows">{drows}</div>
          <p class="dist-note">{T("pump.distNote")}</p></div></div>'''
    pump_hist = f'''<div class="sub trend-wrap"><h4>{T("trend.title")}</h4>
          <svg class="spark" style="height:100px" viewBox="0 0 240 80" preserveAspectRatio="none" role="img" aria-label="{T("pump.histAria")}"><polyline class="t" points="{pts(series(9, 48, 21.5, 2.5, .4), 240, 80, 15, 28)}"/></svg>
          <div class="axis" aria-hidden="true"><span>−24 {H}</span><span>−12 {H}</span><span>{T("trend.now")}</span></div></div>'''
    sheet_pump = sheet("pump", T("hash.pump"), I["pump"], "neutral", T("tile.pump"), T("tile.pumpStatus"), pump_over, pump_hist)

    # ---- Manifold (pr. styring)
    def manifold_sheet(m):
        rs = [r for r in ROOMS if r[2] == m["n"]]
        rows = "".join(f'''
            <button type="button" popovertarget="sheet-{r[0]}" data-state="{r[7]}"><span class="id">Z{r[3]}</span><span class="name">{r[1]}</span>
              <span class="val">{f'<b class="bad">{ST["fault"]}</b>' if r[7] == "fault" else f'<b>{room_val(r)}</b> / {T.num(r[5])}°'}</span></button>''' for r in rs)
        badge = f'<span class="badge ok">{T("status.online")}</span>' if m["online"] else f'<span class="badge warn">{T("status.offline")}</span>'
        status = (T("sheet.manifoldStatus", flow=T.num(m["flow"]), ret=T.num(m["ret"]), n=len(rs)) if m["online"]
                  else T("v6.offline", h=m["seen"]))
        over = f'''
        {"" if m["online"] else f'<p class="msg warn"><span><b>{T("v6.offlineStrong")}</b> {T("v6.offlineBody", h=m["seen"])}</span></p>'}
        <dl class="metrics">{metric(T("m.supply"), T.num(m["flow"]), "°C")}{metric(T("m.return"), T.num(m["ret"]), "°C", "", "c-info")}</dl>
        {kv([(T("ctrl.status"), badge), (T("ctrl.host"), f'<span class="mono">{m["host"]}</span>'), ("IP", f'<span class="mono">{m["ip"]}</span>'), (T("fw.installed"), m["fw"])])}
        <div class="sub"><h4>{T("mani.zones")}</h4><div class="comfort">{rows}</div></div>
        <div class="actions"><a class="btn" href="http://{m["ip"]}/" target="_blank" rel="noopener">{T("v6.open")}</a></div>'''
        hist = f'''<div class="sub trend-wrap"><h4>{T("trend.title")} <span class="legend"><i class="lf"></i>{T("m.supply")}<i class="lr"></i>{T("m.return")}</span></h4>
          <svg class="trend" viewBox="0 0 240 80" preserveAspectRatio="none" role="img" aria-label="{T("trend.aria")}"><polyline class="f" points="{pts(series(m["n"] + 30, 48, m["flow"] - 1, 1.5, .2), 240, 80, 24, 40)}"/><polyline class="r" points="{pts(series(m["n"] + 40, 48, m["ret"] - .5, .8, .15), 240, 80, 24, 40)}"/></svg>
          <div class="axis" aria-hidden="true"><span>−24 {H}</span><span>−12 {H}</span><span>{T("trend.now")}</span></div></div>'''
        return sheet(f"m{m['n']}", f"m{m['n']}", I["mani"], "neutral", m["name"], status, over, hist)

    # ---- Rum
    WL, WF = T.meta("_walls"), T.meta("_walls_full")

    def room_sheet(r):
        rid, name, mn, zn, temp, tgt, valve, st, area, cc, pipe, walls, inc, wt, wind, solar = r
        m = man(mn)
        status = T("sheet.roomStatus", m=m["name"], z=zn, temp=room_val(r), open=0 if level(r) == 0 else valve, state=ST[st])
        fault = st == "fault"
        nodata = temp is None
        alert = (f'''<div class="panel alert"><div class="panel-head"><h3>{T("alert.motorFault", reason=T("fault.endstop"))}</h3></div>
          <p class="note">{T("alert.roomFaultBody")}</p>
          <div class="panel-foot"><a class="btn" href="http://{m["ip"]}/#z{zn}" target="_blank" rel="noopener">{T("v6.resetOnV6")}</a></div></div>''' if fault else "")
        nodata_msg = f'<p class="msg warn"><span><b>{T("room.noDataStrong")}</b> {T("room.noData")}</span></p>' if nodata else ""
        over = f'''{alert}{nodata_msg}
        <dl class="metrics">
          {metric(T("room.temp"), dash if nodata else T.num(temp), "°C")}
          {metric(T("room.target"), T.num(tgt), "°C")}
          {metric(T("room.valve"), 0 if level(r) == 0 else valve, "%")}
        </dl>
        <div class="bar" style="--v:{0 if level(r) == 0 else valve}%" aria-hidden="true"><i></i></div>
        <div class="sub"><h4>{T("room.loops", m=m["name"])}</h4>
          {kv([(f"Z{zn}", f'{"—" if nodata else T.num(temp) + " °C"} · {T("room.valveShort", v=0 if level(r) == 0 else valve)}'),
               (T("m.return"), "—" if nodata else f"{T.num(m['ret'] - 1.2)} °C", "c-info"), (T("room.state"), ST[st], "c-bad" if fault else "")])}</div>'''
        hist = (f'<div class="sub" data-empty><h4>{T("trend.title")}</h4><p class="empty">{T("room.noHistory")}</p></div>' if nodata else
                f'''<div class="sub trend-wrap"><h4>{T("trend.title")} <span class="legend"><i class="lt"></i>{T("legend.temp")}<i class="lg"></i>{T("legend.target")}</span></h4>
          <svg class="spark" style="height:100px" viewBox="0 0 240 80" preserveAspectRatio="none" role="img" aria-label="{T("room.histAria", name=name)}"><polyline class="g" points="0,{round(80 - (tgt - (tgt - 1.5)) / 3 * 80, 1)} 240,{round(80 - 1.5 / 3 * 80, 1)}"/><polyline class="t" points="{pts(series(int(rid[1:]) * 3, 48, temp, .4, .08), 240, 80, tgt - 1.5, tgt + 1.5)}"/></svg>
          <div class="axis" aria-hidden="true"><span>−24 {H}</span><span>−12 {H}</span><span>{T("trend.now")}</span></div></div>''')
        walls_txt = " · ".join(WF[w] for w in walls) if walls else T("common.none")
        off = "" if m["online"] else " data-offline"
        v6 = group(T("room.fromV6", m=m["name"], z=zn),
                   rrow(T("room.area"), f"{T.num(area)} m²") +
                   rrow(T("room.walls"), walls_txt) +
                   srow(f"<span>{T('room.editOnV6Label')}</span>", f'<a class="btn" href="http://{m["ip"]}/#z{zn}/{T("hash.settings")}" target="_blank" rel="noopener">{T("room.editOnV6")}</a>'),
                   extra="" if m["online"] else f'<p class="offline-note">{T("v6.offline", h=m["seen"])}</p>', attrs=off)
        settings = f'''
        <form data-save="rooms" data-patch>
          {group(T("room.house"), sswitch(f"room:{rid}:include", T("room.include"), T("room.includeSub"), inc) +
                 sstep(f"room:{rid}:weight", T("room.weight"), wt, 0, 5, 0.05, "×", dec=2, id_=f"{rid}-weight", hint=T("room.weightHint")))}
          {group(T("room.weather"), sstep(f"room:{rid}:wind", T("room.wind"), wind, 0, 1, 0.05, "", dec=2, id_=f"{rid}-wind") +
                 sstep(f"room:{rid}:solar", T("room.solar"), solar, 0, 1, 0.05, "", dec=2, id_=f"{rid}-solar"))}
          {v6}
          {savebar(f"room-{rid}")}
        </form>'''
        return sheet(rid, rid, I["room"], "", name, status, over, hist, settings)

    sheets = sheet_heat + sheet_plan + sheet_wx + sheet_pump + "".join(manifold_sheet(m) for m in MANIFOLDS) + "".join(room_sheet(r) for r in ROOMS)

    # ================================================================ SYSTEM
    def syscat(cat, title, body, badge=""):
        return (f'<section class="sys-cat" data-cat="{cat}" aria-labelledby="h-c-{cat}"><label class="sys-back" for="c-none">{T("sys.title")}</label>'
                f'<header><div><small>{T("sys.title")}</small><h2 id="h-c-{cat}">{title}</h2></div>{badge}</header>{body}</section>')

    def file_input(name, accept):
        return (f'<label class="input file w-md" for="{name}"><input class="sr-only" type="file" id="{name}" name="{name}" accept="{accept}">'
                f'<span class="file-pick">{T("common.chooseFile")}</span><span class="file-name" data-empty="{T("common.noFile")}">{T("common.noFile")}</span></label>')

    cats = []
    # Enhed
    cats.append(("device", T("cat.device"), '<path d="M4 11l8-7 8 7v9H4z"/>', f'''
      <form data-save="settings">
        {group(T("dev.identity"), sinput("name", T("dev.name"), T("device.sample"), "w-sm", id_="dev_name") +
               sstep("dev_idle", T("dev.idle"), 5, 0, 120, 1, "min", dec=0, hint=T("dev.idleHint")))}
        {savebar("settings")}
      </form>''', ""))
    # Styringer
    nrows = "".join(f'''<tr><td>{m["name"]}</td><td class="mono">{m["host"]}</td>
        <td>{f'<span class="badge ok">{T("status.online")}</span>' if m["online"] else f'<span class="badge warn">{T("status.offline")}</span>'}</td>
        <td class="num">{sum(1 for r in ROOMS if r[2] == m["n"])}</td>
        <td><div class="actions"><button class="btn copy" type="button" data-action="edit-node-name" data-node="{m["n"]}">{T("ctrl.rename")}</button>
        <button class="btn copy" type="button" data-action="edit-node-host" data-node="{m["n"]}">{T("ctrl.editHost")}</button>
        {confirm(f"cf-node-{m['n']}", T("ctrl.remove"), T("ctrl.removeAsk", name=m["name"]), T("ctrl.removeNote"), T("ctrl.removeDo"), action="remove-node", btn_type="button")}</div></td></tr>''' for m in MANIFOLDS)
    cats.append(("controllers", T("cat.controllers"), '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M4 12h16M12 4v16"/>', f'''
      <form data-save="add-node">
        <section class="setting-group"><h4>{T("ctrl.list")}</h4>
          <div class="table-wrap"><table class="table"><thead><tr><th>{T("ctrl.name")}</th><th>{T("ctrl.host")}</th><th>{T("ctrl.status")}</th><th class="num">{T("ctrl.zones")}</th><th></th></tr></thead><tbody>{nrows}</tbody></table></div>
        </section>
        {group(T("ctrl.find"), srow(f'<span>{T("ctrl.scanLabel")}</span>', f'<button class="btn" type="button" data-action="scan-nodes">{T("ctrl.scan")}</button>', T("ctrl.scanHint")) +
               srow(f'<span>lune-v6-kaelder.local</span>', f'<button class="btn" type="button" data-action="add-found" data-host="lune-v6-kaelder.local">{T("ctrl.addFound")}</button>', T("ctrl.found")))}
        {group(T("zs.advanced"), subpage(T("ctrl.addManual"), "", group(T("ctrl.addManual"),
               sinput("name", T("ctrl.name"), "", "w-sm", id_="node_name", extra=f' placeholder="{T("ctrl.namePh")}"') +
               sinput("host", T("ctrl.host"), "", "w-md", id_="node_host", extra=' placeholder="lune-v6.local" inputmode="url"'),
               extra=f'<div class="actions"><button class="btn primary" type="submit">{T("ctrl.add")}</button></div>')))}
      </form>''', ""))
    # Varmekilde
    r_hs, seg_hs = seg("hs_type", "hs", [("http", T("hs.typeHttp")), ("asgard", T("hs.typeAsgard"))], hs_type, T("hs.type"))
    http_f = typed("http",
        group(T("hs.connection"), sinput("http_host", T("hs.host"), "heat-bridge.local") +
              srow(lab("http_port", T("hs.port")), '<input class="input w-xs" type="number" id="http_port" name="http_port" value="80" min="1" max="65535">') +
              sstep("http_push_interval_s", T("hs.pushInterval"), 60, 5, 3600, 5, "s", dec=0)) +
        group(T("hs.mapping"), sinput("http_weighted_temperature_variable", T("hs.weightedVar"), "temperature_feedback_z1") +
              sinput("write_url_template", T("hs.writeUrl"), "", "w-lg", stack=True, extra=' placeholder="http://{host}/{entity}/set?value={value}"') +
              sinput("read_url_template", T("hs.readUrl"), "", "w-lg", stack=True, extra=' placeholder="http://{host}/{entity}"') +
              subpage(T("hs.httpControl"), "", group(T("hs.httpControl"),
                  sinput("target_url_template", T("hs.targetUrl"), "", "w-lg", stack=True) +
                  sinput("heat_request_url_template", T("hs.heatRequestUrl"), "", "w-lg", stack=True) +
                  sinput("curve_offset_url_template", T("hs.curveUrl"), "", "w-lg", stack=True) +
                  sstep("curve_gain", T("hs.curveGain"), 0.5, 0, 2, 0.05, "", dec=2) +
                  sstep("curve_max_offset_c", T("hs.curveMax"), 3.0, 0, 10, 0.5, "°C")))))
    asg_f = typed("asgard",
        group(T("hs.connection"), sinput("asgard_host", T("hs.host"), "192.168.20.11") +
              srow(lab("asgard_port", T("hs.port")), '<input class="input w-xs" type="number" id="asgard_port" name="asgard_port" value="80" min="1" max="65535">') +
              sstep("asgard_push_interval_s", T("hs.pushInterval"), 30, 5, 3600, 5, "s", dec=0)) +
        group(T("hs.houseTemp"), sinput("asgard_weighted_temperature_variable", T("hs.weightedVar"), "Virtual Thermostat Input z1", hint=T("hs.weightedVarHint"))))
    mqtt = subpage("MQTT", T("common.off"),
        ggroup(T("hs.mqttConn"), sswitch("mqtt_enabled", T("hs.mqttEnabled"), T("hs.mqttSub"), False),
               sinput("mqtt_host", T("hs.host"), "", "w-md") +
               srow(lab("mqtt_port", T("hs.port")), '<input class="input w-xs" type="number" id="mqtt_port" name="mqtt_port" value="1883" min="1" max="65535">')) +
        group(T("hs.mqttLogin"), sinput("mqtt_username", T("hs.mqttUser"), "", "w-sm") + sinput("mqtt_password", T("hs.mqttPass"), "", "w-sm", typ="password", extra=' autocomplete="new-password"') +
              sinput("mqtt_topic_prefix", T("hs.mqttPrefix"), "ecodan", "w-md") + sinput("mqtt_hp_id", T("hs.mqttHpId"), "", "w-sm")))
    test = f'''<div class="actions"><button class="btn" type="button" data-action="hs-test-read">{T("hs.testRead")}</button><button class="btn" type="button" data-action="hs-test-push">{T("hs.testPush")}</button></div>
        <div class="test-result" aria-live="polite"><div class="msg ok"><span><b>{T("hs.testOk", time="14:32:05", code=200, ms=84)}</b>{T("hs.testOkBody", v=T.num(HOUSE_TEMP), target="Virtual Thermostat Input z1")}</span></div></div>'''
    cats.append(("heatsource", T("cat.heatsource"), '<path d="M12 3c3 4 5 6.5 5 10a5 5 0 0 1-10 0c0-2 1-3.5 2-5 .5 2 1.5 3 3 3-1-3 0-6 0-8z"/>', f'''
      <form data-save="heat_source.connection" data-patch>
        {r_hs}
        {group(T("hs.type"), sswitch("enabled", T("hs.enabled"), "", True, id_="hs_enabled") + srow(f'<span>{T("hs.type")}</span>', seg_hs))}
        {http_f}{asg_f}
        {group("Odin", sinput("odin_host", T("hs.odinHost"), "odin.local", hint=T("hs.odinHostHint")))}
        {group(T("zs.advanced"), mqtt)}
        {test}
        {savebar("heat-connection")}
      </form>''', f'<span class="badge ok">{T("hs.badge", t="Asgard")}</span>'))
    # Elpris
    r_pm, seg_pm = seg("model", "pm", [("odin", T("price.modelOdin")), ("touch", T("price.modelTouch"))], "touch", T("price.model"))
    r_om, seg_om = seg("odin_mode", "om", [("dynamic", T("price.dynamic")), ("fixed", T("price.fixed"))], "dynamic", T("price.odinMode"))
    odin_f = typed("odin", r_om + group(T("price.odinOwn"), srow(f'<span>{T("price.odinMode")}</span>', seg_om) +
        srow(f'<span>{T("price.writeNow")}</span>', f'<button class="btn" type="button" data-action="price-odin-write">{T("price.writeOdin")}</button>')) +
        typed("dynamic", group(T("price.dynamic"), srow(lab("odin_source", T("price.source")), '<select class="select" id="odin_source" name="odin_source"><option>Nord Pool</option><option>Energi Data Service</option></select>'))) +
        typed("fixed", group(T("price.fixed"), sstep("odin_fixed_price", T("price.fixedPrice"), 2.0, 0, 10, 0.05, T("price.unit"), dec=2))))
    r_ss, seg_ss = seg("spot_source", "ss", [("eds", "EDS"), ("energy_charts", "Energy-Charts"), ("entsoe", "ENTSO-E"), ("fixed", T("price.fixed"))], "eds", T("price.spot"))
    spot = r_ss + group(T("price.spot"), srow(f'<span>{T("price.source")}</span>', seg_ss)) + typed("eds", "") + typed("energy_charts", "") + typed("entsoe", "") + \
        typed("fixed", group(T("price.fixed"), sstep("spot_fixed_eur", T("price.spotFixed"), 0.10, 0, 2, 0.01, "€/kWh", dec=2)))
    taxes = group(T("price.taxes"), srow(lab("price_currency", T("price.currency")), '<select class="select" id="price_currency" name="currency"><option selected>DKK</option><option>EUR</option><option>SEK</option></select>') +
        sstep("fx", T("price.fx"), 7.46, 0, 20, 0.01, "", dec=2) + sstep("energy_tax", T("price.energyTax"), 0.72, 0, 3, 0.01, T("price.unit"), dec=2) +
        sstep("markup", T("price.markup"), 0.05, 0, 1, 0.01, T("price.unit"), dec=2) + sstep("vat_pct", T("price.vat"), 25, 0, 30, 1, "%", dec=0) +
        srow(f'<span>{T("price.zoneDefaults")}</span>', f'<button class="btn" type="button" data-action="price-zone-defaults">{T("price.useDefaults")}</button>'))
    r_gt, seg_gt = seg("grid_source", "gt", [("datahub", "DataHub"), ("schedule", T("price.schedule")), ("none", T("common.none"))], "datahub", T("price.grid"))
    grid = r_gt + group(T("price.grid"), srow(f'<span>{T("price.source")}</span>', seg_gt)) + \
        typed("datahub", group("DataHub", sinput("grid_gln", "GLN", "5790000610099", "w-md", id_="price_gln") + sinput("grid_code", T("price.chargeCode"), "CD", "w-sm", id_="price_code"))) + \
        typed("schedule", group(T("price.schedule"), sinput("grid_schedule", T("price.scheduleRows"), "00-06:0.18;06-17:0.54;17-21:1.36;21-24:0.54", "w-lg", stack=True) +
              srow(f'<span>{T("price.scheduleRow")}</span>', f'<button class="btn" type="button" data-action="price-sched-add">{T("price.addRow")}</button><button class="btn" type="button" data-action="price-sched-remove">{T("price.removeRow")}</button>'))) + \
        typed("none", f'<p class="note">{T("price.noGrid")}</p>')
    r_en, seg_en = seg("system_source", "en", [("datahub", "DataHub"), ("fixed", T("price.fixed"))], "datahub", T("price.system"))
    systar = r_en + group(T("price.system"), srow(f'<span>{T("price.source")}</span>', seg_en)) + typed("datahub", "") + \
        typed("fixed", group(T("price.fixed"), sstep("system_fixed", T("price.systemFixed"), 0.14, 0, 2, 0.01, T("price.unit"), dec=2)))
    touch_f = typed("touch", group(T("price.touchCalc"), subpage(T("price.spot"), "EDS", spot) + subpage(T("price.taxes"), "DKK · 25 %", taxes) +
        subpage(T("price.grid"), "DataHub", grid) + subpage(T("price.system"), "DataHub", systar)))
    cats.append(("prices", T("cat.prices"), '<path d="M12 3v18M16 7H10a3 3 0 0 0 0 6h4a3 3 0 0 1 0 6H8"/>', f'''
      <form data-save="prices">
        {r_pm}
        {group(T("price.title"), sswitch("enabled", T("price.enabled"), T("price.enabledSub"), True, id_="price_enabled") +
               srow(f'<span>{T("price.model")}</span>', seg_pm) +
               srow(lab("price_zone", T("price.zone")), '<select class="select" id="price_zone" name="zone"><option selected>DK1</option><option>DK2</option></select>') +
               sinput("entsoe_token", T("price.token"), "", "w-md", id_="price_token", hint=T("price.tokenHint"), extra=' autocomplete="off"'))}
        {odin_f}{touch_f}
        {group(T("price.status"), rrow(T("price.now"), f'<b>{T.num(1.82, 2)} {T("price.unit")}</b> <span class="scale-chip" data-scale="2">{T("price.scale.2")}</span>') +
               srow(f'<span>{T("price.lastPush")}</span>', f'<button class="btn" type="button" data-action="price-push">{T("price.pushNow")}</button>', T("rt.minutesAgo", v=4)))}
        {savebar("prices")}
      </form>''', ""))
    # Cirkulationspumpe
    cats.append(("pump", T("cat.pump"), '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="1.6"/><path d="M12 10.4c0-2.6 1.2-4.4 3.6-5M13.4 12.8c2.3 1.3 3.2 3.3 2.6 5.7M10.6 12.8c-2.3 1.3-4.5 1.2-6.2-.6"/>', f'''
      <form data-save="circulation">
        {group(T("pump.connection"), sinput("host", T("hs.host"), "alpha2go.local", id_="pump_host") +
               srow(lab("pump_port", T("hs.port")), '<input class="input w-xs" type="number" id="pump_port" name="pump_port" value="80" min="1" max="65535">'))}
        {group(T("pump.entities"), sinput("flow_entity", T("pump.flowEntity"), "pump_flow", id_="pump_flow_entity") +
               sinput("head_entity", T("pump.headEntity"), "pump_head_pressure", id_="pump_head_entity") +
               sinput("power_entity", T("pump.powerEntity"), "pump_power", id_="pump_power_entity"))}
        {savebar("circulation")}
      </form>''', ""))
    # Vejr (placering)
    cats.append(("weather", T("cat.weather"), '<path d="M3 9h11a3 3 0 1 0-3-3M3 14h15a3 3 0 1 1-3 3M3 19h7"/>', f'''
      <form data-save="weather.location" data-patch>
        {group(T("wx.location"), sinput("latitude", T("wx.lat"), "55.6761", "w-sm", id_="wx_lat", extra=' inputmode="decimal"') +
               sinput("longitude", T("wx.lon"), "12.5683", "w-sm", id_="wx_lon", extra=' inputmode="decimal"') +
               srow(f'<span>{T("wx.geoLabel")}</span>', f'<button class="btn" type="button" data-action="wx-geo">{T("wx.geo")}</button>'), extra=f'<p class="note">{T("wx.boostOnSheet")}</p>')}
        {savebar("weather-location")}
      </form>''', ""))
    # Netværk
    cats.append(("network", T("cat.network"), '<path d="M2 9a15 15 0 0 1 20 0M5 13a10 10 0 0 1 14 0M8.5 16.5a5 5 0 0 1 7 0"/><circle cx="12" cy="20" r="1"/>', f'''
      <form data-save="wifi">
        {group("Wi-Fi", rrow(T("wifi.current"), "Birkemose") + rrow(T("wifi.status"), f'<span class="c-ok">{T("wifi.connected", s=-58)}</span>') +
               sinput("ssid", T("wifi.ssid"), "", "w-md", id_="wifi_ssid", extra=' maxlength="32" autocomplete="off" spellcheck="false"') +
               sinput("password", T("wifi.password"), "", "w-md", id_="wifi_password", typ="password", extra=' maxlength="64" autocomplete="new-password"'),
               extra=f'<p class="note">{T("wifi.hint")}</p>')}
        {savebar("wifi")}
      </form>''', ""))
    # Firmware og backup
    cats.append(("firmware", T("cat.firmware"), '<path d="M12 4v10M8 10l4 4 4-4M5 19h14"/>', f'''
      <form data-save="firmware">
        {group(T("fw.firmware"), rrow(T("fw.installed"), "1.4.0") + rrow(T("fw.latest"), "1.4.0") +
               srow(f'<span>{T("fw.update")}</span>', f'<button class="btn" type="submit" name="action" value="check">{T("fw.check")}</button><button class="btn primary" type="submit" name="action" value="install" hidden>{T("fw.install")}</button>', T("fw.upToDate")) +
               srow(lab("ota_file", T("fw.upload")), file_input("ota_file", ".bin,.ota.bin")) +
               srow(f'<span>{T("fw.uploadLabel")}</span>', f'<button class="btn" type="submit" name="action" value="upload">{T("fw.uploadBtn")}</button>'))}
      </form>
      <form data-save="backup">
        {group(T("fw.backup"), srow(f'<span>{T("fw.export")}</span>', f'<button class="btn" type="submit" name="action" value="export">{T("fw.exportBtn")}</button>', T("fw.exportHint")) +
               srow(lab("backup_file", T("fw.importFile")), file_input("backup_file", "application/json,.json")))}
        <div class="actions">{confirm("cf-import", T("fw.import"), T("fw.importAsk"), T("fw.importNote"), T("fw.importDo"), value="import")}</div>
      </form>''', ""))
    # Service
    cats.append(("service", T("cat.service"), '<path d="M14 6a4 4 0 0 0-5 5l-5 5 3 3 5-5a4 4 0 0 0 5-5l-2 2-3-3z"/>', f'''
      <section class="sys-diag">
        {group(T("svc.house"), rrow(T("svc.coverage"), "10 / 12", T("svc.coverageHint")) + rrow(T("svc.authority"), "Touch") +
               rrow(T("svc.dist"), "52 · 38 · 10 %"))}
        {group(T("svc.links"), rrow(T("svc.odinLink"), f'<span class="c-ok">{T("status.ok")}</span> · odin.local') + rrow(T("svc.hostIp"), '<span class="mono">lune-touch.local · 192.168.20.186</span>') +
               rrow(T("svc.nodes"), T("svc.nodesVal", on=2, n=3)) + rrow(T("svc.poll"), T("rt.secondsAgo", v=4)) + rrow("OTA", T("fw.upToDate")))}
        <section class="setting-group"><h4>{T("svc.log")}</h4><pre class="log" data-bind="log" aria-live="polite" lang="en">14:31  <span class="info">asgard</span> push 21.9 °C → temperature_feedback_z1 (200)
14:30  <span class="violet">odin</span> plan updated, next block 06:00–09:00
14:29  <span class="bad">node M2</span> zone Z4 end-stop timeout
12:12  <span class="bad">node M3</span> unreachable (timeout)</pre></section>
        <div class="actions">{confirm("cf-registry", T("svc.reset"), T("svc.resetAsk"), T("svc.resetNote"), T("svc.resetDo"), action="reset-registry", btn_type="button")}</div>
      </section>''', ""))

    sys_radios = f'<input class="state" type="radio" name="syscat" id="c-none" checked aria-label="{T("sys.cats")}">' + "".join(
        f'<input class="state" type="radio" name="syscat" id="c-{c}" data-hash="{T("hash." + c)}" aria-label="{t}">' for c, t, *_ in cats)
    sys_nav = "".join(f'<label for="c-{c}"><svg viewBox="0 0 24 24" aria-hidden="true">{ic}</svg>{t}</label>' for c, t, ic, *_ in cats)
    sys_view = f'''
      <section class="view" id="v-sys" aria-labelledby="h-sys">
        <h2 class="sr-only" id="h-sys">{T("sys.title")}</h2>
        {sys_radios}
        <div class="sys">
          <nav class="sys-nav" aria-label="{T("sys.cats")}">{sys_nav}</nav>
          <div class="sys-main">{"".join(syscat(c, t, body, badge) for c, t, _, body, badge in cats)}</div>
        </div>
      </section>'''

    # ================================================================ side
    cur = T.meta("_lang")
    if len(langs) > 1:
        links = "".join(f'<a href="{lang_urls[c.meta("_lang")]}" hreflang="{c.meta("_lang")}" lang="{c.meta("_lang")}" title="{c.meta("_name")}"'
                        f'{" aria-current=\"true\"" if c.meta("_lang") == cur else ""}>{c.meta("_short")}</a>' for c in langs)
        langnav = f'<nav class="lang" aria-label="{T("lang.label")}">{links}</nav>'
    else:
        langnav = ""
    rt = {k: T(k) for k in ("rt.savedOk", "rt.saveFailed", "rt.saving", "rt.unsaved.one", "rt.unsaved.other", "rt.nothingToSave", "rt.leaveUnsaved",
                            "rt.autoSaving", "rt.autoSaved", "rt.autoFailed", "rt.retry", "rt.secondsAgo", "rt.minutesAgo", "rt.offline",
                            "state.calling", "state.idle", "state.fault", "state.off", "device.copied")}
    rt["_dec"] = T.meta("_dec")
    rt["_lang"] = cur
    rt_json = json.dumps(rt, ensure_ascii=False, separators=(",", ":"))
    LOGO = ('<svg class="logo" viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="15" fill="var(--fg)"/>'
            '<path d="M10 22V12M14 22V10M18 22V13M22 22V11" stroke="var(--accent)" stroke-width="2.4" stroke-linecap="round"/></svg>')
    I_HOME = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 11l8-7 8 7v9h-5v-6H9v6H4z"/></svg>'
    I_SYS = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/></svg>'
    css_tag = f"<style>\n{inline_css}\n</style>" if inline_css else f'<link rel="stylesheet" href="{css_href}">'
    js_tag = (f"<script>\n{FORMS_JS}</script>\n<script>\n{(ROOT / 'binder.js').read_text(encoding='utf-8')}</script>" if inline_css
              else '<script src="/lune-forms.js" defer></script>\n<script src="/ui.js" defer></script>')
    others = "".join(f'<link rel="alternate" hreflang="{c.meta("_lang")}" href="{lang_urls[c.meta("_lang")]}">' for c in langs if c.meta("_lang") != cur) if len(langs) > 1 else ""

    return f'''<!doctype html>
<html lang="{cur}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<title>{T("doc.title")}</title>
{others}
{css_tag}
</head>
<body>

<!-- TILSTAND — før .app: Hjem/System, omfang (kun huset), tema -->
<input class="state" type="radio" name="mode" id="m-home" checked aria-label="{T("nav.home")}">
<input class="state" type="radio" name="mode" id="m-sys" data-hash="{T("hash.system")}" aria-label="{T("nav.system")}">
<input class="state" type="radio" name="scope" id="s-house" checked aria-label="{T("scope.house")}">
<input class="state" type="checkbox" id="theme" aria-label="{T("theme.toggle")}">

<div class="app">
{LDS_DEFS}
  <div class="navbar-wrap wrap">
    <header class="header">
      <details class="device">
        <summary>{LOGO}<span class="name"><b>Lune Touch</b><small>{T("device.sample")}</small></span><span class="caret" aria-hidden="true"></span></summary>
        <div class="device-menu">
          <section class="device-about" aria-labelledby="device-about-h">
            <h3 id="device-about-h">{T("device.about")}</h3>
            {kv([(T("dev.name"), "Lune Touch"), ("IP", "192.168.20.186"), (T("fw.installed"), "1.4.0"), (T("device.uptime"), T("device.uptimeVal"))])}
            <button type="button" class="btn copy" data-copy=".device-about dl">{T("device.copyDiag")}</button>
          </section>
          <nav aria-label="{T("nav.devices")}">
            <a href="#" aria-current="page"><i></i>Lune Touch<small>192.168.20.186 · {T("device.this")}</small></a>
            {"".join(f'<a href="http://{m["ip"]}/"{"" if m["online"] else " data-offline"}><i></i>{m["name"]}<small>{m["ip"]}</small></a>' for m in MANIFOLDS)}
          </nav>
        </div>
      </details>
      <nav class="mode" aria-label="{T("nav.label")}">
        <label for="m-home">{I_HOME}{T("nav.home")}</label>
        <label for="m-sys">{I_SYS}{T("nav.system")}</label>
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
  <main class="content wrap">{home}{sys_view}
  </main>
{sheets}
</div>

<script type="application/json" id="i18n">{rt_json}</script>
<script>
document.addEventListener('click',function(e){{var b=e.target.closest('[data-step]');
if(b&&!b.disabled){{var i=b.parentNode.querySelector('input');b.dataset.step>0?i.stepUp():i.stepDown();i.dispatchEvent(new Event('change',{{bubbles:true}}));}}
var d=document.querySelector('.device[open]');if(d&&!d.contains(e.target))d.open=false;}});
document.addEventListener('change',function(e){{var f=e.target;if(f.type==='file'){{var n=f.closest('label').querySelector('.file-name');if(n)n.textContent=f.files.length?f.files[0].name:n.dataset.empty;}}}});
</script>
{js_tag}
</body>
</html>
'''


# ---------------------------------------------------------------- main -----
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--langs", default=os.environ.get("LUNE_UI_LANGS", "en,da"))
    ap.add_argument("--out", default=str(ROOT / "dist"))
    ap.add_argument("--css", default=str(DS_ROOT / "dist" / "touch" / "lune-ui.css"))
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--hs-type", default="asgard", choices=("http", "asgard"), help="varmekildens type i eksemplet")
    a = ap.parse_args()

    codes = [c.strip() for c in a.langs.split(",") if c.strip()]
    avail = sorted(p.stem for p in (ROOT / "i18n").glob("*.json"))
    for c in codes:
        if c not in avail:
            sys.exit(f"Ukendt sprog '{c}'. Tilgængelige: {', '.join(avail)}")
    base = Cat("en", None) if "en" in avail else None
    cats = [Cat(c, None if c == "en" else base) for c in codes]

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    css = ensure_css(pathlib.Path(a.css))
    files = {"lune-ui.css": css, "lune-forms.js": FORMS_JS, "ui.js": (ROOT / "binder.js").read_text(encoding="utf-8")}
    sizes = {}
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8")
        gz = gzip.compress(text.encode(), 9, mtime=0)
        (out / f"{name}.gz").write_bytes(gz)
        sizes[name] = len(gz)

    urls = {c.meta("_lang"): f"/{c.meta('_lang')}/" for c in cats}
    pages = []
    for c in cats:
        html = render(c, cats, urls, "/lune-ui.css", a.hs_type)
        d = out / c.meta("_lang")
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(html, encoding="utf-8")
        gz = gzip.compress(html.encode(), 9, mtime=0)
        (d / "index.html.gz").write_bytes(gz)
        pages.append((c.meta("_lang"), gz))
        if c.missing:
            print(f"ADVARSEL: {c.meta('_lang')} mangler {len(c.missing)} nøgler: {', '.join(sorted(c.missing))}")
    if a.preview:
        for c in cats:
            (out / f"preview-{c.meta('_lang')}.html").write_text(render(c, cats, urls, None, a.hs_type, inline_css=css), encoding="utf-8")

    total = sum(sizes.values()) + sum(len(g) for _, g in pages)
    print(f"Byggede {', '.join(codes)} → {out}/  (gzip {total / 1024:.1f} kB: " + " + ".join(f"{k} {v / 1024:.1f}" for k, v in sizes.items()) + " + "
          + " + ".join(f"{l} {len(g) / 1024:.1f}" for l, g in pages) + ")")


if __name__ == "__main__":
    main()
