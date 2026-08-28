# Insights Field Definitions

Complete field reference for the `insights-behavior-segment-*` tools.

Which section applies is decided by the `schema_version` field on every response.

---

## v2 responses (`schema_version: "v2"`)

### `insights-behavior-segment-list` — page envelope

| Field | Type | Nullable | Description |
|---|---|---|---|
| `schema_version` | `"v1"` \| `"v2"` | No | Which section of this file applies. Read it first. |
| `database` | string | No | The Insights database the catalog was read from. |
| `c3AccountName` | string | Yes | The resolved c3 account. Null when the credential names a customer rather than an account. |
| `customerId` | string | No | Numeric Conviva account id that owns these segments. |
| `items` | ListItem[] | No | This page of segments. Empty when the offset is past the end. |
| `offset` | number | No | Zero-based index of the first item returned (the effective value after clamping). |
| `limit` | number | No | Effective page size. A requested value above 200 is clamped to 200 — always read this rather than assuming your requested value was used. |
| `total` | number | No | Total segments in the account, across all pages. |
| `has_more` | boolean | No | Whether another page exists. Page by adding `limit` to `offset` while this is true. |

There is **no** date filter. Do not ask the user for a time range before calling this.

#### ListItem (`items[]`)

| Field | Type | Nullable | Description |
|---|---|---|---|
| `segment_id` | string | No | Stable key (e.g. `"arch_ccc_dlv"`). Pass this to `insights-behavior-segment-get`, `-analyze`, and `-sample-users`. |
| `segment_name` | string | No | Display name (e.g. `"Delivery-Reveal Deliberators"`). |
| `description` | string | Yes | One-line summary of the population. Usually enough to pick the right segment without fetching it. |
| `sub_segment_count` | number | No | How many sub-segments the segment has. Always `0` on a v1 account. |
| `created_at` | ISO 8601 | No | When the segment was defined. |

### `insights-behavior-segment-get` — v2 segment definition

Definitions only. This tool returns **no numbers**; use `insights-behavior-segment-analyze`.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `schema_version` | `"v2"` | No | Discriminator. |
| `customer_id` | string | No | Conviva account that owns the segment. |
| `segment_id` | string | No | Stable key. |
| `segment_name` | string | No | Display name. |
| `segment_description` | string | Yes | Prose description of the population. |
| `timeout` | string | Yes | How long the whole `must` sequence has to complete, as free text — `"30 minutes"`, `"1 hour"`. A device that performs every step but takes longer is **not** in the segment. Quote it as given; do not convert it. |
| `must` | MustEntry[] | No | The ordered journey a device must complete to be in the segment. Empty if not recorded. |
| `must_not` | MustNotEntry[] | No | Exclusions — a device matching any of these is thrown out. Empty if not recorded. |
| `created_at` / `updated_at` | ISO 8601 | No | Row timestamps. |
| `sub_segments` | SubSegment[] | No | Narrower refinements of the same journey. Empty when the segment has none. |

