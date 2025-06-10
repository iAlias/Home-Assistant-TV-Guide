# Home-Assistant-TV-Guide

Mostra i programmi *Ora in onda* e *Prima serata* (>= 20:30) utilizzando la
[TVmaze Public API](https://www.tvmaze.com/api).

## Installazione tramite HACS

1. Aggiungi questo repository in **HACS ▸ Integrazioni ▸ ⋮ ▸ Custom repositories**
   (categoria “Integration”).
2. Cerca **TV Guide** e clicca **Installa**.
3. Aggiungi in `configuration.yaml`:

```yaml
sensor:
  - platform: tv_guide
    name: "Guida TV"
    country: IT  # ISO-3166
