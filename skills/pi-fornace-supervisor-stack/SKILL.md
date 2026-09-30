---
name: pi-fornace-supervisor-stack
description: "Launch a sibling cmux supervisor Pi session over a working Pi session: flash-digest monitoring instead of transcript tailing, decision-point-only engagement, fornace/gpt-6-astra escalation rules, and user-facing buffering so the worker is never interrupted by the user. Also the tool for any cross-session question: when the user asks what another pi session/surface is doing, its status, progress, decisions, or latest activity, use worker_digest.py for a cheap flash recap of that session instead of opening its transcript. Use when the user assigns a goal to a worker session and asks for supervision, a second brain, continuation ownership, or a supervisor like the torchio eugeny-6.1 one."
---

# pi fornace supervisor stack

Three-layer token economics for supervising an autonomous worker pi session.
Proven on torchio eugeny-6.1 (2026-09-15): the supervisor reviewed an
implementation session for hours using digests and two Astra engagements,
caught a real lane-closure reasoning error, and never once wasted the
worker's context on status questions.

## Architecture

Model classes, not fixed routes. Defaults are proposed from the USER'S OWN
live pi catalog at launch and confirmed interactively; nothing is assumed.
Proposal priority is informed by the Artificial Analysis Intelligence Index
v4.3 (checked 2026-09-15): top intelligence Claude Fable 5.1 (53) and
GPT-6 Astra (53); best open weights GLM-5.3 max (45), Kimi K3 (44),
GLM-5.3-Flash (42). Re-check
<https://artificialanalysis.ai/models> when the frontier shifts.

- **flash class** (digest recaps): cheapest fast model that still summarizes
  decisions accurately. Fornace default `fornace-flash` (GLM-5.3-Flash, AA
  top-3 open weights at 42).
- **max class** (the supervisor itself): strong current-generation model,
  cheaper than the frontier tier. Fornace default `mantice/fornace-max`
  (GLM-5.3 max effort, best open weights at 45 — near-frontier quality at a
  fraction of frontier cost).
- **astra class** (escalation): the user's best frontier route for rare
  adversarial review. Fornace default `fornace/gpt-6-astra` (AA top
  intelligence at 53). If the user's catalog has no frontier route,
  escalation is disabled with a warning, never silently substituted.

```
USER ──talks to──> SUPERVISOR surface (pi, mantice/fornace-max, full tools)
                     │  charter: references/supervisor-charter.md
                     │  watches worker session file (monitor, no polling)
                     ├─ cheap layer: scripts/worker_digest.py
                     │    mechanical JSONL digest + fornace-flash recap
                     │    (DECISIONS / FILES+RECEIPTS / STATE / BLOCKERS / NEXT)
                     ├─ escalation: fornace/gpt-6-astra subagent
                     │    one compact self-contained question, ~400-word answer
                     │    rules: references/astra-engagement.md
                     └─ steering: cmux send to worker surface (verified,
                        one consolidated message, decision words only)
WORKER surface (pi, any model) ── implements, receipts, commits
```

Why each choice:

- **Sibling cmux surface, not a subagent**: the supervisor must be
  user-facing (interactive), hold watchers, and steer another live session.
  Subagents are fire-and-forget and cannot do cmux steering of a peer.
- **Flash digest, not tailing**: raw transcript reads are paid in supervisor
  input tokens every ping. A flash-class model is near-free and smart enough
  to point at decisions, files and recaps. The digest script reads only NEW
  bytes (state-file offset), never re-reads history, skips thinking blocks
  and large records.
- **Watcher, not polling**: one bounded `monitor` on the worker session file;
  supervisor idles between pings. Zero tokens while the worker works.
- **Decision-point engagement**: every cmux message interrupts or loads the
  worker's context. Status curiosity is never a reason to message the worker.
- **User-facing buffering**: the user questions the supervisor; the supervisor
  absorbs noise and relays only decision-relevant asks to the worker.

## When to use / not use

Use: an autonomous worker session has a goal (persistent pi goal or an
explicit task) and the user wants it driven to completion without babysitting
or interruptions.

