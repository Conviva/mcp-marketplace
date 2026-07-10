# Getting started

Connect to the hosted **Conviva DPI MCP** server. The steps depend on
which client you use:

- **Claude Code (CLI)** — **one step**. Install the plugin; it wires the MCP
  server **and** the Context Center skills automatically.
- **Claude Desktop** — **two steps**. Install the plugin (for the skills), then
  add the MCP server separately (custom connector or manual config).
- **Cursor** — add the remote MCP server to `mcp.json`. Cursor doesn't use Claude
  plugins, so you get the **tools** (not the companion skills).

The hosted endpoint is:

```
https://dpi-mcp.conviva.com/mcp
```

All methods send you through **Okta login** (OAuth) on first use — no token to
paste.

> [!TIP]
> **When is Node.js needed?**
> The **plugin** (Claude Code) and the **custom connector** (Desktop) connect to
> the endpoint natively — **no Node required**. Only the Desktop **manual config**
> uses the [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) bridge, which
> runs on **Node.js 18+**.

---

## Claude Code (CLI) — one step

Claude Code honors the plugin's bundled MCP server, so a single install gets you
both the tools and the skills.

> [!IMPORTANT]
> **Requires Claude Code v2.1.143 or newer.** Older versions can't parse the
> marketplace and fail `/plugin marketplace add` with
> `Invalid schema … Unrecognized key: "displayName"`. Check your version with
> `claude --version` and update with `claude update` (or
> `npm i -g @anthropic-ai/claude-code@latest`), then retry.

1. Add the marketplace from the GitHub repo:

   ```
   /plugin marketplace add Conviva/mcp-marketplace
   ```

2. Install the plugin:

   ```
   /plugin install conviva-dpi-mcp@conviva
   ```

3. On first tool use, complete the **Okta login** in your browser.

> [!NOTE]
> **If the browser login lands on a `localhost` page and doesn't finish**
> Claude Code defaults the OAuth callback host to `localhost`
> (`http://localhost:<port>/callback`), so on a remote/SSH or container session
> the browser can't reach it and the login appears to stall. **Workaround:** copy
> the full `localhost` callback URL from the browser and paste it back into Claude
> Code at the prompt — it converts the URL into a short user code you can approve
> (including out-of-band, e.g. relayed from another machine). This is an upstream
> Claude Code default (an open feature request tracks making the callback host
> configurable), not a Conviva-side setting.

That's it — the `conviva` MCP server starts automatically (tools appear
as `mcp__conviva__…`) and the Context Center skills
(`exploring-context-center`, `querying-predefined-metrics`,
`retrieving-behavior-segment-details`) load alongside them.

> [!TIP]
> **Install scope**
> `/plugin install` defaults to **user** scope (all your projects). For a shared
> team setup, install at **project** scope so it's recorded in
> `.claude/settings.json` and committed with the repo.

