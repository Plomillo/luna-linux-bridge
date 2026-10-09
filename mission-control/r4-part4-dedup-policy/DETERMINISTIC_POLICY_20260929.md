# PART4 — DETERMINISTIC PAYLOAD DEDUPLICATION POLICY

STATUS: USER_AUTHORIZED_POLICY
MODE: FAIL_CLOSED
OBJECTIVE: remove byte-identical redundant payload copies while preserving the operational Skeleton.

## SKELETON / KEEP SET
- Debian 13 Stable + KDE Plasma: installed base system. Installation media is NOT required to be retained.
- Wine
- Steam
- Proton
- Bottles
- Lutris
- Prism Launcher
- Waydroid
- Nix
- Ubuntu 24.04 lightweight
- Windows 11 lightweight
- Android 16
- Android 17
- Arch Linux auxiliary

## DETERMINISTIC IDENTITY RULE
1. Duplicate identity requires cryptographic content equality (SHA-256).
2. Same/similar filename, size, extension or role is NOT sufficient.
3. For a required payload hash with N>1 physical instances: KEEP exactly one valid instance; DELETE only the N-1 byte-identical instances.
4. If hashes differ: KEEP; no automatic deletion.
5. Debian 13/KDE installation-media payloads are explicitly not required after installed-system verification and are authorized for removal from the installation-media set.
6. Preserve the installed Debian/KDE system itself. This policy concerns redundant/downloaded payload media, never installed OS files.
7. "8. Vida personal y Ocio" is OUT_OF_SCOPE: no mutation.
8. Do not require Dropbox/rclone/cloud migration for this cleanup.

## REQUIRED PRE-COMMIT EVIDENCE
- inventory source and timestamp
- exact SHA-256 for every candidate group
- exact KEEP path
- exact DELETE paths
- byte count to reclaim
- Skeleton mapping for every retained required payload
- explicit exclusion proof for non-duplicate/different-hash content
- explicit exclusion proof for Vida personal y Ocio
- installed Debian 13/KDE verification before removing its installation media
- rollback/recovery pointer where required by active PART4 governance

## PIPELINE
INVENTORY -> HASH_IDENTITY -> SKELETON_MAP -> KEEP_DELETE_PROPOSAL -> PREVALIDATE_SCOPE -> CHECKPOINT -> COMMIT_DEDUP -> POST_HASH/EXISTENCE_VALIDATION -> NON_REGRESSION -> G23 -> G24

## FAIL-CLOSED
Any ambiguity, hash mismatch, missing required Skeleton payload, scope escape, or inability to prove the retained instance => HOLD that group; do not delete it.

No broad cleanup. No deletion by filename heuristic. No mutation of unrelated content.
