# Big Bear Local Events Calendar

A curated, Apple Calendar-compatible feed for Big Bear events that are useful to locals: live music, festivals, volunteer days, outdoor happenings, motorsports, and standout community events.

The source of truth is `data/events.json`. `scripts/generate_calendar.py` turns it into `public/big-bear-events.ics`. Netlify serves that file from one stable HTTPS URL so existing Apple Calendar subscriptions receive later published updates.

## Subscribe

On a Mac:

1. Open Calendar.
2. Choose **File → New Calendar Subscription**.
3. Paste the live `.ics` URL shown on the subscription page.
4. Choose **iCloud** as the Location to make it appear on devices signed into the same Apple Account.
5. Choose an automatic refresh interval such as every hour or every day.

Do not use **File → Import** for the downloaded file if you want updates. Importing is a one-time copy; subscribing follows the hosted feed.

## Edit or add an event

1. Edit `data/events.json`.
2. Give every event a permanent, unique `id`. Never change an existing ID just to rename an event; the ID keeps Apple Calendar from making a duplicate.
3. Update `last_verified`. When event content changes, also update `last_modified` and increment `sequence`.
4. Run:

   ```sh
   python3 scripts/generate_calendar.py
   python3 scripts/validate_calendar.py
   python3 -m unittest discover -s tests -v
   ```

5. Commit and push. Netlify rebuilds and publishes the feed.

## Event fields

- Timed event: `start` and optional `end` in local Big Bear time, such as `2026-08-27T10:00`.
- All-day event: `all_day: true`, `start_date`, and optional inclusive `end_date`.
- `status`: use `confirmed` when the event itself is confirmed, `tentative` when the event may not happen, or `details_tbd` when the event is real but some details remain unknown.
- `tbd`: exact uncertainties the subscriber should recheck.
- `conflicts`: another event ID or a plain-language same-day note.
- `sources`: official organizer pages first; a ticket page or authoritative venue page may follow.

Descriptions in the feed are plain text because that is what Apple Calendar displays most reliably. They are assembled from the structured price, schedule, details, tips, TBD, conflict, and source fields.

## Feed behavior

- Time zone: `America/Los_Angeles`, including an embedded daylight-saving definition.
- Stable UIDs: `<event-id>@big-bear-events.bry.rip`.
- Calendar events are transparent, so subscribing does not mark personal time as busy.
- Recommended refresh interval advertised by the feed: one hour. Apple Calendar ultimately controls when it refreshes.
- The feed is curated and independent. Official source links remain attached to every event.
