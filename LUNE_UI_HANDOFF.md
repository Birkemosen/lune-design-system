# Lune UI — handoff fra claude.ai-tråden til Claude Code

Denne fil samler de beslutninger, der er truffet om Lune V6-, Lune Touch- og vægskærm-UI'et, så Claude Code kan arbejde videre uden den oprindelige samtale. Designsystemet (`lune-design-system/`) er facit for detaljer: `DESIGN.md`, `AGENTS.md`, `tokens/tokens.json`, `css/lune-ui.src.css`.

**Sådan bruges filen:** Læs den og designsystemet først. Gennemgå derefter "Status pr. opgave" mod koden i alle tre repos, og marker hvad der allerede er lavet. Spørg før du laver noget, der er markeret "afventer". Arbejd én opgave ad gangen, og byg/test efter hver.

---

## Faste beslutninger

- **Ét designsystem** for V6 (web), Touch (web) og Touch-vægskærmen (LVGL 1024×600, RGB565). Kilde: `tokens/tokens.json` → `tools/lds_build.py` (CSS pr. projekt) og `tools/lds_display.py` (LVGL-tema).
- **Navigation:** ingen sidebar. Tilstandspille (Dashboard | Konfiguration) og zonestrimmel (omfang). Ren CSS via state-radioer før `.app`. JS kun til live-data, +/−, dirty-tracking og submit.
- **Touch-strimmel:** hierarkisk hus → manifold (1–4) → zone (1–6). Delte manifold- og zone-visninger fyldes af binderen.
- **V6 har ingen modulerende varmekilde.** Touch' varmekilde er "Generisk HTTP" eller "Asgard (Odin)". Hvilke typer et build understøtter, sættes i config; typen vælges ved runtime.
- **Visuelt sprog:** Apex-inspireret (varme neutraler, dybde via kontrast, piller), bilskærms-tæthed i tal. Sentence case, én skrifttype (Geist med systemfont som fallback), farver kun med betydning:
  - orange = varme;
  - blå = vejr, sensorer og prognoser;
  - grøn = ok;
  - gul = snart opmærksomhed;
  - rød = fejl nu;
  - lilla = læring og gruppering.
- **Kontrast:** al tekst ≥ 4,5:1 i begge temaer (`--check`). Lyst tema: statusflader afledes af `--card` i OKLab (ingen pasteller på kort).
- **i18n:** build-time, standard `en,da`; alle tekster inkl. aria-labels i kataloger. Rå firmwareværdier vises aldrig.
- **Gem:** Konfiguration gemmer eksplicit pr. panel med clean/dirty-mønster (knapper skjules/deaktiveres aldrig). Dashboard-handlinger (mål) autogemmes efter 1,5 s, som på vægskærmen.
- **Destruktivt:** `.confirm-pop` (native popover, Annullér har fokus), aldrig inline-udfoldning eller "OK".
- **Handlinger efter tilstand:** vis kun det, der kan gøres nu (fx ingen "Approve", når godkendt; "Nulstil fejl" kun ved fejl).
- **Hjælp:** ét "?" pr. panel eller underafsnit, native popover (klik, ikke hover). "Om enhed" ligger i enhedsmenuen under logoet.
- **Sektioner i Konfiguration:** åbne, med sektionslinks. Kun Service/Udvikler kan foldes. Maks. 5 pr. visning.
- **Grafer:** inline-SVG kun til figurer, tekster i HTML. Mål som trappe, akse ≥ 3 °C. Zonegraf: 24 t historik + 6 t **fremskrivning** (dæmpet lineær, φ = 0,85, se DESIGN.md 5.9), beregnet i binderen; data hentes live, ikke indlejret.
- **Vægskærm:** dark som standard. Husrække øverst; manifold-rækker med info til venstre og altid 6 zonefelter. Fuldskærms-zone, nat/dvale. Handoff-pakke: `lune-touch-display-handoff/` (SCREENS.md, tema, mockups).

---

## Status pr. opgave

Hver opgave har en fuld prompt i claude.ai-tråden. Kernen står her. Marker status, når du har tjekket koden.

