---
name: analyzing-session-replays
description: >
  Fetches a Conviva session replay's gzipped rrweb blobs for one clientId and
  window: lists metadata, mints signed URLs, then downloads and parses them
  locally — raw bytes never enter the model context.
  TRIGGER when: a user asks to analyze, debug, inspect, summarize, or explain
    what happened in a session replay (also called cohort replay in the Conviva
    UI) for a specific clientId and time range (natural language is enough),
    OR when you are about to call the session-replay-blob-* tools.
  DO NOT TRIGGER when: the user only wants to discover which sessions have a
    replay, fetch replay metadata by replayId, or get a Conviva UI deeplink —
    that is the session-replay-list / -get / -deeplink surface, not a raw-blob
    download; or the user has no clientId and is describing a behavior instead
    — use finding-replay-candidates first. Never a reason to query ClickHouse
    or list GCS buckets outside the session-replay-blob-* tools.
---

# Analyzing Session Replays

Answers "what happened in this user's session?" from the raw recording. It
orchestrates the two `session-replay-blob-*` tools and runs a **fixed local
parser once**. Skills orchestrate; tools stay primitive.

## Performance rules (hard)

Most wall time is wasted reinventing parsers and doing multi-pass digs. Follow
these strictly:

1. **Do not invent a parser.** Always use `scripts/analyze_rrweb.py` shipped
   with this skill (see workflow). Never write a new Python/Node analyzer.
2. **One download command** (parallel). No per-file curl loops with chatter.
3. **One parse command.** Run the fixed script once; read only its JSON stdout.
4. **One narrative response.** Do not run a second "dig deeper" pass unless the
   user explicitly asks for more detail after seeing the summary.
5. **Never** paste signed URLs, blob paths, raw rrweb JSON, DOM dumps, or
   per-event click/scroll streams into the chat unless the user asks for them.

## Boundary rules (hard) — MCP only, no infra freelancing

Replay storage is multi-tenant. Going around the tools can leak other
customers' data and is forbidden even when the list returns empty.

1. **Only these MCP tools** for discovery and download: `session-replay-blob-list`
   and `session-replay-blob-download-urls` (plus local curl of the signed URLs
   they return). Do not call other session-replay placeholders for blob bytes.
2. **Never** query or browse storage outside those tools: no ClickHouse, no
   `gcloud` / `gsutil`, no Google Cloud Storage client libraries, no listing
   buckets, no scanning other customers' buckets or prefixes, no inventing
   bucket names like `conviva-prod-sessionreplay-<customerId>`.
3. **Empty list → stop.** If `session-replay-blob-list` returns no blobs (or
   404), tell the user there is nothing to summarize for that clientId/window.
   Optionally suggest they confirm the clientId, timezone, or widen the window
   **and re-call the same MCP list tool once**. Do **not** "confirm" via
   ClickHouse, Nexa, or raw GCS. Do not dig across accounts or buckets.
4. **Do not** use shell/Python with Application Default Credentials (or any
   cloud SDK) to search for replay objects. Local shell is only for: curling
   signed URLs from the download-urls tool, running `analyze_rrweb.py`, and
   the single reachability probe in workflow step 4 — it is credential-free,
   names no bucket, and reads only response headers, so it diagnoses *egress*
   and can never reach data. Anything that could return an object is barred.
5. **Tenant scope is the tool's job.** Never pass foreign `blobPaths`, guess
   another account's `customerId`, or search under another customer's prefix.

## The core constraint: raw bytes stay out of the context window

- MCP tools return only **metadata and URLs** — never blob content.
- Download with local shell; analyze with the fixed script; narrate the summary.
- **Never** fetch a signed URL with a web/fetch tool into the model context.

## Inputs you need

- **clientId** — Conviva client id (dotted numeric string). **Required** for
  every session-replay blob tool call. If missing, use
  **finding-replay-candidates** to derive one from the user's behavioral
  question; ask the user directly only if that comes up empty too. Either way,
  do not invent ids, list “all clients,” or query ClickHouse/GCS outside the
  MCP tools. There is no list-all-clients tool on this path yet.
- **Time window** — `startDate`/`endDate` as ISO 8601 WITH timezone offset.
  **Required** on both `session-replay-blob-list` and
  `session-replay-blob-download-urls`. If the user gave a local day/time only,
  ask for timezone rather than assuming UTC. Windows above the per-request cap
  are rejected — narrow and retry.

Natural-language asks like "summarize this session for clientId … from … to …"
are enough. Shape the answer to what they asked; use the parser fields
(pages, messages, errors, timing) as evidence, not as a mandatory report outline.

## Workflow (one shot)

1. **List.** Call `session-replay-blob-list` with `clientId`, `startDate`,
   `endDate`. While `nextPageToken` is present, call again and accumulate —
   do this automatically; do not ask the user to page. Collect every
   `blobPath` / `sizeBytes`. If the first page is empty and there is no
   `nextPageToken` (or the tool returns 404), **stop here** — report no
   blobs; do not open GCS/ClickHouse/Nexa to double-check (see Boundary rules).
