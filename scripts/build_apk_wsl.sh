#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-/mnt/d/lanzou_manga_downloader/source_code_android}"
ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-$HOME/Android/Sdk}"
CMDLINE_TOOLS_URL="${CMDLINE_TOOLS_URL:-https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip}"

log() {
  printf '\n[build_apk_wsl] %s\n' "$1"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing command: $1"; exit 1; }
}

log "Installing system packages (JDK17, unzip, wget, etc.)"
sudo apt update
sudo apt install -y openjdk-17-jdk wget unzip git zip ca-certificates

log "Ensuring Android SDK cmdline-tools are present"
mkdir -p "$ANDROID_SDK_ROOT/cmdline-tools"
if [ ! -x "$ANDROID_SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" ]; then
  TMP_ZIP="/tmp/cmdline-tools.zip"
  rm -f "$TMP_ZIP"
  wget -O "$TMP_ZIP" "$CMDLINE_TOOLS_URL"
  rm -rf "$ANDROID_SDK_ROOT/cmdline-tools/latest"
  unzip -q "$TMP_ZIP" -d "$ANDROID_SDK_ROOT/cmdline-tools"
  mv "$ANDROID_SDK_ROOT/cmdline-tools/cmdline-tools" "$ANDROID_SDK_ROOT/cmdline-tools/latest"
fi

export ANDROID_SDK_ROOT
export PATH="$PATH:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools"

require_cmd java
require_cmd sdkmanager

log "Accepting Android SDK licenses"
yes | sdkmanager --sdk_root="$ANDROID_SDK_ROOT" --licenses >/dev/null

log "Installing Android SDK packages"
sdkmanager --sdk_root="$ANDROID_SDK_ROOT" \
  "platform-tools" \
  "platforms;android-35" \
  "build-tools;35.0.0"

log "Ensuring Gradle 8.7"
if ! command -v gradle >/dev/null 2>&1 || ! gradle -v | grep -q "Gradle 8.7"; then
  TMP_GRADLE_ZIP="/tmp/gradle-8.7-bin.zip"
  rm -f "$TMP_GRADLE_ZIP"
  wget -O "$TMP_GRADLE_ZIP" https://services.gradle.org/distributions/gradle-8.7-bin.zip
  sudo rm -rf /opt/gradle-8.7
  sudo unzip -q "$TMP_GRADLE_ZIP" -d /opt
fi
export PATH="$PATH:/opt/gradle-8.7/bin"

log "Building APK in: $PROJECT_DIR"
cd "$PROJECT_DIR"

if [ ! -f "gradlew" ]; then
  gradle wrapper --gradle-version 8.7
fi

chmod +x gradlew
./gradlew --no-daemon assembleDebug

log "Build completed"
log "APK path: $PROJECT_DIR/app/build/outputs/apk/debug/app-debug.apk"
