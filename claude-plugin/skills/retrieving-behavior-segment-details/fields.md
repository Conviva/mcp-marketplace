# Insights Field Definitions

Complete field reference for `insights-behavior-segment-get` responses.

---

## BehaviorSegmentResponse (top level)

| Field | Type | Nullable | Description |
|---|---|---|---|
| `customer_id` | string | No | Conviva c3 account ID that owns this behavior segment |
| `behavior_segment` | object | No | Core behavior-segment definition — see BehaviorSegment below |
| `insights` | Insight[] | No | Hypotheses explaining why users are not converting |

---

## BehaviorSegment (`behavior_segment`)

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

## Insight (`insights[]`)

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

## ImpactFactor (`impact_factor`)

Describes the nature of the conversion barrier.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `title` | string | No | Name of the barrier or friction point |
| `description` | string | No | Explanation of how this factor prevents conversion |
| `alternative_behavior` | string | Yes | Name of the alternative action users take instead of converting |
| `barrier_type` | string | Yes | Category of the barrier (e.g. technical, UX, business logic) |
| `is_technical` | boolean | No | `true` = technical/engineering issue; `false` = behavioral, UX, or business-logic issue |

---

## Evidence (`evidence`)

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

### evidence_level values

| Value | Meaning |
|---|---|
| `"strong"` | High statistical confidence in this hypothesis |
| `"moderate"` | Medium confidence; pattern is present but may have noise |
| `"weak"` | Low confidence; treat as a signal worth investigating, not a conclusion |

---

## DropOffBand (`drop_off_bands[]`)

Shows *when* in time users abandoned the funnel.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `band` | number | No | Time period index (0 = first bucket, 1 = second, etc.) |
| `name` | string | No | Human-readable label for the bucket (e.g. `"Day 1"`, `"Day 2–7"`) |
| `nc_count` | number | No | Non-conversions that dropped off during this bucket |
| `pct` | number | No | Percentage of `nc_total` that dropped off in this bucket (0–100) |

---

## AlternativeBehavior (`alternative_behaviors[]`)

Shows what users did *instead* of converting.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `behavior` | string | No | Event or action name the user performed instead |
| `nc_count` | number | No | Non-conversion count where this alternative was observed |
| `pct` | number | No | Percentage of `nc_total` exhibiting this alternative (0–100) |
| `is_global` | boolean | No | `true` = seen across all segments; absent = specific to one segment |

---

## SegmentImpact (`segment_impacts[]`)

Cross-segment comparison for this insight.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `cross_segment_comparison` | string | No | Text comparing this insight's impact across segments (e.g. `"80% impact in US vs 45% in EU"`) |

---

## TimeWindow (`time_range`)

| Field | Type | Nullable | Description |
|---|---|---|---|
| `start` | ISO 8601 date | No | Start of the analysis window |
| `end` | ISO 8601 date | No | End of the analysis window |
