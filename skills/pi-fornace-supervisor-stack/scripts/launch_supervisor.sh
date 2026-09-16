#!/bin/zsh
# launch_supervisor.sh — spawn the supervisor surface of the pi fornace
# supervisor stack over a worker pi session, in a sibling cmux surface.
#
# Usage: launch_supervisor.sh <worker-session-ref> [goal text] [options]
#   worker-session-ref : full/partial session UUID, 8-char sidebar id, or .jsonl path
#   goal               : free text of the worker's goal
#
# Options:
#   --yes              accept proposed model defaults without prompting
#   --flash <model>    flash-class digest model (cheap, fast)
#   --max <model>      max-class supervisor model (strong, cheaper than frontier)
#   --astra <model>    astra-class escalation route (best frontier available)
#   --list-only        show the proposed stack and live checks, then exit
#
# Model classes (defaults are proposed from the user's OWN pi catalog, live
# checked; nothing is assumed to exist):
#   flash class  cheapest fast model for digest recaps (flash/fast/mini/haiku)
#   max class    strong current-generation model, cheaper than the frontier
#                tier (max/sonnet/pro class)
#   astra class  the user's best frontier route for rare adversarial review
#                (astra/opus/ultra class). May be absent: escalation is then
#                disabled with a warning, not silently substituted.
#
# Requires: cmux, pi. Flash digests additionally need the gateway env the
# chosen flash route uses (e.g. $MANTICE_API_KEY for mantice routes).

set -eu
SKILL="$HOME/.pi/agent/skills/pi-fornace-supervisor-stack"

worker_ref=""
goal=""
flash="" max="" astra=""
list_only=0 assume_yes=0
args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes)        assume_yes=1 ;;
    --flash)      flash="$2"; shift ;;
    --max)        max="$2"; shift ;;
    --astra)      astra="$2"; shift ;;
    --list-only)  list_only=1 ;;
    -*)           echo "unknown option: $1" >&2; exit 2 ;;
    *)            if [[ -z "$worker_ref" ]]; then worker_ref="$1"
                  elif [[ -z "$goal" ]]; then goal="$1"
                  else goal="$goal $1"; fi ;;
  esac
  shift
done
[[ -n "$worker_ref" ]] || { echo "usage: launch_supervisor.sh <worker-session-ref> [goal] [--yes|--flash M|--max M|--astra M|--list-only]"; exit 2; }

# ---------------------------------------------------------------- model stack
# Live catalog from the user's pi (never assume our routes exist).
catalog=$(pi --list-models 2>/dev/null | awk 'NF>=3 && $2!~/^(commands|categories)$/ {print $1"/"$2}')

propose() {  # propose <class> <patterns...> -> first catalog match
  local class="$1"; shift
  local pat m
  for pat in "$@"; do
    m=$(printf '%s\n' $catalog | grep -iE "$pat" | grep -viE 'lite|mini-|embedding|audio|image|vision|live|mt-|character|coder|math' \
         | { grep -E '^(fornace|mantice)/' || true; } | head -1)
    [[ -z "$m" ]] && m=$(printf '%s\n' $catalog | grep -iE "$pat" | grep -viE 'lite|mini-|embedding|audio|image|vision|live|mt-|character|coder|math' | head -1)
    [[ -n "$m" ]] && { echo "$m"; return; }
  done
  echo ""
}

# Frontier-class proposal informed by Artificial Analysis Intelligence Index
# v4.3 (checked 2026-09-15): top intelligence Claude Fable 5.1 (53) and
# GPT-6 Astra (53); best open weights GLM-5.3 max (45), Kimi K3 (44),
# GLM-5.3-Flash (42). Prefer fable > gpt-6-astra > astra > opus/ultra.
[[ -z "$flash"  ]] && flash=$(propose flash  'fornace-flash|glm-5\.3-flash' 'flash' 'fast|haiku|mini' 'turbo')
[[ -z "$max"    ]] && max=$(propose   max    'fornace-max|glm-5\.3($|[^-])' 'sonnet|claude-.*sonnet' 'gemini-3\.[5-9]($|[^.])' 'gpt-6($|[^0-9])' 'kimi-k3' 'pro' 'fornace-reasoning')
[[ -z "$astra"  ]] && astra=$(propose astra  'fable' 'gpt-6-astra' 'astra' 'opus|ultra' 'o[1-9]($|-)' 'gpt-6\.5|frontier')

live_check() {  # live_check <provider/route> -> ok|fail reason
  local m="$1" model="${1#*/}"  # strip provider prefix -> gateway model id
  if [[ -z "$m" ]]; then echo "absent"; return; fi
  local base="${MANTICE_BASE_URL:-https://llm.fornace.net/v1}"
  if [[ -n "${MANTICE_API_KEY:-}" ]] \
     && curl -sS --max-time 20 -o /dev/null -w '%{http_code}' \
          -H "Authorization: Bearer $MANTICE_API_KEY" \
          "$base/chat/completions" -H "Content-Type: application/json" \
          -d "{\"model\":\"$model\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":1}" \
          | grep -q '^2'; then
    echo "ok"
  else
    # non-mantice route: fall back to pi's own auth check
    if pi auth check --model "$m" --json 2>/dev/null | grep -q '"status":"ready"'; then
      echo "ok"
    else
      echo "unverified(probe-failed)"
    fi
  fi
}

