#!/usr/bin/env python3
"""
Lune Touch web-UI — reference example for Lune Design System 2 (config/touch.json).

    python build_ui.py
    python build_ui.py --langs en,da --preview --hs-type asgard

Output (in --out, default ./dist):
    lune-ui.css(.gz)
    ui.js(.gz)
    <lang>/index.html(.gz)
    preview-<lang>.html   (with --preview)
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent
DS_ROOT = ROOT.parent.parent

# Demo zones: (m, z, name, temp, target, state, opening%, group)
# group: None | "primary" | "member"
ZONES = [
    (1, 1, "Entré", 20.9, 21.0, "idle", 12, None),
    (1, 2, "Køkken", 21.2, 21.0, "idle", 8, None),
    (1, 3, "Spise", 21.4, 21.5, "calling", 52, None),
    (1, 4, "Stue", 21.1, 21.5, "idle", 40, "primary"),
    (1, 5, "Spisekrog", 21.0, 21.5, "calling", 48, "member"),
    (1, 6, "Kontor", 20.6, 21.0, "idle", 10, None),
    (2, 1, "Soveværelse", 19.8, 20.0, "idle", 15, None),
    (2, 2, "Bad", 22.1, 22.0, "idle", 6, None),
    (2, 3, "Gang", 20.2, 20.0, "fault", 0, None),
    (2, 4, "Værelse", 20.5, 21.0, "idle", 11, None),
    (2, 5, "Kontor", 20.7, 21.0, "idle", 9, None),
    (3, 1, "Stue", 20.4, 20.5, "idle", 14, None),
    (3, 2, "Soveværelse", 19.6, 19.5, "idle", 7, None),
    (3, 3, "Bad", 22.0, 22.0, "idle", 5, None),
    (4, 1, "Værksted", 16.8, 18.0, "idle", 20, None),
    (4, 2, "Bil", 8.0, 12.0, "off", 0, None),
]

MANIFOLDS = [
    {"n": 1, "label": "Stueetage", "zones": 6, "flow": 33.1, "return": 29.9},
    {"n": 2, "label": "1. sal", "zones": 5, "flow": 31.2, "return": 28.4},
    {"n": 3, "label": "Anneks", "zones": 3, "flow": 30.5, "return": 27.8},
    {"n": 4, "label": "Garage", "zones": 2, "flow": 28.0, "return": 26.2},
]


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


def zone_level(z):
    st, op = z[5], z[6]
    if st in ("fault", "off"):
        return 0
    return max(1, min(5, math.ceil(op / 20)))


def zone_by_mz():
    return {(z[0], z[1]): z for z in ZONES}


def manifold_stats(mn, zb):
    zones = [zb[(mn, z)] for z in range(1, next(x["zones"] for x in MANIFOLDS if x["n"] == mn) + 1)]
    calling = sum(1 for z in zones if z[5] == "calling")
    faults = sum(1 for z in zones if z[5] == "fault")
    state = "fault" if faults else ("calling" if calling else "idle")
    return zones, calling, faults, state


def ensure_css(path: pathlib.Path) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    cfg = DS_ROOT / "config" / "touch.json"
    build = DS_ROOT / "tools" / "lds_build.py"
    print(f"Mangler {path}, kører lds_build …")
    subprocess.run([sys.executable, str(build), str(cfg)], cwd=DS_ROOT, check=True)
    if not path.is_file():
        sys.exit(f"Kunne ikke bygge {path}")
    return path.read_text(encoding="utf-8")


def render(T, langs, lang_urls, css_href, js_href, hs_type, inline_css=None):
    ST = {k: T(f"state.{k}") for k in ("calling", "idle", "fault", "off")}
    zb = zone_by_mz()
    hs_type = hs_type if hs_type in ("http", "asgard") else "asgard"

    def switch(name, t, sub, on):
        sub_html = f"<small>{sub}</small>" if sub else ""
        chk = " checked" if on else ""
        return (
            f'<label class="switch"><span class="switch-text"><b>{t}</b>{sub_html}</span>'
            f'<input type="checkbox" role="switch" name="{name}"{chk}></label>'
        )

    def row(id_, label, control, hint=""):
        h = f'<span class="hint">{hint}</span>' if hint else ""
        return f'<div class="field row"><label for="{id_}">{label}{h}</label>{control}</div>'

    def stepper(name, val, mn, mx, step, unit, label, dec=1):
        return (
            f'<div class="stepper"><button type="button" data-step="-1" aria-label="{T("common.decrease", x=label.lower())}">−</button>'
            f'<span class="value"><input type="number" inputmode="decimal" id="{name}" name="{name}" '
            f'value="{val:.{dec}f}" min="{mn}" max="{mx}" step="{step}"><span class="unit">{unit}</span></span>'
            f'<button type="button" data-step="1" aria-label="{T("common.increase", x=label.lower())}">+</button></div>'
        )

    def help_btn(hid, topic):
        return (
            f'<button class="help-btn" type="button" popovertarget="{hid}" style="anchor-name:--a-{hid}" '
            f'aria-label="{T("help.aria", topic=topic)}">?</button>'
        )

    def help_pop(hid, body_key):
        return (
            f'<div id="{hid}" popover class="help-pop" style="position-anchor:--a-{hid}">'
            f"<p>{T(body_key)}</p></div>"
        )

    def file_input(name, accept):
        return (
            f'<label class="input file" for="{name}">'
            f'<input class="sr-only" id="{name}" name="{name}" type="file" accept="{accept}">'
            f'<span class="file-pick">{T("common.chooseFile")}</span>'
            f'<span class="file-name" data-empty="{T("common.noFile")}">{T("common.noFile")}</span></label>'
        )

    def metric(label, val, unit, bind="", cls=""):
        b = f' data-bind="{bind}"' if bind else ""
        c = f' class="{cls}"' if cls else ""
        return f'<div class="metric"><dt>{label}</dt><dd{b}{c}>{val} <small>{unit}</small></dd></div>'

    def sect(key):
        return f'<header class="section-head"><span>{T(key)}</span></header>'

    def scope_title_manifold(m):
        mid = f"M{m['n']}"
        return T("scope.title.manifold", id=mid, name=m["label"])

    def scope_title_zone(z):
        mid = f"M{z[0]}"
        zid = f"Z{z[1]}"
        return T("scope.title.zone", id=f"{mid} {zid}", name=z[2])

    house_sub = T(
        "dash.house.sub",
        manifolds=len(MANIFOLDS),
        calling=sum(1 for z in ZONES if z[5] == "calling"),
        faults=sum(1 for z in ZONES if z[5] == "fault"),
    )

    # ---- scope radios (before .app)
    scope_inputs = [
        f'<input class="state" type="radio" name="scope" id="s-house" checked '
        f'data-kind="house" aria-label="{T("scope.house")}" '
        f'data-title="{T("scope.title.house")}" data-sub="{house_sub}">'
    ]
    for m in MANIFOLDS:
        mn = m["n"]
        _, calling, faults, mst = manifold_stats(mn, zb)
        msub = T(
            "dash.manifold.sub",
            zones=m["zones"],
            calling=calling,
            state=ST.get(mst, mst),
        )
        scope_inputs.append(
            f'<input class="state" type="radio" name="scope" id="s-m{mn}" '
            f'data-kind="manifold" data-m="{mn}" aria-label="{scope_title_manifold(m)}" '
            f'data-title="{scope_title_manifold(m)}" data-sub="{msub}">'
        )
        for z in range(1, m["zones"] + 1):
            zd = zb[(mn, z)]
            zsub = T("dash.zone.sub", state=ST[zd[5]], target=T.num(zd[4]))
            scope_inputs.append(
                f'<input class="state" type="radio" name="scope" id="s-m{mn}z{z}" '
                f'data-kind="zone" data-m="{mn}" aria-label="{T("scope.zone", m=mn, z=z)}" '
                f'data-title="{scope_title_zone(zd)}" data-sub="{zsub}">'
            )

    # ---- strip + substrips
    manifold_tiles = []
    substrips = []
    for m in MANIFOLDS:
        mn = m["n"]
        zones, calling, faults, mst = manifold_stats(mn, zb)
        mid = f"M{mn}"
        fault_txt = T("common.noFaults") if faults == 0 else T("common.faults", n=faults)
        aria = (
            T("tile.manifold.ariaOk", id=mid, name=m["label"], calling=calling, zones=m["zones"])
            if faults == 0
            else T("tile.manifold.aria", id=mid, name=m["label"], calling=calling, zones=m["zones"], faults=fault_txt)
        )
        ds = f' data-state="{mst}"' if mst in ("fault", "calling") else ""
        mini = "".join(
            f'<i data-level="{zone_level(zb[(mn, z)])}" data-state="{zb[(mn, z)][5]}"></i>'
            for z in range(1, m["zones"] + 1)
        )
        manifold_tiles.append(
            f'''
          <label class="tile tile-manifold" for="s-m{mn}" aria-label="{aria}"{ds}>
            <span class="tile-id">{mid}</span>
            <span class="tile-name">{m["label"]}</span>
            <span class="tile-val">{T.num(m["flow"])}° / {T.num(m["return"])}°</span>
            <span class="mini" aria-hidden="true">{mini}</span>
          </label>'''
        )
        zone_tiles = []
        for z in range(1, m["zones"] + 1):
            zd = zb[(mn, z)]
            st = zd[5]
            val = T("tile.fault") if st == "fault" else (T("tile.off") if st == "off" else f"{T.num(zd[3])}°")
            grp = f' data-group="{zd[7]}"' if zd[7] else ""
            zaria = T(
                "tile.zone.aria",
                id=f"M{mn} Z{z}",
                name=zd[2],
                state=ST[st],
                temp=T.num(zd[3]),
            )
            zone_tiles.append(
                f'''
          <label class="tile" for="s-m{mn}z{z}" data-state="{st}" data-level="{zone_level(zd)}"{grp} aria-label="{zaria}">
            <span class="lvl" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></span>
            <span class="tile-id">Z{z}</span>
            <span class="tile-name">{zd[2]}</span>
            <span class="tile-val">{val}</span>
          </label>'''
            )
        substrips.append(
            f'''<nav class="substrip" data-m="{mn}" style="--sub-n:{m["zones"]}" aria-label="{T("strip.sub", name=m["label"])}">
{"".join(zone_tiles)}
        </nav>'''
        )

    strip = f'''<nav class="strip strip--tiers" aria-label="{T("strip.label")}">
          <label class="tile tile-sys" for="s-house" title="{T("scope.house")}">
            <span class="tile-id">{T("strip.house")}</span>
            <span class="temps">
              <span class="temp flow">
                <span class="temp-lab" title="{T("heat.supply")}">{T("m.supplyShort")}</span>
                <span class="tile-val">{T.num(21.2)}°</span>
              </span>
              <span class="temp ret">
                <span class="temp-lab" title="{T("heat.return")}">{T("m.returnShort")}</span>
                <span class="tile-val">{T.num(8.4)}°</span>
              </span>
            </span>
          </label>{"".join(manifold_tiles)}
        </nav>
{"".join(substrips)}'''

    def heat_bars():
        cols = []
        for i in range(12):
            plan = 35 + (i * 9) % 55
            act = max(10, plan - 8 + (i % 5))
            cols.append(
                f'<div class="col"><i class="plan" style="--plan:{plan}"></i><i class="act" style="--act:{act}"></i></div>'
            )
        return (
            f'<div class="bars" style="--bars-n:12"><div class="bars-plot">{"".join(cols)}</div>'
            f'<div class="bars-legend"><span><i class="lp"></i>{T("heat.barsLegendPlan")}</span>'
            f'<span><i class="la"></i>{T("heat.barsLegendAct")}</span></div></div>'
        )

    def attn_row(z):
        m, n, name, temp, _target, state, *_rest = z
        return (
            f'<label for="s-m{m}z{n}" data-state="{state}">'
            f'<span class="id">M{m}</span>'
            f'<span class="name">{name}</span>'
            f'<span class="val"><b>{T.num(temp)}°</b> {T(f"state.short.{state}")}</span>'
            f'</label>'
        )

    attention = "".join(attn_row(z) for z in ZONES if z[5] in ("calling", "fault"))

    def zone_row(z):
        m, n, name, temp, target, state, *_rest = z
        return (
            f'<label for="s-m{m}z{n}" data-state="{state}">'
            f'<span class="id">Z{n}</span>'
            f'<span class="name">{name}</span>'
            f'<span class="val"><b>{T.num(temp)}°</b> {T.num(target)}°</span>'
            f'</label>'
        )

    manifold_zones = "".join(zone_row(z) for z in ZONES if z[0] == 1)

    insight = f'''<svg class="insight" viewBox="0 0 240 80" preserveAspectRatio="none" role="img" aria-label="{T("dash.zone.insight")}">
              <path class="area" d="M0 58C28 56 48 44 78 38C112 31 132 24 164 26C198 28 214 34 240 32V80H0Z"/>
              <path class="goal" d="M0 42H240"/>
              <path class="line" d="M0 58C28 56 48 44 78 38C112 31 132 24 164 26C198 28 214 34 240 32"/>
            </svg>'''

    dash_house = f'''
      <section class="view" id="v-dash-house" aria-labelledby="h-dash-house">
        <header class="view-head"><h2 id="h-dash-house" data-bind="scope.title">{T("scope.title.house")}</h2><p data-bind="scope.sub">{house_sub}</p></header>

        <div class="panel alert" hidden>
          <div class="panel-head"><h3>{T("alert.heatConn")}</h3></div>
          <p class="note">{T("alert.heatConnBody")}</p>
          <div class="panel-foot" style="justify-content:flex-start"><label class="btn" for="m-conf">{T("alert.openHeat")}</label></div>
        </div>

        <section class="panel c5">
          <header class="panel-head"><h3>{T("dash.now")}</h3></header>
          <dl class="metrics">
            {metric(T("climate.now"), T.num(21.2), "°C", "house.temp")}
            {metric(T("climate.outdoor"), T.num(8.4), "°C", "house.outdoor", "c-info")}
            {metric(T("climate.target"), T.num(21.0), "°C", "house.target")}
          </dl>
        </section>

        <section class="panel c7">
          <header class="panel-head"><h3>{T("dash.attention")}</h3>{help_btn("help-attn", T("dash.attention"))}<p>{T("dash.attentionHint")}</p></header>
          {help_pop("help-attn", "dash.attentionHelp")}
          <div class="comfort">{attention}</div>
        </section>

        <section class="panel wide" data-hs-type="{hs_type}">
          <header class="panel-head"><h3>{T("heat.title")}</h3><span class="badge ok">{T("heat.badge.ok")}</span></header>
          <div class="hs-type-asgard sub">
            <dl class="metrics">
              {metric(T("heat.supply"), T.num(38.2), "°C", "heat.supply")}
              {metric(T("heat.return"), T.num(32.1), "°C", "heat.return", "c-info")}
              {metric(T("heat.setpoint"), T.num(21.0), "°C", "heat.setpoint")}
            </dl>
            <h4>{T("heat.barsTitle")}</h4>
            {heat_bars()}
          </div>
          <div class="hs-type-http sub">
            <dl class="kv"><div><dt>{T("heat.httpStatus")}</dt><dd class="c-ok" data-bind="heat.httpStatus">200 OK</dd></div></dl>
          </div>
        </section>
      </section>'''

    dash_manifold = f'''
      <section class="view" id="v-dash-manifold" aria-labelledby="h-dash-manifold">
        <header class="view-head"><h2 id="h-dash-manifold" data-bind="scope.title">{T("scope.title.manifold", id="M1", name="Stueetage")}</h2><p data-bind="scope.sub">{T("dash.manifold.sub", zones=6, calling=2, state=ST["calling"])}</p></header>
        <section class="panel c5">
          <header class="panel-head"><h3>{T("mconf.title")}</h3></header>
          <dl class="metrics">
            {metric(T("mconf.supply"), T.num(33.1), "°C")}
            {metric(T("mconf.return"), T.num(29.9), "°C", "", "c-info")}
          </dl>
          <p class="note">{T("common.note")}: {T("mconf.note")}</p>
        </section>
        <section class="panel c7">
          <header class="panel-head"><h3>{T("dash.zones")}</h3><p>{T("dash.zonesHint")}</p></header>
          <div class="comfort">{manifold_zones}</div>
        </section>
      </section>'''

    dash_zone = f'''
      <section class="view" id="v-dash-zone" aria-labelledby="h-dash-zone">
        <header class="view-head"><h2 id="h-dash-zone" data-bind="scope.title">{scope_title_zone(zb[(1, 3)])}</h2><p data-bind="scope.sub">{T("dash.zone.sub", state=ST["calling"], target=T.num(21.5))}</p></header>
        <section class="panel c5">
          <header class="panel-head"><h3>{T("zconf.title")}</h3><span class="badge hot">{ST["calling"]}</span></header>
          <dl class="metrics">
            {metric(T("climate.now"), T.num(21.4), "°C")}
            {metric(T("climate.target"), T.num(21.5), "°C")}
          </dl>
          <h4>{T("dash.zone.insight")}</h4>
          {insight}
          <p class="note">{T("dash.zone.note")}</p>
        </section>
      </section>'''

    http_checked = " checked" if hs_type == "http" else ""
    asgard_checked = " checked" if hs_type == "asgard" else ""

    conf_house = f'''
      <section class="view" id="v-conf-house" aria-labelledby="h-conf-house">
        <header class="view-head"><h2 id="h-conf-house" data-bind="scope.title">{T("scope.title.house")}</h2><p data-bind="scope.sub">{house_sub}</p></header>
        {sect("sect.connect")}
        <form class="panel c6 gated" data-save="heat_source">
          <header class="panel-head"><h3>{T("hs.title")}</h3>{help_btn("help-hs", T("hs.title"))}</header>
          {help_pop("help-hs", "help.heatSource")}
          {switch("enabled", T("hs.enabled"), "", True)}
          <div class="gated-body">
            <input class="state" type="radio" name="hs_type" id="hs-http" value="http"{http_checked}>
            <input class="state" type="radio" name="hs_type" id="hs-asgard" value="asgard"{asgard_checked}>
            <div class="seg" role="radiogroup" aria-label="{T("hs.type")}">
              <label for="hs-http"><span>{T("hs.typeHttp")}</span></label>
              <label for="hs-asgard"><span>{T("hs.typeAsgard")}</span></label>
            </div>
            <fieldset class="hs-fields typed-fields" data-type="http">
              {help_btn("help-hs-http", T("hs.typeHttp"))}
              {help_pop("help-hs-http", "help.heatHttp")}<!-- TODO: POST method is fixed in firmware; no UI field. -->
              <!-- TODO: HTTP timeout 2500 ms is fixed in firmware; not configurable here. -->
              {row("http_host", T("hs.host"), '<input class="input" id="http_host" name="host" value="heat-bridge.local">')}
              {row("http_port", T("hs.port"), stepper("http_port", 80, 1, 65535, 1, "", T("hs.port"), dec=0))}
              {row("http_push_interval_s", T("hs.pushInterval"), stepper("http_push_interval_s", 60, 5, 3600, 5, "s", T("hs.pushInterval"), dec=0))}
              {row("http_weighted_temperature_variable", T("hs.weightedVar"), '<input class="input" id="http_weighted_temperature_variable" name="weighted_temperature_variable" value="temperature_feedback_z1">')}
              {row("write_url_template", T("hs.writeUrl"), '<input class="input" id="write_url_template" name="write_url_template" required placeholder="http://{{host}}/{{entity}}/set?value={{value}}">')}
              {row("read_url_template", T("hs.readUrl"), '<input class="input" id="read_url_template" name="read_url_template" required placeholder="http://{{host}}/{{entity}}">')}
            </fieldset>
            <fieldset class="hs-fields typed-fields" data-type="asgard">
              {help_btn("help-hs-asgard", T("hs.typeAsgard"))}
              {help_pop("help-hs-asgard", "help.heatAsgard")}
              {row("asgard_host", T("hs.host"), '<input class="input" id="asgard_host" name="host" value="asgard.local">')}
              {row("asgard_port", T("hs.port"), stepper("asgard_port", 80, 1, 65535, 1, "", T("hs.port"), dec=0))}
              {row("asgard_push_interval_s", T("hs.pushInterval"), stepper("asgard_push_interval_s", 60, 5, 3600, 5, "s", T("hs.pushInterval"), dec=0))}
              {row("asgard_weighted_temperature_variable", T("hs.weightedVar"), '<input class="input" id="asgard_weighted_temperature_variable" name="weighted_temperature_variable" value="temperature_feedback_z1">')}
              {row("climate_entity", T("hs.climateEntity"), '<input class="input" id="climate_entity" name="climate_entity" value="virtual_thermostat">')}
              {switch("target_sync_enabled", T("hs.targetSync"), "", True)}
              {switch("odin_plan_enabled", T("hs.odinPlan"), "", True)}
            </fieldset>
          </div>
          <footer class="panel-foot">
            <button class="btn" type="button" data-action="hs-test-read">{T("hs.testRead")}</button>
            <button class="btn" type="button" data-action="hs-test-push">{T("hs.testPush")}</button>
            <button class="btn primary" type="submit">{T("hs.save")}</button>
          </footer>
        </form>

        {sect("sect.service")}

        <form class="panel c6" data-save="firmware">
          <header class="panel-head"><h3>{T("csys.firmware")}</h3>{help_btn("help-firmware", T("csys.firmware"))}</header>
          {help_pop("help-firmware", "help.firmware")}
          <dl class="kv">
            <div><dt>{T("csys.fwInstalled")}</dt><dd data-bind="fw.installed">1.0.0</dd></div>
            <div><dt>{T("csys.fwLatest")}</dt><dd data-bind="fw.latest">—</dd></div>
          </dl>
          <div class="actions">
            <button class="btn" type="submit" name="action" value="check">{T("csys.fwCheck")}</button>
            <button class="btn" type="submit" name="action" value="install" disabled>{T("csys.fwInstall")}</button>
          </div>
          <div class="field"><label for="ota_file">{T("csys.fwUpload")}</label>{file_input("ota_file", ".bin,.ota.bin")}</div>
          <footer class="panel-foot"><button class="btn primary" type="submit" name="action" value="upload" disabled>{T("csys.fwUploadBtn")}</button></footer>
        </form>

        <form class="panel c6" data-save="backup">
          <header class="panel-head"><h3>{T("csys.backup")}</h3>{help_btn("help-backup", T("csys.backup"))}</header>
          {help_pop("help-backup", "help.backup")}
          <p class="note">{T("csys.backupNote")}</p>
          <div class="field"><label for="backup_file">{T("csys.backupImport")}</label>{file_input("backup_file", "application/json,.json")}</div>
          <footer class="panel-foot">
            <button class="btn" type="submit" name="action" value="export">{T("csys.backupExport")}</button>
            <button class="btn primary" type="submit" name="action" value="import" disabled>{T("csys.backupImportBtn")}</button>
          </footer>
        </form>
      </section>'''

    conf_manifold = f'''
      <section class="view" id="v-conf-manifold" aria-labelledby="h-conf-manifold">
        <header class="view-head"><h2 id="h-conf-manifold" data-bind="scope.title">{scope_title_manifold(MANIFOLDS[0])}</h2><p data-bind="scope.sub">{T("dash.manifold.sub", zones=6, calling=2, state=ST["calling"])}</p></header>
        <form class="panel c5" data-save="manifold">
          <header class="panel-head"><h3>{T("mconf.title")}</h3></header>
          {row("manifold_name", T("mconf.name"), f'<input class="input" id="manifold_name" name="name" value="{MANIFOLDS[0]["label"]}">')}
          <p class="note">{T("mconf.note")}</p>
          <footer class="panel-foot"><button class="btn primary" type="submit">{T("mconf.save")}</button></footer>
        </form>
      </section>'''

    conf_zone = f'''
      <section class="view" id="v-conf-zone" aria-labelledby="h-conf-zone">
        <header class="view-head"><h2 id="h-conf-zone" data-bind="scope.title">{scope_title_zone(zb[(1, 3)])}</h2><p data-bind="scope.sub">{T("dash.zone.sub", state=ST["calling"], target=T.num(21.5))}</p></header>
        <form class="panel c5" data-save="zone">
          <header class="panel-head"><h3>{T("zconf.title")}</h3></header>
          {row("zone_name", T("zconf.name"), '<input class="input" id="zone_name" name="name" value="Spise">')}
          {switch("zone_enabled", T("zconf.enabled"), "", True)}
          <p class="note">{T("zconf.note")}</p>
          <footer class="panel-foot"><button class="btn primary" type="submit">{T("zconf.save")}</button></footer>
        </form>
      </section>'''

    views = dash_house + dash_manifold + dash_zone + conf_house + conf_manifold + conf_zone

    cur = T.meta("_lang")
    if len(langs) > 1:
        links = "".join(
            f'<a href="{lang_urls[c.meta("_lang")]}" hreflang="{c.meta("_lang")}" lang="{c.meta("_lang")}" '
            f'title="{c.meta("_name")}"{" aria-current=\"true\"" if c.meta("_lang") == cur else ""}>'
            f'{c.meta("_short")}</a>'
            for c in langs
        )
        langnav = f'<nav class="lang" aria-label="{T("lang.label")}">{links}</nav>'
    else:
        langnav = ""

    rt = {k: T(k) for k in ("rt.savedOk", "rt.saveFailed", "state.calling", "state.idle", "state.fault", "state.off")}
    rt["_dec"] = T.meta("_dec")
    rt["_lang"] = cur
    rt_json = json.dumps(rt, ensure_ascii=False, separators=(",", ":"))

    LOGO = (
        '<svg class="logo" viewBox="0 0 32 32" aria-hidden="true">'
        '<circle cx="16" cy="16" r="15" fill="var(--fg)"/>'
        '<path d="M10 22V12M14 22V10M18 22V13M22 22V11" stroke="var(--accent)" stroke-width="2.4" stroke-linecap="round"/></svg>'
    )
    I_DASH = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 14a8 8 0 0 1 16 0"/><path d="M12 14l4-4"/><circle cx="12" cy="14" r="1.2"/></svg>'
    I_CONF = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/></svg>'
    css_tag = f"<style>\n{inline_css}\n</style>" if inline_css else f'<link rel="stylesheet" href="{css_href}">'
    js_tag = f'<script src="{js_href}" defer></script>' if js_href else ""
    others = (
        "".join(
            f'<link rel="alternate" hreflang="{c.meta("_lang")}" href="{lang_urls[c.meta("_lang")]}">'
            for c in langs
            if c.meta("_lang") != cur
        )
        if len(langs) > 1
        else ""
    )

    return f'''<!doctype html>
<html lang="{cur}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" media="(prefers-color-scheme: light)" content="#fbfaf8">
<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#121210">
<title>{T("doc.title")}</title>
{others}
{css_tag}
</head>
<body>

<!-- TILSTAND — før .app -->
<input class="state" type="radio" name="mode" id="m-dash" checked aria-label="{T("mode.dash")}">
<input class="state" type="radio" name="mode" id="m-conf" aria-label="{T("mode.conf")}">
{"".join(scope_inputs)}
<input class="state" type="checkbox" id="theme" aria-label="{T("theme.toggle")}">

<div class="app">
  <div class="top">
    <div class="wrap">
      <header class="header">
        <details class="device">
          <summary>{LOGO}<span class="name"><b>Lune Touch</b><small>{T("device.sample")}</small></span><span class="caret" aria-hidden="true"></span></summary>
          <div class="device-menu">
            <section class="device-about" aria-labelledby="device-about-h">
              <h3 id="device-about-h">{T("device.about")}</h3>
              <dl class="kv">
                <div><dt>{T("device.name")}</dt><dd>Lune Touch</dd></div>
                <div><dt>{T("device.place")}</dt><dd>{T("device.sample")}</dd></div>
                <div><dt>{T("device.ip")}</dt><dd>192.168.1.186</dd></div>
                <div><dt>{T("device.mac")}</dt><dd>—</dd></div>
                <div><dt>{T("device.firmware")}</dt><dd>1.0.0</dd></div>
                <div><dt>{T("device.uptime")}</dt><dd>3 <small>{T("common.days")}</small> 4 <small>{T("common.hours")}</small> 12 <small>{T("common.minutes")}</small></dd></div>
              </dl>
              <button type="button" class="btn" data-action="copy-diag">{T("device.copyDiag")}</button>
            </section>
            <nav aria-label="{T("nav.devices")}">
              <a href="#" aria-current="page"><i></i>Lune Touch<small>192.168.1.186 · {T("device.this")}</small></a>
            </nav>
          </div>
        </details>
        <nav class="mode" aria-label="{T("mode.label")}">
          <label for="m-dash">{I_DASH}{T("mode.dash")}</label>
          <label for="m-conf">{I_CONF}{T("mode.conf")}</label>
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
      {strip}
    </div>
  </div>
  <main class="content wrap">{views}
  </main>
</div>

<script type="application/json" id="i18n">{rt_json}</script>
{js_tag}
<script>
(function(){{
document.addEventListener('click',function(e){{
  var b=e.target.closest&&e.target.closest('[data-step]');
  if(b&&!b.disabled){{var i=b.parentNode.querySelector('input');b.dataset.step>0?i.stepUp():i.stepDown();i.dispatchEvent(new Event('change',{{bubbles:true}}));}}
  var d=document.querySelector('.device[open]');if(d&&!d.contains(e.target))d.open=false;
}});
document.addEventListener('submit',function(e){{e.preventDefault();document.dispatchEvent(new CustomEvent('lune:save',{{detail:{{key:e.target.dataset.save,data:new FormData(e.target,e.submitter)}}}}));}});
}})();
</script>
</body>
</html>
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--langs", default=os.environ.get("LUNE_UI_LANGS", "en,da"))
    ap.add_argument("--out", default=str(ROOT / "dist"))
    ap.add_argument("--css", default=str(DS_ROOT / "dist" / "touch" / "lune-ui.css"))
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--hs-type", default="asgard", choices=("http", "asgard"), help="default heat-source type in preview HTML")
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
    (out / "lune-ui.css").write_text(css, encoding="utf-8")
    css_gz = gzip.compress(css.encode(), 9, mtime=0)
    (out / "lune-ui.css.gz").write_bytes(css_gz)

    binder = (ROOT / "binder.js").read_text(encoding="utf-8")
    (out / "ui.js").write_text(binder, encoding="utf-8")
    js_gz = gzip.compress(binder.encode(), 9, mtime=0)
    (out / "ui.js.gz").write_bytes(js_gz)

    urls = {c.meta("_lang"): f"/{c.meta('_lang')}/" for c in cats}
    pages = []
    for c in cats:
        html = render(c, cats, urls, "/lune-ui.css", "/ui.js", a.hs_type)
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
            prev = render(c, cats, urls, None, "ui.js", a.hs_type, inline_css=css)
            (out / f"preview-{c.meta('_lang')}.html").write_text(prev, encoding="utf-8")

    total = len(css_gz) + len(js_gz) + sum(len(g) for _, g in pages)
    print(
        f"Byggede {', '.join(codes)} → {out}/  (gzip: {total / 1024:.1f} kB: "
        f"css {len(css_gz) / 1024:.1f} + js {len(js_gz) / 1024:.1f} + "
        + " + ".join(f"{l} {len(g) / 1024:.1f}" for l, g in pages)
        + ")"
    )
    print(f"  lune-ui.css.gz: {len(css_gz)} B")
    print(f"  ui.js.gz: {len(js_gz)} B")
    for l, g in pages:
        print(f"  {l}/index.html.gz: {len(g)} B")


if __name__ == "__main__":
    main()
