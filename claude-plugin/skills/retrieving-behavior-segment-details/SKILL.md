---
name: retrieving-behavior-segment-details
description: >
  Retrieves and interprets an Insights behavior segment — its journey criteria
  and its sub-segments — and computes live conversion, device counts and example
  users when numbers are asked for.
  TRIGGER when: the user says "segment" in any form (behavior / audience / user
  segment) and wants to list, look up, analyze, or sample users from one; OR you
  are about to call any insights-behavior-segment-* tool; OR a Context Center
  knowledge hit has asset_type behavior_segment.
  DO NOT TRIGGER when: the user wants a Context Center pattern, metric, dimension
  or critical event (use exploring-context-center), a live predefined-metric
  query (use querying-predefined-metrics), or just their c3 account list.
---

# Retrieving Behavior Segment Details

Playbook that orchestrates the `insights-*` tools to retrieve a stored Insights behavior
segment and interpret it. Every account runs one of two storage schemas — check the
response's `schema_version` before doing anything else; see "Two response shapes" below.
`insights-behavior-segment-get` is always a **static lookup**: the definition it returns
was stored ahead of time, not computed live. On a v2 account, live conversion and device
counts are a separate step — call `insights-behavior-segment-analyze` only when the user
actually asks for numbers. (Insights behavior segments were formerly called "patterns";
the tools are now `insights-behavior-segment-*`. Not to be confused with Context Center
patterns — see `exploring-context-center`.) Skills orchestrate; they do not re-implement
tool logic.

## What an Insights behavior segment is

What a segment contains depends on `schema_version` (full definitions in `fields.md`):

- **v1** — a behavior segment has two halves: **`behavior_segment`**, a conversion funnel
  of ordered `segment_steps` leading to an `outcome_event` (the goal); and **`insights[]`**,
  one pre-computed hypothesis each for *why users did not convert*, pairing an
  **`impact_factor`** (the barrier) with **`evidence`** (volumes, `drop_off_bands`,
  `alternative_behaviors`, and an `evidence_level`).
- **v2** — a segment is described by **`must`** / **`must_not`** (the journey a device has
  to complete, and what excludes it) and zero or more **`sub_segments`** (narrower
  refinements of that same journey). No numbers are stored; compute them with
  `insights-behavior-segment-analyze` only when asked.

Full field-by-field definitions live in **[fields.md](fields.md)** — consult it
whenever a field's meaning, type, units, or nullability is unclear. Do not guess
field semantics.

## Your role

On a v1 account the analysis was already done offline by Insights — your job is to
*interpret what the retrieved segment shows*, not to compute new findings. On a v2
account the definition is stored but the numbers are not: compute them yourself with
`insights-behavior-segment-analyze` when the user asks, then interpret what came back.
Either way, report what the data says, separate observation from interpretation, and
recommend next steps the data supports.

These three rules hold regardless of `schema_version`:

- **Describe behavior, not feelings.** Write event sequences and counts, not "users
  were frustrated/confused." Avoid intensifiers ("clearly", "devastating"). Never
  surface PII (emails, phone numbers, addresses) if it appears in any field.
- **Interpret freely; advise only on request.** Explaining what the data implies is
  always fine. Prescriptive recommendations ("add a banner", "simplify the form")
  only if the user explicitly asked — otherwise offer to provide them.
- **Flag baseline divergence.** If a number clashes with a baseline the user gave
  (business brief, a target, an earlier turn) — roughly 2× off or wrong sign —
  report it as computed and add a one-line callout citing the baseline. Do not
  invent a baseline from general knowledge.

**Out of scope** — product, pricing, or roadmap calls. Surface the relevant data,
state that the decision is the owning team's, and do **not** take a position.

## Two response shapes — branch on `schema_version`

Every `insights-*` response carries a `schema_version` field.

- **`"v2"`** — the current schema. The segment is described in business terms and
  has **sub-segments**. Live numbers come only from
  `insights-behavior-segment-analyze`; example users from
  `insights-behavior-segment-sample-users`.
- **`"v1"`** — the legacy schema. The segment is a single funnel with
  pre-computed `insights[]` carrying `evidence`, `evidence_level`,
  `drop_off_bands` and friends.

