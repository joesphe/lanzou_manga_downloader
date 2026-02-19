#!/usr/bin/env bash
set -euo pipefail

# WSL Ubuntu 24.04 helper for Android build environment + APK build.
# Usage:
#   bash wsl_android_build.sh all
#   bash wsl_android_build.sh install
#   bash wsl_android_build.sh build
#   bash wsl_android_build.sh sign
# Optional env overrides:
#   ANDROID_SDK_ROOT, BUILD_TOOLS_VERSION, ANDROID_PLATFORM

ACTION="${1:-all}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR_DEFAULT="${SCRIPT_DIR}/source_code_android"
PROJECT_DIR="${PROJECT_DIR:-$PROJECT_DIR_DEFAULT}"

ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-$HOME/Android/Sdk}"
ANDROID_HOME="${ANDROID_HOME:-$ANDROID_SDK_ROOT}"
CMDLINE_TOOLS_DIR="$ANDROID_SDK_ROOT/cmdline-tools/latest"
ANDROID_PLATFORM="${ANDROID_PLATFORM:-android-35}"
BUILD_TOOLS_VERSION="${BUILD_TOOLS_VERSION:-35.0.0}"

print_info() {
  echo "[INFO] $*"
}

print_warn() {
  echo "[WARN] $*"
}

require_ubuntu() {
  if [[ ! -f /etc/os-release ]]; then
    print_warn "无法识别系统，继续执行。"
    return
  fi
  # shellcheck disable=SC1091
  source /etc/os-release
  if [[ "${ID:-}" != "ubuntu" ]]; then
    print_warn "检测到系统不是 Ubuntu (${ID:-unknown})，继续执行。"
  fi
}

ensure_base_packages() {
  print_info "安装基础依赖..."
  sudo apt update
  sudo apt install -y openjdk-17-jdk unzip wget curl git ca-certificates
}

ensure_env_in_bashrc() {
  local bashrc="$HOME/.bashrc"
  local marker="# >>> android-sdk-wsl >>>"

  if grep -Fq "$marker" "$bashrc"; then
    print_info "~/.bashrc 已包含 Android 环境变量块，跳过追加。"
  else
    cat >> "$bashrc" <<EOF
$marker
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export ANDROID_HOME=$ANDROID_HOME
export ANDROID_SDK_ROOT=$ANDROID_SDK_ROOT
export PATH=\$PATH:$CMDLINE_TOOLS_DIR/bin:$ANDROID_SDK_ROOT/platform-tools
# <<< android-sdk-wsl <<<
EOF
    print_info "已写入 Android 环境变量到 ~/.bashrc"
  fi

  export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
  export ANDROID_HOME="$ANDROID_HOME"
  export ANDROID_SDK_ROOT="$ANDROID_SDK_ROOT"
  export PATH="$PATH:$CMDLINE_TOOLS_DIR/bin:$ANDROID_SDK_ROOT/platform-tools"
}

install_cmdline_tools() {
  if [[ -x "$CMDLINE_TOOLS_DIR/bin/sdkmanager" ]]; then
    print_info "Android cmdline-tools 已安装，跳过下载。"
    return
  fi

  print_info "安装 Android cmdline-tools..."
  mkdir -p "$ANDROID_SDK_ROOT/cmdline-tools"

  local zip_file
  zip_file="$(mktemp -p /tmp cmdline-tools-XXXXXX.zip)"

  wget -O "$zip_file" "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
  unzip -q "$zip_file" -d "$ANDROID_SDK_ROOT/cmdline-tools"
  rm -f "$zip_file"

  if [[ -d "$ANDROID_SDK_ROOT/cmdline-tools/cmdline-tools" ]]; then
    rm -rf "$CMDLINE_TOOLS_DIR"
    mv "$ANDROID_SDK_ROOT/cmdline-tools/cmdline-tools" "$CMDLINE_TOOLS_DIR"
  fi

  if [[ ! -x "$CMDLINE_TOOLS_DIR/bin/sdkmanager" ]]; then
    echo "[ERROR] cmdline-tools 安装失败：sdkmanager 不存在。" >&2
    exit 1
  fi
}