Verify with `/plugin` (confirm it's enabled) or just ask Claude to list its
Conviva tools.

---

## Claude Desktop — two steps

Desktop installs the plugin's **skills**, but does **not** auto-wire the
plugin's bundled MCP server. So you install the plugin for the skills, then
attach the MCP server yourself.

### Step 1 — Install the plugin (skills)

1. In Claude, open **Customize** in the left sidebar, then the **Plugins** tab.
2. In the **Personal plugins** section, click **+** → **Add marketplace** →
   **Add from a repository**.
3. Enter the repo URL:

   ```
   https://github.com/Conviva/mcp-marketplace
   ```

4. From the `conviva` marketplace, install **Conviva DPI MCP**
   (`conviva-dpi-mcp`).

This gives you the Context Center skills. (Plugins also work in Claude on the web
and in Cowork; in Cowork, open the **Cowork** tab first, then **Customize**.)

### Step 2 — Add the MCP server (tools)

Pick **one** of the two ways to attach the hosted server.

**Option A — Custom connector (recommended, no Node):**

1. Open **Settings → Connectors**.
2. Scroll to the bottom and click **Add custom connector**.
3. Enter the server URL (include `https://`) and click **Add**:

   ```
   https://dpi-mcp.conviva.com/mcp
   ```

4. Complete the **Okta login** when prompted.

**Option B — Manual config (`mcp-remote` bridge, needs Node.js):**

1. Open the **Claude menu in your OS menu bar** (not the in-window settings) →
   **Settings… → Developer → Edit Config**. This opens
   `claude_desktop_config.json`:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
2. Add the server under `mcpServers`:

   ```json
   {
     "mcpServers": {
       "conviva": {
         "command": "npx",
         "args": [
           "mcp-remote",
           "https://dpi-mcp.conviva.com/mcp"
         ]
       }
     }
   }
   ```

3. **Completely quit and restart Claude Desktop.**
4. A browser window opens for **Okta login**. After signing in, the MCP
   indicator appears in the input box and the tools are available.

> [!WARNING]
> **Don't run two copies**
> Use **either** the custom connector **or** the manual config — not both. If you
> previously added the server by hand and now switch to the connector, remove the
> `mcpServers` entry from `claude_desktop_config.json` first.

> [!TIP]
> **First-run OAuth**
> `mcp-remote` caches the broker token under `~/.mcp-auth/`. If login gets stuck or
> you rotate accounts, delete that directory and reconnect to restart the flow.

---

## Which Desktop method?

| Method | Where | You get | Needs |
| --- | --- | --- | --- |
| **Plugin** | Customize → Plugins | Skills | Node.js not required for skills |
| **Custom connector** | Settings → Connectors | MCP tools | — |
| **Manual config** | Developer → Edit Config | MCP tools | Node.js 18+ |

For the full experience on Desktop, combine the **plugin** (skills) with a
**connector** or **manual config** (tools).

---

## Cursor

Cursor connects to remote MCP servers natively — no plugin, no `mcp-remote`. You
get the **tools** (the companion skills are Claude-plugin-only).

1. Add the server to your Cursor MCP config — **`~/.cursor/mcp.json`** (global,
   all projects) or **`.cursor/mcp.json`** (this project only):

   ```json
   {
     "mcpServers": {
       "conviva": {
         "url": "https://dpi-mcp.conviva.com/mcp"
       }
     }
   }
   ```

   Or use **Cursor Settings → Tools & MCP → Add** (the "Customize" sidebar) and
   enter the URL.

2. On first use Cursor opens a browser for **Okta login** (OAuth) — no key to
   paste. Cursor registers with the server automatically (dynamic client
   registration); its OAuth callback is `cursor://anysphere.cursor-mcp/oauth/callback`
   (desktop app) or `https://www.cursor.com/agents/mcp/oauth/callback` (web).

3. Under **Settings → Tools & MCP**, confirm the `conviva` server is toggled on;
   its tools then appear under **Available Tools** in chat. MCP logs live in the
   **Output panel → "MCP Logs"**.

---

## Verifying & troubleshooting

Ask Claude to list the available tools, or run a simple Context Center query.

- **401 / auth loop** — the OAuth flow didn't complete; retry the Okta login
  (manual config: clear `~/.mcp-auth/` first).
- **Claude Code login stalls on a `localhost` callback page** — Claude Code
  defaults the OAuth callback to `localhost`, which a remote/SSH or container
  session can't reach. Copy the `localhost` callback URL from the browser and
  paste it back into Claude Code to exchange it for a short approval code
  (upstream default; an open Claude Code feature request tracks making it
  configurable).
- **`/plugin marketplace add` fails with `Unrecognized key: "displayName"`** —
  your Claude Code is older than **v2.1.143**. Update with `claude update` (or
  `npm i -g @anthropic-ai/claude-code@latest`) and retry.
- **Tools missing in Claude Code** — run `/plugin`, confirm `conviva-dpi-mcp` is
  enabled, and start a new session so the MCP server boots.
- **Tools missing in Desktop** — the plugin alone doesn't add tools; complete
  **Step 2** (connector or manual config). For manual config, check
  `claude_desktop_config.json` is valid JSON and that you fully restarted. Logs:
  `~/Library/Logs/Claude/mcp*.log` (macOS) /
  `%APPDATA%\Claude\logs\mcp*.log` (Windows).
- **Tools missing in Cursor** — check `mcp.json` is valid JSON and the `conviva`
  server is toggled on under **Settings → Tools & MCP**; read the **Output panel
  → "MCP Logs"** and retry the OAuth login.
- **Skills missing** — confirm the plugin is installed/enabled and reload the
  conversation. (Skills are Claude-plugin-only; Cursor doesn't load them.)

## Local development: Redis for nexa-analyze

The async `nexa-analyze` / `nexa-analyze-result` tools use a Redis-backed job
store. Before using them locally, start the bundled Redis via Docker Compose:

```bash
docker compose up -d redis
```

The config default (`config/default.json`) already points at
`redis://localhost:6379`, so no further setup is needed. Without Redis running,
those two tools return a `503` — everything else in the server works fine.
`npm test` needs no Redis (it's mocked in unit tests).

## References

- [Use plugins in Claude](https://support.claude.com/en/articles/13837440-use-plugins-in-claude)
- [Claude Code plugins reference](https://code.claude.com/docs/en/plugins-reference)
- [Cursor — Model Context Protocol](https://cursor.com/docs/mcp)
- [Connect to remote MCP servers (Custom Connectors)](https://modelcontextprotocol.io/docs/develop/connect-remote-servers)
- [Connect to local MCP servers (Edit Config)](https://modelcontextprotocol.io/docs/develop/connect-local-servers)
