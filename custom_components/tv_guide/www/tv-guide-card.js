
class TvGuideCard extends HTMLElement {
  set hass(hass) {
    const config = this._config;
    if (!this.content) {
      const card = document.createElement('ha-card');
      card.header = config.title || 'Guida TV';
      this.content = document.createElement('div');
      this.content.style.padding = '16px';
      this.content.style.fontFamily = 'var(--paper-font-body1_-_font-family)';
      this.content.style.display = 'grid';
      this.content.style.rowGap = '12px';
      card.appendChild(this.content);
      this.appendChild(card);
    }
    const nowSensor = hass.states[config.now_entity];
    const primeSensor = hass.states[config.prime_entity];
    const channels = config.channels || [];
    const nowMap = nowSensor ? nowSensor.attributes.programmi_correnti || {} : {};
    const primeMap = primeSensor ? primeSensor.attributes.prima_serata || {} : {};

    const buildSection = (title, map) => {
      let html = `<h3 style="margin:4px 0;">${title}</h3>`;
      html += '<ul style="list-style:none;padding:0; margin:0;">';
      channels.forEach(ch => {
        const prog = map[ch] || '<span style="opacity:0.6;">—</span>';
        html += `<li style="display:flex;justify-content:space-between;padding:2px 0;border-bottom:1px solid var(--divider-color);">
                   <span>${ch}</span><span style="font-weight:500">${prog}</span>
                 </li>`;
      });
      html += '</ul>';
      return html;
    };

    this.content.innerHTML = `
      ${buildSection('Ora in onda', nowMap)}
      ${buildSection('Stasera in TV', primeMap)}
    `;
  }

  setConfig(config) {
    if (!config.now_entity || !config.prime_entity) {
      throw new Error('now_entity e prime_entity sono obbligatori');
    }
    this._config = config;
  }

  getCardSize() {
    return 3;
  }
}
customElements.define('tv-guide-card', TvGuideCard);
