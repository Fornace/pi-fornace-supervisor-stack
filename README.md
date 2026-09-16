# pi-fornace-supervisor-stack

A [pi](https://github.com/earendil-works/pi-coding-agent) skill that launches a
**sibling cmux supervisor session** over a working pi session, so a long-running
worker agent can be driven to its goal without babysitting and without being
interrupted by the user.

Proven on a real multi-hour supervision case (torchio eugeny-6.1, 2026-09-15):
the supervisor followed the worker through digests and two frontier-model
escalations, and caught a real reasoning error in an experiment-lane closure.

## Architecture

```
USER --talks to--> SUPERVISOR surface (pi, max-class model, full tools)
                     |  charter + engagement rules from this skill
                     |  watches worker session file (one bounded watcher, no polling)
                     +- cheap layer: worker_digest.py
                     |    mechanical JSONL digest (new bytes only) + flash-class recap
                     +- escalation: astra-class frontier route
                     |    one compact self-contained question, ~400-word answer
                     +- steering: cmux send to worker surface (verified, decision words)
WORKER surface (pi, any model) -- implements, receipts, commits
```

Token economics: raw transcript reads are paid in supervisor input tokens, so
the supervisor never tails. `worker_digest.py` keeps a byte-offset state file,
reads only new records, skips thinking blocks, and asks a flash-class model
for a DECISIONS / FILES+RECEIPTS / STATE / BLOCKERS / NEXT recap. Between
watcher pings the supervisor costs nothing.

## Install

```bash
pi install npm:pi-fornace-supervisor-stack
```

## Use

Give a worker pi session a goal, then from any pi session:

```bash
~/.pi/agent/skills/pi-fornace-supervisor-stack/scripts/launch_supervisor.sh \
  <worker-session-ref> "goal text"
```

The launcher proposes a model stack live from YOUR pi catalog
(`pi --list-models` + a gateway auth probe), asks for confirmation
(`--yes`, `--flash/--max/--astra` overrides, `--list-only` to preview):

- **flash class** (digest recaps): cheapest fast model
- **max class** (the supervisor): strong model, cheaper than frontier
- **astra class** (rare adversarial escalation): your best frontier route;
  disabled with a warning if none exists, never silently substituted

Frontier priority is informed by the Artificial Analysis Intelligence Index
(re-check when the frontier shifts).

Then talk to the supervisor surface, not the worker. Milestone reports and
decision questions arrive there.

### Standalone digest

Asked "what is the other session doing?" in any pi session: the skill routes
to `worker_digest.py --session <ref> --summarize` instead of opening the
session transcript.

## Requirements

- pi, cmux
- credentials for whatever routes the confirmed stack uses
  (for the Fornace stack: `MANTICE_API_KEY` for the flash digests)

## Files

```
skills/pi-fornace-supervisor-stack/
  SKILL.md                          orchestration design and usage
  references/supervisor-charter.md  supervisor system prompt
  references/astra-engagement.md    frontier escalation rules
  scripts/launch_supervisor.sh      interactive launcher
  scripts/worker_digest.py          token-lean session digest (also standalone)
```
