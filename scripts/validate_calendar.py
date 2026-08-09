#!/usr/bin/env python3
"""Validate the generated feed's basic RFC 5545 structure and source parity."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "events.json"
ICS_PATH = ROOT / "public" / "big-bear-events.ics"


def unfold(raw: bytes) -> list[str]:
    text = raw.decode("utf-8")
    physical = text.split("\r\n")
    logical: list[str] = []
    for line in physical:
        if line.startswith((" ", "\t")) and logical:
            logical[-1] += line[1:]
        elif line:
            logical.append(line)
    return logical


def validate() -> tuple[int, int]:
    raw = ICS_PATH.read_bytes()
    if b"\r\n" not in raw or raw.replace(b"\r\n", b"").find(b"\n") != -1:
        raise ValueError("Calendar must use CRLF line endings")

    for number, line in enumerate(raw.split(b"\r\n"), start=1):
        if len(line) > 75:
            raise ValueError(f"Physical line {number} is {len(line)} bytes; maximum is 75")

    lines = unfold(raw)
    if lines[0] != "BEGIN:VCALENDAR" or lines[-1] != "END:VCALENDAR":
        raise ValueError("Calendar envelope is malformed")
    if "VERSION:2.0" not in lines or "METHOD:PUBLISH" not in lines:
        raise ValueError("Calendar is missing required publish metadata")
    if "BEGIN:VTIMEZONE" not in lines or "TZID:America/Los_Angeles" not in lines:
        raise ValueError("Pacific time zone definition is missing")

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    expected = sum(len(event.get("occurrences", [None])) for event in data["events"])
    actual = lines.count("BEGIN:VEVENT")
    if actual != expected or lines.count("END:VEVENT") != expected:
        raise ValueError(f"Expected {expected} complete events, found {actual}")

    uids = [line[4:] for line in lines if line.startswith("UID:")]
    if len(uids) != len(set(uids)):
        raise ValueError("Event UIDs are not unique")

    summaries = [line for line in lines if line.startswith("SUMMARY:")]
    descriptions = [line for line in lines if line.startswith("DESCRIPTION:")]
    urls = [line for line in lines if line.startswith("URL:")]
    if not (len(summaries) == len(descriptions) == len(urls) == expected):
        raise ValueError("Every event must have a summary, description, and URL")

    date_pattern = re.compile(
        r"^DTSTART(?:;VALUE=DATE:\d{8}|;TZID=America/Los_Angeles:\d{8}T\d{6})$"
    )
    starts = [line for line in lines if line.startswith("DTSTART") and "1970" not in line]
    if len(starts) != expected or any(not date_pattern.match(line) for line in starts):
        raise ValueError("One or more event start values are malformed")

    expected_ends = sum(
        len(event.get("occurrences", [None]))
        for event in data["events"]
        if event.get("all_day") or event.get("end") or event.get("occurrences")
    )
    end_pattern = re.compile(
        r"^DTEND(?:;VALUE=DATE:\d{8}|;TZID=America/Los_Angeles:\d{8}T\d{6})$"
    )
    ends = [line for line in lines if line.startswith("DTEND")]
    if len(ends) != expected_ends or any(not end_pattern.match(line) for line in ends):
        raise ValueError("One or more event end values are missing or malformed")

    statuses = [line for line in lines if line.startswith("STATUS:")]
    if len(statuses) != expected or any(line not in {"STATUS:CONFIRMED", "STATUS:TENTATIVE"} for line in statuses):
        raise ValueError("One or more event status values are missing or malformed")

    revisions = [line for line in lines if line.startswith("LAST-MODIFIED:")]
    if len(revisions) != expected or any(
        not re.match(r"^LAST-MODIFIED:\d{8}T\d{6}Z$", line) for line in revisions
    ):
        raise ValueError("One or more event revision timestamps are missing or malformed")

    return actual, len(raw)


if __name__ == "__main__":
    event_count, byte_count = validate()
    print(f"Validated {event_count} events ({byte_count:,} bytes)")
