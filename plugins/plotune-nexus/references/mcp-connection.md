# Plotune Nexus MCP Connection Reference

## Endpoint Options

Plotune Nexus MCP uses HTTP URL transport. Choose the endpoint that matches your network topology.

### Direct Local Device

```text
http://<device-ip>/mcp
```

Use when the MCP client can reach the device on the same LAN or VPN.

### Remote Device Through The Managed Tunnel

```text
https://<device-uuid>.plotune.net/mcp
```

Every device is reachable directly at its own `https://<device-uuid>.plotune.net` address through its managed tunnel. The device hostname identifies the device, and the device serves its own OAuth discovery and registration:

```text
https://<device-uuid>.plotune.net/.well-known/oauth-protected-resource/mcp
https://<device-uuid>.plotune.net/.well-known/oauth-authorization-server
https://<device-uuid>.plotune.net/register
```

No device-routing header is needed; the Plotune cloud control plane provisions the tunnel but never proxies MCP traffic.

## Auth

Prefer OAuth 2.0 with dynamic client registration. The device implements RFC 8707-compatible protected resource metadata and handles OAuth approval through the local Nexus UI.

**OAuth flow:**
1. Client discovers `/.well-known/oauth-protected-resource/mcp` and `/.well-known/oauth-authorization-server` on the device origin.
2. Client registers dynamically at `/register`.
3. Browser approval happens at `/authorize`, which requires a logged-in Nexus session. The first verified Plotune account login bootstraps the device owner.
4. Client exchanges the code for a token at `/oauth/token`.

Sessions created with the local recovery password cannot approve OAuth or mint MCP tokens. The device owner must sign in with a Plotune account first.

**Manual bearer token (fallback only):**

An authorized user can mint a time-bound token from the Nexus Security page. Send it as:

```text
Authorization: Bearer <token>
```

or

```text
X-Plotune-MCP-Bearer-Token: <token>
```

Never embed a long-lived token in repository files or plugin config.

## Client Configuration Examples

### Claude Code — Local Device

```bash
claude mcp add --transport http plotune-nexus http://<device-ip>/mcp
```

### Claude Code — Remote Device

```bash
claude mcp add --transport http plotune-nexus https://<device-uuid>.plotune.net/mcp
```

### Codex — Local Device

```bash
codex mcp add plotuneNexus --url http://<device-ip>/mcp
```

Equivalent `~/.codex/config.toml`:

```toml
[mcp_servers.plotuneNexus]
url = "http://<device-ip>/mcp"
```

### Codex — Remote Device With OAuth

```bash
codex mcp add plotune-nexus --url https://<device-uuid>.plotune.net/mcp
codex mcp login plotune-nexus
```

### VS Code / Generic JSON Client

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

### Cursor

```json
{
  "mcpServers": {
    "plotune-nexus": {
      "url": "http://<device-ip>/mcp"
    }
  }
}
```

## Troubleshooting

**Client cannot reach the remote device — timeout or TLS failure:**
- Confirm remote access is on in the device's tunnel settings and the device has an active managed tunnel.
- Confirm the device UUID is correct. Find it in the Nexus local UI under device info.
- Confirm the hostname is exactly `<device-uuid>.plotune.net` — the UUID is the first DNS label.

**OAuth approval does not work:**
- The approving user must be signed in with a Plotune account, not a local recovery session.
- Origin-level discovery paths (`/.well-known/...`, `/register`) are served by the device itself and need no extra configuration.

**Tools or resources missing after MCP server update:**
- Restart the client or flush its tool/resource cache. The MCP server schema is not automatically re-fetched after a device update.

**Bearer token rejected:**
- Manual tokens expire. Mint a new one from the Nexus Security page.
- Tokens minted under a recovery session will not work; the owner must use a Plotune-authenticated session.