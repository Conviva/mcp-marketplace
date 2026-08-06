---
name: finding-replay-candidates
description: >
  Turns a behavioral question ("who hit the checkout error yesterday?") into
  concrete Conviva clientIds, each with its session window, replay
  availability, and device, by asking Nexa which devices match.
  TRIGGER when: a user wants to watch, inspect, or analyze a session replay or
    session recording (also called cohort replay) but has NO clientId — they
    describe a behavior, error, or drop-off instead; or they ask which users or
    devices did something and want their ids; OR when
    analyzing-session-replays needs a clientId and none was supplied.
  DO NOT TRIGGER when: the user already has a clientId — use
    analyzing-session-replays, just asking for the time window if it is
    missing; or they have a replayId and want only its metadata or a Conviva UI
    deeplink (the session-replay-get / session-replay-deeplink surface); or
    they want only aggregate numbers, a trend, or a breakdown with no intent to
    reach an individual session — that is querying-predefined-metrics.
---

# Finding Replay Candidates

Answers "which real user should I watch?" — the missing first leg of the
session-replay flow. It turns a behavioral question into concrete clientIds by
asking Nexa, presents them as a candidate table, and hands the chosen one to
`analyzing-session-replays`. Skills orchestrate; tools stay primitive.

## Why this skill exists

A clientId is a dotted numeric device id
(`1142762076.1464912069.1432685179.529581154`). Customers never know one, and
there is no list-all-clients tool. The only path to a clientId is Nexa's
matched-devices query — and Nexa runs it **only when the question explicitly asks
for client IDs**. Rewriting the user's question so that it does is this skill's
whole job.

## The prompt contract (the part that actually matters)

Nexa answers in free text. A question phrased as an aggregate ("how many users
failed checkout?") comes back as counts with no ids — that is the number-one
failure of this flow.

Send `nexa-analyze` a `userMessage` that satisfies all four:

1. Explicitly ask for the **client IDs** of the matching devices.
2. Ask for each session's **start and end time**.
3. Ask **whether a session replay exists** for each.
4. Ask for a **markdown table with fixed columns**, so extraction is mechanical.

**Submit ONE request covering the user's whole window.** Nexa's internal
matched-devices query is capped at one day per call, but that is Nexa's problem,
not yours — its own instructions tell it to split a longer range into
consecutive one-day calls inside a single analysis. Never fan out into one
`nexa-analyze` job per day: each job costs a separate run of up to ~30 minutes
and returns a fragment you then have to stitch. Ask for the full range once.

Template — swap in the account, behavior, and window; keep the structure:

```
For account ACCOUNT, find the end-user devices that BEHAVIOR between START and END.
List the matching client IDs. For each one give: client ID, session start time,
session end time (both ISO 8601 with timezone offset), whether a session replay
exists, and the platform/device. Return them as a markdown table with exactly
these columns: clientId | startTime | endTime | hasSessionReplay | device.
```

Call `nexa-analyze` with `fallbackReason: no_matching_metric` — no predefined
metric can ever return a clientId, so that is the honest attribution.

The number of devices Nexa returns is decided upstream. Do not ask for "top 3";
you will get what you get.

## Workflow

1. **Pin the window.** You need a start and an end with a timezone. Multi-day
   ranges are fine — pass them through whole. Do not guess a timezone; if the
   user gave a bare local date, ask which timezone they mean.
2. **Submit once.** Call `nexa-analyze` with the rewritten `userMessage`, the
   `c3AccountName`, and `fallbackReason: no_matching_metric`. It returns a
   `jobId` immediately. **One job for the whole window** — never one per day.
3. **Poll.** Call `nexa-analyze-result` with that `jobId` roughly every 30
   seconds until `status` is `succeeded` or `failed`. It can take up to ~30
   minutes — say so once, then poll quietly. Do not narrate every poll.
4. **Extract the candidates** from the answer text: clientId, start, end,
   has-replay, device.
5. **Present, then STOP.** Show the table. Mark clearly which rows have a
   session replay — **only those can be downloaded**. Ask which one to analyze.
   Do not start downloading on your own: download-and-parse is expensive, and
   this pause is the point.
6. **Hand off.** Once the user picks, use `analyzing-session-replays` with that
   clientId and the window built below.

## Building the window for the handoff

Nexa reports pattern-match times, not blob boundaries. Pad **2 minutes on each
side** of the reported start/end, and pass ISO 8601 **with a timezone offset**
(e.g. `2026-07-16T17:00:00Z` or `2026-07-16T10:00:00-07:00`).

This window is **per candidate session**, not the analysis range — one row's
start/end plus padding, so it is minutes long even when the search covered
weeks. `session-replay-blob-list` caps it at 24 hours, which a single session
will not approach. Do not confuse this cap with anything about how wide a
question you may ask Nexa.

## When it does not work

- **No client IDs in the answer.** Retry **once** with a more explicit ask —
  name the four requirements and the columns again. Still nothing → say so
  plainly and ask the user for a clientId. **Never invent one**, and never go
  looking in ClickHouse or GCS.
- **Job `failed` or `not_found`.** Report it and offer to resubmit. Do not
  fabricate findings.
- **Every candidate has no session replay.** Say that no replay exists for this
  behavior in this window, and suggest a different window or behavior. Do
  **not** call `session-replay-blob-list` anyway — it will 404.
- **Nexa says the range was too wide, or reports partial coverage.** Take it at
  its word and relay the limitation. Do not "fix" it by re-submitting the range
  as several per-day jobs — that multiplies cost without adding coverage.

A failed discovery is not a finding. If you could not get ids, say that — do not
describe a session you never saw.

## Privacy

Candidate rows are device and user identifiers. Show only what the user needs in
order to choose. Do not dump the full Nexa answer if it carries more, and do not
surface emails or other PII.
