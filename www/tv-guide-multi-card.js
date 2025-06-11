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
          display: grid;
          row-gap: 16px;
          font-family: var(--ha-card-header-font-family, "Roboto", "Helvetica Neue", sans-serif);
        }
        h3 {
          margin: 0 0 8px;
          font-size: 1rem;
          font-weight: 600;
        }
        ul {
          padding: 0;
          margin: 0;
          list-style: none;
        }
        li {
          display: grid;
          grid-template-columns: 1.5em auto 1fr;
          gap: 8px;
          align-items: center;
          padding: 4px 0;
          line-height: 1.4;
          border-bottom: 1px solid var(--divider-color);
        }
        span.idx {
          text-align: right;
          color: var(--secondary-text-color);
          font-weight: 600;
        }
        span.channel {
          font-weight: 600;
        }
        span.prog {
          font-weight: 500;
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
