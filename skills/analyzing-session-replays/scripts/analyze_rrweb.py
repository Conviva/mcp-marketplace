#!/usr/bin/env python3
"""Summarize gzipped/plain rrweb blob files in a directory to JSON on stdout.

Usage: python3 analyze_rrweb.py /path/to/dir-of-blobs > summary.json
"""

from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path
from typing import Any

# rrweb event types
META = 4
FULL_SNAPSHOT = 2
INCREMENTAL = 3
CUSTOM = 5
PLUGIN = 6

# incremental sources
MUTATION = 0
MOUSE_INTERACTION = 2
SCROLL = 3
INPUT = 5
LOG = 11

# Domain-agnostic DOM chrome only (exact full-string match). Product-specific
# UI labels (chat buttons, role names, etc.) are left for the narrating agent.
NOISE_TEXT = re.compile(
    r"^(SCRIPT_PLACEHOLDER|\d{1,2}:\d{2}\s*(AM|PM)?)$",
    re.I,
)
WHITESPACE = re.compile(r"\s+")
HTMLISH = re.compile(r"</?[a-zA-Z]|\bsrc=|\bhref=|^\*+$")
# Parser output / non-blob names that may sit next to downloaded blobs.
_SKIP_NAMES = frozenset({"summary.json"})


def _blob_files(dir_path: Path) -> list[Path]:
    """Prefer .gz over sibling .json so cached decompressions are not double-counted."""
    files = [
        p
        for p in dir_path.iterdir()
        if p.is_file()
        and p.name not in _SKIP_NAMES
        and (p.suffix in {".gz", ".json"} or p.name.endswith(".json.gz"))
    ]
    names_with_gz = {p.name[: -len(".gz")] for p in files if p.name.endswith(".gz")}
    out: list[Path] = []
    for p in sorted(files):
        # Compare full name (e.g. "foo.json"), not Path.stem ("foo") — otherwise
        # foo.json.gz + gunzip -k sibling foo.json both load and double-count events.
        if p.suffix == ".json" and p.name in names_with_gz:
            continue
        out.append(p)
    return out


def _ts_iso(ms: int | None) -> str | None:
    if ms is None:
        return None
    from datetime import datetime, timezone

    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _load_events(path: Path) -> list[dict[str, Any]]:
    raw = path.read_bytes()
    if path.suffix == ".gz" or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    data = json.loads(raw.decode("utf-8"))
    if isinstance(data, dict) and "events" in data:
        data = data["events"]
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON array of events")
    return [e for e in data if isinstance(e, dict)]


def _walk_text(node: Any, out: list[str]) -> None:
    if isinstance(node, dict):
        if node.get("type") == 3 and isinstance(node.get("textContent"), str):
            t = WHITESPACE.sub(" ", node["textContent"]).strip()
            if t:
                out.append(t)
        for child in node.get("childNodes") or []:
            _walk_text(child, out)
    elif isinstance(node, list):
        for child in node:
            _walk_text(child, out)


