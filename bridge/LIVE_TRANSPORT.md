# LOUKSNA Bridge: Local Live Transport v0.3

Scope: CANDIDATE / READONLY / HOST_USER / NOT_RELEASED. Existing PR #31 remains draft. No privilege, storage, reboot, browser screenshot or remote TCP access.

## Live-local path
A bounded Python AF_UNIX local socket (bridge/live_link.py) exposes status, observe, report, tick_readonly, and watch. The server enforces Linux SO_PEERCRED same-UID identity, socket mode 0600 inside the owner's mode-0700 private state directory, three concurrent clients, bounded requests/responses and up to five observation frames in one stream session. watch writes chained SHA-256 observation receipts; durable base evidence uses boot_id + UTC timestamps. Payloads and status clearly say UNCERTIFIED, not G23/G24. The transport is local-only. Realtime from ChatGPT or off-host requires a reviewed authenticated overlay (such as an owner-configured mTLS/VPN relay); GitHub self-hosted Actions remains an asynchronous, artifact-producing host control/evidence path rather than a persistent low-latency screen stream.

A user-level, resource-capped systemd template is provided in deploy/louksna-live-socket.service.in. It does not automatically install/enable, and does not require or grant root. tick_readonly reuses the existing deterministic scheduler, which refuses GATED_OPERATION. No inbound request can execute shell, sudo, disk writes or reboot.

## Local smoke after independent review
Operator with consent and verified digest supplies a private state dir. In separate terminals:
1. python3 -B bridge/live_link.py --state-dir /exact/private/path serve
2. python3 -B bridge/live_link.py --state-dir /exact/private/path request --op status
3. python3 -B bridge/live_link.py --state-dir /exact/private/path request --op watch --frames 3 --interval-sec 2

Do not run serve using sudo/root; there is no remote socket exposure or screenshot capability.

## Release dependencies
Host sandbox smoke + load under measured CPU/RAM; persistent service trial with controlled restart and evidence retention; authenticated remote read-only relay with replay protection and owner consent; privacy opt-in visual capture and separate permissions; verified APC privilege contract, independent current G23/G24 and distinct second-order authorities, approved read-only/privileged cap registry, actual real CUSTOSZ V7 security review, rollback/postboot demonstration. Until proven: LIVE_LOCAL_CANDIDATE_TESTED is not HOST_DEPLOYED, REMOTE_REALTIME, ROOT_AUTHORIZED or CERTIFIED.