Read the field before interpreting anything. The two shapes share almost no
field names, and applying v1's rules to a v2 response invents numbers that are
not there.

## Workflow

1. **Establish the c3 account (often automatic).** `c3AccountName` is optional on
   account-scoped tools: if the user named an account, pass it verbatim; otherwise
   just omit it — when your login can access exactly one c3 account, the tool
   resolves it for you, no extra call needed. Only when a login can access several
   accounts does the call fail; that error names every available account, so ask
   the user which one and retry with that exact name (`identity-c3-account-list`
   also lists the options up front if you want them before calling anything).
   **Never invent or guess a name** — guessing (e.g. appending a region like
   `…-US`) earns a 403/404.
2. **Find the segment.** Call `insights-behavior-segment-list`. It lists the whole
   catalog — **do not ask the user for a time range before calling it**; it has no
   date parameters. Each item carries `segment_id`, `segment_name`, `description`
   and `sub_segment_count`, which is usually enough to pick the right one without
   fetching anything. Page with `offset`/`limit` when `has_more` is true.
3. **Fetch the definition.** Call `insights-behavior-segment-get` with
   `segmentId` (the `segment_id` from the list — preferred) or
   `segmentName`.
4. **Get numbers only if asked.** `get` returns definitions, never counts. When the
   user asks how big a segment is, how it converts, or which sub-segment performs best,
   call `insights-behavior-segment-analyze` with the `segmentId` and a time window
   (ISO 8601 **with a timezone offset** — see `querying-predefined-metrics` for
   resolving a day to a customer-local range). Narrow `scope` when only one figure
   is needed; `all` over a long window can take minutes.
5. **Sample example users one population at a time.**
   `insights-behavior-segment-sample-users` returns user ids for **one** segment *or*
   **one** sub-segment per call. When the user asks for several segments, or for several
   sub-segments, call it **sequentially**: one call, wait for the response, then the next.
   Never put two of these calls in the same turn, and never run one while an
   `insights-behavior-segment-analyze` call is still in flight — the analytics backend
   admits only a couple of queries at a time, so parallel calls do not finish sooner,
   they make each other fail with a 503. If the user gave **no** time range, do not ask
   for one — omit `startDate`/`endDate` and the tool samples **yesterday in the account's
   own timezone**, read from the c3 account's portal settings. Report the window from the
   response's `time_range`: it carries that offset (e.g. `-04:00`, `+08:00`) and is the
   window the query actually ran against, so quote it rather than saying "yesterday" and
   leaving the day ambiguous. (Both dates or neither; one alone is a 422.)
6. **Deliver** the analysis: open with a one-line scope, distinguish observations
   from interpretations, and tie every confidence claim to the evidence.

## Interpreting a v2 response

- **The unit is devices, not people.** Every count is
  `COUNT(DISTINCT device)`. One person on a phone and a laptop counts twice.
  Say "devices" — never silently translate to "users" or "customers".
- **Bots are included.** `insights-behavior-segment-analyze` returns
  `bot_filtered: false` because it runs the stored query's own filters unmodified —
  nothing is added to exclude bots. Disclose this whenever you report a count.
- **Sub-segments overlap — never sum them.** A sub-segment is a *refinement* of
  the segment (extra steps, extra exclusions), so one device can match several
  sub-segments. Measured example: a segment of 189,120 devices where a single
  sub-segment alone accounts for 150,114. Reporting sub-segments as shares of the
  segment, or adding them up, produces numbers that are simply wrong. Compare
  sub-segments to each other and to the segment, one at a time.
- **A definition says who, never why.** A v2 response carries no stored
  hypotheses about non-conversion. When the user asks *why* a population did not
  convert, say the definition does not answer it, and offer what does —
  `insights-behavior-segment-analyze` for the numbers, or a Nexa analysis for the
  journey. Do not reconstruct a cause from `must_not`: those are the exclusions
  that define the population, not reasons anyone failed.
