
# TV Guide Sensor for Home Assistant

Mostra i programmi *Ora in onda* e *Prima serata* (≥ 20:30) utilizzando la
[TVmaze Public API](https://www.tvmaze.com/api).

## Installazione tramite HACS
1. Aggiungi questo repository in **HACS ▸ Integrazioni ▸ ⋮ ▸ Custom repositories**
   (categoria “Integration”).
2. Cerca **TV Guide** e clicca **Installa**.
3. Aggiungi nel tuo `configuration.yaml`:

```yaml
sensor:
  - platform: tv_guide
    name: "Guida TV"
    country: IT  # codice ISO-3166
```

4. Riavvia Home Assistant.

Entità create:
* `sensor.guida_tv_ora_in_onda`
* `sensor.guida_tv_prima_serata`

### Attribuzione
Dati forniti da [TVmaze.com](https://www.tvmaze.com/).


## Lovelace card minimal

Copia `www/tv-guide-card.js` in `/config/www/` (HACS lo farà per te se usi `panel_iframe`), poi
aggiungi la risorsa:

```yaml
resources:
  - url: /local/tv-guide-card.js
    type: module
```

E inserisci la card:

```yaml
type: custom:tv-guide-card
title: Guida TV
now_entity: sensor.guida_tv_ora_in_onda
prime_entity: sensor.guida_tv_prima_serata
channels:
  - Rai 1
  - Rai 2
  - Rai 3
  - Rete 4
  - Canale 5
  - Italia 1
```

La card mostrerà due sezioni (“Ora in onda” e “Stasera in TV”) con layout
moderno e minimal.
