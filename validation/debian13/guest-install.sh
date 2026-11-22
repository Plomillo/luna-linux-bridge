#!/bin/bash
# Runs inside the Debian guest. Records install results. Does not declare certification.
set -u
export DEBIAN_FRONTEND=noninteractive
mkdir -p /var/log
exec > >(tee /var/log/louksna-guest-install.log) 2>&1
echo phase-a > /var/lib/louksna-boot-marker
apt-get update || echo APT_UPDATE_FAIL
install_group() {
  local name="$1"
  shift
  echo "GROUP_BEGIN $name"
  if apt-get install -y "$@"; then
    echo "GROUP_OK $name"
  else
    echo "GROUP_FAIL $name"
  fi
}
install_group base sudo ca-certificates acl llvm python3 libgomp1 libstdc++6
install_group audio pipewire pipewire-pulse wireplumber
install_group plasma plasma-desktop kwin-wayland sddm xdg-desktop-portal xdg-desktop-portal-kde mesa-utils libgl1-mesa-dri dbus-user-session
if [ -f /var/tmp/LOUKSNA.deb ]; then
  if dpkg -i /var/tmp/LOUKSNA.deb > /var/log/louksna-dpkg.log 2>&1; then
    echo DPKG_OK
  else
    echo DPKG_FAIL
    tail -n 40 /var/log/louksna-dpkg.log || true
  fi
else
  echo DPKG_ABSENT
fi
if [ -f /var/tmp/LOUKSNA.sh ]; then
  if sh /var/tmp/LOUKSNA.sh --prefix /opt/louksna-sh; then
    echo SH_OK
  else
    echo SH_FAIL
  fi
else
  echo SH_ABSENT
fi
session=""
if compgen -G "/usr/share/wayland-sessions/plasma*.desktop" > /dev/null; then
  session=$(basename "$(ls /usr/share/wayland-sessions/plasma*.desktop | head -n 1)" .desktop)
fi
mkdir -p /etc/sddm.conf.d
if [ -n "$session" ]; then
  cat > /etc/sddm.conf.d/10-louksna.conf << EOF
[Autologin]
User=louksna
Session=${session}

[General]
DisplayServer=wayland
EOF
  systemctl enable sddm || echo SDDM_ENABLE_FAIL
  systemctl set-default graphical.target || echo GRAPHICAL_TARGET_FAIL
fi
echo "SESSION:${session:-none}"
echo INSTALL_DONE
