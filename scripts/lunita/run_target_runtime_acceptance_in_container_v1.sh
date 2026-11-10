#!/usr/bin/env bash
set -Eeuo pipefail
: "${LUNITA_ROOTFS_REAL:?LUNITA_ROOTFS_REAL is required}"
: "${LUNITA_ROOT:?LUNITA_ROOT is required}"
: "${LUNITA_XDG_STATE_HOME:?LUNITA_XDG_STATE_HOME is required}"
: "${RUNNER_TEMP:?RUNNER_TEMP is required}"
[ "$(id -u)" -eq 0 ] || { echo "BLOCKED: root is required to establish the isolated candidate mount namespace." >&2; exit 2; }

ROOTFS="$(realpath -e "$LUNITA_ROOTFS_REAL")"
RUNNER_TEMP="$(realpath -e "$RUNNER_TEMP")"
OVERLAY="$LUNITA_ROOT/engines/runtime_engines_v1"
test -d "$OVERLAY"
test -f "$OVERLAY/target_runtime_acceptance_v1.py"
test -x "$ROOTFS/usr/bin/unshare"
test -x "$ROOTFS/usr/bin/setpriv"
test ! -e "$ROOTFS/.oldroot"
test ! -L "$ROOTFS/.oldroot"
command -v unshare >/dev/null
command -v mount >/dev/null
command -v pivot_root >/dev/null

# Evidence paths are new per-run data; reject symlinks and non-directory collisions.
umask 077
for path in "$RUNNER_TEMP/lunita-xdg" "$RUNNER_TEMP/lunita-xdg/lunita" \
            "$RUNNER_TEMP/lunita-xdg/lunita/runtime_validation" \
            "$RUNNER_TEMP/lunita-target-vectors" "$RUNNER_TEMP/lunita-target-audit"; do
    if [ -L "$path" ] || { [ -e "$path" ] && [ ! -d "$path" ]; }; then
        echo "BLOCKED: unsafe host evidence path: $path" >&2
        exit 2
    fi
    mkdir -p "$path"
done
RESTORE_FILE="$RUNNER_TEMP/lunita-userns-sysctl.restore"
if [ -e "$RESTORE_FILE" ] || [ -L "$RESTORE_FILE" ]; then
    echo "BLOCKED: stale sysctl restore file already exists: $RESTORE_FILE" >&2
    exit 2
fi
(set -o noclobber; : > "$RESTORE_FILE")
HOST_BIND_NAME="lunita-host-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}"
export HOST_BIND_NAME

