# Birthday Tracker v0.4.0 — Lovelace card refresh

This release keeps the working v0.3.3 Apple iCloud CalDAV attachment downloader **unchanged** and redesigns the Lovelace card.

## Changes

- Responsive birthday list with next birthday countdown, age on birthday, and special treatment for birthdays today.
- Tap or click a birthday to open an accessible details dialog with full name, UK-format birth date, relationship, address, notes, gift ideas and interests.
- Optional 30-day/90-day filters; "All" remains the default. Missing JSON metadata is handled gracefully.
- Plain-text DOM rendering (no injected HTML from birthday.json), Escape key and close button.
- Calendar discovery, privacy/security restrictions, attachment retrieval, multiple people on one event, all-day/title filtering and age calculation are **unchanged** from v0.3.3.

## HACS update

1. Extract the ZIP and replace the repository files **at the root** (not in a nested folder).
2. Keep your own issue tracker URL in `custom_components/birthday_tracker/manifest.json` if you already customised it; the packaged placeholder is `OWNER/REPOSITORY`.
3. Commit and publish GitHub release `v0.4.0`.
4. Refresh HACS and update the Birthday Tracker integration, then restart Home Assistant.
5. **Important:** HACS integration updates do not automatically copy the Lovelace card. Copy `www/birthday-tracker-card.js` from this release to Home Assistant's `/config/www/birthday-tracker-card.js`.
6. If not already configured, add `/local/birthday-tracker-card.js` as a JavaScript module resource under **Settings → Dashboards → Resources** (the location may vary with HA version). If previously registered, leave it as-is, then hard-refresh the browser or append a resource version query like `?v=040` to invalidate the cache.

Manual card YAML:

```yaml
type: custom:birthday-tracker-card
entity: sensor.upcoming_birthdays # replace with your actual entity ID
title: Upcoming Birthdays
max_items: 10
show_filters: true
```

`max_items` limits the number visible after filtering, not the number fetched. Change `show_filters` to `false` to hide the filter chips.

## Attachment status

v0.3.3 confirmed one `birthday.json` was downloaded and parsed from your iCloud calendar. The backend is unchanged here. Events without a `birthday.json` display their event titles without ages, until you add birth dates. Dates *inside* JSON stay in `DD/MM/YYYY` format. The card does not show private addresses until details are opened.

## Safety

The integration reads calendars and attachments only; it never writes to Apple Calendar. Avoid posting personal addresses, attachment links or credentials in public issues. The attachment downloader retains the same strict HTTPS host restrictions as v0.3.3.
