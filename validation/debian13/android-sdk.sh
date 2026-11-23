#!/bin/bash
# Installs the Android command-line SDK into the guest so case 297 can observe it.
# A missing download or a failed emulator binary stays a recorded failure.
# This does not certify mobile compilation and does not invent an emulator wrapper.
set -u
if [ "$(id -u)" -ne 0 ]; then
  echo ANDROID_NOT_ROOT
  exit 1
fi
free_b=$(df -B1 --output=avail / | tail -n 1 | tr -d ' ')
if [ "$free_b" -lt $((1500 * 1024 * 1024)) ]; then
  echo "ANDROID_DISK $free_b"
  exit 1
fi
if [ -x /opt/android-sdk/emulator/emulator ] && /opt/android-sdk/emulator/emulator -version >/dev/null 2>&1 && /opt/android-sdk/platform-tools/adb version 2>/dev/null | grep -q "Android Debug Bridge"; then
  ln -sfn /opt/android-sdk/emulator/emulator /usr/local/bin/emulator
  ln -sfn /opt/android-sdk/platform-tools/adb /usr/local/bin/adb
  echo ANDROID_SDK_PRESENT
  exit 0
fi
export DEBIAN_FRONTEND=noninteractive
export ANDROID_HOME=/opt/android-sdk
export ANDROID_SDK_ROOT=/opt/android-sdk
apt-get install -y openjdk-21-jre-headless unzip ca-certificates curl \
  libpulse0 libnss3 libx11-6 libxext6 libxcomposite1 libxcursor1 libxi6 libxtst6 libxrandr2 libxkbfile1 || {
  echo ANDROID_PACKAGES_FAIL
  exit 1
}
tmp=$(mktemp -d)
url=https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
if ! curl -fL --retry 3 --max-time 180 -o "$tmp/cmdtools.zip" "$url"; then
  echo ANDROID_DOWNLOAD_FAIL
  exit 1
fi
mkdir -p /opt/android-sdk/cmdline-tools
unzip -q "$tmp/cmdtools.zip" -d "$tmp"
rm -rf /opt/android-sdk/cmdline-tools/latest
mv "$tmp/cmdline-tools" /opt/android-sdk/cmdline-tools/latest
mkdir -p /root/.android
touch /root/.android/repositories.cfg
yes | timeout 180 /opt/android-sdk/cmdline-tools/latest/bin/sdkmanager --sdk_root=/opt/android-sdk --licenses >/var/log/android-licenses.log 2>&1 || true
yes | timeout 900 /opt/android-sdk/cmdline-tools/latest/bin/sdkmanager --sdk_root=/opt/android-sdk "platform-tools" "emulator" || {
  echo ANDROID_SDKMANAGER_FAIL
  exit 1
}
ln -sfn /opt/android-sdk/platform-tools/adb /usr/local/bin/adb
ln -sfn /opt/android-sdk/emulator/emulator /usr/local/bin/emulator
install -d /etc/profile.d
printf 'export ANDROID_HOME=/opt/android-sdk\nexport ANDROID_SDK_ROOT=/opt/android-sdk\nexport PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"\n' > /etc/profile.d/android-sdk.sh
if ! /usr/local/bin/adb version | grep -q "Android Debug Bridge"; then
  echo ANDROID_ADB_FAIL
  exit 1
fi
if ! /usr/local/bin/emulator -version >/var/log/android-emulator-version.txt 2>&1; then
  echo ANDROID_EMULATOR_FAIL
  tail -n 40 /var/log/android-emulator-version.txt || true
  exit 1
fi
echo ANDROID_SDK_OK
