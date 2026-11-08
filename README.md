# Birthday Tracker — HACS-ready starter (v0.1.1)

## Add this to your GitHub repository

1. Extract the ZIP and upload its **contents directly to the repository root** (not the `birthday_tracker_hacs_v0.1.1` folder).
2. In `custom_components/birthday_tracker/manifest.json`, replace `OWNER/REPOSITORY` in `issue_tracker` with your actual GitHub repository owner and name. Keep an Issues page enabled.
3. Commit changes to your default branch. Optionally create a GitHub release tagged `v0.1.1` after committing.
4. In HACS add the repo as a **custom repository** with type **Integration**; then refresh / re-download.
5. Restart Home Assistant and add **Birthday Tracker** from Settings → Devices & services.

**Important about the Lovelace card:** HACS integration installs only `custom_components/birthday_tracker`, not the repo-root `www` folder. Copy `www/birthday-tracker-card.js` manually to `/config/www/birthday-tracker-card.js` and register `/local/birthday-tracker-card.js` as a JavaScript module in Dashboard Resources.

**Important about Apple attachments:** the code does **not** yet fetch the `birthday.json` files attached through Apple Calendar. It currently supports optional local JSON metadata files; age and personal details remain unavailable until supplied.

---

# Birthday Tracker — Home Assistant starter (v0.1)

**Status:** Functional calendar-backed prototype, with optional *local* JSON metadata. **It does not yet retrieve Apple Calendar event attachments.** That requires investigating how this particular iCloud account exposes `ATTACH` references via CalDAV. Do not assume `birthday.json` is accessible through Home Assistant's calendar API.

## Installation

1. Copy `custom_components/birthday_tracker/` into `/config/custom_components/birthday_tracker/` on Home Assistant.
2. Copy `www/birthday-tracker-card.js` into `/config/www/birthday-tracker-card.js`.
3. Restart Home Assistant.
4. Settings → Devices & services → Add integration → Birthday Tracker; select the existing CalDAV `calendar.*` entity.
5. In Settings → Dashboards → Resources, add `/local/birthday-tracker-card.js` as a **JavaScript module** (if resources are managed manually).
6. Find the new `sensor.*upcoming_birthdays` entity under the Birthday Tracker device. In the dashboard add a Manual card:

```yaml
type: custom:birthday-tracker-card
entity: sensor.upcoming_birthdays
title: Upcoming Birthdays
max_items: 10
```

Replace `sensor.upcoming_birthdays` with the **actual entity ID**, which may be different.

## Calendar and JSON metadata

The sensor reads events from `calendar.get_events` for the next 370 days, using all events in the chosen calendar. It expects that calendar to contain birthdays only. It takes the event summary as the person's name, and displays the upcoming occurrence. The age is omitted until a validated date of birth is available.

For the **local fallback**, create `/config/birthday_tracker/events/` and put JSON files there. The filename is a 24-character SHA-256 prefix of the event UID (if Home Assistant supplies one) or otherwise the event title, with `.json` suffix. Expand a card row to see its expected filename. Copy `example-birthday.json` into that file and change its values. Updates are picked up every 30 minutes (or on reload). Missing/empty/invalid JSON is handled without failing the card.

The local fallback is temporary and **does not change or download the JSON attached in Apple Calendar**.

## Apple attachment integration: next engineering step

1. Inspect the raw iCalendar `VEVENT` record via an authenticated CalDAV request (not the HA calendar service).
2. Locate `ATTACH` properties, with parameters such as `FILENAME`, `FMTTYPE`, and `MANAGED-ID` (some servers may use different metadata).
3. Confirm whether the attachment is a readable HTTPS URL, embedded payload, or a managed reference requiring authenticated requests.
4. Match event UID and recurrence instances to the correct `birthday.json`.
5. Restrict attachment fetching to an allowlist of trusted Apple/iCloud hosts, enforce size limits, avoid logging URLs/credentials/personal metadata, and never serve JSON publicly.
6. Integrate retrieval into the backend and test with an actual attached file before marking it supported.

Attachment handling varies by server and cannot be guaranteed without seeing a safe, redacted sample of the raw event's `ATTACH` metadata. **Do not share passwords, tokens, or live attachment URLs.**

## Known limitations

- No automatic Apple attachment ingestion yet.
- Calendar may not expose a stable event UID, which can make local metadata matching rely on the summary. Renaming the event then changes the metadata lookup key.
- The card reads HA state attributes; large calendars could exceed state attribute limits. A dedicated WebSocket API is a better option for large deployments.
- Leap-day birthdays are shown according to the calendar's actual recurrence; the age uses the year of the actual occurrence.
- This is starter code, not an audited or tested production integration.
