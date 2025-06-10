
class TvGuideMultiCard extends HTMLElement{
  setConfig(c){if(!c.now_entity||!c.prime_entity)throw new Error('now_entity e prime_entity necessari');this._config=c}
  set hass(h){
    const c=this._config;
    if(!this.root){
      this.root=this.attachShadow({mode:'open'});
      const style=document.createElement('style');
      style.textContent='ha-card{padding:1rem} h3{margin:0 0 .4rem 0;font-size:1rem;font-weight:500} ul{padding:0;margin:0;list-style:none} li{display:flex;justify-content:space-between;padding:.2rem 0;border-bottom:1px solid var(--divider-color)} span.value{font-weight:500}';
      this.root.appendChild(style);
      this.card=document.createElement('ha-card');
      this.root.appendChild(this.card);
    }
    const now=h.states[c.now_entity];
    const prime=h.states[c.prime_entity];
    const ch=c.channels||[];
    const nowMap=now?.attributes.programmi_correnti||{};
    const primeMap=prime?.attributes.prima_serata||{};
    const list=(title,map)=>{let html='<h3>'+title+'</h3><ul>';ch.forEach(k=>{html+='<li><span>'+k+'</span><span class="value">'+(map[k]||'—')+'</span></li>';});html+='</ul>';return html;}
    this.card.innerHTML=`<h2 class="card-header">${c.title||'Guida TV'}</h2>${list('Ora in onda',nowMap)}${list('Stasera',primeMap)}`;
  }
  getCardSize(){return 3}
}
customElements.define('tv-guide-multi-card',TvGuideMultiCard);
