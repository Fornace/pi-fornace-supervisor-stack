#!/usr/bin/env python3
"""worker_digest.py — token-lean window into a worker pi session.

Mechanically digests NEW records of a pi session JSONL (never re-reads old
bytes; offset kept in a state file), then optionally summarizes the digest
with fornace-flash via the Mantice gateway. This replaces raw tailing of
worker transcripts by expensive supervisor models.

Usage:
  worker_digest.py --session <path-or-id-prefix> [--state <file>]
                   [--summarize] [--json] [--full]

  --session   session file path, full/partial session UUID, 8-char sidebar id,
              or a pi-identity short id (see pi-session-id list)
  --state     state file (default /tmp/pi-sup-digest-<id8>.state)
  --summarize call fornace-flash for a DECISIONS/FILES/STATE/BLOCKERS/NEXT recap
  --json      print recap as JSON
  --full      also print the raw mechanical digest (default: recap only when
              summarizing, digest only otherwise)

Output: compact digest lines "TYPE role tool | one-line summary" and, with
--summarize, a flash recap. Exit 0 with "NO NEW RECORDS" when nothing changed.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

SESSIONS_ROOT = Path.home() / ".pi/agent/sessions"
IDENTITY_REGISTRY = Path.home() / ".pi" / "agent" / "state" / "pi-sessions.json"
MAX_DIGEST_BYTES = 24000  # cap fed to flash
LARGE_RECORD = 120_000  # bytes; summarize existence, skip extraction
DEFAULT_FLASH = os.environ.get("PI_SUP_FLASH_MODEL", "fornace-flash")
FIRST_RUN_RECENT_WINDOW = 256 * 1024  # first run on big sessions: last N bytes
FIRST_RUN_BIG = 512 * 1024


def slug_to_session_id(ref: str) -> str | None:
    """A pi-identity short id resolves to the session it is bound to."""
    try:
        registry = json.loads(IDENTITY_REGISTRY.read_text())
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as error:
        sys.exit(f"ERROR: unreadable identity registry at {IDENTITY_REGISTRY}: {error}")
    for session_id, identity in registry.get("sessions", {}).items():
        if identity.get("slug") == ref:
            return session_id
    return None


def resolve_session(ref: str) -> Path:
    ref = ref.strip()
    p = Path(ref)
    if p.exists() and p.suffix == ".jsonl":
        return p
    # a short id is an exact identity; anything else is a filename search
    ref = slug_to_session_id(ref) or ref
    matches = []
    for f in SESSIONS_ROOT.glob("*/*.jsonl"):
        name = f.name
        if ref in name:
            matches.append(f)
    if not matches:
        sys.exit(f"ERROR: no session file matching {ref!r} under {SESSIONS_ROOT}")
    return max(matches, key=lambda f: f.stat().st_mtime)


def one_line(s: str, n: int = 160) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    return s[:n]


def summarize_tool_args(args) -> str:
    try:
        if isinstance(args, str):
            return one_line(args)
        parts = []
        for k, v in args.items():
            if isinstance(v, str):
                parts.append(f"{k}={one_line(v, 90)}")
        return " ".join(parts) if parts else one_line(json.dumps(args), 160)
    except Exception:
        return "?"


def digest_record(rec: dict) -> str | None:
    t = rec.get("type")
    if t == "message":
        m = rec.get("message", {})
        role = m.get("role", "?")
        content = m.get("content")
        out = []
        if isinstance(content, str):
            if content.strip():
                out.append(f"MSG {role} | {one_line(content, 200)}")
        elif isinstance(content, list):
            for c in content:
                ct = c.get("type")
                if ct == "text":
                    out.append(f"MSG {role} | {one_line(c.get('text',''), 200)}")
                elif ct == "thinking":
                    continue  # never pay for worker thinking
                elif ct == "toolCall":
                    out.append(f"CALL {role} {c.get('name','?')} | {summarize_tool_args(c.get('arguments', {}))}")
        return "\n".join(out) if out else None
    if t == "custom":
        ct = rec.get("customType", "?")
        if ct == "fornace.work.v1":
            d = rec.get("data", {})
            evt = d.get("type", "")
            if "goal" in d or evt.startswith("goal_"):
                g = d.get("goal") or {}
                status = g.get("status", "?")
                rev = f" rev {g.get('revision')}" if g.get("revision") else ""
                used = f" {g.get('tokensUsed', 0):,} tok" if g.get("tokensUsed") else ""
                return f"GOAL {status}{rev}{used} | {one_line(str(g.get('objective','')), 200)}"
            if evt.startswith("todo_") or "item" in d:
                item = d.get("item", {})
                lane = item.get("lane", "?").upper()
                title = item.get("title", "")
                rej = f" [rejected #{item['rejection']['challengeCount']}]" if item.get("rejection") else ""
                return f"TODO {lane}{rej} | {one_line(title, 160)}"
            if evt == "event_batch":
                return f"WORK batch ({len(d.get('events', []))} events)"
            return f"WORK {evt}"
        if ct == "pi-codex-goal":
            d = rec.get("data", {})
            g = d.get("goal", {})
            return f"GOAL {g.get('status','?')} | {one_line(str(g.get('objective','')), 200)}"
        if ct == "monitor":
            return f"MONITOR | {one_line(str(rec.get('content','')), 140)}"
        return f"CUSTOM {ct} | {one_line(json.dumps(rec.get('data',{})), 120)}"
    if t == "summary":
        return f"SUMMARY | {one_line(rec.get('summary',''), 200)}"
    return None


def flash_summarize(digest: str, model: str, as_json: bool) -> str:
    base = os.environ.get("MANTICE_BASE_URL", "https://llm.fornace.net/v1")
    key = os.environ.get("MANTICE_API_KEY")
    if not key:
        sys.exit("ERROR: MANTICE_API_KEY not set; cannot summarize (run without --summarize)")
    system = (
        "You summarize a coding-agent worker session digest. Be terse and factual. "
        "Output sections exactly: DECISIONS (numbered, who decided what), FILES+RECEIPTS "
        "(paths and commit hashes mentioned), STATE (what is done/running/blocked), "
        "BLOCKERS, NEXT (likely next decision point). "
        + ("Output strict JSON with those keys." if as_json else "Max 15 lines total.")
    )
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": digest[:MAX_DIGEST_BYTES]},
        ],
        "reasoning_effort": "none",
        "max_tokens": 700,
        "temperature": 0,
    }).encode()
    req = urllib.request.Request(
        f"{base.rstrip('/')}/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    reasoning = data.get("usage", {}).get("completion_tokens_details", {}).get("reasoning_tokens", 0)
    if reasoning and reasoning > 0:
        raise RuntimeError(f"Summary route {data.get('model')} violated no-reasoning request ({reasoning} tokens)")
    choices = data.get("choices") or []
    choice = choices[0] if choices else {}
    content = choice.get("message", {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(f"Empty summary response (model={data.get('model')}, "
                           f"finish={choice.get('finish_reason')}, reasoning_tokens={reasoning})")
    return content.strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--state")
    ap.add_argument("--summarize", action="store_true")
    ap.add_argument("--model", default=DEFAULT_FLASH,
                    help=f"summarizer model, any gateway route (default {DEFAULT_FLASH})")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()

    f = resolve_session(args.session)
    # Named session filenames can start with a date, so a UUID regex collides.
    id8 = hashlib.sha256(str(f.resolve()).encode()).hexdigest()[:16]
    state_file = Path(args.state or f"/tmp/pi-sup-digest-{id8}.state")

    size = f.stat().st_size
    first_run = not state_file.exists()
    offset = int(state_file.read_text().strip()) if state_file.exists() else 0
    if offset > size:  # session file truncated/replaced
        offset = 0
    if first_run and size > FIRST_RUN_BIG:
        offset = size - FIRST_RUN_RECENT_WINDOW  # recent window + goal scan below

    lines = []
    with f.open("rb") as fh:
        fh.seek(offset)
        raw = fh.read()
        new_offset = offset + len(raw)

    if not raw:
        # still advance nothing; report idle
        print("NO NEW RECORDS")
        return

    for blob in raw.split(b"\n"):
        if not blob.strip():
            continue
        if len(blob) > LARGE_RECORD:
            lines.append(f"RECORD | [large {len(blob)}B skipped]")
            continue
        try:
            rec = json.loads(blob)
        except Exception:
            lines.append("RECORD | [unparsable line]")
            continue
        d = digest_record(rec)
        if d:
            lines.append(d)

    digest = "\n".join(lines) or "(new bytes but no digestible records)"

    # On first run over a big session, also surface the worker's GOAL history
    # (mechanical scan of the whole file, tiny output, no flash cost).
    if first_run and size > FIRST_RUN_BIG:
        goals = []
        with f.open("rb") as fh:
            for blob in fh:
                if b"fornace.work.v1" not in blob and b"pi-codex-goal" not in blob and b'"summary"' not in blob:
                    continue
                if len(blob) > LARGE_RECORD:
                    continue
                try:
                    rec = json.loads(blob)
                except Exception:
                    continue
                d = digest_record(rec)
                if d and (d.startswith("GOAL") or d.startswith("TODO") or d.startswith("WORK") or d.startswith("SUMMARY")):
                    goals.append(d)
        if goals:
            digest = "GOAL/TODO/SUMMARY HISTORY (full scan):\n" + "\n".join(goals[-15:]) + "\n\nRECENT ACTIVITY:\n" + digest

    recap = None
    if args.summarize:
        try:
            recap = flash_summarize(digest, args.model, args.json)
        except Exception as error:
            print(f"FLASH SUMMARY FAILED: {error}", file=sys.stderr)
            sys.exit(1)  # Keep the cursor: a failed recap has not consumed records.

    state_file.write_text(str(new_offset))

    if args.summarize:
        if recap:
            print(recap)
        if args.full:
            print("\n=== RAW DIGEST ===")
            print(digest)
    else:
        print(digest)
    print(f"\n[new: {new_offset - offset}B, total {size}B, state={state_file}]", file=sys.stderr)


if __name__ == "__main__":
    main()
