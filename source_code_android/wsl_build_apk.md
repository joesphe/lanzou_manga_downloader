# WSL Ubuntu 24.04 构建 Android APK 指南

本文档给出在 WSL2 + Ubuntu 24.04 环境下，安装 Android 构建依赖并编译 APK 的完整命令。

## 1. 系统依赖安装

```bash
sudo apt update
sudo apt install -y openjdk-17-jdk unzip wget curl git ca-certificates
```

验证 Java：

```bash
java -version
javac -version
```

## 2. 安装 Android SDK Command-line Tools

```bash
mkdir -p "$HOME/Android/Sdk/cmdline-tools"
cd /tmp
wget -O commandlinetools-linux.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
unzip -q commandlinetools-linux.zip -d "$HOME/Android/Sdk/cmdline-tools"
mv "$HOME/Android/Sdk/cmdline-tools/cmdline-tools" "$HOME/Android/Sdk/cmdline-tools/latest"
```

## 3. 配置环境变量

```bash
cat <<'EOF' >> ~/.bashrc
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export ANDROID_HOME=$HOME/Android/Sdk
export ANDROID_SDK_ROOT=$ANDROID_HOME
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools
EOF

source ~/.bashrc
```

## 4. 安装 Android SDK 组件

本项目当前 `compileSdk=35`，建议安装以下组件：

```bash
yes | sdkmanager --licenses
sdkmanager "platform-tools" "platforms;android-35" "build-tools;35.0.0"
```

可选（如果你要在 WSL 内创建 AVD）：

```bash
sdkmanager "emulator" "system-images;android-35;google_apis;x86_64"
```

## 5. 进入项目目录

```bash
cd /mnt/d/lanzou_manga_downloader/source_code_android
```

## 6. Gradle Wrapper（若仓库缺失时）

先检查：

```bash
ls -la gradlew gradle/wrapper
```

如果缺失，执行：

```bash
sudo apt install -y gradle
gradle wrapper --gradle-version 8.7
chmod +x gradlew
```

## 7. 编译 APK

### 7.1 Debug APK

```bash
./gradlew --no-daemon clean :app:assembleDebug
```

输出：

```text
app/build/outputs/apk/debug/app-debug.apk
```

### 7.2 Release APK（未签名或已签名）

```bash
./gradlew --no-daemon clean :app:assembleRelease
```

输出通常为以下之一：

```text
app/build/outputs/apk/release/app-release-unsigned.apk
app/build/outputs/apk/release/app-release.apk
```

## 8. Release 签名（可选，但上架/分发推荐）

### 8.1 生成 keystore

```bash
mkdir -p ~/keys
keytool -genkeypair -v \
  -keystore ~/keys/lanzou-release.jks \
  -alias release \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000
```

### 8.2 配置签名参数

在 `source_code_android` 下创建 `keystore.properties`（可参考 `keystore.properties.example`）：

```properties
storeFile=/home/<your_user>/keys/lanzou-release.jks
storePassword=YOUR_STORE_PASSWORD
keyAlias=release
keyPassword=YOUR_KEY_PASSWORD
```

### 8.3 重新编译 Release

```bash
./gradlew --no-daemon clean :app:assembleRelease
```

若签名配置正确，产物为：

```text
app/build/outputs/apk/release/app-release.apk
```

## 9. 常见问题

1. `sdkmanager: command not found`
- 说明 PATH 未生效，执行 `source ~/.bashrc`，并确认 `$ANDROID_HOME/cmdline-tools/latest/bin` 存在。

2. `Could not determine java version` / JDK 版本不对
- 确认 `java -version` 是 17，并且 `JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64`。

3. `SDK location not found`
- 确认 `ANDROID_HOME` / `ANDROID_SDK_ROOT` 已设置，或在 `source_code_android/local.properties` 写入：

```properties
sdk.dir=/home/<your_user>/Android/Sdk
```

4. WSL 内无法直接运行 Android Studio 图形界面
- 建议在 Windows 侧 Android Studio 打开项目；WSL 主要用于命令行构建。
