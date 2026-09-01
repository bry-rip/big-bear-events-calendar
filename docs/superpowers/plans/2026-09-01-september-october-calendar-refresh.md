# September-October 2026 Big Bear Calendar Refresh Implementation Plan

> **For agentic workers:** Execute these checked tasks inline against `chatgpt-sept-2026-refresh`; preserve permanent event IDs and the stable feed URL.

**Goal:** Publish a fully verified September/October 2026 calendar refresh that follows Bryan's price and subject preferences and reaches the existing Apple Calendar subscription feed.

**Architecture:** `data/events.json` remains the source of truth. The Python generator expands irregular series into stable event IDs and writes `public/big-bear-events.ics`; repository validators enforce source shape, RFC-style ICS output, retirement rules, and revision metadata. GitHub `main` and Netlify production are separate publication gates and will both be verified.

**Tech Stack:** JSON, dependency-free Python 3, RFC 5545 iCalendar, Git/GitHub, Netlify.

## Global Constraints

- Prefer free events; readily include relevant $1-20 events; require distinction at $20-40; be selective at $40-50; normally exclude anything over $50.
- Keep relevant likely-free or inexpensive events as explicit TBD reminders when an exact price or start time is not yet published.
- Favor free concerts, car shows, karaoke, trivia, line dancing, country/punk/metal, astronomy, wildlife, plants, geology/science, environmental volunteering, and unusual mountain-town events.
- Keep transportation schedules out of the events feed.
- Never change an existing event ID or the stable `/big-bear-events.ics` URL.
- Retire Skyline at Sundown durably and remove every stale conflict reference.
- Use official/organizer sources where available and expose material uncertainty in `tbd` rather than inventing details.

---

### Task 1: Establish the current source and publication baselines

**Files:**
- Inspect: `CLAUDE.md`
- Inspect: `README.md`
- Inspect: `data/events.json`
- Inspect: `netlify.toml`

- [x] Fetch remote refs and compare local `main`, `origin/main`, and `origin/chatgpt-sept-2026-refresh`.
- [x] Recover the prior approval set from the referenced conversation.
- [x] Confirm the linked Netlify site, stable URL, live response headers, and pre-update feed hash.
- [x] Incorporate the already-committed Skyline retirement workflow and related calendar corrections from the existing calendar work branch.

### Task 2: Complete the primary-source event sweep

**Files:**
- Create: `docs/research/2026-09-01-september-october-event-sweep.md`

- [x] Verify dates, times, admission, location, recurrence, and official URLs for every approved addition.
- [x] Sweep Wyatt's, Barrel 33, karaoke, trivia, dancing, themed nights, and relevant local music for September and October.
- [x] Record excluded, rejected, and unresolved candidates so future sweeps do not repeat weak research.

### Task 3: Encode durable curation and event data

**Files:**
- Modify: `README.md`
- Modify: `data/events.json`
- Test: `tests/test_calendar.py`

**Interfaces:**
- Consumes: the official-source research note and existing event schema.
- Produces: unique stable event IDs, a durable `curation` policy, durable `excluded` records, and revised source events.

- [x] Add a source-level curation policy containing the exact price bands, favored themes, and transportation boundary.
- [x] Add/update every verified approved September/October event with detailed pricing, schedule, logistics, sources, categories, revision metadata, and conflicts.
- [x] Keep unresolved event details in explicit `tbd` fields while retaining relevant likely-free or inexpensive reminders.
- [x] Add validation tests for durable exclusions and uniqueness where the existing validator does not cover the new source fields.

### Task 4: Generate and validate the calendar artifact

**Files:**
- Generate: `public/big-bear-events.ics`

- [x] Run `python3 scripts/generate_calendar.py` and require exit 0.
- [x] Run `python3 scripts/validate_calendar.py` and require exit 0 with the expected event count.
- [x] Run `python3 -m unittest discover -s tests -v` and require zero failures.
- [x] Run `python3 scripts/validate_updates.py 41a0938db48b9899703ae06148bc52d6d5882de0` and require exit 0.
- [x] Run Python syntax compilation and a duplicate/stale-conflict audit over expanded event IDs.
- [x] Regenerate once more and require `git diff --exit-code -- public/big-bear-events.ics` after generation.

### Task 5: Review, publish, and verify each layer

**Files:**
- Review: all changes relative to `origin/main`

- [x] Review the full diff and event manifest against every requirement in this plan.
- [x] Commit the refresh on `chatgpt-sept-2026-refresh` and push it.
- [x] Merge the branch into `main`, push `main`, and verify local `HEAD` equals `origin/main`.
- [x] Confirm the production Netlify deploy for the pushed commit, using an explicit production deploy if the Git-linked deploy does not complete promptly.
- [x] Fetch the stable feed and require HTTP 200, `Content-Type: text/calendar`, the expected SHA-256, and representative required event UIDs/titles.