2. **Scope (brief).** One short line: blob count and total bytes. Only pause to
   confirm if total size is very large (hundreds of MB); otherwise continue.
3. **Mint URLs.** Call `session-replay-blob-download-urls` with the **same**
   `clientId`, `startDate`, `endDate`, and the `blobPaths` (batches ≤ per-call
   cap). Note `expiresAt`.
4. **Download in parallel, immediately** (URLs expire in minutes):

   ```bash
   WORKDIR=$(mktemp -d /tmp/session-replay-XXXXXX)
   # Write one curl line per URL, then run them in parallel — do not serial-loop
   # with progress chatter. Example if you have URLs in a bash array:
   #   printf '%s\n' "${URLS[@]}" | nl -ba | xargs -P 8 -n 2 \
   #     bash -c 'curl -fsS -o "'"$WORKDIR"'/$(printf %04d "$1").gz" "$2"' _
   ```

   If any download returns `400` / `ExpiredToken`, re-mint **only** the failed
   paths and retry those. Prefer one parallel batch over serial per-file curls.

   **A `403` is a different failure — do not re-mint.** Distinguish the two
   before acting, because the remedies are opposite. This one probe is the
   sanctioned exception to Boundary rule 4 — no bucket, no credentials, headers
   only; it is not a way to look for blobs:

   ```bash
   curl -s -D - -o /dev/null --max-time 15 https://storage.googleapis.com/ | head -3
   ```

   - Reply carries `server: UploadServer` or `x-guploader-uploadid` → you reached
     GCS. A `403` then means the path is not owned by this account; re-check the
     clientId. (The bare-bucket probe returning `400` is normal.)
   - No such header, or the proxy answers `403` itself → **your environment has
     no egress to GCS.** Re-minting cannot fix this. Say so plainly and tell the
     user to run the flow where a shell can reach the internet — a terminal, or
     an agent running on their own machine. Sandboxed hosts (Claude Cowork, and
     any VM-backed session) are blocked by policy; a plain chat surface has no
     shell at all, so the download step has nowhere to run.
5. **Parse once with the fixed script** (resolve path next to this SKILL.md):

   ```bash
   SCRIPT="<this-skill-dir>/scripts/analyze_rrweb.py"
   # Fallback when the skill dir is not on disk (e.g. Cursor without the plugin):
   # use the copy from the dpi-mcp checkout —
   #   claude-plugin/skills/analyzing-session-replays/scripts/analyze_rrweb.py
   # Write summary OUTSIDE $WORKDIR so the parser does not pick it up as a blob.
   SUMMARY=$(mktemp /tmp/session-replay-summary-XXXXXX.json)
   python3 "$SCRIPT" "$WORKDIR" > "$SUMMARY"
   ```

   Read **only** `$SUMMARY`. Do not gunzip/cat blob files into the chat.
6. **Narrate once.** From `$SUMMARY` (+ the user's question), write the
   summary. Prefer timestamps, pages, visible text/messages, errors, and
   outcome when relevant — omit sections the user did not ask for. Shape the
   narrative to the session type (browsing, checkout, support UI, etc.); do
   not assume an agent chat. Then stop.
7. **Cleanup (optional).** Remove `$WORKDIR` and `$SUMMARY` if the user has no further need.

## Privacy

Replay text often includes PII (names, emails, order ids, form/message bodies).
Summarize what is needed to answer the question; do not dump full transcripts
or signed URLs unless the user asks. Do not treat recorder placeholders
(`SCRIPT_PLACEHOLDER`) or trivial UI chrome (clock labels, lone button text)
as findings.

## Notes & gotchas

- **Blob paths are tenant-scoped.** Only paths from `session-replay-blob-list`
  for this account can be signed; anything else → 403.
- **Empty window ≠ broken tool.** List 404 / empty → no blobs for this
  clientId/window under the authenticated account. Ask the user to confirm
  clientId / timezone or widen the window via another MCP list call. Do not
  treat empty as permission to enumerate buckets or other tenants.
- **UI shows replay but MCP list is empty** → say so and stop; that is a
  data/mapping gap for the session-replay team, not a cue to scan GCS yourself.
- **Expired URLs are cheap to replace.** Re-mint remaining paths; do not abort.
- **A failed analysis is not a finding.** If download or parse fails, say what
  failed — do not invent session behavior. Name *which* step failed: a blocked
  environment, an expired URL, and a wrong clientId look alike from the outside
  and need different fixes.
- **Follow-ups.** If the user later asks for a deeper slice (full transcript,
  click-level detail), re-use `$WORKDIR` if it still exists and/or re-run the
  fixed script — still do not invent a new parser.
