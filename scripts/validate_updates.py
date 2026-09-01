#!/usr/bin/env python3
"""Require revision metadata whenever an existing calendar event changes."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import generate_calendar as generator


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "events.json"
IGNORED_CHANGE_FIELDS = {"last_modified", "sequence"}
DATE_SUFFIX = re.compile(r"-\d{4}-\d{2}-\d{2}$")


def expanded_by_id(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {event["id"]: event for event in generator.expand_occurrences(data["events"])}


def is_retired(event_id: str, retired_ids: set[str]) -> bool:
    """A removed ID is permitted only when it, or its series parent, was retired.

    Occurrence IDs are generated as "<series-id>-<YYYY-MM-DD>", so retiring the
    series parent covers every date it expands to without listing them all.
    """
    if event_id in retired_ids:
        return True
    parent = DATE_SUFFIX.sub("", event_id)
    return parent != event_id and parent in retired_ids


def retired_ids(data: dict[str, Any]) -> set[str]:
    return {entry["id"] for entry in data.get("retired", [])}


def event_content(event: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in event.items() if key not in IGNORED_CHANGE_FIELDS}


def validate_updates(current: dict[str, Any], previous: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    current_events = expanded_by_id(current)
    previous_events = expanded_by_id(previous)
    retired = retired_ids(current)

    for event_id, old in previous_events.items():
        new = current_events.get(event_id)
        if new is None:
            if not is_retired(event_id, retired):
                errors.append(
                    f"{event_id}: existing event ID was removed without being listed in "
                    "data/events.json \"retired\"; add it there with a reason to drop it deliberately"
                )
            continue
        if event_content(new) == event_content(old):
            continue

        old_sequence = old.get("sequence", 0)
        new_sequence = new.get("sequence", 0)
        if not isinstance(new_sequence, int) or new_sequence <= old_sequence:
            errors.append(
                f"{event_id}: content changed, so sequence must increase above {old_sequence}"
            )

        old_modified = generator.revision_datetime(old.get("last_modified", old["last_verified"]))
        new_modified = generator.revision_datetime(new.get("last_modified", new["last_verified"]))
        if new_modified <= old_modified:
            errors.append(
                f"{event_id}: content changed, so last_modified must be later than "
                f"{old.get('last_modified', old['last_verified'])}"
            )

    return errors


def load_previous(revision: str) -> dict[str, Any] | None:
    if not revision or set(revision) == {"0"}:
        return None
    result = subprocess.run(
        ["git", "show", f"{revision}:data/events.json"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Could not read data/events.json at {revision}: {result.stderr.strip()}"
        )
    return json.loads(result.stdout)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/validate_updates.py <base-git-revision>", file=sys.stderr)
        return 2

    try:
        previous = load_previous(sys.argv[1])
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if previous is None:
        print("No prior dataset found; revision check skipped")
        return 0

    current = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    errors = validate_updates(current, previous)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Validated revision metadata for changed events")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
