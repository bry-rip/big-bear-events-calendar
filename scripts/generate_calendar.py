#!/usr/bin/env python3
"""Generate an Apple Calendar-compatible ICS feed from data/events.json."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "events.json"
OUTPUT_PATH = ROOT / "public" / "big-bear-events.ics"


def escape_text(value: str) -> str:
    """Escape an RFC 5545 TEXT value."""
    return (
        value.replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def fold_line(line: str, limit: int = 75) -> list[str]:
    """Fold a content line without splitting UTF-8 code points."""
    chunks: list[str] = []
    current = ""
    current_bytes = 0
    chunk_limit = limit

    for char in line:
        char_bytes = len(char.encode("utf-8"))
        if current and current_bytes + char_bytes > chunk_limit:
            chunks.append(current)
            current = char
            current_bytes = char_bytes
            chunk_limit = limit - 1  # Continuation lines begin with one space.
        else:
            current += char
            current_bytes += char_bytes

    chunks.append(current)
    return [chunks[0], *[f" {chunk}" for chunk in chunks[1:]]]


def content_line(name: str, value: str, *, text_value: bool = True) -> list[str]:
    rendered = escape_text(value) if text_value else value
    return fold_line(f"{name}:{rendered}")


def iso_date(value: str) -> date:
    return date.fromisoformat(value)


def ical_date(value: str) -> str:
    return iso_date(value).strftime("%Y%m%d")


def ical_datetime(value: str) -> str:
    return datetime.fromisoformat(value).strftime("%Y%m%dT%H%M%S")


def display_datetime(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    return parsed.strftime("%a, %b %-d, %Y at %-I:%M %p")


def event_when(event: dict[str, Any]) -> str:
    if event.get("all_day"):
        first = iso_date(event["start_date"])
        last = iso_date(event.get("end_date", event["start_date"]))
        if first == last:
            return first.strftime("%a, %b %-d, %Y (all day)")
        return f"{first.strftime('%a, %b %-d')}–{last.strftime('%a, %b %-d, %Y')} (all day)"

    start = datetime.fromisoformat(event["start"])
    end_raw = event.get("end")
    if not end_raw:
        return display_datetime(event["start"])
    end = datetime.fromisoformat(end_raw)
    if start.date() == end.date():
        return (
            f"{start.strftime('%a, %b %-d, %Y, %-I:%M %p')}–"
            f"{end.strftime('%-I:%M %p')}"
        )
    return f"{display_datetime(event['start'])}–{display_datetime(end_raw)}"


def format_section(title: str, lines: list[str]) -> list[str]:
    if not lines:
        return []
    return [title, *[f"• {line}" for line in lines]]


def build_description(event: dict[str, Any], event_by_id: dict[str, dict[str, Any]]) -> str:
    blocks: list[list[str]] = []

    blocks.append([event["summary"].strip()])
    blocks.append([f"WHEN\n{event_when(event)}"])

    if event.get("pricing"):
        blocks.append(format_section("PRICE / ADMISSION", event["pricing"]))
    if event.get("schedule"):
        blocks.append(format_section("SCHEDULE", event["schedule"]))
    if event.get("details"):
        blocks.append(format_section("WHAT TO EXPECT", event["details"]))
    if event.get("tips"):
        blocks.append(format_section("USEFUL NOTES", event["tips"]))
    if event.get("tbd"):
        blocks.append(format_section("TBD / VERIFY BEFORE GOING", event["tbd"]))

    conflict_lines: list[str] = []
    for conflict in event.get("conflicts", []):
        if isinstance(conflict, str) and conflict in event_by_id:
            other = event_by_id[conflict]
            conflict_lines.append(f"Overlaps or competes with: {other['title']} ({event_when(other)}).")
        else:
            conflict_lines.append(str(conflict))
    if conflict_lines:
        blocks.append(format_section("CONFLICTS / SAME-DAY OPTIONS", conflict_lines))

    source_lines = [f"{source['label']}: {source['url']}" for source in event["sources"]]
    blocks.append(format_section("OFFICIAL SOURCES", source_lines))

    status = event.get("status", "confirmed").upper()
    blocks.append([
        f"CALENDAR STATUS: {status}",
        f"Last checked: {event['last_verified']}",
        "Details can change. Recheck the official source before making a special trip.",
    ])

    return "\n\n".join("\n".join(block) for block in blocks if block)


def location_text(event: dict[str, Any]) -> str:
    location = event.get("location", {})
    return " — ".join(part for part in [location.get("name"), location.get("address")] if part)


def event_lines(
    event: dict[str, Any], calendar: dict[str, Any], event_by_id: dict[str, dict[str, Any]]
) -> list[str]:
    timezone = calendar["timezone"]
    last_modified = datetime.fromisoformat(event.get("last_modified", event["last_verified"]))
    timestamp = last_modified.strftime("%Y%m%dT%H%M%SZ")
    status = "TENTATIVE" if event.get("status") == "tentative" else "CONFIRMED"

    lines = ["BEGIN:VEVENT"]
    lines += content_line("UID", f"{event['id']}@big-bear-events.bry.rip", text_value=False)
    lines += content_line("DTSTAMP", timestamp, text_value=False)
    lines += content_line("LAST-MODIFIED", timestamp, text_value=False)
    lines += content_line("SEQUENCE", str(event.get("sequence", 0)), text_value=False)

    if event.get("all_day"):
        start = ical_date(event["start_date"])
        inclusive_end = iso_date(event.get("end_date", event["start_date"]))
        exclusive_end = (inclusive_end + timedelta(days=1)).strftime("%Y%m%d")
        lines += content_line("DTSTART;VALUE=DATE", start, text_value=False)
        lines += content_line("DTEND;VALUE=DATE", exclusive_end, text_value=False)
    else:
        lines += content_line(f"DTSTART;TZID={timezone}", ical_datetime(event["start"]), text_value=False)
        if event.get("end"):
            lines += content_line(f"DTEND;TZID={timezone}", ical_datetime(event["end"]), text_value=False)

    lines += content_line("SUMMARY", event["title"])
    location = location_text(event)
    if location:
        lines += content_line("LOCATION", location)
    lines += content_line("DESCRIPTION", build_description(event, event_by_id))
    lines += content_line("URL", event["sources"][0]["url"], text_value=False)
    categories = ",".join(escape_text(category) for category in event.get("categories", ["Big Bear Events"]))
    lines += content_line("CATEGORIES", categories, text_value=False)
    lines += content_line("STATUS", status, text_value=False)
    lines += content_line("TRANSP", "TRANSPARENT", text_value=False)
    lines += content_line("X-BIGBEAR-DETAIL-STATUS", event.get("status", "confirmed").upper())
    lines.append("END:VEVENT")
    return lines


def timezone_lines() -> list[str]:
    return [
        "BEGIN:VTIMEZONE",
        "TZID:America/Los_Angeles",
        "X-LIC-LOCATION:America/Los_Angeles",
        "BEGIN:DAYLIGHT",
        "TZOFFSETFROM:-0800",
        "TZOFFSETTO:-0700",
        "TZNAME:PDT",
        "DTSTART:19700308T020000",
        "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU",
        "END:DAYLIGHT",
        "BEGIN:STANDARD",
        "TZOFFSETFROM:-0700",
        "TZOFFSETTO:-0800",
        "TZNAME:PST",
        "DTSTART:19701101T020000",
        "RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU",
        "END:STANDARD",
        "END:VTIMEZONE",
    ]


def load_data() -> dict[str, Any]:
    with DATA_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data


def expand_occurrences(source_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expand an irregular series into stable, independently updateable events."""
    expanded: list[dict[str, Any]] = []
    for source in source_events:
        occurrences = source.get("occurrences")
        if not occurrences:
            expanded.append(source)
            continue

        for occurrence in occurrences:
            event = deepcopy(source)
            event.pop("occurrences", None)
            occurrence_date = occurrence["date"]
            event["id"] = occurrence.get("id", f"{source['id']}-{occurrence_date}")
            event["start"] = f"{occurrence_date}T{source['start_time']}"
            event["end"] = f"{occurrence_date}T{source['end_time']}"
            event.pop("start_time", None)
            event.pop("end_time", None)
            for key, value in occurrence.items():
                if key not in {"date", "id"}:
                    event[key] = value
            expanded.append(event)
    return expanded