install_android_sdk_packages() {
  print_info "接受 Android SDK 许可..."
  yes | sdkmanager --licenses >/dev/null

  print_info "安装 Android SDK 组件..."
  sdkmanager \
    "platform-tools" \
    "platforms;$ANDROID_PLATFORM" \
    "build-tools;$BUILD_TOOLS_VERSION"
}

ensure_gradle_wrapper() {
  cd "$PROJECT_DIR"

  if [[ -x "./gradlew" && -f "./gradle/wrapper/gradle-wrapper.properties" ]]; then
    print_info "Gradle Wrapper 已存在。"
    return
  fi

  print_warn "未检测到 Gradle Wrapper，尝试生成..."
  if ! command -v gradle >/dev/null 2>&1; then
    sudo apt install -y gradle
  fi

  gradle wrapper --gradle-version 8.7
  chmod +x ./gradlew
}

build_apk() {
  cd "$PROJECT_DIR"

  print_info "开始构建 Debug APK..."
  ./gradlew --no-daemon clean :app:assembleDebug

  print_info "开始构建 Release APK..."
  ./gradlew --no-daemon :app:assembleRelease

  print_info "构建完成，输出目录："
  echo "  - $PROJECT_DIR/app/build/outputs/apk/debug"
  echo "  - $PROJECT_DIR/app/build/outputs/apk/release"

  if [[ -f "$PROJECT_DIR/app/build/outputs/apk/release/app-release.apk" ]]; then
    print_info "检测到已签名 release APK: app-release.apk"
  elif [[ -f "$PROJECT_DIR/app/build/outputs/apk/release/app-release-unsigned.apk" ]]; then
    print_warn "检测到未签名 release APK: app-release-unsigned.apk"
    print_warn "如需签名，请配置 $PROJECT_DIR/keystore.properties"
  fi
}

validate_signing_properties() {
  local prop_file="$PROJECT_DIR/keystore.properties"
  local required_keys=("storeFile" "storePassword" "keyAlias" "keyPassword")

  if [[ ! -f "$prop_file" ]]; then
    echo "[ERROR] 未找到 $prop_file" >&2
    echo "[ERROR] 请先基于 keystore.properties.example 创建并填写签名配置。" >&2
    exit 1
  fi

  for key in "${required_keys[@]}"; do
    local val
    val="$(grep -E "^${key}=" "$prop_file" | head -n1 | cut -d'=' -f2- || true)"
    if [[ -z "${val// }" ]]; then
      echo "[ERROR] keystore.properties 缺少或为空: $key" >&2
      exit 1
    fi
  done
}

build_signed_release() {
  cd "$PROJECT_DIR"
  validate_signing_properties

  print_info "开始构建已签名 Release APK..."
  ./gradlew --no-daemon clean :app:assembleRelease

  local signed_apk="$PROJECT_DIR/app/build/outputs/apk/release/app-release.apk"
  if [[ ! -f "$signed_apk" ]]; then
    echo "[ERROR] 未检测到已签名 APK: $signed_apk" >&2
    echo "[ERROR] 请检查 keystore.properties 路径和密码配置是否正确。" >&2
    exit 1
  fi

  print_info "已签名 APK 构建完成: $signed_apk"
}

run_install() {
  require_ubuntu
  ensure_base_packages
  install_cmdline_tools
  ensure_env_in_bashrc
  install_android_sdk_packages
  ensure_gradle_wrapper
}

case "$ACTION" in
  install)
    run_install
    ;;
  build)
    ensure_env_in_bashrc
    ensure_gradle_wrapper
    build_apk
    ;;
  sign)
    ensure_env_in_bashrc
    ensure_gradle_wrapper
    build_signed_release
    ;;
  all)
    run_install
    build_apk
    ;;
  *)
    echo "用法: bash wsl_android_build.sh [install|build|sign|all]"
    exit 1
    ;;
esac
