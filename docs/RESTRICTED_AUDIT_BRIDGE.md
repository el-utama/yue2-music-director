# Restricted remote audit bridge — operator recovery

This is an audit-only path, separate from Music Director's local generation
CLI. It is not a production remote Studio service or permission to expose
the entire native MCP server.

## Verified setup

A Mac with Tailscale and the existing OpenAI Tunnel client connects to the
Windows Studio's network-access-protected endpoint over the private tailnet.
Studio and yue-server remain under their existing native ownership. The
Mac runs the operator's private `yue2-audit-bridge-v2.py` (bridge 0.2.0;
tunnel-client 0.0.21). The existing private YUE2 connector uses the tunnel.
The demo stub and then the real bridge were verified by server_info from
ChatGPT. Native server identity was music-server 5.0.0; velocity_probe and
writing_guide were successfully called. This is a foreground, operator-owned
connection, not an always-on managed service.

The bridge source is a private local artifact, not a file shipped by this
repository. The delivered v2 artifact SHA-256 is
`9877a4cb941a766d38b1f114455720487f16fa08d60904e4154ef4823f97f5fe`.
This is the delivered file's identity, not independent verification of the
Mac's current bytes. Preserve a private backup of the script. Its
machine-specific endpoint must not be committed to this public repository.
If lost, reconstruct from the scoped contract below and retest before use;
do not replace it with unrestricted forwarding.

## Allowed scope

- server_info: native initialize and identity only.
- writing_guide: fixed topics song, style, lyrics, score, transcript, sections.
- velocity_probe: fixed synthetic MIDI conversion and re-export fixture;
  no existing score or library data. Already completed, do not repeat.

Native requests use the Studio Network Access Key via Bearer authorization.
No arbitrary URLs, tools, library reads, UI clicks, settings changes, model
downloads, training or synthesis. Audit credentials are not native
generation credentials for the agent. The native UI bridge does not reach
inside the MIDI editor iframe for generic click/type, so automated UI
velocity editing was not performed.

## Restart and troubleshoot (Mac only)

Run the existing private script in its own Terminal:

    python3 ~/Downloads/yue2-audit-bridge-v2.py

The first successful setup saves Studio key, existing Tunnel ID, and
Runtime API key under `~/.config/yue2-audit-bridge/` (private directory
and credential files). Do not print or share contents. The Runtime key
has Tunnels Read/Use access, not an admin key. Do not create a new tunnel
or connector just to restart. Keep the Mac awake and the Terminal open
when actively using the bridge.

Check the native connection without starting a tunnel:

    python3 ~/Downloads/yue2-audit-bridge-v2.py --check

If the health port is already occupied, identify the listener:

    lsof -nP -iTCP:18080 -sTCP:LISTEN

Stop only the identified old tunnel process (prefer Ctrl+C in its own
Terminal). Do not kill an unrelated listener. Never run two clients for
the same tunnel ID. Once the bridge is started, check local readiness
from a second Terminal:

    curl -fsS http://127.0.0.1:18080/readyz

Readiness is not end-to-end proof; call server_info using the existing
connector. If the connector's tool list is stale from the demo stub,
refresh tool discovery and the ChatGPT session if available.

For native 401 after a key change, use `--reset-studio-key` with the
script; for an invalid/revoked Runtime key, use `--reset-runtime-key`.
Only re-enter the affected key privately. Rotate any exposed secret via
its owning service; do not paste keys into chat, commit logs or issue
reports. If the bridge is unavailable, continue source audit rather than
claiming a live result or asking the operator to repeat completed tests.

## Security and limitations

Use the tailnet/private access boundary, never publish Studio directly
on the Internet or weaken the native key check. No extra public port,
router forwarding, generic UI automation or shell execution. The current
client has a foreground lifecycle and depends on both hosts and the
network; no persistence/service guarantee. Do not turn the audit bridge
into an autonomous production endpoint without a separately reviewed
authentication, authorization, lifecycle and recovery design.
