# UI + Icon Handoff Guide

目的：只分享 UI 与图标相关代码给第三方，不暴露下载业务逻辑。

## 建议分享范围

- `app/src/main/AndroidManifest.xml`
- `app/src/main/res/values/strings.xml`
- `app/src/main/res/values/colors.xml`
- `app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml`
- `app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml`
- `app/src/main/res/mipmap-*/ic_launcher_foreground.png`
- `app/src/main/java/com/lanzou/manga/downloader/MainActivity.kt`
- `app/src/main/java/com/lanzou/manga/downloader/ui/*`
- `app/build.gradle.kts` (UI 依赖版本)

## 不建议分享

- `data/repo/*`、`domain/*`、`data/config/*` 等业务与配置实现
- 任意链接、密码、混淆逻辑相关文件

## 一键导出

在仓库根目录执行：

```powershell
pwsh -File .\source_code_android\tools\export_ui_icon_bundle.ps1
```

默认输出到：

- `backup\archives\android_ui_icon_bundle_<timestamp>.zip`
