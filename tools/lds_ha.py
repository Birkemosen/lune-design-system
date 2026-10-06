#!/usr/bin/env python3
"""
Lune Design System → Home Assistant-tema.

    python tools/lds_ha.py      → dist/home-assistant/themes/lune.yaml

Ét tema ("Lune") med lyst og mørkt tilstand (HA's `modes`), genereret fra
tokens/tokens.json, så HA, Lune V6 og Lune Touch altid deler farver og former.
Farvebetydningen følger husets farvesprog (DESIGN.md 14): status, domæner og
skalaer. Grøn = godt for huset (ok, egenproduktion/eksport/billig strøm,
natur og liv). Accentfarven i HA er dom-energy (grøn); primærfarven er
inverteret (lys på mørkt / omvendt) som LDS' primære knapper.
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import lds_build as L

C = L.flat_colors()
def v(name, th): return L.resolve(name, th, C)
def rgb(hexv):
    h = hexv.lstrip("#"); return ", ".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))
def q(x): return f'"{x}"'

MAP = {  # HA-variabel: LDS-token (se tokens.$semantic for de tre lag)
    # Grundflader og tekst
    "primary-color": "fg", "accent-color": "dom-energy", "text-primary-color": "bg",
    "primary-text-color": "fg", "secondary-text-color": "muted", "disabled-text-color": "faint",
    "divider-color": "border",
    "primary-background-color": "bg", "secondary-background-color": "card",
    "card-background-color": "card", "ha-card-background": "card",
    "app-header-background-color": "bg", "app-header-text-color": "fg",
    "sidebar-background-color": "bg", "sidebar-text-color": "muted", "sidebar-icon-color": "muted",
    "sidebar-selected-text-color": "fg", "sidebar-selected-icon-color": "dom-energy",
    "state-icon-color": "muted",
    # Lag 1: status
    "error-color": "danger", "warning-color": "warn", "success-color": "ok", "info-color": "info",
    # Lag 2: domæner → tilstandsfarver
    "state-climate-heat-color": "dom-heat", "state-climate-cool-color": "dom-cool",
    "state-climate-auto-color": "dom-energy", "state-climate-heat_cool-color": "dom-plan",
    "state-climate-fan_only-color": "dom-water", "state-climate-dry-color": "dom-water",
    "state-water_heater-active-color": "dom-heat",
    "state-light-active-color": "dom-light", "state-sun-above_horizon-color": "dom-light",
    "state-fan-active-color": "dom-water", "state-humidifier-on-color": "dom-water", "state-valve-open-color": "dom-water",
    "state-plant-active-color": "dom-nature", "state-person-home-color": "dom-nature", "state-device_tracker-home-color": "dom-nature",
    "state-lock-locked-color": "ok", "state-lock-unlocked-color": "warn", "state-lock-jammed-color": "danger",
    "state-alarm_control_panel-armed_away-color": "dom-security", "state-alarm_control_panel-armed_home-color": "dom-security",
    "state-alarm_control_panel-armed_night-color": "dom-security", "state-alarm_control_panel-triggered-color": "danger",
    "state-cover-open-color": "dom-security", "state-binary_sensor-active-color": "dom-security",
    "state-media_player-playing-color": "dom-media", "state-media_player-on-color": "dom-media",
    "state-vacuum-cleaning-color": "dom-plan", "state-automation-on-color": "dom-plan", "state-script-on-color": "dom-plan",
    "state-switch-active-color": "fg", "state-input_boolean-on-color": "fg",
    # Kontroller
    "switch-checked-color": "fg", "switch-checked-button-color": "fg", "switch-checked-track-color": "fg",
    "switch-unchecked-button-color": "muted", "switch-unchecked-track-color": "raised",
    "input-fill-color": "field", "input-ink-color": "fg",
    # Energi: grøn = godt for huset
    "energy-solar-color": "dom-light", "energy-grid-return-color": "dom-energy", "energy-non-fossil-color": "dom-energy",
    "energy-grid-consumption-color": "dom-cool", "energy-battery-in-color": "dom-plan", "energy-battery-out-color": "dom-plan",
    "energy-gas-color": "dom-heat", "energy-water-color": "dom-water",
}
RGB = [k for k in MAP if k.startswith("state-") and k != "state-switch-active-color" and k != "state-input_boolean-on-color"] + ["primary-color", "accent-color", "error-color", "warning-color", "success-color", "info-color"]

def mode(th):
    out = []
    for k, tok in MAP.items():
        val = v(tok, th)
        out.append(f"      {k}: {q(val)}")
    for k in RGB:
        val = v(MAP[k], th)
        if val.startswith("#"): out.append(f"      rgb-{k}: {q(rgb(val))}")
    edge = v("card-edge-c", th)
    out.append(f"      ha-card-border-color: {q(edge if edge != 'transparent' else 'rgba(0, 0, 0, 0)')}")
    return "\n".join(out)

font = "'Geist', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"

# UIX (UI eXtension, efterfølgeren til card-mod) styler HA's egne elementer fra temaet.
# Selektorerne i HA's interne markup ændrer sig mellem versioner — tjek dem med browserens inspektør.
UIX = r"""
  # ---- UIX: kræver UI eXtension (HACS). Uden UIX ignoreres disse nøgler bare. ----
  uix-theme: Lune
  # Geist som variabel font. Læg filen i /config/www/fonts/ (serveres som /local/fonts/).
  uix-fonts: |
    geist:
      family: Geist
      source: url("/local/fonts/Geist-Variable.woff2") format("woff2")
      descriptors:
        weight: "100 900"
        style: normal
        display: swap
  ha-font-family-heading: "'Geist', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
  # Kort: LDS-dybde (lys topkant + bløde lagdelte skygger i stedet for HA's standardskygge)
  uix-card: |
    ha-card {
      box-shadow: inset 0 1px 0 rgba(255,255,255,.06), 0 0 0 1px var(--ha-card-border-color), 0 1px 2px rgba(0,0,0,.25), 0 10px 30px rgba(0,0,0,.18) !important;
      border: none !important;
    }
  # Topbjælken som svævende pille (LDS 5.1 Navbar). Indholdet scroller under den.
  uix-root-yaml: |
    .: |
      .header {
        background: transparent !important;
        box-shadow: none !important;
        border: none !important;
        padding: max(12px, env(safe-area-inset-top)) 16px 0 !important;
      }
      .toolbar {
        max-width: 1320px;
        margin: 0 auto;
        padding: 0 8px !important;
        border-radius: 999px;
        background: color-mix(in srgb, var(--card-background-color) 82%, transparent) !important;
        -webkit-backdrop-filter: blur(18px) saturate(1.3);
        backdrop-filter: blur(18px) saturate(1.3);
        box-shadow: inset 0 1px 0 rgba(255,255,255,.06), 0 0 0 1px var(--divider-color), 0 10px 30px rgba(0,0,0,.22);
      }
      .main-title { font-weight: 600; letter-spacing: -0.01em; }
  # Dialoger (more-info = LDS-detaljeark): store radier og svævende skygge
  uix-dialog: |
    :host {
      --ha-dialog-border-radius: 24px;
      --dialog-box-shadow: inset 0 1px 0 rgba(255,255,255,.07), 0 0 0 1px var(--divider-color), 0 30px 80px rgba(0,0,0,.5);
    }
