# SERVER_READY post-reboot remediation — 15 minute gross ceiling

STATUS = AUTHORIZED_CONTINUATION
AUTHORITY = Louksna.md
DOCTRINE = EXTEND_DO_NOT_REPLACE
FAILURE_POSTURE = FAIL_CLOSED
GLOBAL_WALLCLOCK_MAX_SECONDS = 900
STOP_EARLY_IF_SUCCESS = TRUE
NO_REPEAT_CLOSED_WORK = TRUE

## Last verified checkpoint

PREBOOT_BOOT_ID = fd991162-2a6a-46b6-aa4a-ab84e4bf2db6
POSTBOOT_BOOT_ID = 22c7417c-f451-4a25-ad66-1567276527fb

Material host evidence already observed:

- G08_BOOT_CHANGE = PASS
- RUNNER_AUTORETURN = PASS
- SYMPHYLAX_PERSISTENCE = PASS
- SYMPHYLAX_HEALTH = PASS
- LINGER = PASS
- health.boot_changed_since_baseline = true
- health.status = HEALTHY

Do not repeat reboot. Do not re-register the runner. Do not execute `./run.sh`.

## Defects being remediated

1. `final_server_ready_postboot_verify.py` previously invoked `systemctl --user`
   from the system-service runner context without binding the user's systemd bus.
2. The terminal workflow called G09 "closure" without materially executing the
   controlled failure/recovery tests. Missing evidence therefore fell back to a
   HOLD template.
3. G23 and G24 correctly denied certification because G08/G09 were not proven.

## Authorized continuation

Repair the observer context additively, execute G09 materially on the governed
host, freeze the resulting evidence bundle, then submit the exact frozen bundle
to fresh read-only G23 and subsequently G24.

Required G09 evidence includes:

- controlled SIGKILL and automatic recovery with new PID;
- HEALTHY recovery;
- wrong-hash rejection;
- missing-artifact/dependency rejection;
- bounded timeout safe handling;
- no orphan process;
- state recovery;
- evidence survival across service restart.

No canonical mutation, no false PASS, no certification propagation.

Terminal PASS is permitted only when G08, G09, all 15 SERVER_READY gates, G23
and G24 are PASS on the same frozen evidence chain. Otherwise preserve HOLD
with the exact blocker and reproducible evidence.
