# Birthday Tracker v0.2.0 — HACS integration

Tracks upcoming birthdays from an **existing Home Assistant calendar** (including a CalDAV calendar).

## Changes in v0.2.0

- Only **all-day** calendar events containing `birthday` in the title are included by default (case-insensitive).
- The title keyword can be changed under **Settings → Devices & services → Birthday Tracker → Configure**.
- Sensor state attributes include diagnostic counts (`calendar_events_scanned`, `non_birthdays_skipped`, `timed_events_skipped`, `metadata_missing`, etc.).
- `attachment_status: not_available_through_calendar_get_events` explicitly explains the Apple attachment limitation.
- Preserves the sensor unique ID from v0.1.1 so existing dashboards should continue working.

## Important limitations

This version **does not download birthday.json attachments from iCloud**. Home Assistant's `calendar.get_events` service exposes event summary, description, start, end and location, **not `ATTACH` or CalDAV managed attachment metadata**. This version has no direct iCloud credentials or CalDAV attachment downloader. An empty JSON attachment will not provide a date of birth, so ages remain unknown until valid metadata is loaded.

Local fallback metadata can be placed at `/config/birthday_tracker/events/<metadata_filename>` where the filename is shown on each birthday in the sensor attributes. This is a **local fallback**, not the Apple Calendar attachment. Note that Home Assistant does not expose event UIDs through this action; matching currently falls back to event titles, meaning identically titled events share a metadata filename.

## HACS installation / upgrade

1. Upload the **contents** of this archive to your GitHub repository root; `custom_components/birthday_tracker/manifest.json` must be directly under the repository's `custom_components` directory.
2. Replace `OWNER/REPOSITORY` in `manifest.json` under `issue_tracker` with your GitHub URL (and optionally replace `documentation`).
3. Commit and optionally publish release tag `v0.2.0`.
4. In HACS, refresh/redownload the integration; restart Home Assistant.
5. Your previously configured Birthday Tracker should remain configured. Open Developer Tools → States, find your Birthday Tracker sensor, and inspect the `birthdays` list and diagnostic counts.

## Dashboard card (manual installation)

HACS installs the Python integration under `custom_components`; it **does not install the JavaScript card from `www/`** in this combined repository. To install the card, copy `www/birthday-tracker-card.js` into `/config/www/birthday-tracker-card.js`, register `/local/birthday-tracker-card.js` as a JavaScript module resource in your dashboard, and add a manual card:

```yaml
type: custom:birthday-tracker-card
entity: sensor.upcoming_birthdays
title: Upcoming Birthdays
max_items: 10
```

Use the actual entity ID created in your system. Reload your browser after updating the card.

## Example birthday.json (local fallback, UK dates)

```json
{
  "full_name": "Example Person",
  "date_of_birth": "12/11/1994",
  "address": {
    "line1": "12 High Street",
    "line2": "",
    "city": "Birmingham",
    "postcode": "B1 1AA",
    "country": "UK"
  },
  "relationship": "Friend",
  "notes": "",
  "gift_ideas": [],
  "interests": []
}
```

**Privacy:** The sensor exposes names and any loaded personal details as attributes to users who can access that entity in Home Assistant. Restrict dashboard and Home Assistant access accordingly.

## Troubleshooting

- If non-birthday events appear, check that their titles contain the chosen keyword, and refresh the integration.
- If a birthday is missing, check that it is all-day and its title includes `birthday`; the title filter cannot identify other labels automatically.
- If `turning_age` is `null`, there is no valid, matching JSON date of birth available; this version doesn't retrieve Apple attachments.
- If a JSON file is empty, `metadata_status` becomes `empty`, rather than crashing the integration.
