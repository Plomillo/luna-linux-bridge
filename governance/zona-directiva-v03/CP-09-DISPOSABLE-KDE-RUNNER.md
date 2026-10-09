# CP-09 — Disposable Debian 13 KDE runner setup

CP-09 deliberately requires a real Debian 13 host with an active KDE graphical session. GitHub-hosted Ubuntu runners, Debian containers, and Xvfb-only sessions do not satisfy this gate.

## Required target

Use a **disposable VM** running Debian 13 with KDE Plasma. Do not register a daily-use workstation, production host, or machine containing credentials. The candidate .deb is installed with elevated privileges during this test; package maintainer scripts therefore execute as root.

Required environment and tools:

- /etc/os-release: ID=debian, VERSION_ID=13.
- KDE session active; KDE_FULL_SESSION=true, XDG_CURRENT_DESKTOP contains KDE, and DISPLAY, DBUS_SESSION_BUS_ADDRESS, and XDG_RUNTIME_DIR are present.
- dpkg-deb, apt-get, sudo, timeout, python3.
- A dedicated runner account with non-interactive sudo for package install/removal. Use this only on the disposable VM. Do not expose repository secrets to this runner.

## Register the runner

1. In the GitHub repository, open Settings → Actions → Runners → New self-hosted runner and select Linux x64 if it matches the VM.
2. Follow GitHub's displayed installation instructions. The one-time registration token expires; never commit or paste it into workflow files.
3. Configure labels exactly as required by the workflow: debian-13,kde,disposable (GitHub automatically adds self-hosted and linux).
4. Launch ./run.sh from a terminal inside the active KDE session so the runner inherits the actual graphical-session environment. A service started without that environment will correctly fail the gate.
5. Confirm the runner is online in Settings → Actions → Runners. Do not add secrets to the runner environment.

When CP-08 passes, the sequential workflow's CP-09 job will be eligible and will wait for a matching runner. The job performs the Debian 13 container smoke as supplemental evidence, then separately installs, launches, and removes the exact CP-08 package on the KDE host. The host report binds the package SHA-256, candidate commit, runtime environment, install/launch/rollback outcomes, and log SHA-256.

## Fail-closed behavior

No matching runner means CP-09 remains queued; an absent KDE session, OS mismatch, install failure, launch failure, or rollback failure yields HOLD/FAIL. Do not add a hosted-runner fallback or manually create a PASS evidence file. Destroy/reimage the disposable VM after the run.
