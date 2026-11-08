# Birthday Tracker v0.3.3 — Apple external attachment downloads

## Changes from v0.3.2

- When a birthday event has an `ATTACH` referencing `birthday.json` on an allowed iCloud HTTPS host, attempts to download it in read-only mode.
- Uses Apple app-specific password **only** when the attachment URL host is exactly the authenticated calendar host. A different iCloud attachment hostname is fetched without credentials. **Never sends credentials to arbitrary URLs or across automatic redirects.**
- Validates each redirect target (at most three), enforces a 64 KiB JSON size limit and reports safe error codes (without exposing private attachment URLs).
- Adds `caldav_json_download_failed` and `caldav_json_download_statuses` to sensor diagnostics. Individual birthday `metadata_status` also indicates the result.
- Preserves existing Home Assistant calendar selection, CalDAV discovery, event filtering, UK `DD/MM/YYYY` dates, fallback local metadata, and card.

## Upgrade using HACS

1. Copy the **contents** of this ZIP to the root of your existing GitHub repository (not inside another folder).
2. In `custom_components/birthday_tracker/manifest.json`, replace the placeholder `OWNER/REPOSITORY` in `issue_tracker` with your GitHub repo details if needed.
3. Commit your changes, publish a release tagged `v0.3.3`, refresh HACS, update, and restart Home Assistant.
4. Existing Apple Calendar credentials and `https://caldav.icloud.com/` should be retained. Do not enable public calendar sharing.
5. Inspect the birthday sensor attributes: `attachment_status`, `caldav_json_found`, `caldav_json_loaded`, `caldav_json_download_failed`, `caldav_json_download_statuses`, and the `metadata_status` for Stephen's birthday.

## What to expect

Your v0.3.2 diagnostics showed one matching iCloud external attachment for Stephen's birthday. v0.3.3 now attempts to read it. If the result is `attachment_http_403` (or similar), Apple did not permit access with this method and we will need to investigate how its managed attachment URLs are authorised. `external_attachment_url` should no longer be the result for a trusted iCloud HTTPS attachment URL. Other birthday events without an attached `birthday.json` will continue to have `no_birthday_json_attach`.

**Security limits:** Only HTTPS URLs on subdomains of `icloud.com` or `icloud-content.com`, default HTTPS port, and up to three similarly validated redirects are permitted. External hosts are fetched without credentials. The implementation is experimental and untested against your live iCloud attachment endpoint. The calendar and attachments are never modified. Never post private attachment URLs, app-specific passwords, or personal addresses in public issues.

## Example JSON (UK dates)

```json
{
  "full_name": "Example Person",
  "date_of_birth": "12/11/1994",
  "address": {"line1":"", "line2":"", "city":"", "postcode":"", "country":"UK"},
  "relationship": "Friend",
  "notes": "",
  "gift_ideas": [],
  "interests": []
}
```

For two people on one event, see `example-multiple-people.json`.

## Card

The included `www/birthday-tracker-card.js` still requires manual installation (it is not automatically installed as a HACS integration resource). If installed already, no change is required. Otherwise copy it to `/config/www/`, add a `/local/birthday-tracker-card.js` JavaScript module dashboard resource and use the existing `custom:birthday-tracker-card` configuration with your actual sensor ID.
