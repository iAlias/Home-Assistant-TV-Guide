# <img src="logo.png" width="96" alt="icon" align="right">
# TV Guide Multi‑Source (v4.1.0)

Integrazione Home Assistant che mostra i palinsesti raccolti dal sito
"TV Sorrisi e Canzoni" (`sorrisi.com`). I canali vengono ordinati secondo la
numerazione italiana tradizionale. La card elenca i canali con il relativo numero ed ordina automaticamente l'elenco.


## Installazione (HACS)
1. Aggiungi questo repo ai *Custom repositories* (categoria Integration).
2. Installa, riavvia HA.

### YAML
```yaml
sensor:
  - platform: tv_guide_multi
    name: "Guida TV"
    country: IT
```

### Card
```yaml
resources:
  - url: /local/tv-guide-multi-card.js?v=3
    type: module
```

```yaml
type: custom:tv-guide-multi-card
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
  - La7
```

Per personalizzare l'aspetto con [card_mod](https://github.com/thomasloven/lovelace-card-mod) puoi aggiungere, ad esempio:

```yaml
style: |
  ha-card {
    border-radius: 16px;
    box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0,0,0,0.3));
    padding: 12px;
    background: var(--card-background-color);

  }
```

### Editor visuale
La card include un editor grafico utilizzabile dall'interfaccia Lovelace.
Da qui puoi modificare titolo, entità e lista dei canali senza ricorrere
al codice YAML.
