# Birthday Tracker v0.3.0 — HACS update (experimental iCloud attachments)

## Improvements

- Preserves existing calendar entity and sensor unique ID; filters all-day `birthday` events.
- Removes repeated annual occurrences of the same birthday from the upcoming list.
- Adds read-only **direct CalDAV** access to search iCalendar VEVENT `ATTACH` properties.
- Supports `birthday.json` metadata directly on the CalDAV event **when the server exposes it**; local `/config/birthday_tracker/events/<metadata_filename>` remains the fallback.
- Supports a single-person JSON object, a top-level list of people, or `{ "people": [ ... ] }` for shared events.
- Parses date of birth as `DD/MM/YYYY`; displays the age on the matching birthday.
- Publishes diagnostics such as `attachment_status`, `caldav_events_found`, `caldav_json_found`, and `caldav_json_loaded`.

## Important: Apple CalDAV attachment compatibility

**This is an experimental reader, not a guarantee Apple exposes files.** Apple Calendar's Add Attachment may use a managed attachment that does not show up as an ordinary downloadable `ATTACH` with `FILENAME=birthday.json` in CalDAV data. A `MANAGED-ID` alone does not supply the attachment bytes. In such cases the sensor will say `no_named_json_attachments_exposed`; use the local JSON fallback until a compatible attachment retrieval mechanism is verified.

The integration makes a CalDAV `REPORT` request to the **calendar collection URL** you supply. It expects a calendar collection that supports `calendar-query`, authenticated by an Apple app-specific password. An iCloud account landing URL (such as `https://caldav.icloud.com/`) is **not necessarily the calendar collection URL**. Obtain the full collection URL from your working CalDAV client configuration or discovery. The program does not attempt autodiscovery. This is intentionally read-only: it never modifies the Apple event.

## Update via HACS

1. Upload the **contents** of this ZIP to the **root** of the Git repository and commit.
2. In `custom_components/birthday_tracker/manifest.json`, replace `OWNER/REPOSITORY` with your GitHub repository path for the issue tracker.
3. Publish release tag `v0.3.0` (recommended); refresh HACS and download the new version.
4. Restart Home Assistant. Existing Birthday Tracker entity and configuration should be retained.
5. Open **Settings → Devices & services → Birthday Tracker → Configure**. To enable direct CalDAV inspection, enter the calendar collection HTTPS URL, Apple ID email, and **app-specific password**. Do **not** enter your normal Apple ID password. Leave these blank to keep the existing Home Assistant calendar + local JSON mode.
6. Check **Developer tools → States → your Birthday Tracker sensor** for `attachment_status`, `caldav_events_found`, `caldav_json_found`, `caldav_json_loaded`, and `metadata_source`.

### Diagnostics

| Value | Meaning |
|---|---|
| `not_configured` | No direct CalDAV connection configured; calendar parsing still works |
| `caldav_connected` | CalDAV REPORT succeeded; inspect per-event metadata status |
| `no_named_json_attachments_exposed` | No event published a file named `birthday.json` via ATTACH |
| `caldav_http_401` | iCloud rejected credentials |
| `caldav_http_403` | Calendar access forbidden |
| `caldav_http_404` | The supplied URL is not the correct calendar collection |
| `caldav_request_failed` | Network or malformed XML response |
| `attachment_redirect_unsupported` | Attachment server asked to redirect; downloader refuses to forward credentials |
| `external_attachment_url` | Attachment host differs from calendar host; downloader refuses to forward credentials |
| `ambiguous_event_title` | Multiple event components have same title and cannot be matched safely by HA event title |

## JSON format

```json
{
  "full_name": "Example Person",
  "date_of_birth": "12/11/1994",
  "address": { "line1": "12 High Street", "line2": "", "city": "Birmingham", "postcode": "B1 1AA", "country": "UK" },
  "relationship": "Friend", "notes": "", "gift_ideas": [], "interests": []
}
```

For a shared birthday, see `example-multiple-people.json`.

**Local fallback:** Place a file named as `metadata_filename` from sensor attributes in `/config/birthday_tracker/events/`. This is separate from the Apple event attachment. Empty JSON attachments cannot supply an age.

## Card installation

HACS installs the Python integration only. Manually copy `www/birthday-tracker-card.js` to `/config/www/birthday-tracker-card.js` and register `/local/birthday-tracker-card.js` as a dashboard JavaScript module. Existing card configuration remains:

```yaml
type: custom:birthday-tracker-card
entity: sensor.upcoming_birthdays
title: Upcoming Birthdays
max_items: 10
```

Use your actual sensor entity ID. Refresh the dashboard browser cache after changing the card.

## Security / privacy

- Only use a dedicated Apple app-specific password, never your normal account password. The credentials are stored in the Home Assistant config entry options and are **not** added to Git.
- Credentials are never sent to a different hostname, and HTTPS URLs are required. Redirects are not followed.
- The attachment downloader rejects files over 64 KiB and server responses over 4 MiB.
- Birthday names, dates of birth, and addresses are published as Home Assistant sensor attributes. Anyone with access to this entity may view them.
- For duplicate event names, the Home Assistant calendar API lacks UIDs and matching is intentionally conservative.

## Known limits

- CalDAV collection URL must be supplied; there is no autodiscovery.
- Direct attachment download is limited to same-host HTTPS URLs; redirects and external hosts are refused.
- Apple's managed attachment format may not expose a normal `birthday.json` URL through CalDAV.
- The CalDAV REPORT fetches the calendar collection, so very large calendars may exceed the 4 MiB safeguard.
- Title-based matching can be ambiguous. Metadata for separate events with identical titles will not be matched automatically.
- Not verified against a live iCloud account. Validate with a non-sensitive test birthday first.
