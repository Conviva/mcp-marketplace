# Conviva DPI MCP

Companion plugin for **Conviva DPI MCP**, packaged for **Claude Code** and
**Cursor**. It wires the hosted MCP endpoint into your client and installs
companion skills for Context Center, metrics, behavior segments and session
replay. On **Claude Desktop** the plugin supplies the skills and you attach the
MCP server as a connector — see below.

## Install

**Claude Code** — one step; the plugin wires the MCP server **and** the skills.
Run each command on its own (the copy button copies one block at a time):

1. Add the marketplace:

   ```
   /plugin marketplace add Conviva/mcp-marketplace
   ```

2. Install the plugin:

   ```
   /plugin install conviva-dpi-mcp@conviva
   ```

**Claude Desktop** — open **Customize → Plugins → Personal**, click **+**, paste
the repo URL below with **Sync automatically** on, then install **Conviva DPI
MCP**. That gets the skills **and** the `conviva` MCP server. If you only want
the tools, add the endpoint as a custom connector instead (Settings →
Connectors); on **Team/Enterprise** plans an Owner must add that connector at
**Organization settings → Connectors** first.

**Cursor** — this repo is also a Cursor plugin (`.cursor-plugin/`), so one
install gets **tools and skills**. Cursor installs plugins from a marketplace,
so import this repo as one:

1. Open **Customize → Personal → + Add Marketplace → Import from GitHub** and
   enter:

   ```
   https://github.com/Conviva/mcp-marketplace
   ```

2. Back on the **Personal** tab, a **Conviva** section now lists **Conviva DPI
   MCP** (`conviva-dpi-mcp`) — click **Add**, then complete the browser login
   for the bundled `conviva` server. A **Conviva** tab filters to the same
   entry.

To roll it out org-wide instead, a **Teams/Enterprise** admin imports the same
URL once at **Dashboard → Plugins → Add Marketplace → Import from Repo**;
members then install it from **Customize**.

Prefer not to add a marketplace? You can still get the **tools** (without the
skills) by pointing Cursor's `mcp.json` at the endpoint below — see
[GETTING_STARTED.md](./GETTING_STARTED.md).

All clients authenticate via **Okta OAuth** in your browser on first use — no
token to paste. For step-by-step setup and troubleshooting, see
[GETTING_STARTED.md](./GETTING_STARTED.md).

## Update

**Claude Code (terminal or desktop app)** — run these in a session, one at a
time (the copy button copies one block at a time):

1. Refresh the marketplace:

   ```
   /plugin marketplace update conviva
   ```

2. Update the plugin:

   ```
   /plugin update conviva-dpi-mcp@conviva
   ```

3. Apply it without restarting:

   ```
   /reload-plugins
   ```

`/reload-plugins` needs Claude Code v2.1.260 or newer, and it does not
reconnect the plugin's MCP server in the desktop app — start a new session for
that.

From a shell instead (pass the scope you installed with — `user` is the
default, otherwise `project` or `local`):

```sh
claude plugin marketplace update conviva
claude plugin update conviva-dpi-mcp@conviva --scope user
```

To skip this each release, open `/plugin` → **Marketplaces** →
`conviva` → **Enable auto-update**. Third-party marketplaces have
auto-update **off** by default.

**Claude Desktop** — updates are per marketplace, not per plugin. Under
**Customize → Plugins → Personal**, click **⋯** next to the marketplace: leave
**Sync automatically** on, or hit **Check for updates** to pull now. The
**Synced commit** shown there tells you which revision you're on.

**Cursor** — updates are automatic; there's no button to press. A **User**-scope
import picks up new releases after Cursor restarts; for a **Team** marketplace,
an admin clicks **Refresh** in **Dashboard → Plugins** or turns on **Auto
Refresh**. Confirm the version *and* the skill list under **Customize**.

> ⚠️ Cursor's marketplace sync can go stale: the GitHub import doesn't take, or
> it sticks on an older commit and **Update**/**Reinstall** does nothing. It's a
> Cursor-side bug — the workaround is to clone this repo and add it via
> **Add Marketplace → Import from Disk**. See
> [GETTING_STARTED.md](./GETTING_STARTED.md#known-cursor-bug).

Updating the plugin updates its configuration and bundled skills. The hosted MCP
service itself is deployed separately — new server-side tools appear without a
plugin update.

## What it connects to

The plugin registers an MCP server that connects to the hosted Conviva DPI MCP
endpoint:

```
https://dpi-mcp.conviva.com/mcp
```

Access is authenticated per Conviva account — installing the plugin does not by
itself grant access to data. You must be an authorized Conviva user.

## Version

`1.5.2` — see the release tags for history. Each published version
corresponds to the identically-tagged commit in Conviva's internal repository.

This repository is **generated** on each release from that internal source, and
every file in it is overwritten. Please don't send pull requests here — they
can't be merged and the next release would erase them. Open an issue, or reach
your Conviva contact, instead.
