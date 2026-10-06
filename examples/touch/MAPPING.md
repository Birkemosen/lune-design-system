# Touch: Dashboard/Konfiguration → Hjem / ark / System

Grundlag: produktets Touch-UI (`lune-coordinator/web/touch-ui`), ikke kun det lille LDS-eksempel.
`conf_fields.txt` rummer alle 90 felter og handlinger (inkl. rækker, som `binder.js` tegner).
`check_fields.py` tjekker, at hvert navn findes i den nye markup, og at grupperne holder grænserne.

Test (DESIGN.md 15.1): én ting man kan pege på → dens ark · gælder enheden/forbindelser → System ·
ændres ugentligt → også på Hjem.

## Hjem (huset)

| Indhold | Fra |
|---|---|
| Hovedsektion: statuslinje, hustemperatur + mål i termostat-ring (`house_target`, autogem) | Dashboard › Husklima |
| Felt **Varme**: fremløb → retur, styres af · åbner Varme-arket | Dashboard › Varmekilde |
| Felt **Næste varme**: næste blok fra Odins plan, kWh + aktuel elpris som én linje med `.scale-chip` · åbner Næste varme-arket | Dashboard › Opvarmningsplan; Konf. › Elpris (status) |
| Felt **Vejr**: ude nu, vind, preload · åbner Vejr-arket | Dashboard › Vejrudsigt |
| Felt **Cirkulation**: flow · åbner Cirkulation-arket | Dashboard › Flow |
| Varmekort: rum pr. manifold (10-segment ventil + procent + afvigelses-chip); rum → Rum-ark, gruppeoverskrift → Manifold-ark | (nyt; erstatter hierarkisk strimmel og "Kræver opmærksomhed") |
| Fejlpanel (varmekilde / styring) | Dashboard › alerts |

Uden data: felter og serier skjules, tal vises som «—».

## Ark

| Ark › fane › gruppe | Felter / indhold | Fra |
|---|---|---|
| **Varme** › Overblik | vægtet temperatur, setpunkt, seneste push, målrolle, VP-temperaturer, Odin-link/driver/nu/plan; "Sendes til Asgard" med vægtnings-fold | Dashboard › Varmekilde; Konf. › Varmekilde › Sendes til |
| › Historik | 24 t (vægtet temperatur, setpunkt) | (nyt) |
| › Indstillinger › Komfortmål (`heat_source.behavior`, PATCH) | `target_sync_enabled` (gated) → `climate_entity` | Konf. › Varmekilde (Asgard › Mål) |
| › Indstillinger › Odin-plan | `odin_plan_enabled`, `odin_control_enabled` (gated) → `odin_max_lift_c` | Konf. › Varmekilde › Odin |
| **Næste varme** › Overblik / Historik | Odins plan (`.plan`), forklaring; ingen indstillinger | Dashboard › Opvarmningsplan |
| **Vejr** › Overblik / Historik | prognose 72 t, preload | Dashboard › Vejrudsigt |
| › Indstillinger (`weather.boost`, PATCH) | `wx_boost` (maks. preload-boost) | Konf. › Vejrplacering |
| **Cirkulation** › Overblik | flow, løftehøjde, effekt, m³/h, fordeling pr. manifold (`.dist`) | Dashboard › Flow |
| **Rum** (pr. rum) › Overblik | temperatur, mål, kredse fra V6-boards (ventil, retur), status | (nyt; data fra V6) |
| › Historik | 24 t | (nyt) |
| › Indstillinger (`rooms`, PATCH) | Hustemperatur: `room:*:include`, `room:*:weight`; Vejr: `room:*:wind`, `room:*:solar`; «Fra V6 (<styring>, Z<n>)»: areal, rørafstand, rørtype, ydervægge som læseværdier + «Redigér på V6 ›» (ny fane, `http://<v6>/#z<n>/indstillinger`). Offline: dæmpet + «V6 er ikke tilgængelig» | Konf. › Rum (tabel) |
| **Manifold** (pr. V6) › Overblik | styringens status, fremløb/retur, dens zoner; link til V6 | Dashboard › strimmel |

## System

| Kategori › gruppe | Felter / handlinger | Fra |
|---|---|---|
| **Enhed** › Identitet | `name`, `dev_idle` (skærmdvale) | Konf. › Identitet |
| **Styringer** | tabel (navn, adresse, status, zoner; `edit-node-name`, `edit-node-host`, `remove-node`), `scan-nodes` + fundne (`add-found`), tilføj manuelt (`name`, `host`) | Konf. › Styringer |
| **Varmekilde** (`heat_source.connection`, PATCH) › Type | `enabled`, `hs_type` (HTTP / Asgard) | Konf. › Varmekilde |
| › Forbindelse | `http_host`/`asgard_host`, `http_port`/`asgard_port`, `*_push_interval_s` (efter type) | samme |
| › Mapping | `*_weighted_temperature_variable`; HTTP: `write_url_template`, `read_url_template` | samme |
| › Odin | `odin_host` | samme |
| › Test | `hs-test-read`, `hs-test-push` med `.test-result` | samme |
| › Avanceret | underside **HTTP-styring** (`target_url_template`, `heat_request_url_template`, `curve_offset_url_template`, `curve_gain`, `curve_max_offset_c`); underside **MQTT** (`mqtt_enabled` gated → host, port, brugernavn, adgangskode, topic-prefix, VP-id) | samme |
| **Elpris** (efter Varmekilde; model + zone som hovedgruppe, Spot/Afgifter/Nettarif/Systemtarif som undersider) | `enabled`, `model`, `zone`, `entsoe_token`; Odins egen (`odin_mode`, `odin_source`, `odin_fixed_price`, `price-odin-write`); Spot (`spot_source`, `spot_fixed_eur`); Afgifter (`currency`, `fx`, `energy_tax`, `markup`, `vat_pct`, `price-zone-defaults`); Nettarif (`grid_source`, `grid_gln`, `grid_code`, `grid_schedule`, `price-sched-add/remove`); Systemtarif (`system_source`, `system_fixed`); `price-push` | Konf. › Elpris til Odin |
| **Cirkulationspumpe** | `host`, `pump_port`, `flow_entity`, `head_entity`, `power_entity` | Konf. › Pumpe |
| **Vejr** › Placering (`weather.location`, PATCH) | `latitude`, `longitude`, `wx-geo` | Konf. › Vejrplacering |
| **Netværk** › Wi-Fi | nuværende, status, `ssid`, `password` | Konf. › Wifi |
| **Firmware og backup** | installeret/nyeste, `check`, `install`, `ota_file` + `upload`; `export`, `backup_file` + `import` | Konf. › Firmware, Sikkerhedskopi |
| **Service** › Diagnostik | dækning (coverage), autoritet, Odin-link, host/IP, fordeling, noder, poll, OTA | Dashboard › Husklima/Varmekilde/Flow; Konf. › Service |
| › Log | kommandolog | Konf. › Service |
| Sidst | «Nulstil register…» (`reset-registry`, `.confirm-pop`) | Konf. › Service |
