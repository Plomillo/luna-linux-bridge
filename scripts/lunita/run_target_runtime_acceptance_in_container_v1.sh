#!/usr/bin/env bash
set -Eeuo pipefail

: "\${LUNITA_ROOTFS_REAL:?LUNITA_ROOTFS_REAL is required}"
: "\${LUNITA_ROOT:?LUNITA_ROOT is required}"
: "\${LUNITA_XDG_STATE_HOME:?LUNITA_XDG_STATE_HOME is required}"
: "\${RUNNER_TEMP:?RUNNER_TEMP is required}"

ROOTFS="$(realpath -e "$LUNITA_ROOTFS_REAL")"
OVERLAY="$LUNITA_ROOT/engines/runtime_engines_v1"
test -d "$OVERLAY"
test -f "$OVERLAY/target_runtime_acceptance_v1.py"
test -x "$ROOTFS/usr/bin/unshare"

export XDG_STATE_HOME="$LUNITA_XDG_STATE_HOME"
export LUNITA_TARGET_RUNTIME_RECEIPT_DIR="$LUNITA_XDG_STATE_HOME/lunita/runtime_validation"
export PYTHONPATH="$OVERLAY/vendor/python3.12/site-packages:$OVERLAY"
export LUNITA_FASTEMBED_CACHE="$OVERLAY/model-cache/fastembed"
export LUNITA_VECTOR_DB_PATH="$RUNNER_TEMP/lunita-target-vectors"
export LUNITA_ENGINE_AUDIT_LOG="$RUNNER_TEMP/lunita-target-audit/engine-execution.jsonl"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1
export R_HOME="$ROOTFS/opt/lunita/instruments/lapiz/R-4.6.1/lib/R"
export FLATPAK_SYSTEM_DIR="$ROOTFS/var/lib/flatpak"

RESTORE_FILE="$RUNNER_TEMP/lunita-userns-sysctl.restore"
mkdir -p "$(dirname "$LUNITA_ENGINE_AUDIT_LOG")" "$LUNITA_TARGET_RUNTIME_RECEIPT_DIR"
: > "$RESTORE_FILE"

sysctl_path() {
    case "$1" in
        kernel.apparmor_restrict_unprivileged_userns) printf '%s\n' /proc/sys/kernel/apparmor_restrict_unprivileged_userns ;;
        kernel.unprivileged_userns_clone) printf '%s\n' /proc/sys/kernel/unprivileged_userns_clone ;;
        user.max_user_namespaces) printf '%s\n' /proc/sys/user/max_user_namespaces ;;
        *) echo "ERROR: unregistered user-namespace sysctl: $1" >&2; return 2 ;;
    esac
}

restore_userns_sysctls() {
    local key original path observed failed=0
    while IFS='=' read -r key original; do
        [ -n "$key" ] || continue
        if ! sysctl -q -w "$key=$original"; then
            echo "ERROR: could not restore user-namespace sysctl $key" >&2
            failed=1
            continue
        fi
        path="$(sysctl_path "$key")"
        observed="$(cat "$path")"
        if [ "$observed" != "$original" ]; then
            echo "ERROR: sysctl restoration mismatch for $key: $observed != $original" >&2
            failed=1
        fi
    done < "$RESTORE_FILE"
    return "$failed"
}

cleanup_mounts() {
    local failed=0 target
    for target in run sys proc dev; do
        if mountpoint -q "$ROOTFS/$target"; then
            umount -R "$ROOTFS/$target" || failed=1
        fi
    done
    return "$failed"
}

cleanup() {
    local result=$?
    trap - EXIT
    set +e
    restore_userns_sysctls || result=1
    cleanup_mounts || result=1
    exit "$result"
}
trap cleanup EXIT

enable_userns_sysctl() {
    local key="$1" wanted="$2" original path
    path="$(sysctl_path "$key")"
    if [ ! -e "$path" ]; then
        echo "USERNS_SYSCTL_UNAVAILABLE=$key"
        return 0
    fi
    if [ ! -r "$path" ]; then
        echo "ERROR: user-namespace sysctl is not readable: $key" >&2
        return 1
    fi
    original="$(cat "$path")"
    if [ "$original" != "$wanted" ]; then
        printf '%s=%s\n' "$key" "$original" >> "$RESTORE_FILE"
        sysctl -q -w "$key=$wanted"
    fi
    printf 'USERNS_SYSCTL_ACTIVE %s=%s (original=%s)\n' "$key" "$wanted" "$original"
}

enable_userns_sysctl kernel.apparmor_restrict_unprivileged_userns 0
enable_userns_sysctl kernel.unprivileged_userns_clone 1
if [ -r /proc/sys/user/max_user_namespaces ] && [ "$(cat /proc/sys/user/max_user_namespaces)" = "0" ]; then
    enable_userns_sysctl user.max_user_namespaces 65536
fi

mount --rbind /dev "$ROOTFS/dev"
mount --make-rslave "$ROOTFS/dev"
mount -t proc proc "$ROOTFS/proc"
mount --rbind /sys "$ROOTFS/sys"
mount --make-rslave "$ROOTFS/sys"
mount --rbind /run "$ROOTFS/run"
mount --make-rslave "$ROOTFS/run"
install -d -o 1000 -g 1000 -m 0700 "$ROOTFS/run/lunita-runtime-1000"

sudo -n chroot --userspec=1000:1000 "$ROOTFS" /usr/bin/unshare --user --map-root-user /usr/bin/true
echo "PASS: target UID 1000 created the user namespace required by Flatpak bubblewrap."
echo "PASS: privileged namespace-capable CI container is only the execution host; candidate policy and Flatpak app permissions are unchanged."

python3.12 "$OVERLAY/target_runtime_acceptance_v1.py"