Also use (standalone digest, no supervision launch): the user asks what
another pi session or surface is doing — "what's the eugeny session up to?",
"status of the worker", "summarize the other surface's progress". Run
`worker_digest.py --session <ref> --summarize`, optionally after
`rm /tmp/pi-sup-digest-<id8>.state` to force a fresh window. Never open
another session's raw transcript for a status question.

Do not use: for short interactive tasks (supervision costs more than the
task), for sub-10-minute jobs, or over a user-owned orchestrator (the monitor
skill's orchestrator rule still applies: observe, never steer).

## Launch procedure

Prerequisites: cmux, pi. Flash digests need whatever credentials the chosen
flash route uses (for mantice routes: `$MANTICE_API_KEY`).

```bash
# 1. The worker session already has its goal (user set it there).
# 2. From any pi session (usually the one the user is talking to):
~/.pi/agent/skills/pi-fornace-supervisor-stack/scripts/launch_supervisor.sh \
  <worker-session-ref> "goal text"
```

The launcher proposes a model stack live from the user's pi catalog
(`pi --list-models` + `pi auth check` per route), shows it with check
status, and asks for confirmation on a tty (or takes `--yes`/
`--flash/--max/--astra` overrides non-interactively; `--list-only` previews
without launching). If no astra-class route exists, escalation is disabled
with a note, not substituted.

It then resolves the worker session file, locates the worker surface, creates
a sibling terminal surface, launches pi there with the charter as appended
system prompt (full tools, stable session id `sup-<worker8>`), and delivers
the mission message including the confirmed model stack. Verify by reading
the new surface:

```bash
cmux read-screen --surface <new-surface> --lines 40
```

Confirm the supervisor accepted the mission and created its watcher. If the
worker surface could not be resolved automatically, tell the supervisor the
surface ref directly; it re-verifies anyway (surface indices shift).

## Operating the supervisor (for the user-facing session)

- The user talks to the supervisor surface from now on. Milestone reports and
  decision questions arrive there.
- If the invoking session must relay something urgent (safety, spend
  authority, goal change), message the supervisor surface the same way; the
  supervisor owns worker-safe delivery.
- End of life: when the goal completes or the user calls it off, tell the
  supervisor to write a final report and close its watcher
  (`monitor_kill`), then close the surface with `cmux close-surface`.

## Digest tool (supervisor's window; also usable standalone)

```bash
python3 ~/.pi/agent/skills/pi-fornace-supervisor-stack/scripts/worker_digest.py \
  --session <ref> --summarize [--model <flash-class-route>] [--full] [--json]
```

- `--summarize`: flash recap of only the NEW records since last call.
- `--full`: also print the mechanical digest lines.
- First run on a large session: starts from the last 256KB (recent
  activity) plus a mechanical full-file scan of GOAL/SUMMARY history, so a
  mid-flight supervisor sees current state and the goal without paying for
  the whole transcript.
- Summary requests send `reasoning_effort: "none"` and reject reported reasoning tokens or empty content. Verify the live route supports reasoning off: an always-on model is incompatible with this summary contract, even if the gateway normalizes off to minimal.
- Failed summaries exit nonzero and leave the byte cursor unchanged. State keys hash the resolved session path so named sessions do not share a date-prefix cursor.
- `NO NEW RECORDS` when idle. State in `/tmp/pi-sup-digest-<pathhash16>.state`.
- Standalone use: cheap progress check on any worker session without opening
  its transcript, from any session or shell.

## Astra engagement (supervisor escalation)

Route label: the astra-class route confirmed at launch (Fornace:
exactly `fornace/gpt-6-astra`, distinct from `fornace-astra`; corrected
2026-09-15 — do not substitute). One compact, self-contained question with
all numbers inline, no file dependencies, expected ~400-word answer, one call
per decision point. Full rules and the proven pattern:
[references/astra-engagement.md](references/astra-engagement.md).

## Hard rules inherited by every layer

- Never steer an unverified surface; never interrupt a worker turn except for
  safety, authorization or expiring decisions (one `escape` only).
- Explicit decision words: GRANTED / DENIED / WAIT.
- Paid work (GPU, external spend) requires explicit user authority.
- Failed receipts are evidence; direct the next repair from them, never an
  unchanged rerun.
- No gate, threshold or contract relaxation without the user's approval.
