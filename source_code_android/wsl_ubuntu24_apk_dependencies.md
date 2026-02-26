# WSL Ubuntu 24.04 APK 构建依赖安装命令

> 目标：不使用 Android Studio，仅在 WSL(Ubuntu 24.04) 命令行构建 `source_code_android` APK。

## 1. 系统基础依赖

```bash
sudo apt update
sudo apt install -y \
  openjdk-17-jdk \
  unzip zip wget curl ca-certificates git \
  build-essential \
  lib32stdc++6 lib32z1
```

检查版本：

```bash
java -version
javac -version
```

## 2. 安装 Android SDK Command-line Tools

```bash
mkdir -p "$HOME/Android/Sdk/cmdline-tools"
cd /tmp
```

下载 commandline-tools（按常见版本号依次尝试，成功一个即可）：

```bash
for v in 13114758 12266719 11076708; do
  url="https://dl.google.com/android/repository/commandlinetools-linux-${v}_latest.zip"
  echo "Trying: $url"
  if wget -O cmdline-tools.zip "$url"; then
    break
  fi
done
```

解压并整理目录：

```bash
unzip -o cmdline-tools.zip -d "$HOME/Android/Sdk/cmdline-tools"
mkdir -p "$HOME/Android/Sdk/cmdline-tools/latest"
if [ -d "$HOME/Android/Sdk/cmdline-tools/cmdline-tools" ]; then
  mv "$HOME/Android/Sdk/cmdline-tools/cmdline-tools/"* "$HOME/Android/Sdk/cmdline-tools/latest/"
fi
```

## 3. 配置环境变量

```bash
cat >> ~/.bashrc <<'EOF'
export ANDROID_SDK_ROOT=$HOME/Android/Sdk
export ANDROID_HOME=$ANDROID_SDK_ROOT
export PATH=$PATH:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin
export PATH=$PATH:$ANDROID_SDK_ROOT/platform-tools
EOF
source ~/.bashrc
```

## 4. 安装 Android 构建组件

先接受 license：

```bash
yes | sdkmanager --licenses
```

安装常用构建组件（优先 36，对应当前项目 compileSdk=36）：

```bash
sdkmanager \
  "platform-tools" \
  "platforms;android-36" \
  "build-tools;36.0.0"
```

如果 36 组件暂不可用，可先安装 35：

```bash
sdkmanager \
  "platforms;android-35" \
  "build-tools;35.0.0"
```

## 5. Gradle（仅当项目没有 `gradlew` 时需要）

```bash
sudo apt install -y gradle
```

在项目目录生成 wrapper（一次性）：

```bash
cd /mnt/d/lanzou_manga_downloader/source_code_android
gradle wrapper --gradle-version 8.10
```

## 6. 构建 APK（单目录输出）

```bash
cd /mnt/d/lanzou_manga_downloader/source_code_android
./gradlew --no-daemon clean assembleDebug
```

产物位置：

```bash
ls -lh app/build/outputs/apk/debug/
```

### 私有参数注入（默认读取 private_credentials.properties）

将 `source_code_android/private_credentials.template.properties` 复制到你自己的私有位置，
并写入以下字段（不要提交到 Git）：

- `LANZOU_PROD_URL`
- `LANZOU_PROD_PASSWORD`

默认会自动读取 `source_code_android/private_credentials.properties`。  
也可通过 `~/.gradle/gradle.properties` 或命令行 `-P` 覆盖。

示例（命令行）：

```bash
./gradlew --no-daemon assembleDebug \
  -PLANZOU_PROD_URL="https://example.lanzou.com/xxxx" \
  -PLANZOU_PROD_PASSWORD="your_password"
```
