
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
