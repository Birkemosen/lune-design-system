# V6: Dashboard/Konfiguration → Hjem / ark / System

Endelig placering af hvert felt og hver handling fra den gamle Konfiguration (og
hverdagsfelterne på det gamle Dashboard). `check_fields.py` tjekker, at hvert navn i
`conf_fields.txt` findes i den nye markup, og at grupperne holder grænserne i DESIGN.md 15.5.

`{i}` = zone 1–6. "Ark" er en `.sheet`-popover; "System" er `#v-sys` med kategorier.

## Zone (gammel: Dashboard › zone + Konfiguration › zone)

| Felt / handling | Gammel placering | Ny placering |
|---|---|---|
| `z{i}_target` | Dashboard › Komfort (Gem mål) | Zone-ark › Overblik › klima-kontrol (autogem) og › Indstillinger › Komfort › Mål |
| `action:reset_fault` | Dashboard › fejlpanel; Konfiguration › Motor | Zone-ark › Overblik › fejlpanel (kun ved fejl) og › Indstillinger › Avanceret › Motor og kalibrering (kun ved fejl) |
| `z{i}_enabled` | Konfiguration › Rum og følere | Zone-ark › Indstillinger › Komfort › Zone aktiveret |
| `z{i}_name`, `z{i}_area` | Konfiguration › Rum og følere | Zone-ark › Indstillinger › Rum |
| `z{i}_src`, `z{i}_ble` (+ `data-action:ble-scan`), `z{i}_ret` | Konfiguration › Rum og følere › Følere | Zone-ark › Indstillinger › Rum |
| `z{i}_wall`, `z{i}_wind`, `z{i}_solar` | Konfiguration › Gulv og vejr › Vejr-preload | Zone-ark › Indstillinger › Vejr |
| `z{i}_spacing`, `z{i}_pipe`, `z{i}_lead` | Konfiguration › Gulv og vejr › Gulv og rør | Zone-ark › Indstillinger › Gulv |
| `z{i}_merge` | Konfiguration › Rum og følere | Zone-ark › Indstillinger › Avanceret › Gruppering (underside) |
| Motor: ripples, faktorer, preheat adv., seneste fejl | Konfiguration › Motor | Zone-ark › Indstillinger › Avanceret › Motor og kalibrering (underside) |
| `action:reset_relearn` | Konfiguration › Motor | Zone-ark › Indstillinger, sidst (`.confirm-pop`) |
| Zonegraf 24 t + 6 t | Dashboard › zone | Zone-ark › Historik |
| Ventil, retur, status | Dashboard › Ventil og motor | Zone-ark › Overblik |

Grupperede medlemszoner (Z5): Overblik viser, at målet styres af Z4, med en knap, der åbner Z4's ark.

## Manifold (gammel: Dashboard › Manifold + Konfiguration › Manifold)

| Felt / handling | Gammel placering | Ny placering |
|---|---|---|
| Fremløb, retur, ΔT, samlet åbning | Dashboard › Varme nu | Hjem › Varme nu og Manifold-ark › Overblik |
| Fremløb/retur 24 t | Dashboard › Varme nu | Hjem › Varme nu og Manifold-ark › Historik |
| Balanceringstabel | Dashboard › Balancering | Manifold-ark › Overblik |
| `bal_mode`, `bal_interval`, `bal_step`, `bal_min`, `bal_max` | Konfiguration › Regulering | Manifold-ark › Indstillinger › Balancering |
| `preheat_enabled`, `ph_band`, `ph_delta` | Konfiguration › Regulering | Manifold-ark › Indstillinger › Opsugning (gated) |
| `forecast_enabled`, `fc_model`, `fc_thr`, `fc_max`, `action:fetch` | Konfiguration › Vejr-preload | Manifold-ark › Indstillinger › Vejr-preload (gated) |
| `action:reset_balancing` | Konfiguration › Regulering | Manifold-ark › Indstillinger, sidst (`.confirm-pop`) |
| Vejrudsigt | Dashboard › Manifold | Hjem (uændret; den ene ekstra sektion, DESIGN.md 15.7) |

## System (gammel: Konfiguration › Manifold og Service)

| Felt / handling | Gammel placering | Ny placering |
|---|---|---|
| `fc_lat`, `fc_lon` | Konfiguration › Vejr-preload | System › Enhed › Placering |
| `manifold_type`, `probe_flow`, `probe_return` | Konfiguration › Manifold og motorer | System › Manifold og motorer › Manifold |
| `motor_drivers`, `motor_type`, `m_runtime` | Konfiguration › Manifold og motorer | System › Manifold og motorer › Motorer (gated) |
| `m_cthr`, `m_cslope`, `m_cfloor` | Konfiguration › … › Endestop- og læringsgrænser | System › Manifold og motorer › Avanceret › Lukke-endestop (underside) |
| `m_othr`, `m_oslope`, `m_ofloor`, `m_ripple` | samme | … › Åbne-endestop (underside) |
| `m_relmov`, `m_relh`, `m_minsamp`, `m_maxdev` | samme | … › Genlæring (underside) |
| `manual_mode`, `man_zone`, `man_target`, `action:stop`, `action:move` | Konfiguration › Service | System › Service › Manuel motorstyring (gated) |
| `action:dump_tasks` | Konfiguration › Service | System › Service › Diagnostik |
| `action:reset_probe_map`, `action:restart` | Konfiguration › Service | System › Service, sidst (`.confirm-pop`) |
| Wi-Fi, oppetid, log | Dashboard › Enhed | System › Service › Diagnostik |
| Firmware/ESPHome/IP | Konfiguration › Service › Enhed | System › Firmware og backup |

Nyt på System (DESIGN.md 15.4): Enhed › Navn og BLE-ur; Forbindelser › Lune Touch (handlinger efter tilstand, 6.1b); Firmware og backup › backup og gendannelse. Motorlab vises kun i dev-builds (`--dev`), sidst.
