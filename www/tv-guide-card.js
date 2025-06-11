class TvGuideMultiCard extends HTMLElement {
  setConfig(config) {
    if (!config.now_entity || !config.prime_entity) {
      throw new Error('now_entity e prime_entity necessari');
    }
    this._config = config;
  }

  set hass(hass) {
    const cfg = this._config;
    if (!this.root) {
      this.root = this.attachShadow({mode: 'open'});
      const style = document.createElement('style');
      style.textContent = `
        .tvg-container {
          padding: 16px;
          display: grid;
          row-gap: 16px;
          font-family: var(--ha-card-header-font-family, "Roboto", "Helvetica Neue", sans-serif);
        }
        h3 {
          margin: 0;
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
          grid-template-columns: 2em auto 1fr;
          gap: 8px;
          align-items: center;
          padding: 6px 8px;
          margin-bottom: 4px;
          border-radius: 8px;
          background: var(--tv-guide-item-background, rgba(0,0,0,0.05));
        }
        li:nth-child(even) {
          background: var(--tv-guide-item-background-alt, rgba(0,0,0,0.1));
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
        }
        span.value {
          font-weight: 500;
          color: var(--primary-text-color);
        }
      `;
      this.root.appendChild(style);
      this.card = document.createElement('ha-card');
      if (cfg.title) this.card.header = cfg.title;
      this.container = document.createElement('div');
      this.container.className = 'tvg-container';
      this.card.appendChild(this.container);
      this.root.appendChild(this.card);
    }
    const now = hass.states[cfg.now_entity];
    const prime = hass.states[cfg.prime_entity];
    const nowMap = now?.attributes.programmi_correnti || {};
    const primeMap = prime?.attributes.prima_serata || {};
    const ORDER = ['Rai 1','Rai 2','Rai 3','Rete 4','Canale 5','Italia 1','La7','TV8','NOVE'];
    const keys = cfg.channels || [...Object.keys(nowMap), ...Object.keys(primeMap).filter(k => !(k in nowMap))];
    const unique = Array.from(new Set(keys));
    unique.sort((a,b)=>{
      const ai = ORDER.indexOf(a);
      const bi = ORDER.indexOf(b);
      if (ai === -1 && bi === -1) return a.localeCompare(b);
      if (ai === -1) return 1;
      if (bi === -1) return -1;
      return ai - bi;
    });
    const list = (title, map) => {
      let html = `<h3>${title}</h3><ul>`;
      unique.forEach(ch => {
        const pos = ORDER.indexOf(ch);
        const idx = pos >= 0 ? pos + 1 : unique.indexOf(ch) + 1;
        html += `<li><span class="idx">${idx}</span><span class="channel">${ch}</span><span class="value">${map[ch] || '—'}</span></li>`;
      });
      html += '</ul>';
      return html;
    };
    this.container.innerHTML = `${list('Ora in onda', nowMap)}${list('Stasera', primeMap)}`;
  }

  getCardSize() { return 3; }
}
customElements.define('tv-guide-multi-card', TvGuideMultiCard);