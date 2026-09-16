# Astra engagement rules (astra class)

The route label is the astra-class route confirmed at launch. On the Fornace
stack that is exactly `fornace/gpt-6-astra` (distinct from `fornace-astra`;
the user corrected this on 2026-09-15 — do not substitute). On other stacks
it is whatever frontier route the user confirmed; if none was available,
escalation is disabled and these rules apply to whatever the user later
provides. The route is extremely expensive, limited usage. Engage like this:

## When to engage

- Adversarial review of a consequential decision: lane closure, rejection of a
  hypothesis, promotion, root-cause attribution.
- Higher mathematics or deep numerical debugging beyond Max's reach.
- A measured-evidence contradiction the supervisor cannot resolve by reading
  receipts (e.g. two measurements implying different cost models).

## When NOT to engage

- Status, summarization, mechanical checks, implementation, retries.
- Anything a digest or one receipt read answers.
- More than one engagement per decision point without the user's approval.

## Question format (this is what makes it cheap)

One compact, self-contained question, no file access required:

- All numbers, labels and scope inline (measurements, ratios, conditions,
  which implementation they were measured in).
- State the exact claim under review and the acceptance criteria.
- State what a good answer contains (e.g. "confirm or reject each numbered
  claim; identify the cheapest measurement that discriminates").
- Expected answer: ~400 words. Say so.
- One call. No follow-up questions; a second needs user approval.

## After the answer

1. Verify the answer actually addresses the numbered claims; if it restates the
   question or hedges, do not re-ask — treat as no-verdict and fall back to
   your own reasoning or a cheap measurement.
2. Relay the verdict to the worker as one consolidated directive, including
   the cheapest resolving measurement when Astra prescribed one.
3. Record the engagement (question, route, verdict) in the session record or
   the repo's evidence directory.

## Proven pattern (2026-09-15, torchio eugeny-6.1)

A worker wanted to close a rows-16/32 kernel lane citing a 1.15x flattening
measured inside a rows<=8 implementation. Astra rejected the closure: the
flattening was measured in a different envelope, the pilot's own numbers
contradicted the fixed-cost model, and prescribed one interleaved 4/8/8/4
replay as the cheapest discriminator. The replay confirmed the row-dependent
cost was real AND falsified the fixed-residual assumption — both prior claims
were partially wrong. Result: lane stayed open, no unsupported extrapolation.
This is the quality bar: Astra checks reasoning against the numbers, not the
conclusion.
