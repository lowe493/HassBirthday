/* Birthday Tracker v0.4.1 — Lovelace card. No external dependencies. */
class BirthdayTrackerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._selected = null;
    this._filter = "all";
    this._lastSignature = null;
    this._escapeHandler = (event) => {
      if (event.key === "Escape" && this._selected !== null) this._closeDetails();
    };
  }
  setConfig(config) {
    if (!config || typeof config.entity !== "string" || !config.entity.trim()) {
      throw new Error("Birthday Tracker: provide an entity, e.g. sensor.upcoming_birthdays");
    }
    this._config = {
      title: "Upcoming Birthdays", max_items: 10, days_ahead: null,
      show_filters: true, show_age: true, show_countdown: true,
      compact_mode: false, show_missing_metadata: true, ...config
    };
    this._render();
  }
  set hass(hass) {
    this._hass = hass;
    if (!this._config) return;
    const state = hass.states[this._config.entity];
    const signature = JSON.stringify({
      birthdays: state?.attributes?.birthdays ?? [],
      state: state?.state ?? null,
      filter: this._filter,
    });
    if (signature !== this._lastSignature) {
      this._lastSignature = signature;
      this._render();
    }
  }
  connectedCallback() { document.addEventListener("keydown", this._escapeHandler); }
  disconnectedCallback() { document.removeEventListener("keydown", this._escapeHandler); }
  getCardSize() { return 4; }
  static getStubConfig() { return {
    entity: "sensor.upcoming_birthdays", title: "Upcoming Birthdays",
    max_items: 5, days_ahead: 60, show_filters: false,
    show_age: true, show_countdown: true, compact_mode: true,
    show_missing_metadata: false
  }; }

  _element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }
  _date(iso, options = { day: "numeric", month: "short" }) {
    if (typeof iso !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return "Date unknown";
    const [year, month, day] = iso.split("-").map(Number);
    const date = new Date(year, month - 1, day, 12);
    if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) return "Date unknown";
    return new Intl.DateTimeFormat("en-GB", options).format(date);
  }
  _countdown(days) {
    if (days === 0) return "Today 🎉";
    if (days === 1) return "Tomorrow";
    return Number.isFinite(days) ? `${days} days` : "Upcoming";
  }
  _closeDetails() { this._selected = null; this._render(); }
  _detailsField(container, label, value) {
    if (value === null || value === undefined || value === "" || (Array.isArray(value) && !value.length)) return;
    const line = this._element("div", "field");
    line.append(this._element("span", "field-label", label));
    line.append(this._element("span", "field-value", Array.isArray(value) ? value.join(", ") : value));
    container.append(line);
  }
  _renderDetails(card, person) {
    const backdrop = this._element("div", "backdrop");
    backdrop.addEventListener("click", (event) => { if (event.target === backdrop) this._closeDetails(); });
    const dialog = this._element("section", "dialog");
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.setAttribute("aria-label", `Birthday details for ${person.name || person.event_title || "person"}`);
    const top = this._element("div", "dialog-heading");
    const heading = this._element("div", "");
    heading.append(this._element("div", "dialog-title", person.name || person.event_title || "Birthday"));
    heading.append(this._element("div", "subtle", `${this._date(person.date, { day: "numeric", month: "long", year: "numeric" })} · ${this._countdown(person.days_until)}`));
    const close = this._element("button", "close", "×");
    close.type = "button";
    close.setAttribute("aria-label", "Close birthday details");
    close.addEventListener("click", () => this._closeDetails());
    top.append(heading, close); dialog.append(top);
    if (this._config.show_age !== false && Number.isInteger(person.turning_age)) {
      const age = this._element("div", "age-banner", `🎂 Turning ${person.turning_age}`);
      dialog.append(age);
    }
    const fields = this._element("div", "fields");
    this._detailsField(fields, "Full name", person.name);
    this._detailsField(fields, "Date of birth", person.date_of_birth);
    this._detailsField(fields, "Relationship", person.relationship);
    const address = person.address && typeof person.address === "object" ? person.address : {};
    this._detailsField(fields, "Address", [address.line1, address.line2, address.city, address.postcode, address.country].filter(Boolean).join(", "));
    this._detailsField(fields, "Notes", person.notes);
    this._detailsField(fields, "Gift ideas", Array.isArray(person.gift_ideas) ? person.gift_ideas : []);
    this._detailsField(fields, "Interests", Array.isArray(person.interests) ? person.interests : []);
    if (!fields.childNodes.length) fields.append(this._element("div", "subtle", "No extra birthday details available yet."));
    dialog.append(fields);
    if (this._config.show_missing_metadata !== false && person.metadata_status !== "loaded") {
      dialog.append(this._element("div", "metadata-hint", "ℹ No birthday.json details loaded for this event yet."));
    }
    backdrop.append(dialog);
    card.append(backdrop);
    this._focusClose = close;
  }
  _render() {
    if (!this._config || !this.shadowRoot) return;
    const shadow = this.shadowRoot;
    shadow.replaceChildren();
    const style = document.createElement("style");
    style.textContent = `
      :host{display:block;color:var(--primary-text-color);font-family:var(--primary-font-family,Roboto,sans-serif)}
      ha-card{display:block;position:relative;background:var(--ha-card-background,var(--card-background-color,#fff));border-radius:var(--ha-card-border-radius,12px);padding:18px;overflow:visible}
      .header{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px}
      .title{font-size:20px;font-weight:650;letter-spacing:-.3px}
      .count{font-size:12px;background:var(--secondary-background-color,#eee);border-radius:20px;padding:5px 9px;white-space:nowrap}
      .filters{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 12px}
      button{font-family:inherit;color:inherit;cursor:pointer}
      .filter{border:1px solid var(--divider-color,#ddd);border-radius:20px;padding:6px 10px;background:transparent;font-size:12px}
      .filter[aria-pressed="true"]{background:var(--primary-color,#03a9f4);color:white;border-color:transparent}
      .entry{border-top:1px solid var(--divider-color,#ddd)}
      .entry:first-child{border-top:none}
      .birthday{width:100%;display:flex;align-items:center;gap:12px;text-align:left;background:transparent;border:0;padding:12px 4px;border-radius:9px}
      .birthday:hover,.birthday:focus-visible{background:var(--secondary-background-color,#f3f3f3)}
      .avatar{width:42px;height:42px;border-radius:50%;background:var(--secondary-background-color,#eee);display:grid;place-items:center;flex-shrink:0;font-size:21px}
      .identity{flex:1;min-width:0}.name{font-size:14px;font-weight:650;overflow-wrap:anywhere}.subtitle{font-size:12px;color:var(--secondary-text-color,#777);margin-top:3px}
      .right{display:grid;justify-items:end;gap:5px}.pill{font-size:12px;border-radius:18px;background:var(--secondary-background-color,#eee);padding:5px 8px;white-space:nowrap}
      .today .pill{background:var(--success-color,#279650);color:white}.chevron{font-size:15px;color:var(--secondary-text-color,#888)}
      .empty{padding:14px 0;color:var(--secondary-text-color,#777);font-size:14px}
      .backdrop{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9999;display:flex;align-items:center;justify-content:center;padding:16px;box-sizing:border-box}
      .dialog{background:var(--ha-card-background,var(--card-background-color,#fff));color:var(--primary-text-color);width:min(460px,100%);max-height:min(80vh,680px);overflow:auto;border-radius:16px;padding:20px;box-sizing:border-box;box-shadow:0 18px 55px rgba(0,0,0,.25)}
      .dialog-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}.dialog-title{font-size:20px;font-weight:700}.subtle{color:var(--secondary-text-color,#777);font-size:13px;margin-top:5px}
      .close{background:var(--secondary-background-color,#eee);border:0;border-radius:50%;width:32px;height:32px;font-size:22px;flex-shrink:0}
      .age-banner{border-radius:10px;padding:10px 12px;margin:17px 0 5px;background:var(--secondary-background-color,#eee);font-weight:650}
      .fields{margin-top:12px}.field{display:grid;grid-template-columns:110px minmax(0,1fr);gap:12px;padding:10px 0;border-bottom:1px solid var(--divider-color,#ddd);font-size:13px;line-height:1.5}
      .field-label{color:var(--secondary-text-color,#777)}.field-value{overflow-wrap:anywhere;white-space:pre-wrap}
      .metadata-hint{margin-top:14px;font-size:12px;color:var(--secondary-text-color,#777)}
      .compact ha-card{padding:10px 12px}
      .compact .header{margin-bottom:6px}
      .compact .title{font-size:17px}
      .compact .birthday{padding:7px 2px;gap:8px}
      .compact .avatar{width:32px;height:32px;font-size:17px}
      .compact .subtitle{margin-top:2px;font-size:11px}
      .compact .pill{font-size:11px;padding:3px 7px}
      .compact .right{gap:2px}
      .compact .filters{margin-bottom:7px}
      .compact .count{padding:3px 7px}
      @media(max-width:360px){.birthday{gap:8px}.avatar{height:36px;width:36px}.field{grid-template-columns:1fr;gap:2px}}
    `;
    shadow.append(style);
    const root = this._element("div", this._config.compact_mode === true ? "compact" : "");
    const card = this._element("ha-card");
    const state = this._hass?.states[this._config.entity];
    const source = Array.isArray(state?.attributes?.birthdays) ? state.attributes.birthdays : [];
    const birthdays = source.filter(b => b && typeof b === "object");
    const requestedDays = this._config.days_ahead;
    const daysAhead = requestedDays === null || requestedDays === undefined || requestedDays === ""
      ? Infinity : Number(requestedDays);
    const horizon = Number.isFinite(daysAhead) && daysAhead >= 0 ? daysAhead : Infinity;
    const eligible = birthdays.filter(b => Number.isFinite(b.days_until)
      && b.days_until >= 0 && b.days_until <= horizon);
    const header = this._element("div", "header");
    header.append(this._element("div", "title", `🎂 ${this._config.title}`));
    header.append(this._element("span", "count", `${eligible.length} upcoming`));
    card.append(header);
    if (this._config.show_filters !== false) {
      const filters = this._element("div", "filters");
      for (const [key, label] of [["all", "All"], ["30", "30 days"], ["90", "90 days"]]) {
        const btn = this._element("button", "filter", label);
        btn.type = "button"; btn.setAttribute("aria-pressed", String(this._filter === key));
        btn.addEventListener("click", () => { this._filter = key; this._selected = null; this._render(); });
        filters.append(btn);
      }
      card.append(filters);
    }
    if (!state) {
      card.append(this._element("div", "empty", `Entity not found: ${this._config.entity}`));
    } else if (state.state === "unavailable" || state.state === "unknown") {
      card.append(this._element("div", "empty", "Birthday Tracker is currently unavailable."));
    } else {
      const max = Math.max(1, Number.parseInt(this._config.max_items, 10) || 10);
      const filterLimit = this._config.show_filters === false || this._filter === "all" ? Infinity : Number(this._filter);
      const visible = eligible.filter(b => b.days_until <= filterLimit)
        .sort((a, b) => a.days_until - b.days_until)
        .slice(0, max);
      if (!visible.length) card.append(this._element("div", "empty", "No birthdays in this period."));
      for (const person of visible) {
        const item = this._element("div", `entry${person.days_until === 0 ? " today" : ""}`);
        const button = this._element("button", "birthday");button.type = "button";
        button.setAttribute("aria-label", `View birthday details for ${person.name || person.event_title || "person"}`);
        const avatar = this._element("span", "avatar", person.days_until === 0 ? "🎉" : "🎁");
        const main = this._element("div", "identity");
        main.append(this._element("div", "name", person.name || person.event_title || "Birthday"));
        let subtitle = this._date(person.date, { day: "numeric", month: "long" });
        if (this._config.show_age !== false && Number.isInteger(person.turning_age)) subtitle += ` · Turning ${person.turning_age}`;
        main.append(this._element("div", "subtitle", subtitle));
        const right = this._element("div", "right");
        if (this._config.show_countdown !== false) {
          right.append(this._element("span", "pill", this._countdown(person.days_until)));
        }
        right.append(this._element("span", "chevron", "›"));
        button.append(avatar, main, right);
        button.addEventListener("click", () => { this._selected = person; this._render(); });
        item.append(button);card.append(item);
      }
    }
    if (this._selected !== null) this._renderDetails(card, this._selected);
    root.append(card);
    shadow.append(root);
    if (this._selected !== null && this._focusClose) this._focusClose.focus();
  }
}
if (!customElements.get("birthday-tracker-card")) customElements.define("birthday-tracker-card", BirthdayTrackerCard);
window.customCards = window.customCards || [];
if (!window.customCards.some(c => c.type === "birthday-tracker-card")) {
  window.customCards.push({ type: "birthday-tracker-card", name: "Birthday Tracker", description: "Upcoming birthdays with a details popup" });
}
