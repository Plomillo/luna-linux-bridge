#!/usr/bin/env bash
# Authorised: install git-lfs and rclone from signed Debian APT indexes
# to the runner user's own ~/.local/bin; no sudo or global mutations.
set -Eeuo pipefail
umask 077
fail() { printf 'FAIL_CLOSED: %s\n' "$*" >&2; exit 2; }
[[ ${GITHUB_REPOSITORY:-} == "Plomillo/luna-linux-bridge" ]] || fail "Unexpected repository"
[[ ${GITHUB_REF:-} == "refs/heads/staging/contenedor-semantico-e826-20260927" ]] || fail "Unexpected branch"
[[ $(uname -s) == Linux ]] || fail "Not Linux"
for cmd in apt-get dpkg-deb dpkg sha256sum python3; do command -v "$cmd" >/dev/null || fail "Missing $cmd"; done

target="$HOME/.local/bin"
mkdir -p "$target"
export PATH="$target:$PATH"
if [[ -n ${GITHUB_PATH:-} ]]; then printf '%s\n' "$target" >> "$GITHUB_PATH"; fi
need_lfs=1; need_rclone=1
if command -v git-lfs >/dev/null; then git-lfs version; need_lfs=0; fi
if command -v rclone >/dev/null; then rclone version | head -1; need_rclone=0; fi

installed_now=()
temp=""
cleanup() {
  status=$?
  if (( status != 0 )); then
    for installed in "${installed_now[@]}"; do rm -f -- "$target/$installed"; done
    printf 'ROLLBACK: %s newly installed binaries removed\n' "${#installed_now[@]}" >&2
  fi
  if [[ -n "$temp" && -d "$temp" ]]; then rm -rf -- "$temp"; fi
}
trap cleanup EXIT

if (( need_lfs || need_rclone )); then
  temp="$(mktemp -d "$HOME/.local/cas-tools-install.XXXXXXXX")"
  mkdir -p "$temp/lists/partial" "$temp/cache/archives/partial" "$temp/packages" "$temp/extracted"
  opts=(
    -o "Dir::State::lists=$temp/lists"
    -o "Dir::Cache::archives=$temp/cache/archives"
    -o "APT::Sandbox::User=$(id -un)"
  )
  echo "APT_SIGNED_INDEX_REFRESH_START"
  apt-get "${opts[@]}" update -qq || fail "Cannot refresh verified Debian indexes"
  cd "$temp/packages"
  packages=()
  (( need_lfs )) && packages+=(git-lfs)
  (( need_rclone )) && packages+=(rclone)
  apt-get "${opts[@]}" download "${packages[@]}" || fail "Cannot download Debian packages"
  for package in "${packages[@]}"; do
    candidates=("$temp/packages/$package"_*.deb)
    (( ${#candidates[@]} == 1 )) || fail "Unexpected package count: $package"
    deb="${candidates[0]}"
    [[ $(dpkg-deb -f "$deb" Package) == "$package" ]] || fail "Wrong package"
    arch="$(dpkg-deb -f "$deb" Architecture)"
    [[ $arch == "$(dpkg --print-architecture)" || $arch == all ]] || fail "Wrong architecture"
    dest="$temp/extracted/$package"
    mkdir -p "$dest"
    dpkg-deb -x "$deb" "$dest"
    [[ -f "$dest/usr/bin/$package" && -x "$dest/usr/bin/$package" ]] || fail "Binary missing: $package"
    [[ ! -e "$target/$package" && ! -L "$target/$package" ]] || fail "Refuse overwrite: $package"
    install -m 0755 "$dest/usr/bin/$package" "$target/$package"
    installed_now+=("$package")
    printf 'INSTALLED_LOCAL package=%s deb_sha256=%s binary_sha256=%s\n' \
      "$package" "$(sha256sum "$deb" | cut -d' ' -f1)" \
      "$(sha256sum "$target/$package" | cut -d' ' -f1)"
  done
fi

command -v git-lfs >/dev/null || fail "Missing git-lfs"
command -v rclone >/dev/null || fail "Missing rclone"
git-lfs version
rclone version | head -1
mkdir -p "$HOME/.local/state/louksna/installations"
audit="$HOME/.local/state/louksna/installations/cas-tools-$(date -u +%Y%m%dT%H%M%SZ).txt"
{
  echo "OPERATION=INSTALL_GIT_LFS_RCLONE"
  echo "SCOPE=USER_LOCAL_SIGNED_DEBIAN_PACKAGES"
  echo "TARGET=$target"
  echo "STATUS=PASS"
  echo "GITHUB_REF=$GITHUB_REF"
  echo "GITHUB_SHA=${GITHUB_SHA:-UNKNOWN}"
  echo "GIT_LFS_VERSION=$(git-lfs version)"
  echo "RCLONE_VERSION=$(rclone version | head -1)"
  echo "GIT_LFS_SHA256=$(sha256sum "$(command -v git-lfs)" | cut -d' ' -f1)"
  echo "RCLONE_SHA256=$(sha256sum "$(command -v rclone)" | cut -d' ' -f1)"
  echo "G23=NOT_EXECUTED"
  echo "G24=NOT_EXECUTED"
} > "$audit"
chmod 0600 "$audit"
printf 'INSTALL_PASS audit=%s\n' "$audit"