**There is no query field on this response, and its absence is not a degradation.**
The stored analytics queries (`segment_query`, `conversion_query`, and each
sub-segment's own) are internal plumbing between this MCP server and Conviva's
analytics backend — `insights-behavior-segment-analyze` and
`insights-behavior-segment-sample-users` read them straight from storage and run
them for you. They were removed from this response on 2026-08-26. If a user asks
how a segment is implemented, describe it from `must` / `must_not` / `timeout`;
never say you have the query, and never imply one is missing.

#### MustEntry (`must[]`)

| Field | Type | Nullable | Description |
|---|---|---|---|
| `event` | string | No | Internal event name the step matches. An identifier, not something to show the user. |
| `logical` | string | No | The step in words, written for a person — e.g. `"Arrive at the cart with an item in it"`. **Quote this, not `event`.** |
| `step` | number | No | 1-based position in the journey. The steps are ordered; report them in order. |

#### MustNotEntry (`must_not[]`)

| Field | Type | Nullable | Description |
|---|---|---|---|
| `event` | string | No | Internal event name. As above, not for display. |
| `logical` | string | No | What the event is, in words. Quote this. |
| `excluded_window` | string | No | **Where in the journey the event must not occur** — e.g. `"anywhere within segment"`, or `"between Checkout Page View(step 2) and Delivery Scheduling Interaction(step 3)"`. An event banned only between two steps is **not** banned outright; describing it as outright forbidden defines a different, smaller population. Always report the window with the exclusion. |

**This response carries no hypotheses about non-conversion, and that is not a
degradation either.** A segment definition says who is in the population, never
why they failed. When asked why, say so and offer
`insights-behavior-segment-analyze` or a Nexa analysis.

#### SubSegment (`sub_segments[]`)

| Field | Type | Nullable | Description |
|---|---|---|---|
| `sub_segment_id` | string | No | Stable key. Pass to `insights-behavior-segment-analyze` with `scope: "sub_segment"`, or to `insights-behavior-segment-sample-users` as `subSegmentId`. |
| `sub_segment_name` | string | No | Display name. |
| `sub_segment_description` | string | Yes | Prose description of this sub-segment. |
| `timeout` | string | Yes | The sub-segment's own window — same contract as the segment's, and not necessarily the same value. |
| `must` / `must_not` | MustEntry[] / MustNotEntry[] | No | The sub-segment's own journey and exclusions, with their own `step` and `excluded_window` values. Read them; a sub-segment does not inherit the segment's. |

A sub-segment is a **narrower** version of the segment, not a slice of it. Sub-segments overlap; their counts never sum to the segment.

### `insights-behavior-segment-sample-users` — example users

| Field | Type | Nullable | Description |
|---|---|---|---|
| `schema_version` | `"v1"` \| `"v2"` | No | Discriminator. This tool serves both schemas. |
| `segment_id` / `segment_name` / `customer_id` | string | No | The segment the sample came from — always present, even when a sub-segment was sampled. |
| `sub_segment_id` / `sub_segment_name` | string | Yes | The sub-segment sampled, or **both null** when the segment itself was. When they are set, the users belong to that sub-segment, not to the whole segment — name it when reporting them, or you will attribute the users to a larger group than they came from. |
| `time_range` | `{start, end}` | No | The window actually queried, echoed back with its timezone offset. Omitting both request dates samples **yesterday in the account's own timezone** (from its portal settings), resolved server-side — so read the day and the offset off this field rather than assuming the one you asked for. |
| `user_ids` | string[] | No | Up to 200 of the customer's own user identifiers. Opaque strings — GUIDs for one account, digit strings for another. Never parse, sort, or do arithmetic on them. |

One call covers **one** population — the segment, or a single sub-segment. Several
segments or sub-segments means several calls, made **one at a time**: the analytics
backend admits only a couple of queries at a time, so issuing them together
makes them fail with a 503 rather than finish sooner.

Three properties of `user_ids` you must carry into any answer:

- **They are the MOST RECENT matches, not a random or representative sample.**
  The query is ordered newest-first, and on a busy segment the returned users can
  all fall inside the last few minutes of the window. Never infer the segment's
  size, proportions, or characteristics from them — that is what
  `insights-behavior-segment-analyze` is for.
- **Matches with no user id are skipped**, so the list covers identified users
  only.
- **Fewer than 200 is normal.** It means the segment genuinely had fewer matching
  identified users in that window, not that the result was cut short.

### `insights-behavior-segment-analyze` — computed figures

| Field | Type | Nullable | Description |
|---|---|---|---|
| `schema_version` | `"v2"` | No | Discriminator. |
| `segment_id` / `segment_name` / `customer_id` | string | No | Which segment was measured. |
| `time_range` | `{start, end}` | No | The window actually queried, echoed back with its timezone offset. |
| `bot_filtered` | boolean | No | Always `false`. The stored queries carry no bot exclusion and none is added, so **bot traffic is included in every count below**. Disclose this whenever you report one. |
| `conversion` | Conversion | Yes | Present when `scope` was `all` or `conversion`. Null when the segment has no stored conversion query or the query failed — check `errors[]`. |
| `segment` | `{unique_devices}` | Yes | Present when `scope` was `all` or `segment`. |
| `sub_segments` | SubSegmentCount[] | Yes | Present when `scope` was `all` or `sub_segment`. |
| `errors` | PartError[] | No | Parts that did not complete. Empty on a fully successful call. A non-empty array means the response is **partial** — say what is missing rather than presenting the rest as the whole answer. |

#### Conversion (`conversion`)

| Field | Type | Nullable | Description |
|---|---|---|---|
| `denominator` | number | No | Devices that reached the conversion query's qualifying step. |
| `numerator` | number | No | Devices that also reached the converting step. A real `0` means measured zero conversions, not missing data. |
| `conversion_rate` | number | Yes | `numerator / denominator`, between 0 and 1. **Null when the denominator is 0** — report that as "no qualifying devices in this window", never as 0%. |

#### SubSegmentCount (`sub_segments[]`)

| Field | Type | Nullable | Description |
|---|---|---|---|
| `sub_segment_id` / `sub_segment_name` | string | No | Which sub-segment. |
| `unique_devices` | number | Yes | Distinct devices matching this sub-segment. **Null means unknown** (the backend returned nothing for it), not zero. |

#### PartError (`errors[]`)

| Field | Type | Nullable | Description |
|---|---|---|---|
| `part` | `"conversion"` \| `"devices"` | No | Which figure is missing from this response. |
| `message` | string | No | What to tell the user, and what to try instead (usually a shorter window or a narrower `scope`). |

---

## v1 responses (`schema_version: "v1"`)

### BehaviorSegmentResponse (top level)

| Field | Type | Nullable | Description |
|---|---|---|---|
| `customer_id` | string | No | Conviva c3 account ID that owns this behavior segment |
| `behavior_segment` | object | No | Core behavior-segment definition — see BehaviorSegment below |
| `insights` | Insight[] | No | Hypotheses explaining why users are not converting |

---

### BehaviorSegment (`behavior_segment`)

| Field | Type | Nullable | Description |
|---|---|---|---|
| `behavior_segment_id` | string | No | Unique ID for this segment; maps to `pattern_id` in the DB |
| `name` | string | No | Human-readable pattern name |
| `description` | string | Yes | Optional description of what this behavior represents |
| `definition` | object | Yes | Raw JSON criteria defining the segment (internal structure varies) |
| `outcome_event` | object | Yes | The target/goal event users must reach (the conversion). Null means no explicit outcome was defined |
| `segment_steps` | string[] | No | Ordered list of event/action names comprising the funnel journey leading to the outcome |
| `created_at` | ISO 8601 | No | When this pattern was created |
| `updated_at` | ISO 8601 | No | When this pattern was last modified |

---

### Insight (`insights[]`)

Each insight is one hypothesis about why users are **not** reaching the `outcome_event`.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `insight_id` | string | No | Unique ID for this hypothesis |
| `behavior_segment_id` | string | No | ID of the parent behavior segment |
| `time_range` | TimeWindow | Yes | Analysis period — see TimeWindow below |
| `title` | string | No | Short label for this hypothesis |
| `text` | string | No | Full description of the non-conversion hypothesis |
| `conversion` | string | No | Arrow-separated string showing the intended journey (e.g. `"login → browse → purchase"`) |
| `impact_factor` | ImpactFactor | No | What is blocking conversion — see ImpactFactor below |
| `evidence` | Evidence | No | Quantitative metrics supporting this hypothesis — see Evidence below |
| `segment_impacts` | SegmentImpact[] | No | Cross-segment comparisons of this insight's impact |

---

### ImpactFactor (`impact_factor`)

Describes the nature of the conversion barrier.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `title` | string | No | Name of the barrier or friction point |
| `description` | string | No | Explanation of how this factor prevents conversion |
| `alternative_behavior` | string | Yes | Name of the alternative action users take instead of converting |
| `barrier_type` | string | Yes | Category of the barrier (e.g. technical, UX, business logic) |
| `is_technical` | boolean | No | `true` = technical/engineering issue; `false` = behavioral, UX, or business-logic issue |

---

### Evidence (`evidence`)

Quantitative data backing the hypothesis.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `evidence_level` | enum | Yes | Confidence rating: `"strong"`, `"moderate"`, or `"weak"`. Null if unset |
| `volume` | number | Yes | Raw count of non-conversion events matching this insight |
| `volume_pct` | number | Yes | Percentage of total non-conversions explained by this insight (0–100) |
| `users_affected` | number | Yes | Distinct users who encountered this barrier |
| `baseline_rate` | number | Yes | Conversion rate in the absence of this barrier (decimal 0–1) |
| `segment_size` | number | Yes | Total users in the analyzed segment |
| `nc_total` | number | Yes | Total non-conversion count in the segment (denominator for percentages) |
| `conversion_time_window_minutes` | number | Yes | How many minutes users have to complete the full journey before being counted as non-converted |
| `drop_off_bands` | DropOffBand[] | No | Time-bucketed breakdown of when users dropped off — see DropOffBand below |
| `alternative_behaviors` | AlternativeBehavior[] | No | What users did instead of converting — see AlternativeBehavior below |

#### evidence_level values

| Value | Meaning |
|---|---|
| `"strong"` | High statistical confidence in this hypothesis |
| `"moderate"` | Medium confidence; pattern is present but may have noise |
| `"weak"` | Low confidence; treat as a signal worth investigating, not a conclusion |

---

### DropOffBand (`drop_off_bands[]`)

Shows *when* in time users abandoned the funnel.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `band` | number | No | Time period index (0 = first bucket, 1 = second, etc.) |
| `name` | string | No | Human-readable label for the bucket (e.g. `"Day 1"`, `"Day 2–7"`) |
| `nc_count` | number | No | Non-conversions that dropped off during this bucket |
| `pct` | number | No | Percentage of `nc_total` that dropped off in this bucket (0–100) |

---

### AlternativeBehavior (`alternative_behaviors[]`)

Shows what users did *instead* of converting.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `behavior` | string | No | Event or action name the user performed instead |
| `nc_count` | number | No | Non-conversion count where this alternative was observed |
| `pct` | number | No | Percentage of `nc_total` exhibiting this alternative (0–100) |
| `is_global` | boolean | No | `true` = seen across all segments; absent = specific to one segment |

---

### SegmentImpact (`segment_impacts[]`)

Cross-segment comparison for this insight.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `cross_segment_comparison` | string | No | Text comparing this insight's impact across segments (e.g. `"80% impact in US vs 45% in EU"`) |

---

### TimeWindow (`time_range`)

| Field | Type | Nullable | Description |
|---|---|---|---|
| `start` | ISO 8601 date | No | Start of the analysis window |
| `end` | ISO 8601 date | No | End of the analysis window |
