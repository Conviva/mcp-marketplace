---
name: querying-predefined-metrics
description: >
  The primary flow for answering "what is this metric?" questions: runs a
  predefined Conviva Context Center metric by its id over a date range,
  optionally broken down by dimension ids — using asset ids only, never raw SQL
  or a raw query payload — and returns real values.
  TRIGGER when: a user asks for the value, trend, or breakdown of a named or
  known predefined metric (e.g. "show Successful Payment Count last week",
  "break Payments down by Payment Method", "what's our checkout conversion
  trend?"), OR when you are about to call metric-query-run.
  DO NOT TRIGGER when: the user only wants to find, define, or fetch a metric/asset
  (including "I have id m_… — just get its definition" — that is a direct
  context-center-asset-get (assetType: metric) via exploring-context-center, not a
  run over a date range); is retrieving an Insights behavior segment (use
  retrieving-behavior-segment-details); or hands you raw SQL / a raw query payload to
  execute (this skill deliberately does not do that).
---

# Querying Predefined Metrics

This is the dominant way to answer a metric question in Conviva DPI MCP. It orchestrates
the `context-center-*` and `metric-query-*` tools to answer "what is this metric,
and optionally how does it split by X?" — by **asset id only**. Skills
orchestrate; they do not re-implement tool logic.

## The core constraint: ids, not SQL

Conviva metrics are defined by raw query machinery (mapped events, fields,
patterns, aggregations). Assembling that payload correctly takes deep query
expertise an agent does not have, so **this flow never constructs or accepts raw
SQL or a raw query payload.** You supply *ids* for things a human already defined:

- a **metric id** (`m_*`) — the predefined metric to run,
- optionally a **pattern id** (`p_*`) — only to disambiguate which pattern the
  metric aggregates,
- optionally **dimension ids** (`dimension_*`) — to break the metric down by.

If you cannot map the user's request to a predefined metric id, do **not** invent
a query. Surface what predefined metrics exist and ask the user to pick.

## Clarify the time range first (hard gate)

`metric-query-run` is **range-dependent** — every run needs a `startDate`/`endDate`
window. **If the user has not given a time range, ask for it and wait for the
answer *before* running the metric.** Do not assume a default window. You may
resolve the metric/dimension ids first (that needs no range), but **do not call
`metric-query-run` until you have a range the user gave or confirmed.** If the user
**already gave a range**, do not re-ask — just proceed. (Resolving the window to a
timezone-aware datetime is step 4 below.)

## Workflow

1. **Establish the c3 account (required).** Account-scoped tools require an
   explicit `c3AccountName` — there is **no safe default**. An OAuth caller may have
   many accounts and the primary is not guaranteed, so never assume one. **Never
   invent or guess a name** — guessing (e.g. appending a region like `…-US`) earns a
   403/404. If the user named an account, use it verbatim. If they didn't, call
   `identity-c3-account-list`: use the returned account when there is exactly one,
   or ask the user which when there are several.
2. **Resolve the metric to an id — by tool call, not from memory.** If you don't
   already have an `m_*` id **from a tool call in this conversation**, use the
   **exploring-context-center** skill to find it: search the knowledge layer by
   meaning, then confirm with `context-center-asset-get` (assetType: metric). Do
   **not** reuse a remembered/assumed id (or its pattern/dimension ids) without
   resolving it via the tools — a stale or wrong id silently runs the wrong metric.
   Confirm the match with the user when the name is fuzzy rather than guessing.
3. **Resolve any breakdown to dimension ids.** If the user wants a split ("by
   platform", "by payment method"), find each dimension's `dimension_*` id the
   same way (`context-center-asset-list` with assetType: dimension / knowledge
   search). Pass the ids, not free-text dimension names.
4. **Resolve the date window to timezone-aware datetimes.** `startDate`/`endDate`
   are ISO 8601 date-times **with a timezone offset**, to second precision (e.g.
   `2026-06-01T00:00:00-07:00`), **not** bare `YYYY-MM-DD` dates. The same local
   day maps to a different UTC cutoff per timezone, so the offset is required:
   - **Interpret the user's day/time in the customer's local timezone.** A bare
     day (or "last week/month") means that local day spanning `00:00:00`–`23:59:59`
     local time; a clock time they give is local wall-clock time.
   - **Emit the offset.** Express the window as ISO 8601 carrying the customer's
     offset (e.g. `…-07:00`) — or the equivalent `…Z`. End-of-day is `23:59:59`
     local, not the next midnight.
   - **"last week/month" → the last *complete* calendar period** in the customer's
     local timezone (not a trailing window), unless the user says otherwise.
   - **If you don't know the customer's timezone, ask** (or state the assumption)
     rather than silently defaulting to UTC — the cutoff depends on it.
   - Confirm the resolved window with the user when the request was vague.
5. **Run it.** Call `metric-query-run` with `metricId`, the timezone-aware
   `startDate`/`endDate` from step 4, and any `patternId` / `groupByDimensionIds`.
   Nothing else — no SQL, no payload.
6. **Interpret the result — only real returned values.** Report the value(s)
   with their date window and any breakdown; pair percentages with raw counts; do
   not overstate precision. **If `metric-query-run` errors** (e.g. a 422 "could
   not run metric …", a 5xx, or a timeout), you have **no data** — **never
   fabricate, estimate, or fill in a number, table, or trend.** Say the run failed,
   report what failed (metric id + window/breakdown), then either retry with a
   corrected window/breakdown or fall back to `nexa-analyze` with
   `fallbackReason: metric_query_failed`. A made-up number presented as real is the
   worst possible outcome — worse than admitting the run failed.

## Fallback to open-ended analysis (with a reason)

A predefined metric cannot answer everything. Fall back to **`nexa-analyze`**
only when the request genuinely does not map to a predefined metric, and you MUST
pass a `fallbackReason`:

- `no_matching_metric` — no predefined metric corresponds to what they asked.
- `unsupported_breakdown` — the metric exists but the requested split has no
  predefined dimension.
- `open_ended_analysis` — a "why did X change / what's driving Y" question that
  needs investigation, not a single number.
- `multi_metric_or_comparison` — needs several metrics correlated / compared in a
  way a single metric run can't express.
- `metric_query_failed` — resolution succeeded but `metric-query-run` failed and
  the user's question is still answerable by analysis.
- `other` — anything else; explain in the message.

When you fall back, tell the user the answer came from open-ended Nexa analysis,
not a predefined metric. **Do not default to `nexa-analyze`** when a predefined
metric fits — resolve and run the metric first.

## Notes & gotchas

- **No raw SQL — ever.** If the user pastes SQL or a raw query payload, explain
  this flow runs *predefined* metrics by id and offer to help find the right
  metric id instead.
- **Drill-down reuses ids.** When the user refines ("now break that down by …"),
  reuse the same `metricId` and window and just add `groupByDimensionIds` — don't
  re-resolve the metric from scratch.
- **A failed run is not a number.** `metric-query-run` runs live against Conviva's
  analytics backend, which can return an error (422 rejected payload, 5xx, timeout). When
  it does, there is no value to report — do not invent one, do not "estimate from
  what you'd expect," do not reuse a number from an earlier turn as if it were
  this window's result. Surface the failure and fall back per step 6.
