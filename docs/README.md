# Lune Design System — dokumentation

Designsystemet bag Lune V6, Lune Touch og vægskærmen: regler, tokens, komponenter og værktøjer.
Chippen er filnavnet; linket siger, hvad dokumentet er til.

**Lune-dokumentation:** [Lune V6](https://github.com/Birkemosen/lune/blob/main/docs/README.md) · [Lune Touch](https://github.com/Birkemosen/lune-coordinator/blob/main/docs/README.md) · **Designsystem** (denne side)

---

**Start her**

- `README` [Hvad designsystemet er, og hvordan det bygges](../README.md)
- `DESIGN` [Designsystemet: principper, grundelementer, komponenter, Hjem/ark/System og vægskærmen](../DESIGN.md) — med indholdsfortegnelse
- `design-system.html` [Visuel reference med levende eksempler](design-system.html) — åbn filen lokalt i en browser (GitHub viser kun kildekoden)

**Regler og ændringer**

- `AGENTS` [Regler for kodeagenter i V6 og Touch](../AGENTS.md)
- `CHANGELOG` [Ændringer pr. version](../CHANGELOG.md)

**Kilder**

- `tokens.json` [Alle farver, typografi, afstande, radier og skærmpaletten](../tokens/tokens.json)
- `lune-ui.src.css` [Komponenterne](../css/lune-ui.src.css)
- `lune-forms.js` [Formularer: ugemt/gem, autogem, deep links](../js/lune-forms.js)
- `config` [Projektopsætning for V6 og Touch](../config/)

**Migrering til Hjem / ark / System**

- `examples/v6/MAPPING` [Hvor hvert felt på V6 flyttede hen](../examples/v6/MAPPING.md)
- `examples/touch/MAPPING` [Hvor hvert felt på Touch flyttede hen](../examples/touch/MAPPING.md)
- `LUNE_UI_HANDOFF` [Beslutninger fra den oprindelige designtråd](../LUNE_UI_HANDOFF.md)

**Værktøjer** (`python tools/<navn>`)

- `lds_build.py` [Byg CSS pr. projekt og tjek tokens, kontrast og `var(--…)`](../tools/lds_build.py)
- `lds_display.py` [Vægskærmens tema (RGB565) og firmwarefiler til Touch](../tools/lds_display.py)
- `lds_ha.py` [Tema til Home Assistant](../tools/lds_ha.py)
- `lds_brand.py` [Brand-mærker (PNG/SVG)](../tools/lds_brand.py)
- `build_docs.py` [Byg den visuelle reference](../tools/build_docs.py)
- `md_toc.py` [Indholdsfortegnelser i Markdown (`<!-- toc -->`), som i DESIGN.md](../tools/md_toc.py)