- **`must` / `must_not` are the segment in words.** `must[]` is the ordered
  journey a device has to complete, each entry numbered by `step`; `must_not[]`
  are the exclusions that throw a device out, each carrying an
  `excluded_window` saying *where* in the journey the event must not occur
  (e.g. `"anywhere within segment"`, or `"between Checkout Page View(step 2) and
  Delivery Scheduling Interaction(step 3)"`). The window matters — an event
  banned only between two steps is not banned outright, and saying so would
  describe a different population.
- **Report the `logical` text, not the `event` name.** Each entry has both:
  `event` is the internal event identifier, `logical` is the sentence written for
  a human ("Arrive at the cart with an item in it"). Use `logical`; mention
  `event` only if the user asks what is being matched.
- **`timeout` bounds the whole journey.** The segment and every sub-segment carry a
  `timeout` such as `"30 minutes"` or `"1 hour"` — the window the entire `must`
  sequence has to complete within. A device that does every step but takes
  longer is not in the segment. State it whenever you describe the journey; it is
  free text, so quote it as given rather than converting it.
- **Sub-segments have their own `sub_segment_description`, `timeout`, `must` and
  `must_not`.** A sub-segment is not just a name — read its own criteria rather
  than assuming it inherits the segment's.
- **The analytics queries are not in the response.** v2 responses contain no SQL
  and no `*_query` field. If the user asks how a segment is implemented, describe
  it from `must`/`must_not`/`timeout`; do not claim to have the query.
- **A `null` count means unknown, not zero.** The analyze tool reports `null`
  when the backend returned nothing for that population.
- **Read `errors[]`.** A partial response is normal. Name what is missing rather
  than presenting the remainder as the whole answer.
- **`conversion_rate` is `null` when the denominator is 0.** Do not render that
  as 0%.
- **Never fabricate.** Do not invent fields, events, or metrics the response does
  not contain.

### v1 responses

Everything below applies only when `schema_version` is `"v1"` — the legacy shape
(`behavior_segment` + `insights[]`, `evidence_level`, `drop_off_bands`, `baseline_rate`,
`nc_total`, and friends). None of these fields exist on a v2 response; do not apply
this guidance there.

**Interpretation guide**

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

**Treat insights as hypotheses, not facts**

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

**Analytical discipline**

- **Calibrate causal language to evidence.** Words like "caused", "is responsible
  for", "led to", "because of" are allowed **only** for a `strong` insight whose
  counterfactual holds — and then name the evidence ("the cohort without X
  converted at 4.1% vs 1.2% with it"). For `moderate`/`weak` or unvalidated
  observations, stay hedged ("the data shows X; a possible reason is Y").
- **Report absolute and relative together.** Pair every percentage with its raw
  count (`volume`, `users_affected`). When `users_affected` or `segment_size` is
  small (≲100), add a low-sample caveat.

## Common mistakes

### v2

| Mistake | Instead |
|---|---|
| Asking the user for a time range before listing segments | The list tool has no date filter — just call it |
| Summing sub-segment counts, or reporting them as shares of the segment | Sub-segments overlap; compare them individually |
| Saying "users" or "customers" for a device count | Say "devices", and note one person can be several |
| Reporting a count without noting bots are included | Disclose `bot_filtered: false` |
| Reading a cause of non-conversion out of a v2 definition | It carries none; compute one, or say it is not there |
| Describing a `must_not` event as banned outright | Read its `excluded_window` — most are banned only between two steps |
| Describing the journey without its `timeout` | The whole `must` sequence must finish inside it, e.g. "30 minutes" |
| Quoting the internal `event` name to the user | Report the `logical` sentence; it is written for people |
| Claiming to have the segment's query or SQL | v2 responses carry no query — describe it from `must`/`must_not` |
| Calling `insights-behavior-segment-get` expecting numbers | `get` is definitions only; numbers come from `-analyze` |
| Firing several `-sample-users` calls in one turn to cover several segments/sub-segments | One call per population, sequentially — parallel calls 503 each other |
| Asking the user for a time range before sampling users | Omit both dates — the tool samples the account's own yesterday and echoes the window in `time_range` |
| Running `scope: "all"` when the user asked one question | Narrow the scope; a full run can take minutes |
| Applying v1's `evidence_level` / `nc_total` rules to a v2 response | Branch on `schema_version` first |

### v1

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
