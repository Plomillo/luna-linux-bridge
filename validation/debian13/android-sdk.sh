#!/bin/bash
# Installs the Android command-line SDK into the guest so case 297 can observe it.
# A missing download stays a recorded failure. This does not certify mobile compilation.
set -u
if [ "$(id -u)" -ne 0 ]; then
  echo ANDROID_NOT_ROOT
  exit 1
fi
if [ -x /opt/android-sdk/emulator/emulator ] && command -v adb >/dev/null; then
  ln -sfn /opt/android-sdk/emulator/emulator /usr/local/bin/emulator
  echo ANDROID_SDK_PRESENT
  exit 0
fi
export DEBIAN_FRONTEND=noninteractive
apt-get install -y openjdk-21-jre-headless unzip ca-certificates adb || {
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
yes | timeout 900 /opt/android-sdk/cmdline-tools/latest/bin/sdkmanager --sdk_root=/opt/android-sdk "platform-tools" "emulator" || {
  echo ANDROID_SDKMANAGER_FAIL
  exit 1
}
ln -sfn /opt/android-sdk/platform-tools/adb /usr/local/bin/adb
ln -sfn /opt/android-sdk/emulator/emulator /usr/local/bin/emulator
install -d /etc/profile.d
printf 'export ANDROID_HOME=/opt/android-sdk\nexport PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"\n' > /etc/profile.d/android-sdk.sh
if ! /usr/local/bin/adb version | grep -q "Android Debug Bridge"; then
  echo ANDROID_ADB_FAIL
  exit 1
fi
if ! /usr/local/bin/emulator -version >/dev/null; then
  echo ANDROID_EMULATOR_FAIL
  exit 1
fi
echo ANDROID_SDK_OK
