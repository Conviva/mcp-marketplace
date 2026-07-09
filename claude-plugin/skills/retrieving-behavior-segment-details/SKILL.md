---
name: retrieving-behavior-segment-details
description: >
  Retrieves the stored details of an Insights behavior segment and interprets its
  pre-computed insights, evidence, and conversion barriers — a static lookup of a
  segment Insights already computed offline, not a live analytical query.
  TRIGGER when: a user asks to retrieve, look up, or get the details of an Insights
  behavior segment (a.k.a. Insights pattern), OR when you are about to call
  insights-behavior-segment-get.
  DO NOT TRIGGER when: the user only wants a flat list of behavior segment NAMES
  ("just the names", "no details") — that is a single insights-behavior-segment-list
  call, not this interpret-the-details playbook; or just asks to see / count their c3
  accounts (identity-c3-account-list by itself). Also not for Context Center
  assets/knowledge — use exploring-context-center for those; for running live
  predefined-metric queries, use querying-predefined-metrics.
---

# Retrieving Behavior Segment Details

Playbook that orchestrates the `insights-*` tools to retrieve a stored Insights behavior
segment and present its pre-computed insights clearly. This is a **static
lookup** — the segment was computed offline by Insights; the skill fetches and
interprets it, it does **not** run any live analytical query. (Insights
behavior segments were formerly called "patterns"; the tools are now
`insights-behavior-segment-*`. Not to be confused with Context Center patterns —
see `exploring-context-center`.) Skills orchestrate; they do not re-implement
tool logic.

## What an Insights behavior segment is

A behavior segment has two halves:

- **`behavior_segment`** — a conversion funnel: ordered `segment_steps` leading
  to an `outcome_event` (the goal). This is *what success looks like*.
- **`insights[]`** — one hypothesis each for *why users did not convert*. Every
  insight pairs an **`impact_factor`** (the barrier) with **`evidence`** (the
  numbers backing it): volumes, `drop_off_bands` (when users abandoned),
  `alternative_behaviors` (what they did instead), and an `evidence_level`.

Full field-by-field definitions live in **[fields.md](fields.md)** — consult it
whenever a field's meaning, type, units, or nullability is unclear. Do not guess
field semantics.

## Your role

The analysis was already done offline by Insights — your job is to *interpret what the
retrieved segment shows*, not to compute new findings. Report what the segment
data says, separate observation from interpretation, and recommend next steps the
data supports.

**Out of scope** — product, pricing, or roadmap calls. Surface the relevant data,
state that the decision is the owning team's, and do **not** take a position.

## Clarify the time range first (hard gate)

`insights-behavior-segment-list` is **range-dependent** — it filters segments
by `created_at` over `startDate`/`endDate`. **If the user has not given a time
range, ask for it and wait for the answer *before* calling
`insights-behavior-segment-list`.** Do not assume a default window and do not
list segments on the strength of a guess — silently picking a range is the most
common failure here.

