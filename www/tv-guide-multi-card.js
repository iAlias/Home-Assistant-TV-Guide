class TvGuideMultiCard extends HTMLElement {
  setConfig(config) {
    if (!config.now_entity || !config.prime_entity) {
      throw new Error("now_entity e prime_entity obbligatori");
    }
    this._config = config;
  }

  set hass(hass) {
    const cfg = this._config;
    if (!this.card) {
      this.card = document.createElement("ha-card");
      if (cfg.title) this.card.header = cfg.title;
      this.container = document.createElement("div");
      this.container.className = "tvg-container";
      this.card.appendChild(this.container);
      const style = document.createElement("style");
      style.textContent = `
        .tvg-container {
          padding: 16px;
          margin: 8px;
          display: grid;
          row-gap: 16px;
          font-family: var(--tv-guide-font-family, var(--ha-card-header-font-family, "Roboto", "Helvetica Neue", sans-serif));
          background: var(--tv-guide-background,
            linear-gradient(135deg, var(--card-background-color, #fff), var(--secondary-background-color, #f5f7fa)));
          border-radius: var(--ha-card-border-radius, 12px);
          box-shadow: var(--tv-guide-container-shadow, var(--ha-card-box-shadow, 0 2px 4px rgba(0,0,0,0.15)));
        }
        h3 {
          margin: 0 0 8px;
          font-size: 1.1rem;
          font-weight: 600;
          color: var(--tv-guide-header-color, var(--primary-text-color));
        }
        ul {
          padding: 0;
          margin: 0;
          list-style: none;
        }
        li {
          display: grid;
          grid-template-columns: 2em auto 1fr;
          gap: 8px;
          align-items: center;
          padding: 8px 12px;
          margin: 4px 0;
          border-radius: 8px;
          background: var(--tv-guide-item-background, rgba(0,0,0,0.05));
          box-shadow: var(--tv-guide-item-shadow, 0 1px 2px rgba(0,0,0,0.15));
          transition: background 0.3s ease, box-shadow 0.3s ease;
        }
        li:hover {
          background: var(--tv-guide-item-hover-background, rgba(0,0,0,0.1));
          box-shadow: var(--tv-guide-item-shadow, 0 2px 6px rgba(0,0,0,0.25));
        }
        li:nth-child(even) {
          background: var(--tv-guide-item-background-alt, rgba(0,0,0,0.08));
        }
        span.idx {
          display: inline-grid;
          place-items: center;
          width: 1.8em;
          height: 1.8em;
          background: var(--accent-color);
          color: var(--text-primary-color, #fff);
          font-size: 0.75rem;
          font-weight: 600;
          border-radius: 50%;
        }
        span.channel {
          font-weight: 600;
          font-size: 0.9rem;
        }
        span.prog {
          font-weight: 500;
          font-size: 0.95rem;
          color: var(--primary-text-color);
        }
      `;
      this.card.appendChild(style);
      this.appendChild(this.card);
    }

    const nowState   = hass.states[cfg.now_entity];
    const primeState = hass.states[cfg.prime_entity];
    const nowMap   = nowState?.attributes.programmi_correnti || {};
    const primeMap = primeState?.attributes.prima_serata      || {};

    const ORDER = ['Rai 1','Rai 2','Rai 3','Rete 4','Canale 5','Italia 1','La7','TV8','NOVE'];
    const keys = cfg.channels || [
      ...Object.keys(nowMap),
      ...Object.keys(primeMap).filter((k) => !(k in nowMap)),
    ];
    const channels = Array.from(new Set(keys));
    channels.sort((a,b)=>{
      const ai = ORDER.indexOf(a);
      const bi = ORDER.indexOf(b);
      if (ai === -1 && bi === -1) return a.localeCompare(b);
      if (ai === -1) return 1;
      if (bi === -1) return -1;
      return ai - bi;
    });

    const section = (label, map) => {
      let html = `<h3>${label}</h3><ul>`;
      channels.forEach((ch) => {
        const pos = ORDER.indexOf(ch);
        const idx = pos >= 0 ? pos + 1 : channels.indexOf(ch) + 1;
        const title = map[ch] || "—";
        html += `<li><span class="idx">${idx}</span><span class="channel">${ch}</span><span class="prog">${title}</span></li>`;
      });
      html += "</ul>";
      return html;
    };

    this.container.innerHTML = `
      ${section("Ora in onda", nowMap)}
      ${section("Stasera",     primeMap)}
    `;
  }

  getCardSize() {
    return 3;
  }
}
customElements.define("tv-guide-multi-card", TvGuideMultiCard);

class TvGuideMultiCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._assign();
  }

  _assign() {
    if (!this.shadowRoot) return;
    this.shadowRoot
      .querySelectorAll("ha-entity-picker")
      .forEach((el) => {
        el.hass = this._hass;
      });
  }

  _render() {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    const cfg = this._config || {};
    this.shadowRoot.innerHTML = `
      <style>
        .form {
          padding: 16px;
          display: grid;
          row-gap: 12px;
        }
      </style>
      <div class="form">
        <ha-textfield
          label="Titolo"
          value="${cfg.title || ""}"
          configValue="title"
        ></ha-textfield>
        <ha-entity-picker
          label="Entity ora in onda"
          value="${cfg.now_entity || ""}"
          configValue="now_entity"
        ></ha-entity-picker>
        <ha-entity-picker
          label="Entity prima serata"
          value="${cfg.prime_entity || ""}"
          configValue="prime_entity"
        ></ha-entity-picker>
        <ha-textarea
          label="Canali (uno per riga)"
          configValue="channels"
        >${(cfg.channels || []).join("\n")}</ha-textarea>
      </div>
    `;
    this._assign();
    this.shadowRoot
      .querySelectorAll('[configValue]')
      .forEach((el) =>
        el.addEventListener('change', (ev) => this._valueChanged(ev))
      );
  }

  _valueChanged(ev) {
    if (!this._config) this._config = {};
    const target = ev.target;
    const prop = target.configValue;
    if (prop === 'channels') {
      this._config.channels = target.value
        .split(/\n|,/)
        .map((v) => v.trim())
        .filter(Boolean);
    } else {
      const value = target.value;
      if (value === '') {
        delete this._config[prop];
      } else {
        this._config[prop] = value;
      }
    }
    this.dispatchEvent(
      new CustomEvent('config-changed', { detail: { config: this._config } })
    );
  }
}
customElements.define('tv-guide-multi-card-editor', TvGuideMultiCardEditor);

TvGuideMultiCard.getConfigElement = async function () {
  return document.createElement('tv-guide-multi-card-editor');
};

TvGuideMultiCard.getStubConfig = function () {
  return {
    title: 'Guida TV',
    now_entity: '',
    prime_entity: '',
    channels: ['Rai 1', 'Rai 2', 'Rai 3'],
  };
};
