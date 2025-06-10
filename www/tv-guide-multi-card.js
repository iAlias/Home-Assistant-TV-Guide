class TvGuideMultiCard extends HTMLElement {

  setConfig(config) {
    if (!config.now_entity || !config.prime_entity) {
      throw new Error("now_entity e prime_entity obbligatori");
    }
    this._config = config;
  }

  set hass(hass) {
    const cfg = this._config;

    /* crea lo scheletro una sola volta */
    if (!this.card) {
      this.card = document.createElement("ha-card");
      if (cfg.title) this.card.header = cfg.title;
      this.container = document.createElement("div");
      this.container.className = "tvg-container";
      this.card.appendChild(this.container);

      const style = document.createElement("style");
      style.textContent = `
        .tvg-container{padding:16px;display:grid;row-gap:16px;font-family:var(--ha-card-header-font-family,"Roboto","Helvetica Neue",sans-serif)}
        h3{margin:0 0 8px 0;font-size:1rem;font-weight:500}
        ul{padding:0;margin:0;list-style:none}
        li{display:flex;justify-content:space-between;align-items:center;padding:2px 0;border-bottom:1px solid var(--divider-color)}
        .prog{font-weight:500}
      `;
      this.card.appendChild(style);
      this.appendChild(this.card);
    }

    /* estrai dati dai sensori */
    const nowState   = hass.states[cfg.now_entity];
    const primeState = hass.states[cfg.prime_entity];

    const nowMap   = nowState?.attributes.programmi_correnti || {};
    const primeMap = primeState?.attributes.prima_serata      || {};

    const channels = cfg.channels || Object.keys({...nowMap, ...primeMap}).sort();

    const section = (label, map) => {
      let html = `<h3>${label}</h3><ul>`;
      channels.forEach(ch => {
        const title = map[ch] || "—";
        html += `<li><span>${ch}</span><span class="prog">${title}</span></li>`;
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