flash_st=$(live_check "$flash"); max_st=$(live_check "$max"); astra_st=$(live_check "$astra")

cat <<EOF
=== pi fornace supervisor stack: proposed models (live from your pi catalog) ===
  flash class (digest recaps):  ${flash:-<none found>} [$flash_st]
  max class   (supervisor):     ${max:-<none found>} [$max_st]
  astra class (escalation):     ${astra:-<none found in your catalog>} [$astra_st]
EOF
if [[ -z "$flash" || -z "$max" ]]; then
  echo "ERROR: flash and max class models are required. Pass --flash/--max explicitly."
  exit 1
fi
if [[ "$flash_st" == ok && "$max_st" == ok ]]; then
  echo "  live check: both required routes authenticated."
else
  echo "  WARNING: a live check did not fully pass; supervisor may fail at runtime."
fi
if [[ -z "$astra" ]]; then
  echo "  NOTE: no astra-class route found; adversarial escalation will be DISABLED."
  echo "        Pass --astra <route> to enable, or ignore if you don't have a frontier route."
fi

if [[ $list_only -eq 1 ]]; then exit 0; fi

# Interactive confirmation when we have a tty and no --yes.
if [[ -t 0 && $assume_yes -eq 0 ]]; then
  printf "Use this stack? [Y/n] or enter overrides as: flash=<m> max=<m> astra=<m> "
  read -r answer
  answer="${answer:-Y}"
  case "$answer" in
    [Yy]*) : ;;
    *)
      for kv in ${(s: :)answer}; do
        case "$kv" in
          flash=*)  flash="${kv#flash=}" ;;
          max=*)    max="${kv#max=}" ;;
          astra=*)  astra="${kv#astra=}" ;;
        esac
      done
      echo "overridden: flash=$flash max=$max astra=${astra:-<disabled>}"
      ;;
  esac
fi

export PI_SUP_FLASH_MODEL="$flash"
export PI_SUP_MAX_MODEL="$max"
export PI_SUP_ASTRA_MODEL="$astra"

# ---------------------------------------------------------------- resolve worker
session_file=$(python3 - "$worker_ref" <<'EOF'
import sys
from pathlib import Path
ref = sys.argv[1].strip()
p = Path(ref)
if p.exists() and p.suffix == ".jsonl":
    print(p); raise SystemExit
root = Path.home()/".pi/agent/sessions"
m = [f for f in root.glob("*/*.jsonl") if ref in f.name]
if not m: sys.exit(f"ERROR: no session matching {ref!r}")
print(max(m, key=lambda f: f.stat().st_mtime))
EOF
)
worker_id8=$(basename "$session_file" | grep -oE '[0-9a-f]{8}-' | head -1 | tr -d '-')
worker_full=$(basename "$session_file" .jsonl)
worker_full=${worker_full#*_}   # strip timestamp prefix -> full uuid

surface=$(cmux top --all --processes --flat 2>/dev/null | grep "pi\\.$worker_full" | head -1 | awk -F'\t' '{print $1}' || true)

# ---------------------------------------------------------------- launch
new_surface=$(cmux new-surface --type terminal --focus false 2>&1 | grep -oE 'surface:[0-9]+' | head -1)
[[ -n "$new_surface" ]] || { echo "ERROR: could not create surface"; exit 1; }

sup_id="sup-${worker_id8}"
cmux send --surface "$new_surface" \
  "pi --model $max --name Supervisor --session-id $sup_id --append-system-prompt $SKILL/references/supervisor-charter.md"
cmux send-key --surface "$new_surface" enter

sleep 6

goal_line=""
[[ -n "$goal" ]] && goal_line=" GOAL: $goal."

astra_line="Astra escalation DISABLED (no route available)."
[[ -n "$astra" ]] && astra_line="Astra escalation route: $astra (class rules still apply: references/astra-engagement.md)."

read -r -d '' mission <<EOF || true
MISSION. Worker pi session $worker_full (file $session_file, surface ${surface:-verify-me})$goal_line
Your charter is in your system prompt. Model stack confirmed live at launch:
- digest model (flash class): $flash
- escalation: $astra_line
Startup sequence:
1) Verify the worker surface per ~/.pi/agent/guides/cmux-agent-communication.md.
2) Confirm the worker goal from pi-codex-goal digest events; if absent, ask me.
3) Create ONE bounded monitor watcher on the session file, then go idle.
4) Digest with: python3 $SKILL/scripts/worker_digest.py --session $worker_full --summarize --model $flash
5) If an astra route is named above, use exactly that route label for escalation subagents.
Engage only at decision points. I will talk to you, not the worker.
EOF

cmux send --surface "$new_surface" "$mission"
cmux send-key --surface "$new_surface" enter

echo "SUPERVISOR LAUNCHED: surface=$new_surface session=$sup_id"
echo "  supervisor model: $max"
echo "  digest model:     $flash"
echo "  astra route:      ${astra:-<disabled>}"
echo "  worker:           $worker_full (surface ${surface:-unverified})"
echo "Next: read $new_surface to confirm the mission was accepted."
