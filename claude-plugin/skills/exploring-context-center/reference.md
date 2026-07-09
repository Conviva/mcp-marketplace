# Context Center Reference

Companion to `exploring-context-center`. Asset taxonomy, the knowledge↔asset
links, and the response shapes the orchestration relies on.

---

## Asset types → hydrate tool

`categories` on a knowledge entry (and `source_info.detail.asset_type`) are drawn
from this set. Each maps to an `assetType` value on `context-center-asset-get` /
`context-center-asset-list`:

| Asset type | `assetType` value | Notes |
|---|---|---|
| `pattern` | `pattern` | `critical_events` lists its ordered critical-event ids |
| `metric` | `metric` | `definition.calculated_with` points at its pattern id |
| `critical_event` | `critical-event` | the raw-event matcher; its raw match SQL (`expression`) is hidden — use name + description |
| `dimension` | `dimension` | |
| `segment` | `segment` | |
| `template` | `template` | |
| `insights_finder` | `insights-finder` | **list-only** — `context-center-asset-list` only, no get-by-id route upstream |
| `dashboard` | — | **knowledge-only here**; no asset get tool (removed from this MCP) |
| `customer_brief` | — | knowledge-only; a free-text brief about the customer, no asset |

`context-center-asset-get` fetches one asset by id + `assetType`;
`context-center-asset-list` pages through all assets of an `assetType`
(returns `{ items, pagination }`). Neither tool expands or inlines a related
asset's full record — follow an id field with its own `context-center-asset-get`
call to fetch a relative.

---

## Decomposition hierarchy

Assets nest. To go from a high-level number down to what matches raw events:

```
metric (m_*)            aggregates →  pattern (p_*)
pattern (p_*)           sequences →   critical_event (ce_*)   [+ referred_metrics]
critical_event (ce_*)   matches →     raw events  (raw match SQL hidden)
```

- A metric's `definition.calculated_with` / `referred` points at its pattern.
- A pattern's `critical_events: [ce_*]` lists its steps; fetch each with its own
  `context-center-asset-get` call (`assetType: critical-event`) to get its name,
  description, and validity. The raw match SQL (`expression`) comes back as a
  `[hidden …]` placeholder.
- A pattern also exposes `referred_metrics: [m_*]` (which metrics use it).
- The chain bottoms out at the critical event's description — the raw SQL is
  intentionally not exposed, so describe a matcher by what it represents, not by
  reconstructing its query.

---

## Knowledge entry shape (`context-center-nexa-*`)

| Field | Meaning |
|---|---|
| `knowledge_id` (`k_*`) | business id of the knowledge entry |
| `summary` | LLM-generated `name: … | what: … | how: …` description (the embedded/searchable text) |
| `source_info.type` | `"asset"` for asset-derived knowledge |
| `source_info.detail.asset_id` | the asset this summarizes (the handle into the asset layer) |
| `source_info.detail.asset_type` | which `assetType` to pass to `context-center-asset-get` (see map above) |
| `categories` / `terms` | asset-type tags used by semantic search |
| `score` | semantic-search similarity (0–1); **null** outside semantic search |
| `is_active` | only active entries are returned by search/list by default |

---

## The two cross-links

| Direction | Field | Tool to follow it |
|---|---|---|
| knowledge → asset | `source_info.detail.asset_id` (+ `asset_type`) | `context-center-asset-get` |
| asset → knowledge | `knowledge_id` on the asset | `context-center-nexa-knowledge-get` |

The link is 1:1: every asset has one knowledge summary, and every asset-derived
knowledge entry points back at exactly one asset.

---

## Worked example (illustrative — ids are placeholders)

- Semantic search `query: "<concept in your words>"`, `categories: ["pattern"]` →
  a knowledge hit with a `score` and a summary
  (`"name: … | what: … | how: …"`), plus
  `source_info.detail = { asset_id: "p_<id>", asset_type: "pattern" }`.
- Hydrate `context-center-asset-get assetType=pattern assetId=p_<id>` →
  `critical_events: ["ce_<id>"]`, `referred_metrics: ["m_<id>"]`. A follow-up
  `context-center-asset-get assetType=critical-event assetId=ce_<id>` returns its
  name/description/validity — its `expression` is returned as a `[hidden …]`
  placeholder, not the raw query.
- Reverse: an asset that carries `knowledge_id: "k_<id>"` →
  `context-center-nexa-knowledge-get k_<id>` returns its summary.
