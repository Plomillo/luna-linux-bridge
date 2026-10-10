# CP-09 — Debian 13 KDE disposable VM via GitHub Actions

## Purpose

This workflow is a higher-fidelity operational test than a Debian container or Xvfb-only smoke test. It boots a disposable Debian 13 cloud image as a QEMU guest, installs KDE Plasma and Xorg's dummy virtual display driver, starts SDDM with a dedicated test account, and attempts the candidate package install/launch/removal sequence. The VM disk and SSH key exist only in the workflow runner and are discarded when the job ends.

Workflow: `.github/workflows/louksna-cp09-debian13-kde-vm.yml`

## Dispatch inputs

- `candidate_commit`: full 40-character source commit SHA.
- `candidate_deb_url`: HTTPS URL to the exact candidate Debian package on an approved GitHub asset domain.
- `candidate_deb_sha256`: expected SHA-256 of that package.

The workflow rejects non-HTTPS URLs, non-approved initial hostnames, non-`.deb` URLs, malformed commit IDs, and malformed SHA-256 values. The downloaded package must match the supplied SHA-256 before it is passed to the guest.

## What the VM test covers

1. Debian 13 guest boot and cloud-init completion.
2. Installation inventory for KDE Plasma, KWin X11, SDDM, and Xorg dummy display.
3. A logged-in KDE/Xorg session smoke check.
4. Installation of the exact hash-pinned candidate `.deb`.
5. Bounded executable discovery and process-launch check.
6. Package removal and verification that the package is no longer installed.
7. Evidence manifest with SHA-256 hashes and run/commit identity.

## Boundaries

- This is a disposable **virtual machine inside GitHub Actions**, not a persistent or physical host.
- KDE runs in a guest Xorg session with a virtual dummy display. It is not proof of GPU acceleration, a physical display, microphone access, or real audio devices.
- The candidate URL must point to a publicly downloadable GitHub-hosted asset; private artifacts requiring an authenticated download are not supported by this workflow as written.
- The launch probe is a process-level smoke test. It does not establish end-to-end product correctness.
- Evidence is not a certification. CP-09 must not be marked certified solely from the presence of an artifact; review the guest boot, desktop-session, package, launch, rollback, and evidence logs. G23/G24 remain independent gates.
- The existing strict CP-09 governance document describes a dedicated disposable KDE runner. This workflow is a virtualized CI alternative and must not silently replace or downgrade that canonical requirement. Any acceptance of this VM profile as satisfying CP-09 requires an explicit governance decision.

## Fail-closed policy

A failed VM boot, missing KDE/Xorg session, package hash mismatch, package install failure, executable launch failure, or rollback failure must leave the test failed/held. Do not create a PASS marker manually or translate missing evidence into a pass.
