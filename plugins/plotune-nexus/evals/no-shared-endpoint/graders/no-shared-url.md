---
type: llm
---

PASS if the reply explains that there is no single shared endpoint: each user connects to their own device, using either its LAN
address (http://<device-ip>/mcp) or its managed tunnel address (https://<device-uuid>.plotune.net/mcp).
FAIL if it invents or asserts a specific shared URL for everyone.
