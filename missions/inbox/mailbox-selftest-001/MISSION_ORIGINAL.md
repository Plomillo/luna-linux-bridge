MISSION_ID = MAILBOX-SELFTEST-001
MISSION_CLASS = TEST_ONLY
REQUIRED_CAPABILITIES = MAILBOX_ROUTING

PRIMARY_OBJECTIVE = Verify that GitHub Mission Mailbox preserves this source byte-exact, registers it in CUSTOSZ V7, checks CUSTOSZ_RUNTIME compatibility, and emits an exact terminal HOLD if no governed executor/adapter exists.

SUCCESS = RECEIPT + BYTE_EXACT_NATIVE_ENVELOPE + CUSTOSZ_ROUTING_DECISION + RUNTIME_COMPATIBILITY + PRECISE_TERMINAL_REPORT

FORBIDDEN = No material user-data mutation. No Windows/EFI/GPT/partitions/PROYECTOS/F3-DISK mutation. No canonical mutation. No executor substitution. No capability implementation.

CAPABILITY_SUGGESTIONS = Suggestions only; Family 9 review required; emit none unless non-duplication is evidenced.
