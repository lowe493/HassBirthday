# Birthday Tracker v0.4.3 — Fix age calculation

This update fixes `turning_age: null` when an attached `birthday.json` contains a valid UK date of birth but its day/month differs from the Apple calendar event. **The calendar continues to determine the scheduled birthday date and countdown.** The JSON date determines the birth year for the turning age; the discrepancy is reported instead of suppressing the age.

## Example

An event scheduled for `2026-11-12` with JSON `date_of_birth: 09/11/1996` now reports:

```yaml
turning_age: 30
date_mismatch: true
```

The calendar event is still shown as November 12. If the correct date is November 9, edit the recurring event in Apple Calendar too. The sensor also includes `birthday_date_mismatches` in its diagnostic attributes. If the JSON birth date is missing/invalid, `turning_age` remains null. The existing leap-day observation convention is preserved.

## HACS update

1. Extract the ZIP at the **root** of your existing GitHub repository.
2. Preserve any customised GitHub issue URL in `custom_components/birthday_tracker/manifest.json`.
3. Commit, tag and release `v0.4.3`, then refresh HACS and install the update.
4. Restart Home Assistant or reload the Birthday Tracker integration.
5. Check Developer Tools → States → Birthday Tracker: `turning_age`, `date_mismatch` and `birthday_date_mismatches`.

The Lovelace card JavaScript is unchanged from v0.4.2; **you do not need to recopy it or update its resource URL**. All existing YAML options remain supported.

## Previous v0.4.2 details

# Birthday Tracker v0.4.2 — Lovelace card configuration

This release keeps the working v0.3.3 Apple iCloud CalDAV attachment downloader **unchanged** and redesigns the Lovelace card.

## Changes

- **Popup readability fix:** the birthday detail dialog now uses an opaque dark/light background rather than inheriting transparent theme card backgrounds. Stronger backdrop and contrast make dashboard widgets behind the popup less distracting.
- Optional `--birthday-tracker-dialog-background` CSS custom property can override the popup surface; ensure any override is opaque.


- Responsive birthday list with next birthday countdown, age on birthday, and special treatment for birthdays today.
- Tap or click a birthday to open an accessible details dialog with full name, UK-format birth date, relationship, address, notes, gift ideas and interests.
- Optional 30-day/90-day filters; "All" remains the default. Missing JSON metadata is handled gracefully.
- Plain-text DOM rendering (no injected HTML from birthday.json), Escape key and close button.
- Calendar discovery, privacy/security restrictions, attachment retrieval, multiple people on one event, all-day/title filtering and age calculation are **unchanged** from v0.3.3.

## HACS update

1. Extract the ZIP and replace the repository files **at the root** (not in a nested folder).
2. Keep your own issue tracker URL in `custom_components/birthday_tracker/manifest.json` if you already customised it; the packaged placeholder is `OWNER/REPOSITORY`.
3. Commit and publish GitHub release `v0.4.2`.
4. Refresh HACS and update the Birthday Tracker integration, then restart Home Assistant.
5. **Important:** HACS integration updates do not automatically copy the Lovelace card. Copy `www/birthday-tracker-card.js` from this release to Home Assistant's `/config/www/birthday-tracker-card.js`.
6. If not already configured, add `/local/birthday-tracker-card.js` as a JavaScript module resource under **Settings → Dashboards → Resources** (the location may vary with HA version). If previously registered, leave it as-is, then hard-refresh the browser or append a resource version query like `?v=042` to invalidate the cache.

Manual card YAML:

```yaml
type: custom:birthday-tracker-card
entity: sensor.upcoming_birthdays # replace with your actual entity ID
title: Upcoming Birthdays
max_items: 5
days_ahead: 60
show_filters: false
show_age: true
show_countdown: true
compact_mode: true
show_missing_metadata: false
```

`max_items` limits the number visible after filtering, not the number fetched. Change `show_filters` to `false` to hide the filter chips.

## Attachment status

v0.3.3 confirmed one `birthday.json` was downloaded and parsed from your iCloud calendar. The backend is unchanged here. Events without a `birthday.json` display their event titles without ages, until you add birth dates. Dates *inside* JSON stay in `DD/MM/YYYY` format. The card does not show private addresses until details are opened.

## Safety

The integration reads calendars and attachments only; it never writes to Apple Calendar. Avoid posting personal addresses, attachment links or credentials in public issues. The attachment downloader retains the same strict HTTPS host restrictions as v0.3.3.

## New v0.4.2 card options

- `days_ahead` (optional, default unlimited): only display birthdays within the next number of days; `0` shows today's birthdays only. This is a **card display setting**, not a calendar fetch period.
- `show_filters` (default `true`): toggles 30/90-day buttons. When hidden the card uses `days_ahead` directly.
- `show_age` (default `true`): displays/hides turning age in the row and detail dialog.
- `show_countdown` (default `true`): displays/hides countdown pill in each row.
- `compact_mode` (default `false`): tighter spacing, shorter rows and smaller heading/avatar.
- `show_missing_metadata` (default `true`): displays/hides the missing-JSON note in the detail dialog. Does **not** remove birthdays without JSON from the list.
- `max_items` (default `10`): max visible birthdays, applied after the date horizon and filter.

Existing integration, Apple CalDAV download code and stored credentials are unchanged. You must manually replace the `/homeassistant/www/birthday-tracker-card.js` file and update the resource URL to `/local/birthday-tracker-card.js?v=0.4.1` (or force-refresh) to load the new card.

## v0.4.2 upgrade note

If you only want this frontend fix, you can copy `www/birthday-tracker-card.js` to `/homeassistant/www/birthday-tracker-card.js` and update your dashboard resource URL to `/local/birthday-tracker-card.js?v=0.4.2`. A Home Assistant restart is not required for this JavaScript-only change.
