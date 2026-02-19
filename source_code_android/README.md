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

## 说明
- 当前下载目录为：`/Android/data/com.lanzou.downloader/files/downloads`。
- 若目标站点调整下载页脚本，优先更新 `resolveRealDownloadUrl()` 解析规则。
