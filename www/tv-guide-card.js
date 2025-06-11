
class TvGuideMultiCard extends HTMLElement{
  setConfig(c){if(!c.now_entity||!c.prime_entity)throw new Error('now_entity e prime_entity necessari');this._config=c}
  set hass(h){
    const c=this._config;
    if(!this.root){
      this.root=this.attachShadow({mode:'open'});
      const style=document.createElement('style');
      style.textContent='.tvg-container{padding:16px;display:grid;row-gap:16px;font-family:var(--ha-card-header-font-family,"Roboto","Helvetica Neue",sans-serif)}h3{margin:0 0 8px;font-size:1rem;font-weight:600}ul{padding:0;margin:0;list-style:none}li{display:grid;grid-template-columns:1.5em auto 1fr;gap:8px;align-items:center;padding:4px 0;line-height:1.4;border-bottom:1px solid var(--divider-color)}span.idx{text-align:right;color:var(--secondary-text-color);font-weight:600}span.channel{font-weight:600}span.value{font-weight:500;color:var(--primary-text-color)}';
      this.root.appendChild(style);
      this.card=document.createElement('ha-card');
      if(c.title) this.card.header=c.title;
      this.container=document.createElement('div');
      this.container.className='tvg-container';
      this.card.appendChild(this.container);
      this.root.appendChild(this.card);
    }
    const now=h.states[c.now_entity];
    const prime=h.states[c.prime_entity];
    const nowMap=now?.attributes.programmi_correnti||{};
    const primeMap=prime?.attributes.prima_serata||{};
    const keys=c.channels||[...Object.keys(nowMap),...Object.keys(primeMap).filter(k=>!(k in nowMap))];
    const ch=Array.from(new Set(keys));
    const list=(title,map)=>{let html='<h3>'+title+'</h3><ul>';ch.forEach((k,i)=>{html+='<li><span class="idx">'+(i+1)+'</span><span class="channel">'+k+'</span><span class="value">'+(map[k]||'—')+'</span></li>';});html+='</ul>';return html;}
    this.container.innerHTML=`${list('Ora in onda',nowMap)}${list('Stasera',primeMap)}`;
  }
  getCardSize(){return 3}
}
customElements.define('tv-guide-multi-card',TvGuideMultiCard);