sysctl_path() {
    case "$1" in
        kernel.apparmor_restrict_unprivileged_userns) printf '%s\n' /proc/sys/kernel/apparmor_restrict_unprivileged_userns ;;
        kernel.unprivileged_userns_clone) printf '%s\n' /proc/sys/kernel/unprivileged_userns_clone ;;
        user.max_user_namespaces) printf '%s\n' /proc/sys/user/max_user_namespaces ;;
        *) echo "ERROR: unregistered user-namespace sysctl: $1" >&2; return 2 ;;
    esac
}
restore_userns_sysctls() {
    local result=$? key original path observed
    trap - EXIT
    set +e
    while IFS='=' read -r key original; do
        [ -n "$key" ] || continue
        sysctl -q -w "$key=$original" || result=1
        path="$(sysctl_path "$key")" || { result=1; continue; }
        observed="$(cat "$path" 2>/dev/null)"
        [ "$observed" = "$original" ] || result=1
    done < "$RESTORE_FILE"
    rm -f "$RESTORE_FILE"
    exit "$result"
}
trap restore_userns_sysctls EXIT
enable_userns_sysctl() {
    local key="$1" wanted="$2" original path
    path="$(sysctl_path "$key")"
    if [ ! -e "$path" ]; then echo "USERNS_SYSCTL_UNAVAILABLE=$key"; return 0; fi
    if [ ! -r "$path" ]; then echo "ERROR: user-namespace sysctl is not readable: $key" >&2; return 1; fi
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
export LUNITA_ROOTFS_REAL="$ROOTFS"
export RUNNER_TEMP

# CLONE_NEWUSER is denied from chroot. Make the candidate the mount-namespace root.
unshare --mount --propagation private --fork /bin/bash -s <<'PIVOT'
set -Eeuo pipefail
ROOTFS="$(realpath -e "$LUNITA_ROOTFS_REAL")"
RUNNER_TEMP="$(realpath -e "$RUNNER_TEMP")"
mount --make-rprivate /
mount --bind "$ROOTFS" "$ROOTFS"
mount --make-rprivate "$ROOTFS"
for part in dev proc sys run; do
    test -d "$ROOTFS/$part"
    test ! -L "$ROOTFS/$part"
done
mount --rbind /dev "$ROOTFS/dev"
mount --make-rslave "$ROOTFS/dev"
mount -t proc proc "$ROOTFS/proc"
mount --rbind /sys "$ROOTFS/sys"
mount --make-rslave "$ROOTFS/sys"
mount --rbind /run "$ROOTFS/run"
mount --make-rslave "$ROOTFS/run"

HOST_BIND="$ROOTFS/run/$HOST_BIND_NAME"
if [ -e "$HOST_BIND" ] || [ -L "$HOST_BIND" ]; then
    echo "BLOCKED: per-run host bind path already exists: $HOST_BIND" >&2
    exit 2
fi
mkdir -m 0700 "$HOST_BIND"
mount --bind "$RUNNER_TEMP" "$HOST_BIND"
mount --make-rslave "$HOST_BIND"

mkdir "$ROOTFS/.oldroot"
cd "$ROOTFS"
pivot_root . .oldroot
cd /
umount -l /.oldroot
rmdir /.oldroot

cleanup_host_bind() {
    local result=$?
    trap - EXIT
    set +e
    umount -l "/run/$HOST_BIND_NAME" 2>/dev/null || result=1
    rmdir "/run/$HOST_BIND_NAME" 2>/dev/null || result=1
    exit "$result"
}
trap cleanup_host_bind EXIT

export LUNITA_IN_PIVOT_ROOT=1
export LUNITA_ROOTFS_REAL=/
export LUNITA_TARGET_ROOTFS=/
export LUNITA_ROOT=/opt/lunita
export FLATPAK_SYSTEM_DIR=/var/lib/flatpak
export XDG_STATE_HOME="/run/$HOST_BIND_NAME/lunita-xdg"
export LUNITA_XDG_STATE_HOME="$XDG_STATE_HOME"
export LUNITA_TARGET_RUNTIME_RECEIPT_DIR="$XDG_STATE_HOME/lunita/runtime_validation"
export RUNNER_TEMP="/run/$HOST_BIND_NAME"
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PYTHONPATH=/opt/lunita/engines/runtime_engines_v1/vendor/python3.12/site-packages:/opt/lunita/engines/runtime_engines_v1
export LUNITA_FASTEMBED_CACHE=/opt/lunita/engines/runtime_engines_v1/model-cache/fastembed
export LUNITA_VECTOR_DB_PATH="$RUNNER_TEMP/lunita-target-vectors"
export LUNITA_ENGINE_AUDIT_LOG="$RUNNER_TEMP/lunita-target-audit/engine-execution.jsonl"
export R_HOME=/opt/lunita/instruments/lapiz/R-4.6.1/lib/R
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1

setpriv --reuid=1000 --regid=1000 --clear-groups \
    /usr/bin/unshare --user --map-root-user /usr/bin/true
echo "PASS_PIVOT_ROOT_UID1000_USERNS: UID 1000 created a user namespace from the actual candidate mount root."
echo "PASS_TARGET_ROOTFS_EXECUTION_CONTEXT: private mount namespace + pivot_root; no chroot user-namespace workaround."
set +e
/usr/bin/python3.12 /opt/lunita/engines/runtime_engines_v1/target_runtime_acceptance_v1.py
status=$?
set -e
exit "$status"
PIVOT