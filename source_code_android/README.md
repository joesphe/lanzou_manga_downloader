# Android Migration (source_code_android)

该目录是基于 `source_code_prod/lanzoub_downloader_gui.py` 迁移出的 Android 原生版本（Kotlin + Compose）。

## 兼容范围
- `minSdk=31` (Android 12)
- `targetSdk=35`（Android 15）
- Android 16 可在新 SDK 发布后把 `compileSdk/targetSdk` 升级到对应版本。

## 已迁移能力
- 分享页参数提取：`fid/uid/t/k`
- `filemoreajax.php` 分页获取文件列表（`pg` 翻页、重试、`zt` 判定、去重）
- 文件下载：解析真实下载直链后流式下载到应用私有目录

## 目录结构
- `app/src/main/java/com/lanzou/downloader/data/LanzouRepository.kt`：核心网络逻辑
- `app/src/main/java/com/lanzou/downloader/ui/MainViewModel.kt`：状态管理
- `app/src/main/java/com/lanzou/downloader/ui/MainScreen.kt`：Compose UI

## 运行方式
1. 用 Android Studio 打开 `source_code_android`。
2. 等待 Gradle 同步并下载依赖。
3. 连接 Android 12+ 真机，点击 Run。

## WSL (Ubuntu 24.04) 构建
1. 进入目录：`cd /mnt/d/lanzou_manga_downloader/source_code_android`
2. 若仓库尚无 Gradle Wrapper，先生成：
   - `sudo apt install -y gradle`
   - `gradle wrapper --gradle-version 8.7`
3. 构建 debug APK：`./gradlew --no-daemon :app:assembleDebug`
4. 构建 release APK（未签名或已签名，取决于是否配置 `keystore.properties`）：
   - `./gradlew --no-daemon :app:assembleRelease`

## Release 签名配置
1. 生成签名文件（示例）：
   - `keytool -genkeypair -v -keystore ~/keys/lanzou-release.jks -alias release -keyalg RSA -keysize 2048 -validity 10000`
2. 在 `source_code_android` 下创建 `keystore.properties`（可参考 `keystore.properties.example`）：
   - `storeFile=/home/<user>/keys/lanzou-release.jks`
   - `storePassword=***`
   - `keyAlias=release`
   - `keyPassword=***`
3. 执行 `./gradlew --no-daemon :app:assembleRelease` 生成已签名 release APK。

## 说明
- 当前下载目录为：`/Android/data/com.lanzou.downloader/files/downloads`。
- 若目标站点调整下载页脚本，优先更新 `resolveRealDownloadUrls()` 解析规则。