def validate_source(data: dict[str, Any]) -> None:
    events = data.get("events", [])
    ids = [event.get("id") for event in events]
    if not events:
        raise ValueError("The event dataset is empty")
    if len(ids) != len(set(ids)):
        raise ValueError("Every event id must be unique")

    for event in events:
        required = {"id", "title", "summary", "sources", "last_verified"}
        missing = required - event.keys()
        if missing:
            raise ValueError(f"{event.get('id', '<unknown>')}: missing {sorted(missing)}")
        if not event["sources"]:
            raise ValueError(f"{event['id']}: at least one source is required")
        if event.get("all_day"):
            if "start_date" not in event:
                raise ValueError(f"{event['id']}: all-day event needs start_date")
        elif "start" not in event:
            raise ValueError(f"{event['id']}: timed event needs start")

    event_ids = set(ids)
    for event in events:
        for conflict in event.get("conflicts", []):
            if isinstance(conflict, str) and conflict not in event_ids:
                raise ValueError(f"{event['id']}: unknown conflict id {conflict}")


def generate() -> tuple[int, Path]:
    data = load_data()
    data["events"] = expand_occurrences(data["events"])
    validate_source(data)
    calendar = data["calendar"]
    events = sorted(
        data["events"], key=lambda event: event.get("start", event.get("start_date", ""))
    )
    event_by_id = {event["id"]: event for event in events}

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{calendar['product_id']}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    lines += content_line("X-WR-CALNAME", calendar["name"])
    lines += content_line("X-WR-CALDESC", calendar["description"])
    lines += content_line("X-WR-TIMEZONE", calendar["timezone"], text_value=False)
    lines += content_line("REFRESH-INTERVAL;VALUE=DURATION", calendar["refresh_interval"], text_value=False)
    lines += content_line("X-PUBLISHED-TTL", calendar["refresh_interval"], text_value=False)
    lines += timezone_lines()

    for event in events:
        lines += event_lines(event, calendar, event_by_id)
    lines.append("END:VCALENDAR")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))
    return len(events), OUTPUT_PATH


if __name__ == "__main__":
    count, output = generate()
    print(f"Generated {count} events at {output}")
