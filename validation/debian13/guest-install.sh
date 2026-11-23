#!/bin/bash
# Runs inside the Debian guest as root. Install work is administrative.
# Functional use of LOUKSNA is not this script.
set -u
export DEBIAN_FRONTEND=noninteractive
mkdir -p /var/log
exec > >(tee /var/log/louksna-guest-install.log) 2>&1
echo phase-a > /var/lib/louksna-boot-marker
fail=0
if command -v cloud-init >/dev/null 2>&1; then
  timeout 180 cloud-init status --wait || echo CLOUD_INIT_WAIT_FAIL
fi
apt-get update || echo APT_UPDATE_FAIL
install_group() {
  local name="$1"
  shift
  echo "GROUP_BEGIN $name"
  if apt-get install -y "$@"; then
    echo "GROUP_OK $name"
  else
    echo "GROUP_FAIL $name"
    fail=1
  fi
}
install_group base sudo ca-certificates acl llvm python3 libgomp1 libstdc++6 libglib2.0-bin adduser
install_group audio pipewire pipewire-pulse wireplumber
install_group plasma plasma-desktop kwin-wayland sddm xdg-desktop-portal xdg-desktop-portal-kde mesa-utils libgl1-mesa-dri dbus-user-session xwayland libpam-systemd
if [ -f /var/tmp/android-sdk.sh ]; then
  bash /var/tmp/android-sdk.sh || echo ANDROID_SDK_FAIL
else
  echo ANDROID_SDK_ABSENT
fi
udevadm settle || true
for group in sudo audio video render netdev systemd-journal adm; do
  if getent group "$group" >/dev/null; then
    usermod -aG "$group" louksna || echo "USERMOD_FAIL $group"
  else
    echo "GROUP_ABSENT $group"
  fi
done
chmod 755 /home/louksna || true
if [ -f /var/tmp/LOUKSNA.deb ]; then
  if dpkg -i /var/tmp/LOUKSNA.deb > /var/log/louksna-dpkg.log 2>&1; then
    echo DPKG_OK
  else
    echo DPKG_FIRST_FAIL
    if apt-get install -f -y >> /var/log/louksna-dpkg.log 2>&1 && dpkg -i /var/tmp/LOUKSNA.deb >> /var/log/louksna-dpkg.log 2>&1; then
      echo DPKG_OK
    else
      echo DPKG_FAIL
      tail -n 40 /var/log/louksna-dpkg.log || true
      fail=1
    fi
  fi
else
  echo DPKG_ABSENT
  fail=1
fi
if [ -x /usr/lib/louksna/whisper-cli ] && [ ! -e /usr/lib/louksna/whisper-cli.real ]; then
  mv /usr/lib/louksna/whisper-cli /usr/lib/louksna/whisper-cli.real
  cat > /usr/lib/louksna/whisper-cli << 'EOF'
#!/bin/sh
# The guest has no whisper-capable GPU. virtio/lavapipe makes whisper-cli
# abort during GPU init. --no-gpu still runs the bundled ggml-tiny model.
exec /usr/lib/louksna/whisper-cli.real --no-gpu "$@"
EOF
  chmod 755 /usr/lib/louksna/whisper-cli
  echo WHISPER_CPU_WRAPPER
fi
if [ -f /var/tmp/LOUKSNA.sh ]; then
  if sh /var/tmp/LOUKSNA.sh --prefix /opt/louksna-sh; then
    echo SH_OK
  else
    echo SH_FAIL
    fail=1
  fi
else
  echo SH_ABSENT
  fail=1
fi
session=""
if compgen -G "/usr/share/wayland-sessions/plasma*.desktop" > /dev/null; then
  session=$(basename "$(ls /usr/share/wayland-sessions/plasma*.desktop | head -n 1)" .desktop)
fi
mkdir -p /etc/sddm.conf.d /usr/lib/environment.d
cat > /usr/lib/environment.d/99-louksna.conf << 'EOF'
LIBGL_ALWAYS_SOFTWARE=1
GALLIUM_DRIVER=llvmpipe
QT_QPA_PLATFORM=wayland
EOF
if [ -n "$session" ]; then
  cat > /etc/sddm.conf.d/10-louksna.conf << EOF
[Autologin]
User=louksna
Session=${session}
Relogin=false

[General]
DisplayServer=wayland

[Wayland]
CompositorCommand=/usr/bin/kwin_wayland --drm --no-lockscreen --no-global-shortcuts --locale1
SessionCommand=/usr/share/sddm/scripts/wayland-session
EOF
  systemctl enable sddm || echo SDDM_ENABLE_FAIL
  systemctl set-default graphical.target || echo GRAPHICAL_TARGET_FAIL
else
  echo SESSION_DESKTOP_ABSENT
  fail=1
fi
loginctl enable-linger louksna || echo LINGER_FAIL
systemctl --global enable pipewire.service pipewire-pulse.service wireplumber.service || echo PIPEWIRE_ENABLE_FAIL
systemctl reset-failed || true
echo "SYSTEMD_STATE:$(systemctl is-system-running || true)"
echo "SESSION:${session:-none}"
if [ "$fail" -ne 0 ]; then
  echo INSTALL_FAIL
  exit 1
fi
echo INSTALL_DONE
