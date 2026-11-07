---
name: plotune-mcp-setup
description: Use when configuring an MCP client to connect to a Plotune Nexus device, choosing between the local or the device's managed remote endpoint, setting up OAuth login, configuring bearer-token fallback, or troubleshooting connection and auth failures.
---

# Plotune Nexus MCP Setup

Plotune Nexus MCP uses HTTP URL transport. Do not configure it as a local stdio server.

## Who registers the server

There is no shared Nexus endpoint: every user connects to their **own** device.

- **Claude Code:** this plugin asks for "Your Nexus MCP URL" when it is enabled and registers `plotune-nexus` with it. Change the URL later in `/config` (plugin options) or with `/plugin`. To point at a second device, add it manually with `claude mcp add` under a different server name (Step 2).
- **Codex and other clients:** the plugin cannot ask for a per-user URL, so register the server yourself with the commands in Step 2.

## Step 1 — Choose Your Endpoint

| Scenario | Endpoint |
|---|---|
| Client is on the same LAN or VPN as the device | `http://<device-ip>/mcp` |
| Remote access through the device's managed tunnel | `https://<device-uuid>.plotune.net/mcp` |

Every device is reachable directly at its own `https://<device-uuid>.plotune.net` address through its managed tunnel. OAuth discovery and registration happen on the device itself, so no device-routing header is needed.

Find the device UUID in the Nexus local UI under device information.

## Step 2 — Register The MCP Server In Your Client

**Claude Code — local device:**
```bash
claude mcp add --transport http plotune-nexus http://<device-ip>/mcp
```

**Claude Code — remote device:**
```bash
claude mcp add --transport http plotune-nexus https://<device-uuid>.plotune.net/mcp
```

**Codex — local device:**
```bash
codex mcp add plotuneNexus --url http://<device-ip>/mcp
```

**Codex — remote device with OAuth:**
```bash
codex mcp add plotune-nexus --url https://<device-uuid>.plotune.net/mcp
codex mcp login plotune-nexus
```

**VS Code / generic JSON client:**
```json
{
  "servers": {
    "plotune-nexus": {
      "type": "http",
      "url": "https://<device-uuid>.plotune.net/mcp"
    }
  }
}
```

## Step 3 — Authenticate

**Preferred: OAuth with dynamic client registration.**

The device handles OAuth through its local UI:
1. The client discovers `/.well-known/oauth-protected-resource/mcp` and `/.well-known/oauth-authorization-server` on the device origin.
2. The client registers dynamically at `/register`.
3. The operator approves the request in the Nexus local UI at `/authorize`. The approving user must be signed in with a Plotune account — a local recovery session cannot approve OAuth flows.
4. The client receives a token via `/oauth/token`.

Because the device hostname already identifies the device, origin-level discovery paths work without extra configuration.

**Fallback: manual bearer token.**

An authorized user can mint a time-bound token from the Nexus Security page. Send it as:
```text
Authorization: Bearer <token>
```
or:
```text
X-Plotune-MCP-Bearer-Token: <token>
```

Never embed a long-lived token in plugin or repository files.

## Step 4 — Verify The Connection

After registration, read a resource to confirm the server is reachable and authenticated:
```
read resource: plotune://device/context
```

A successful read returns device hostname, load, and clock sync state. A 401 or 403 means auth is not complete. A timeout or TLS failure against the remote address usually means the device is offline, remote access is turned off, or the UUID is wrong.

## Step 5 — Refresh After Device Updates

If the Nexus device software is updated, restart the MCP client or flush its tool and resource cache. New tools and resources are not automatically discovered after a server restart.

## Guardrails

- Never ask the user to paste a long-lived token into repository or plugin files.
- Do not embed a real device UUID or bearer token in plugin config.
- OAuth is the preferred path; bearer token is fallback only.
- If OAuth approval fails, verify the operator is signed in with a Plotune account, not a local recovery session.
- If the remote endpoint is unreachable, confirm remote access is on in the device's tunnel settings and that the device has an active managed tunnel.