def _mutation_texts(data: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    for add in data.get("adds") or []:
        _walk_text(add.get("node"), texts)
    for t in data.get("texts") or []:
        val = t.get("value") if isinstance(t, dict) else None
        if isinstance(val, str):
            cleaned = WHITESPACE.sub(" ", val).strip()
            if cleaned:
                texts.append(cleaned)
    return texts


def _plugin_error(event: dict[str, Any]) -> str | None:
    """Return an error message only for real console/plugin error levels (not msg text)."""
    data = event.get("data") or {}
    payload = data.get("payload") if isinstance(data, dict) else None
    if not isinstance(payload, dict):
        payload = data if isinstance(data, dict) else {}
    level = str(payload.get("level") or payload.get("type") or "").lower()
    msg = payload.get("message") or payload.get("trace") or payload.get("error")
    if isinstance(msg, dict):
        msg = msg.get("message") or str(msg)
    if not msg:
        return None
    # Require an error/exception level — do not treat "error" substring in message
    # text as an error (avoids false positives on log/info lines).
    if level in ("error", "exception") or level.endswith(".error"):
        return str(msg)[:500]
    if event.get("type") == PLUGIN and "console" in str(data.get("plugin", "")).lower():
        if level == "error":
            return str(msg)[:500]
    return None


def analyze(dir_path: Path) -> dict[str, Any]:
    files = _blob_files(dir_path)
    if not files:
        raise SystemExit(f"No .gz/.json blob files found in {dir_path}")

    events: list[dict[str, Any]] = []
    for f in files:
        try:
            events.extend(_load_events(f))
        except Exception as exc:  # noqa: BLE001 — report per-file and continue
            print(f"warn: failed to load {f.name}: {exc}", file=sys.stderr)

    events.sort(key=lambda e: e.get("timestamp") or 0)
    if not events:
        raise SystemExit("No events parsed from blobs")

    t0 = events[0].get("timestamp")
    t1 = events[-1].get("timestamp")

    pages: list[dict[str, Any]] = []
    seen_href: set[str] = set()
    full_snapshots = 0
    scrolls = 0
    clicks = 0
    errors: list[dict[str, Any]] = []
    messages: list[dict[str, Any]] = []
    seen_msg: set[str] = set()

    last_activity = t0
    idle_gaps: list[dict[str, Any]] = []

    for ev in events:
        ts = ev.get("timestamp")
        et = ev.get("type")
        data = ev.get("data") or {}

        if isinstance(ts, int) and isinstance(last_activity, int) and ts - last_activity >= 30_000:
            idle_gaps.append(
                {
                    "from": _ts_iso(last_activity),
                    "to": _ts_iso(ts),
                    "seconds": round((ts - last_activity) / 1000),
                }
            )
        if isinstance(ts, int):
            last_activity = ts

        if et == META:
            href = data.get("href")
            if isinstance(href, str) and href not in seen_href:
                seen_href.add(href)
                pages.append(
                    {
                        "at": _ts_iso(ts),
                        "href": href,
                        "width": data.get("width"),
                        "height": data.get("height"),
                    }
                )
        elif et == FULL_SNAPSHOT:
            full_snapshots += 1
            texts: list[str] = []
            _walk_text(data.get("node"), texts)
            for text in texts:
                _maybe_add_message(messages, seen_msg, ts, text)
        elif et == INCREMENTAL:
            source = data.get("source")
            if source == SCROLL:
                scrolls += 1
            elif source == MOUSE_INTERACTION and data.get("type") in (2, 4):  # Click / DblClick
                clicks += 1
            elif source == MUTATION:
                for text in _mutation_texts(data):
                    _maybe_add_message(messages, seen_msg, ts, text)
            elif source == INPUT:
                text = data.get("text")
                if isinstance(text, str):
                    _maybe_add_message(messages, seen_msg, ts, text)
            elif source == LOG:
                level = str(data.get("level") or "").lower()
                payload = data.get("payload")
                msg = " ".join(str(x) for x in payload) if isinstance(payload, list) else str(payload or "")
                if level == "error" and msg:
                    errors.append({"at": _ts_iso(ts), "message": msg[:500]})
        elif et in (CUSTOM, PLUGIN):
            err = _plugin_error(ev)
            if err:
                errors.append({"at": _ts_iso(ts), "message": err})

    return {
        "blobFiles": len(files),
        "eventCount": len(events),
        "recordingStart": _ts_iso(t0),
        "recordingEnd": _ts_iso(t1),
        "durationSeconds": round(((t1 or 0) - (t0 or 0)) / 1000) if t0 and t1 else None,
        "pages": pages,
        "fullSnapshots": full_snapshots,
        "interactionCounts": {"clicks": clicks, "scrolls": scrolls},
        "errors": errors[:50],
        "errorCount": len(errors),
        "messages": messages[:200],
        "messageCount": len(messages),
        "idleGapsSecondsGe30": idle_gaps[:30],
        "notes": [
            "messages are heuristic text extracted from DOM mutations/snapshots; filter noise when narrating",
            "answer the user's question from this summary only — do not re-parse raw blobs unless asked",
        ],
    }


def _maybe_add_message(
    messages: list[dict[str, Any]], seen: set[str], ts: int | None, text: str
) -> None:
    text = WHITESPACE.sub(" ", text).strip()
    if len(text) < 8 or len(text) > 800:
        return
    if NOISE_TEXT.match(text) or HTMLISH.search(text):
        return
    key = text.lower()
    if key in seen:
        return
    seen.add(key)
    messages.append({"at": _ts_iso(ts), "text": text})


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        raise SystemExit(2)
    summary = analyze(Path(sys.argv[1]).expanduser().resolve())
    json.dump(summary, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
