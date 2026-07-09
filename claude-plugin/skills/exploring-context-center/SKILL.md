---
name: exploring-context-center
description: >
  Finds Conviva Context Center assets by meaning or topic, then hydrates the full
  structured definition — search the knowledge layer first, then fetch the asset.
  TRIGGER when: a user wants to find/understand a pattern, metric, dimension,
  segment, or critical event but does not have its id, asks "what does an account
  track about X", or wants to explore a customer's Context Center; OR when you are
  about to call context-center-nexa-semantic-search.
  DO NOT TRIGGER when: the user already has an exact asset id and just wants it
  fetched (e.g. "fetch pattern p_…", "get the definition of metric m_…") — there
  is nothing to discover, so call context-center-asset-get directly with the
  matching assetType; or is retrieving an Insights behavior segment (use
  retrieving-behavior-segment-details — Insights behavior segments are a different
  system).
---

# Exploring Context Center

Playbook that orchestrates the `context-center-*` tools to go from a fuzzy
question ("what does this account track about playback errors?") to the exact
structured asset definition. Skills orchestrate; they do not re-implement tool
logic.

## The two layers (read this first)

Context Center exposes the same underlying objects through **two distinct,
1:1-linked layers**. They are *not* interchangeable — pick by what you have:

- **Knowledge** (`context-center-nexa-*`) — an LLM-generated natural-language
  *summary* of each asset (`name / what / how`), tagged by `categories` (which
  are the asset types) and embedded for search. This is the **only** layer you
  can search by meaning. A knowledge entry carries
  `source_info.detail.asset_id` + `asset_type` pointing back to its asset.
- **Assets** (`context-center-asset-get` / `context-center-asset-list`) — the
  authoritative *structured definition*: a pattern's `critical_events`, a
  critical event's match definition, a metric's `referred` pattern, `definition`,
  validity. This is the **only** layer with the real machinery. An asset carries
  `knowledge_id` pointing back to its summary. **Raw match SQL is intentionally
  hidden** from these responses (a critical event's `expression`, a mapped
  event's `sql` come back as a `[hidden …]` placeholder) — reason about assets by
  id, name, and description, not by the underlying query definition.

So: **search knowledge to discover, fetch assets to define.** See
**[reference.md](reference.md)** for the asset taxonomy, the decomposition
hierarchy, and the exact response shapes — consult it whenever a field, link, or
asset-type → tool mapping is unclear. Do not guess.

## Grounding — never answer from memory (hard rule)

Every asset fact you report — an id, a name, a definition, the steps a pattern
sequences, a critical event's meaning, a count, or even that an asset **exists** —
**must come from a tool call you made in THIS conversation.** Discover by meaning
with `context-center-nexa-semantic-search`, then hydrate by id with
`context-center-asset-get`, and only then state what you found.

- **Do not state an asset id, definition, or count from memory, prior context, or
  a plausible guess** — not even one that "looks right" (e.g. asserting `m_…` or
  its pattern/critical-events without fetching them). A remembered or guessed id
  may be wrong, stale, or belong to another account, and presenting it as fact is
  a fabrication.
- **Do not skip the discovery step because you think you already know the answer.**
  If the user asks by meaning ("what do we track about X", "what counts as a
  checkout"), you must actually run `nexa-semantic-search` (and the `asset-get`
  chain), even if a likely id comes to mind. Answering first and offering to
  "verify later" is not acceptable — call the tool first, answer from its result.
- If a required tool returns nothing (or is unavailable), say so — do not fill the
  gap with remembered/assumed detail.

## Workflow

1. **Establish the c3 account (required).** Account-scoped tools require an
   explicit `c3AccountName` — there is **no safe default**. An OAuth caller may have
   many accounts and the primary is not guaranteed, so never assume one. **Never
   invent or guess a name** — guessing (e.g. appending a region like `…-US`) earns a
   403/404. If the user named an account, use it verbatim. If they didn't, call
   `identity-c3-account-list`: use the returned account when there is exactly one,
   or ask the user which when there are several.
2. **Discover via knowledge.** You usually start without an id.
   - **By meaning / phrasing, or to browse a category** → `context-center-nexa-semantic-search`
     with a free-text `query` (vector ANN, returns a `score`; rank by it). This is
     the only discovery path — there is no plain browse tool. Scope it with
     `categories` (see `context-center-nexa-categories-list` if unsure of valid
     values) and optionally add `terms` for exact substrings alongside the
     semantic query.
   - Scope `categories` to the asset type you want (`pattern`, `metric`,
     `dimension`, `segment`, `critical_event`, `dashboard`, `customer_brief`).
3. **Read the pointer.** Each knowledge hit's `source_info.detail` gives
   `asset_id` + `asset_type`. That is your handle into the asset layer.
4. **Hydrate the asset.** Call `context-center-asset-get` with that `asset_type`
   (see reference.md for the map) and the `asset_id` — e.g. `assetType: pattern`,
   `assetType: metric`, `assetType: critical-event`, `assetType: dimension`,
   `assetType: segment`. This returns the real definition the summary only
   describes.
5. **Follow related ids if needed.** Assets nest: **metric → pattern →
   critical_event**. A hydrated asset's own id fields point at its relatives —
   e.g. a metric's `definition.calculated_with` names its pattern id, a
   pattern's `critical_events` list its critical-event ids. Fetch each with its
   own `context-center-asset-get` call; this is a plain follow-the-id lookup, not
   a promoted or automatic expansion. The chain stops at the critical event's
   description — its raw match SQL is hidden, so don't try to read or
   reconstruct it.
6. **Reverse lookup when you start from an asset.** If you already have an asset
   and want its summary, read its `knowledge_id` and call
   `context-center-nexa-knowledge-get`.

## Choosing the search tool

| You have… | Use |
|---|---|
| A concept in the user's own words, or an exact category/keyword | `context-center-nexa-semantic-search` (`query` and/or `terms`, scoped by `categories`; rank by `score`) |
| Need the list of valid categories | `context-center-nexa-categories-list` |
| Want everything in a category (no specific concept) | `context-center-nexa-semantic-search` scoped to that `categories` value (discovery is meaning-based; there is no plain browse tool) |
| An exact asset id already | Skip search — call `context-center-asset-get` directly |

## Notes & gotchas

- **Asset endpoints have no real search.** They offer paginated `list` +
  `get-by-id` only; the `search` argument filters one already-fetched page
  in-process, not the whole result set. To find by topic, go through knowledge.
- **`dashboard` and `customer_brief` are knowledge-only here.** Their summaries
  are searchable, but there is no asset get tool for them in this MCP (dashboard
  asset tools were removed). Report the summary and the `asset_id`; don't try to
  hydrate.
- **`insights_finder` is list-only** — `context-center-asset-list` with
  `assetType: insights-finder`, no get-by-id.
- **Knowledge `score`** is only populated by semantic search. A higher score is a
  closer semantic match; still confirm relevance against the hit's `summary`.
- **Lists return `{ items, pagination }`.** Check `pagination.hasMore` before
  concluding a result set is complete.
- **Quote the summary, verify with the asset.** A knowledge summary is generated
  text; when precision matters (the exact steps, validity, asset ids), cite the
  hydrated asset, not the summary. (Raw match SQL is hidden in both layers.)
