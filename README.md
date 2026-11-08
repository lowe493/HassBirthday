# Birthday Tracker v0.3.2 — HACS update (CalDAV retrieval + startup resilience)

**Changes from 0.3.1**

- Handles unavailable/missing Home Assistant calendar entities gracefully with `UpdateFailed`, allowing scheduled retries instead of an unexpected traceback.
- Tries a bounded CalDAV REPORT first, then an unbounded REPORT, then a limited read-only PROPFIND + GET fallback (maximum 200 `.ics` objects). The fallback may be slow for a large calendar; a limit prevents an unbounded fetch.
- Adds diagnostics: `caldav_request_method`, `caldav_request_fallback`, `caldav_request_errors` (sanitised codes only), `caldav_failure_stage`, and fallback counts. Never returns CalDAV URLs or credentials in sensor attributes.
- Continues to use authenticated autodiscovery to match `calendar.shared` with `Shared`, and retains the `DD/MM/YYYY` JSON structure and existing sensor.
- **Note:** Apple Calendar managed attachment support remains experimental. The update cannot guarantee that `birthday.json` will appear in CalDAV ATTACH properties.

## Upgrade

Upload ZIP contents to repository root, commit and tag `v0.3.2`, refresh HACS, install and restart Home Assistant. Existing options should remain; use `https://caldav.icloud.com/` with an Apple app-specific password. Inspect sensor diagnostic attributes and share only status/method/error codes, never private URLs or passwords.

# Birthday Tracker v0.3.1 (previous release details) — HACS update (CalDAV autodiscovery)

**Changes from 0.3.0**

- Starts authenticated CalDAV discovery at `https://caldav.icloud.com/` (or your configured HTTPS server), instead of assuming the address is already a calendar collection.
- Uses standard WebDAV `current-user-principal` and CalDAV `calendar-home-set` properties to discover the account's calendar collections.
- Matches the discovered display name to your previously selected Home Assistant calendar entity (e.g. `calendar.shared`). If multiple calendars cannot be matched uniquely, it reports a diagnostic instead of retrieving data from a possibly incorrect calendar.
- Follows only HTTPS redirects to the same server or another `*.caldav.icloud.com` server for iCloud. Never passes app-specific credentials to unrelated hosts.
- Keeps the existing birthday sensor, all-day filtering, UK `DD/MM/YYYY` parsing, multiple-person metadata support, and optional local JSON fallback.

## Installation / update

1. Upload the **contents** of this ZIP to the **root** of the existing GitHub repository, replacing the old files. Check `custom_components/birthday_tracker/manifest.json` has your own issue tracker URL rather than `OWNER/REPOSITORY`.
2. Commit and create a GitHub release tagged `v0.3.1` (recommended).
3. Refresh and download in HACS; restart Home Assistant.
4. In **Settings → Devices & services → Birthday Tracker → Configure**, keep the already selected Home Assistant calendar (e.g. `calendar.shared`). Use `https://caldav.icloud.com/` as the URL, your Apple Account email, and an Apple **app-specific password**. You no longer need a manually constructed private collection URL. The existing options should be retained after upgrading.
5. Inspect the Birthday Tracker sensor in Developer Tools → States.

## Diagnostics to send back (do not include credentials or private URLs)

- `attachment_status`
- `discovered_calendars_count`, `discovered_calendar_names`, `calendar_match_status`, `discovered_calendar_name` (if available)
- `caldav_events_found`, `caldav_events_with_attach`, `caldav_json_found`, `caldav_json_loaded` (if available)
- `metadata_loaded`, `metadata_missing`

Common statuses:

| Status | Meaning |
|---|---|
| `discovery_http_401` / `discovery_http_403` | The discovery request was rejected by the server; confirm the app-specific password and account permissions |
| `discovery_principal_not_found` | No usable current-user-principal was returned |
| `discovery_calendar_home_not_found` | Server didn't return a calendar-home-set |
| `calendar_name_not_matched` | Discovered calendars don't have a display name matching the selected Home Assistant entity |
| `ambiguous_calendar_name` | Several calendars matched; automatic selection was refused |
| `caldav_connected` | Discovery and subsequent collection REPORT succeeded |
| `no_named_json_attachments_exposed` | No `birthday.json` ATTACH references were returned |
| `caldav_http_403` | The discovered collection rejected its REPORT request |

**Limitations:** Not yet validated against a live Apple CalDAV account. iCloud's *Add Attachment* feature may use managed attachments that aren't exposed as a normal `ATTACH` property; automatic discovery does not guarantee attachment downloading. The original event data is read-only. Calendar titles and birth details remain stored in Home Assistant sensor attributes. Do not share passwords, collection URLs or personal information in public logs. The existing matching of event metadata by title (because `calendar.get_events` doesn't expose event UIDs) can be ambiguous when separate birthday events share a name.

## JSON structure

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

For two people in one event, use `example-multiple-people.json`.

## Lovelace card

The card is included but **not installed automatically by HACS**. If already installed, keep using it. Otherwise copy `www/birthday-tracker-card.js` to `/config/www/`, register `/local/birthday-tracker-card.js` as a dashboard JavaScript module and add:

```yaml
type: custom:birthday-tracker-card
entity: sensor.upcoming_birthdays
title: Upcoming Birthdays
max_items: 10
```

Use your actual sensor ID.