| # | Opgave | Repo(s) | Status (tjekket mod koden 2026-10-03) |
|---|---|---|---|
| 1 | Designsystem 2: tokens, CSS, build, docs, V6-eksempel, i18n | design system | **Lavet.** `--check` og `lds_display.py --check` består; `dist/`, docs og eksempler er genbygget. |
| 2 | Lyst tema: kontrast og afledte statusflader | design system | **Lavet i alle tre repos.** V6 kopierer LDS-CSS; Touch' `web/design-system/` holdes synkron med LDS. |
| 3 | Hierarkisk strimmel + varmekilde HTTP/Asgard (Touch) | design system, Touch | **Erstattet.** Touch har nu kun Hus (se 13); den hierarkiske strimmel og manifold-/zonevisningerne er fjernet fra produktet (findes stadig i LDS). Varmekilde-typer virker. Rest: `heat_source_types` læses ikke fra config (typerne er hardkodet; standard er `asgard`, ikke config'ens første type). |
| 4 | Dirty state, Fortryd, autogem på dashboard | alle | **V6: lavet. Touch: næsten.** Touch' husmål autogemmes (`.autosave`, poll overskriver ikke et ventende mål). Rest på Touch: Fortryd nulstiller til HTML-standardværdierne, ikke de indlæste; sektioner og sektionslinks får ikke dirty-prik. |
| 5 | Sektioner, sektionslinks, tilstandsafhængige handlinger | alle | **Delvist.** V6' zone-konfiguration har ikke længere den gamle `.section-head`. Rest: V6' binder sætter aldrig `error`, og `luneSaved()` sletter `data-state` på Touch-parringspanelet (alle knapper vises efter gem); Touch bruger ikke `data-show-when`; Touch-sektionen "Opsætning" har kun ét panel. |
| 6 | Forbindelser som ét panel (V6), Weather-sektion fjernet | V6 | **Delvist.** Weather og `.stack` er væk, men Lune Touch, BLE-ur og Enhedsidentitet er stadig tre paneler (nu i tre ens spalter). |
| 7 | `.confirm-pop` i stedet for `details.confirm`; "Nulstil fejl" efter tilstand | alle | **V6: lavet.** Rest på Touch: popoveren til "Fjern styring" (bygges i binderen) mangler `role="alertdialog"`, aria og `autofocus` på Annullér. |
| 8 | Touch › Hus-konfiguration: layout, testresultater, "Sendes til Asgard", vægtning | Touch | **Næsten lavet.** `.test-result`, "Sendes til Asgard/HTTP", vægtningstabel og nu **Rum**-tabellen (medregn, vægt, vind, sol pr. rum; fuld atomisk opdatering). Rest: ok-testresultat viser "200" uden HTTP-kode; vægtningstabellen skifter stille til lige vægte. |
| 9 | Zonegraf 24 t + 6 t fremskrivning + historik-endpoint | V6 (+ design system) | **Lavet.** `projection.test.js` består (22/22). Afvigelser: testen kører ikke i `make test`; med < 2 historikpunkter fremskrives fra klientbufferen som halvtimespunkter; huller i slutningen springes over. |
| 10 | **Kompakt tæthed** | alle | **Lavet.** Tokens + `density.compact`, `@compact`-blok genereret af `lds_build.py`, `data-density`, `.empty`, Konfiguration 1/2/3 spalter (to ved færre end tre én-spalte-paneler), `.stack` udgået. Ændret efter feedback: **én fælles kontrolbredde** `--ctl-w` = 5 × `--hit` (160 px) for input/select/stepper i stedet for naturlige bredder; `.w-xs/sm/md` er aliaser, kun `.w-lg` står under labelen. Målt ved 1440 px mus: V6 › System 7 → 11 felter over folden, Touch › Hus 2 → 9–11; touch ved 390 px uændret. |
| 11 | Vægskærm i LVGL | Touch | via `lune-touch-display-handoff/` i Cursor (ikke berørt). |
| 12 | Navngivning og V6-visninger | V6, design system | **Lavet.** Første felt/omfang hedder **System** («Manifold» kun om det hydrauliske). Zone-dashboard: mål + detaljer i ét panel ved siden af grafen (hero-temperaturen udgår, den står i zonefeltet). «Group with» gemmes via `zone_sync_to` (også None), og gruppering males ved runtime fra `sync_to` i stedet for build-time demodata. Niveau 0 (lukket ventil/ingen data) er slukket. |
| 13 | Touch kun Hus + V6-rækker | Touch, design system | **Lavet.** Manifold-/zonevisninger og strimmel fjernet (Touch tilføjer ingen egne zoneindstillinger). Dashboard: én V6-række pr. board (`.boards`: System-felt + zonefelter; links til V6 med `#s-sys`/`#s-zN`), pumpe flettet ind i varmekilde-panelet. Board-navn: Touch-navn → V6 `device_name`/`device_location` → «Unavngivet». Diagnostik oversat. Asset-URL'er versioneres (`?v=hash`), da `/ui.js` og CSS serveres `immutable`. |
| 14 | Firmware-rettelser fundet undervejs | V6, Touch | **Lavet, ikke testet på hardware.** V6 `/api/v1/zones` sender `device_name`/`device_location`. Touch accepterer V6' nye `lv6-`-fingerprint (overview-polls blev kasseret, så fremløb/retur aldrig kom frem). Læring: 600 ms pause før reversering i backoff (driverens fejl-latch afbrød læringen), ulærte zoner læres automatisk (én ad gangen, kun med drivere slået til), og automatisk læring/relearn venter i manuel tilstand. |

**Rettet ud over listen (opgave 10–14):**
- Touch: hvert tryk på +/− tog to trin (dobbelt handler).
- Touch: vejrudsigtsgrafen blev aldrig tegnet (tom SVG, manglende y-akse); «Preload»-badgen viste den rå nøgle `fc.badge`.
- Touch: badges for husklima og zone var statiske («Calling»/orange); manifold-dashboardet viste faste demotal.
- Touch: det gamle zone-gem virkede aldrig (`/zones/{room}/room` kræver fuld atomisk opdatering; `include_in_house_temperature` blev ignoreret af `/forecast-profile`). Erstattet af Rum-tabellen.
- V6: `toNumber('')` gav 0; «Group with» kunne ikke nulstilles og blev aldrig udfyldt fra enheden.

**Backlog (besluttet, ikke startet):**
- **Notifikationsløsning.** Fejl, mislykket læring, blokerede motorer og offline-boards ses i dag kun, når man kigger i UI'et (badges, `.panel.alert`, log). Der skal på et tidspunkt laves en notifikationsløsning (fx push/e-mail/Home Assistant), så brugeren får besked uden at åbne V6 eller Touch. Kanal, hvilke hændelser og afsender (V6 selv eller Touch for hele huset) er ikke afklaret.

**Kendte rester:**
- **Motorlæring:** homing-lukning klassificeres som `JAM` efter ca. 0,8 s, også efter 10 s backoff-åbning — sandsynligvis detektion, ikke mekanik. Kræver et motor-trace (CSV) af en lukning på zone 4, før klassifikatoren ændres.
- **Vind/sol ejes to steder:** V6 (Gulv og vejr) og Touch (Rum, sendes ikke til V6). Afklar hvilke der styrer forvarmning, når et board er parret.
- Flash-budget overskredet: CSS ca. 18 kB gzip; V6 i alt ca. 56 kB mod mål 40 kB.
- V6' `make test-dashboard` forventer `data-save="touch"` og `data-dev-only`, som ikke længere findes.
- Touch' `tests/dashboard/test_phase8_overview.sh` kræver `rg`.
- `__pycache__/` i lune-coordinator er ikke i `.gitignore`.

### Observerede fejl i seneste skærmbilleder (rettet under opgave 10)

- V6-dashboard viser `0.0 °C` for fremløb/retur uden måling. Det skal vises som "—" (null, ikke 0).
- Den tomme fremløb/retur-graf fylder ca. 300 px. Den skal klappe sammen til én linje.
- Zone uden temperatur (Z3) vises som flad linje og `0.0°` i gul. Den skal vise "—" og ingen sparkline.
- Touch-strimlen: M2 viser seks fulde orange mini-søjler, selvom 0 zoner kalder. Uden data skal de være `seg-off`.
- Touch: manifolds hedder "Unnamed". Det er korrekt adfærd, men navngiv dem i UI'et.
- Hus-feltet i Touch-strimlen viser "Flow —"/"Ret —" i farve uden data; det skal være dæmpet.
- Touch-dashboardet: "Heat source" viser "0 s ago · Blocked" som et stort tal. Status hører til i badge/kv, ikke som metric. Panelet er halvt tomt (tæthed/spalter).
- Touch-dashboardet har stadig "Save house target". Mål skal autogemmes (opgave 4).

---

## Opgave 10 — kompakt tæthed (kernen)

Tætheden afgøres af inputtypen. Med mus på skærme ≥ 1024 px bliver UI'et kompakt; med touch er det uændret (44/48 px).

| Token | Kompakt |
|---|---|
| `--hit` | 32 px |
| `--field-gap` | 6 px |
| `--panel-pad` / `--panel-gap` | 18 / 14 px |
| `--fs-panel` / `--fs-view` | 15 / 26 px |
| `--row-h` | 36 px |
| `--tile-h` | 52 px |

- `.field.row` = label ⟷ kontrol med naturlig bredde.
  - Stepper: 136 px.
  - Inputs: `.w-xs` 8ch (port/tal), `.w-sm` 14ch, `.w-md` 22ch (host/entity), `.w-lg` 32ch (URL). Lange felter står under labelen.
- Konfiguration: 1/2/3 spalter (< 900 / ≥ 900 / ≥ 1280 px) med paneler stablet oppefra, `align-items: start`. `.wide` spænder alle spalter. Ens højde gælder kun Dashboard; `.stack` udgår.
- Tomme grafer klapper sammen til én `.empty`-linje. Manglende værdier vises som "—", aldrig 0.
- `data-density="compact|comfortable"` på `.app` kan tvinge tætheden.
- Accept:
  - ved 1440 px med mus er ≥ 40 % flere felter synlige over folden;
  - ingen stepper er > 160 px;
  - ingen panel har > 48 px tom bund;
  - touch-emulering ved 390 px er uændret;
  - `--check` og alle builds består.

---

## Arbejdsgang i Claude Code

1. Start i en mappe med alle tre repos (fx `~/code/lune/`), eller tilføj de andre repos som ekstra arbejdsmapper.
2. Kopiér `lune-design-system/AGENTS.md` ind i hvert repos `CLAUDE.md` (eller henvis til den).
3. Lad Claude Code gennemgå "Status pr. opgave" mod koden og rapportere, før den ændrer noget.
4. Kør én opgave ad gangen og byg efter hver: `python tools/lds_build.py --check`, projekt-builds og skærmbilleder ved 390 og 1440 px i begge temaer.