"""

yaml = f"""# Genereret af tools/lds_ha.py fra tokens/tokens.json — redigér tokens, ikke denne fil.
# Lune Design System {L.TOK['$meta']['version']} · Home Assistant-tema med lyst og mørkt tilstand (+ UIX).
# Installation: læg filen i /config/themes/ og tilføj i configuration.yaml:
#   frontend:
#     themes: !include_dir_merge_named themes
# Vælg derefter "Lune" under din profil (Tema → Lune, tilstand: Auto/Lys/Mørk).
# Med UI eXtension (UIX) installeret får HA også LDS-navbar, kortdybde, dialoger og Geist (se uix-*).
Lune:
  # Fælles (begge tilstande)
  primary-font-family: {q(font)}
  paper-font-common-base_-_font-family: {q(font)}
  ha-font-family-body: {q(font)}
  ha-card-border-radius: "16px"
  ha-card-border-width: "1px"
  ha-card-box-shadow: "none"
  ha-dialog-border-radius: "24px"
  ha-badge-border-radius: "999px"
{UIX}
  modes:
    light:
{mode('light')}
    dark:
{mode('dark')}
"""
out = L.ROOT/"dist/home-assistant/themes"; out.mkdir(parents=True, exist_ok=True)
(out/"lune.yaml").write_text(yaml, encoding="utf-8")
print(f"→ {out/'lune.yaml'}  ({len(MAP)} variabler pr. tilstand)")
