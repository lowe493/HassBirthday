/* Birthday Tracker Lovelace card. No external libraries. */
class BirthdayTrackerCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) throw new Error("Set entity: sensor.upcoming_birthdays");
    this._config = config;
    this._expanded = null;
    this._render();
  }
  set hass(value) {
    const state = value.states[this._config?.entity];
    const signature = JSON.stringify(state?.attributes?.birthdays || []);
    if (this._signature !== signature) {
      this._signature = signature;
      this._hass = value;
      this._render();
    }
  }
  getCardSize() { return 4; }
  _render() {
    if (!this._config) return;
    if (!this.shadowRoot) this.attachShadow({mode: "open"});
    const state = this._hass?.states[this._config.entity];
    this.shadowRoot.replaceChildren();
    const style = document.createElement("style");
    style.textContent = `
      :host{display:block;font-family:var(--primary-font-family,Arial,sans-serif)}
      ha-card{display:block;padding:18px;color:var(--primary-text-color);background:var(--ha-card-background,var(--card-background-color));border-radius:var(--ha-card-border-radius,12px)}
      h2{font-size:19px;margin:0 0 14px} .item{border-top:1px solid var(--divider-color,#ddd)}
      button{font:inherit;color:inherit;background:none;border:0;padding:13px 2px;width:100%;cursor:pointer;text-align:left;display:flex;align-items:center;justify-content:space-between;gap:10px}
      button:hover{background:var(--secondary-background-color,#eee)} .person{font-weight:600}
      .subtitle,.muted{font-size:13px;color:var(--secondary-text-color,#777)}
      .detail{padding:0 4px 14px;font-size:14px;line-height:1.7;overflow-wrap:anywhere}
      .detail div{margin:2px 0}.pill{font-size:12px;padding:4px 8px;border-radius:12px;background:var(--secondary-background-color,#eee);white-space:nowrap}
      .empty{padding:12px 0;color:var(--secondary-text-color,#777)}
    `;
    this.shadowRoot.append(style);
    const card = document.createElement("ha-card");
    const header = document.createElement("h2");
    header.textContent = this._config.title || "🎂 Upcoming birthdays";
    card.append(header);
    if (!state) {
      const notice = document.createElement("div");notice.className="empty";
      notice.textContent=`Entity not found: ${this._config.entity}`;card.append(notice);
    } else {
      const birthdays = (state.attributes.birthdays || []).slice(0, this._config.max_items || 10);
      if (!birthdays.length) { const empty=document.createElement("div");empty.className="empty";empty.textContent="No upcoming birthdays found";card.append(empty); }
      birthdays.forEach((b,index)=>{
        const row=document.createElement("div");row.className="item";
        const button=document.createElement("button");button.type="button";
        const left=document.createElement("div");
        const name=document.createElement("div");name.className="person";name.textContent=b.name;
        const sub=document.createElement("div");sub.className="subtitle";
        const day=new Date(`${b.date}T12:00:00`);
        const formatted=day.toLocaleDateString("en-GB",{day:"numeric",month:"long"});
        sub.textContent=`${formatted}${b.turning_age === null ? "" : ` · Turning ${b.turning_age}`}`;
        left.append(name,sub);
        const pill=document.createElement("span");pill.className="pill";pill.textContent=b.days_until === 0 ? "Today 🎉" : `${b.days_until} days`;
        button.append(left,pill);button.setAttribute("aria-expanded",String(this._expanded===index));
        button.addEventListener("click",()=>{this._expanded=this._expanded===index?null:index;this._render();});
        row.append(button);
        if (this._expanded===index) {
          const details=document.createElement("div");details.className="detail";
          const address=b.address||{};
          const values=[
            ["Date of birth",b.date_of_birth], ["Relationship",b.relationship],
            ["Address",[address.line1,address.line2,address.city,address.postcode,address.country].filter(Boolean).join(", ")],
            ["Notes",b.notes],
            ["Gift ideas",Array.isArray(b.gift_ideas)?b.gift_ideas.join(", "):""],
            ["Interests",Array.isArray(b.interests)?b.interests.join(", "):""],
          ];
          values.forEach(([label,value])=>{
            if (!value) return;
            const item=document.createElement("div");
            const bold=document.createElement("strong");bold.textContent=`${label}: `;
            item.append(bold,document.createTextNode(String(value)));details.append(item);
          });
          if (b.metadata_status!=="loaded") {
            const status=document.createElement("div");status.className="muted";
            status.textContent=`JSON metadata: ${b.metadata_status}. Check attachment_status in the sensor diagnostics.`;details.append(status);
            const hint=document.createElement("div");hint.className="muted";
            hint.textContent=`Local fallback filename: ${b.metadata_filename}`;details.append(hint);
          }
          row.append(details);
        }
        card.append(row);
      });
    }
    this.shadowRoot.append(card);
  }
}
if (!customElements.get("birthday-tracker-card")) customElements.define("birthday-tracker-card",BirthdayTrackerCard);
window.customCards=window.customCards||[];
window.customCards.push({type:"birthday-tracker-card",name:"Birthday Tracker",description:"Upcoming calendar birthdays with expandable personal information"});
