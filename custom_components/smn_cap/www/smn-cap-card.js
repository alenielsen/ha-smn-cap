/* SMN CAP Lovelace card — zero dependencies; all external text is escaped via textContent. */
class SmnCapCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) throw new Error("Configurá entity: sensor.smn_..._cantidad_de_alertas");
    this.config = {title:"Alertas meteorológicas",...config};
  }
  set hass(hass) {
    this._hass=hass;
    if (!this.shadowRoot) this.attachShadow({mode:"open"});
    this.render();
  }
  getCardSize(){return 5;}
  static getStubConfig(){return {entity:"sensor.smn_alertas_cap_cantidad_de_alertas",title:"Alertas meteorológicas"};}
  render(){
    if(!this.shadowRoot || !this._hass || !this.config)return;
    const state=this._hass.states[this.config.entity];
    const root=this.shadowRoot;
    root.replaceChildren();
    const style=document.createElement("style");
    style.textContent=`
      :host{display:block}ha-card{display:block;padding:20px;border-radius:18px;color:var(--primary-text-color);background:var(--ha-card-background,var(--card-background-color));}
      .header{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:16px}
      .title{font-size:18px;font-weight:650;letter-spacing:-.3px}.sub{font-size:12px;color:var(--secondary-text-color);margin-top:5px}
      .pill{border-radius:100px;padding:5px 10px;font-size:12px;font-weight:650;background:var(--secondary-background-color)}
      .item{padding:14px;margin:10px 0;border-radius:12px;background:var(--secondary-background-color);border-left:4px solid var(--divider-color)}
      .item[data-level="Moderate"]{border-left-color:#e4ac35}.item[data-level="Severe"]{border-left-color:#ef8d32}
      .item[data-level="Extreme"]{border-left-color:#dd4545}
      .label{font-size:16px;font-weight:650}.meta{font-size:12px;color:var(--secondary-text-color);margin-top:6px}
      .detail{font-size:14px;line-height:1.55;white-space:pre-wrap;margin-top:10px}
      .instructions{border-top:1px solid var(--divider-color);padding-top:9px;margin-top:10px;font-size:13px;white-space:pre-wrap}
      .empty{padding:20px;text-align:center;color:var(--secondary-text-color)}.error{color:var(--error-color)}
      a{color:var(--primary-color);text-decoration:none}.footer{margin-top:15px;font-size:12px;color:var(--secondary-text-color)}
    `;
    const card=document.createElement("ha-card");root.append(style,card);
    const el=(tag,cls,text,parent)=>{const x=document.createElement(tag);if(cls)x.className=cls;if(text!==undefined)x.textContent=String(text);if(parent)parent.append(x);return x;};
    const header=el("div","header",undefined,card),left=el("div","",undefined,header);
    el("div","title",this.config.title,left);
    el("div","sub",this.config.location||"Servicio Meteorológico Nacional · Argentina",left);
    if(!state || ["unavailable","unknown"].includes(state.state)){
      el("div","pill error","Sin datos confiables",header);
      el("div","empty","No se pudieron verificar las alertas del SMN. Consultá la fuente oficial.",card);
    }else{
      const alerts=Array.isArray(state.attributes.alerts)?state.attributes.alerts:[];
      const now=Date.now();
      const active=alerts.filter(a=>!a.effective || new Date(a.effective).getTime()<=now);
      el("div","pill",alerts.length?`${active.length} vigentes · ${alerts.length-active.length} próximas`:"Sin alertas detectadas",header);
      if(!alerts.length)el("div","empty","No se detectaron alertas para el punto configurado.",card);
      for(const a of [...alerts].sort((a,b)=>Date.parse(a.effective||0)-Date.parse(b.effective||0))){
        const item=el("div","item",undefined,card);
        item.dataset.level=a.severity||"Unknown";
        el("div","label",a.headline||a.event||"Alerta meteorológica",item);
        const start=a.effective&&new Date(a.effective).getTime()>now;
        const fmt=v=>{if(!v)return "Sin información";const d=new Date(v);return Number.isNaN(d.getTime())?"Sin información":new Intl.DateTimeFormat("es-AR",{dateStyle:"short",timeStyle:"short"}).format(d);};
        el("div","meta",`${start?"Próxima":"Vigente"} · CAP: ${a.severity||"Desconocida"} · ${fmt(a.effective)} — ${fmt(a.expires)}`,item);
        if(a.description)el("div","detail",a.description,item);
        if(a.instruction)el("div","instructions",`Recomendaciones: ${a.instruction}`,item);
        if(a.areas?.some(Boolean))el("div","meta",`Zonas: ${a.areas.filter(Boolean).join("; ")}`,item);
      }
    }
    const footer=el("div","footer",undefined,card);
    if(state?.attributes?.last_success)el("span","",`Última lectura válida: ${new Date(state.attributes.last_success).toLocaleString("es-AR")} · `,footer);
    const anchor=el("a","","Consultar alertas oficiales ↗",footer);
    anchor.href="https://www.smn.gob.ar/alertas";anchor.target="_blank";anchor.rel="noopener noreferrer";
  }
}
if(!customElements.get("smn-cap-card"))customElements.define("smn-cap-card",SmnCapCard);
window.customCards=window.customCards||[];
if(!window.customCards.some(c=>c.type==="smn-cap-card"))window.customCards.push({type:"smn-cap-card",name:"SMN CAP - Alertas detalladas",description:"Alertas vigentes y futuras, con detalles e instrucciones."});
