# Big Bear Local Events Calendar

A curated, Apple Calendar-compatible feed for Big Bear events that are useful to locals: live music, festivals, volunteer days, outdoor happenings, motorsports, and standout community events.

The source of truth is `data/events.json`. `scripts/generate_calendar.py` turns it into `public/big-bear-events.ics`. Netlify serves that file from one stable HTTPS URL so existing Apple Calendar subscriptions receive later published updates.

- Subscription page: https://big-bear-events.netlify.app/
- Calendar feed: https://big-bear-events.netlify.app/big-bear-events.ics
- Repository: https://github.com/bry-rip/big-bear-events-calendar

## Subscribe

On a Mac:

1. Open Calendar.
2. Choose **File → New Calendar Subscription**.
3. Paste `https://big-bear-events.netlify.app/big-bear-events.ics`.
4. Choose **iCloud** as the Location to make it appear on devices signed into the same Apple Account.
5. Choose an automatic refresh interval such as every hour or every day.

On an iPhone or iPad running iOS/iPadOS 26 or later:

1. In Calendar, tap **Calendars**.
2. Tap **Add Calendar → Add Subscription Calendar**.
3. Enter `https://big-bear-events.netlify.app/big-bear-events.ics`, then tap **Find**.
4. Choose **iCloud** next to Account, choose a name/color, and tap **Done**.

Do not use **File → Import** for the downloaded file if you want updates. Importing is a one-time copy; subscribing follows the hosted feed.

## Curation rules

This is a selective locals calendar, not a mirror of every tourism listing. The durable policy also lives in `data/events.json` so future event sweeps inherit it:

- Free events are the default target. Relevant $1–20 events are easy additions; $20–40 events need to be distinctive; $40–50 is selective; events over $50 are normally excluded unless genuinely exceptional.
- Unknown price or exact start time is not, by itself, a reason to omit a promising event that is likely free or inexpensive. Add it as a clearly labeled `details_tbd` reminder so the subscriber can investigate if interested.
- Prioritize free concerts and car shows, karaoke, trivia, line dancing and Wyatt's nights, country/punk/metal, astronomy, wildlife, native plants, geology/science, environmental volunteering, and unusual mountain-town events.
- Recurring local nights need a supported cadence or dated occurrence, but do not need every price or timing detail. Generic expensive tourist packages do not qualify merely because they recur.
- Transportation and service schedules stay outside this events feed.
- `curation.permanent_exclusions` blocks a rejected event by title as well as ID. This keeps a future sweep from re-adding the same event under a different ID.

## Edit or add an event

1. Edit `data/events.json`.
2. Give every event a permanent, unique `id`. Never change an existing ID just to rename an event; the ID keeps Apple Calendar from making a duplicate.
3. Update `last_verified`. When event content changes, also increment `sequence` and set `last_modified` to a later UTC ISO timestamp, such as `2026-08-09T23:00:00Z`. The automated check rejects changed events without both revision updates so Apple Calendar can recognize the change.
4. Run:

   ```sh
   python3 scripts/generate_calendar.py
   python3 scripts/validate_calendar.py
   python3 -m unittest discover -s tests -v
   ```

5. Commit and push. Netlify rebuilds and publishes the feed.

## Retire an event

Events are never deleted casually — a removed ID vanishes from every subscriber's
calendar. To drop one deliberately:

1. Delete the event object from `events`.
2. Remove every `conflicts` reference pointing at it, including references to the
   dated occurrence IDs a series expands into.
3. Add an entry to the top-level `retired` list with `id`, `reason` and `retired_on`.
   Retiring a series parent covers all the dated occurrences it expands to.
4. Bump `sequence` and `last_modified` on every event whose `conflicts` you edited —
   their descriptions changed, so subscribers need the revision.

`scripts/validate_updates.py` rejects any removal whose ID is not in `retired`, so an
accidental deletion still fails the build. Use this for curation calls; an event that
is genuinely cancelled by its organizer is a different case and still needs a real
cancellation workflow.

## Event fields

- Timed event: `start` and optional `end` in local Big Bear time, such as `2026-08-27T10:00`.
- All-day event: `all_day: true`, `start_date`, and optional inclusive `end_date`.
- `status`: use `confirmed` when the event itself is confirmed, `tentative` when the event may not happen, or `details_tbd` when the event is real but some details remain unknown.
- `tbd`: exact uncertainties the subscriber should recheck.
- `conflicts`: another event ID, or an explicit free-text object such as `{ "note": "Same-day traffic may be heavy." }`.
- `sources`: official organizer pages first; a ticket page or authoritative venue page may follow.

Descriptions in the feed are plain text because that is what Apple Calendar displays most reliably. They are assembled from the structured price, schedule, details, tips, TBD, conflict, and source fields.

## Feed behavior

- Time zone: `America/Los_Angeles`, including an embedded daylight-saving definition.
- Stable UIDs: `<event-id>@big-bear-events.bry.rip`.
- Calendar events are transparent, so subscribing does not mark personal time as busy.
- Recommended refresh interval advertised by the feed: one hour. Apple Calendar ultimately controls when it refreshes.
- The feed is curated and independent. Official source links remain attached to every event.