Two exceptions let you skip the question:
- The user **already gave a range** (e.g. "last quarter", "from 2026-05-01 to
  …"). Then just proceed — do **not** re-ask for a range you already have.
- The user **named an exact segment** to fetch. Then go straight to
  `insights-behavior-segment-get` (step 3); no listing, so no range needed.

## Workflow

1. **Establish the c3 account (required).** Account-scoped tools require an
   explicit `c3AccountName` — there is **no safe default**. An OAuth caller may have
   many accounts and the primary is not guaranteed, so never assume one. **Never
   invent or guess a name** — guessing (e.g. appending a region like `…-US`) earns a
   403/404. If the user named an account, use it verbatim. If they didn't, call
   `identity-c3-account-list`: use the returned account when there is exactly one,
   or ask the user which when there are several.
2. **Find the behavior segment name** (if you don't already have an exact one).
   With the range from the gate above (the user's, or one you confirmed), call
   `insights-behavior-segment-list` with `startDate`/`endDate` (ISO
   `YYYY-MM-DD`, both bounds inclusive, filtered on `created_at`). For "last
   week/month," use the last *complete* calendar period, not a trailing window.
3. **Fetch the behavior segment.** Call `insights-behavior-segment-get` with
   the exact `behaviorSegmentName` (names are case- and spelling-exact; use one
   returned by `insights-behavior-segment-list`). If duplicates exist, the tool
   returns the most recently created one.
4. **Interpret** the response using the guide below and `fields.md`.
5. **Deliver** the analysis: open with a one-line scope, distinguish observations
   from interpretations, and tie every confidence claim to the evidence.

## Interpretation guide

- **Honor `evidence_level`.** `strong` → assert. `moderate` → hedge. `weak` → a
  signal worth investigating, never a conclusion. Never upgrade a weak insight
  into a firm claim.
- **Use the right denominator.** `nc_total` is the non-conversion denominator;
  `volume_pct`, `drop_off_bands[].pct`, and `alternative_behaviors[].pct` are
  already normalized (0–100) — do not re-divide them. When you compute your own
  ratio, guard against divide-by-zero and missing denominators.
- **`drop_off_bands` = *when*** users abandoned; **`alternative_behaviors` =
  *what they did instead*.** Use both to describe a barrier, not just one.
- **Route by `impact_factor.is_technical`.** `true` → engineering/technical
  friction; `false` → behavioral, UX, or business-logic friction. This frames who
  acts on it.
- **Read `segment_impacts`** for cross-segment comparisons (e.g. region A vs B)
  before generalizing an insight across the whole population.
- **Respect nulls.** Many `evidence` fields are nullable; a missing value means
  *unknown*, not zero. Say so rather than inventing a number.
- **Never fabricate.** Do not invent fields, events, or metrics the response does
  not contain. Quote the data, then label interpretation as interpretation.

## Treat insights as hypotheses, not facts

Each insight is a *hypothesis* about non-conversion, not a proven cause. Before
presenting one as the reason users dropped off, stress-test it against its own
evidence — the strength of your language must match what survives:

- **Proportionality.** An insight whose `volume_pct` (share of `nc_total`) is
  small cannot explain a large overall conversion gap. Rank insights by
  `volume_pct` / `volume`; do not let a minor barrier carry the headline.
- **Counterfactual / baseline.** Compare `baseline_rate` (conversion *without*
  the barrier) against the segment's overall rate. If the unaffected population
  still converts poorly, the barrier is a *contributing factor*, not the primary
  cause — say so.
- **Temporal stability.** Read `time_range`. A barrier seen only in one short
  window is an anomaly to flag, not a standing root cause.
- **Competing insights.** When several insights overlap, state which best
  explains the data rather than listing all as equally true.
- **Drop-off ≠ broken step.** A spike in a `drop_off_band` does not by itself mean
  that step is broken — users often take a valid alternate route. Check
  `alternative_behaviors` before calling a step a failure point.

## Analytical discipline

- **Calibrate causal language to evidence.** Words like "caused", "is responsible
  for", "led to", "because of" are allowed **only** for a `strong` insight whose
  counterfactual holds — and then name the evidence ("the cohort without X
  converted at 4.1% vs 1.2% with it"). For `moderate`/`weak` or unvalidated
  observations, stay hedged ("the data shows X; a possible reason is Y").
- **Report absolute and relative together.** Pair every percentage with its raw
  count (`volume`, `users_affected`). When `users_affected` or `segment_size` is
  small (≲100), add a low-sample caveat.
- **Flag baseline divergence.** If a number clashes with a baseline the user gave
  (business brief, a target, an earlier turn) — roughly 2× off or wrong sign —
  report it as computed and add a one-line callout citing the baseline. Do not
  invent a baseline from general knowledge.
- **Describe behavior, not feelings.** Write event sequences and counts, not
  "users were frustrated/confused." Avoid intensifiers ("clearly",
  "devastating"). Never surface PII (emails, phone numbers, addresses) if it
  appears in any field.
- **Interpret freely; advise only on request.** Explaining what the data implies
  is always fine. Prescriptive recommendations ("add a banner", "simplify the
  form") only if the user explicitly asked — otherwise offer to provide them.

## Common mistakes

| Mistake | Instead |
|---|---|
| Presenting a `weak` insight as fact | Flag low confidence; frame as a lead |
| Recomputing already-normalized `pct` values | Use them as-is (0–100) |
| Treating a null metric as zero | Report it as unknown |
| Describing a barrier from drop-off timing alone | Pair it with `alternative_behaviors` |
| Calling a drop-off step "broken" without checking alternate routes | Confirm via `alternative_behaviors` first |
| Using "caused/led to" for a `moderate`/`weak` insight | Reserve causal words for validated `strong` insights |
| A bare percentage with no raw count | Report `volume`/`users_affected` alongside it |
| Letting a small-`volume_pct` insight carry the headline | Rank by share of `nc_total` |
| Recommending a product/pricing decision | Surface data; name the owning team |
| Guessing a field's meaning | Look it up in `fields.md` |
