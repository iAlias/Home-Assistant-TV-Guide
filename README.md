# <img src="icon.svg" width="96" alt="icon" align="right">

# TV Guide Multi‑Source (v3.1.1)

Questa versione dimostrativa utilizza l'API gratuita di **TVmaze** per ottenere
il palinsesto giornaliero, senza effettuare scraping di siti web. In futuro può
essere estesa ad altre fonti come TVIT o IPTV-org.

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
  - url: /local/tv-guide-multi-card.js?v=1
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
