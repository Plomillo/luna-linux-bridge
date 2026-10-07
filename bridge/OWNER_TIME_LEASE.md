# Owner-signed hot read-only time lease (candidate 0.4)

STATUS: SOURCE_CANDIDATE_UNCERTIFIED. No production owner signing key, production trust roots, root privileges, G23/G24 or daemon installation are created here.

The original core supports live heartbeat interval/reduced budget; it intentionally rejects increased limits. This additive module allows a **genuine owner-signed** bounded increase, preserving the absolute hard_deadline_sec from CONTRACT.v0.json (currently 3600 seconds). The authorized nonprivileged observer picks up the revised TIME_POLICY.json at its next safe checkpoint, without restarting. No new privilege, no extension of preexisting mission deadlines, no root lease extension, no G23/G24 extension, no arbitrary script execution.

Required original owner-only lease fields: schema LRB_SIGNED_OWNER_READONLY_TIME_LEASE/0.4; lease_id unique (16–80 approved chars); owner_intent EXACTLY EXPLICIT_NONPRIVILEGED_BUDGET_CHANGE; current host and boot_id; raw contract and controller SHA-256; expected current policy revision; new max_work_seconds within immutable ceiling; heartbeat_sec within configured bounds; issued_utc, expires_utc not more than 15 minutes apart and still fresh.

Signer: trusted OWNER identity from separately provisioned root-controlled /etc/louksna/remote-bridge/trust.json, via external_gates.ExternalGateVerifier. No key issuance here. The owner lease must be signed out of band using a distinct private key (never in GitHub or artifacts). Other independent authority identities are not reused.

Execution after independent review:
  python3 -B bridge/owner_time_lease.py --state-dir /exact/private/state --contract bridge/CONTRACT.v0.json --lease /exact/owner-lease.json --signature /exact/owner-lease.sig

Successful signed update: serialized on TIME_POLICY.lock, records OWNER_LEASE_INTENT, performs atomic JSON write, records OWNER_LEASE_COMMIT. Every existing policy reader validates chained evidence and refuses an incomplete owner lease or detected state rollback. A crash between intention and commitment yields **HOLD_INCOMPLETE_SIGNED_TIME_LEASE** until independent forensic reconciliation; it never silently replays an ambiguous increased budget. The module does not change a running monitor's already-expired execution outcome.

Negative tests: unsigned/tampered owner payload, unknown fields (including injected sudo), stale signature/deadline, wrong host or boot, source drift, ceiling overshoot, repeated lease, stale revision, incomplete transaction and policy rollback. Test owner certificates are ephemeral, synthetic and NOT production authorization.

Deployment dependency: actual owner signature and audited root-protected trust anchors must exist and G23/G24 for any separate mutating/privileged operations must be issued for their exact scopes. Time signatures do not grant authority to the root broker.
