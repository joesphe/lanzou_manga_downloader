# Lanzou Downloader Android

Android client for Lanzou file listing and downloads.

## Current scope
- Fetch file list.
- Resolve real download links (`i -> fn -> ajaxm.php` flow).
- Download selected files with progress.
- Solve `acw_sc__v2` challenge in pure network mode.
- UI built with Compose + Miuix.

## Build environment
- Recommended: WSL Ubuntu + JDK 17.
- Gradle wrapper entry: `./gradlew` (Linux/macOS/WSL).

Build debug APK:

```bash
cd /mnt/d/lanzou_manga_downloader/source_code_android
./gradlew :app:assembleDebug --no-daemon
```

Output:
- `app/build/outputs/apk/debug/app-debug.apk`

## Key module layout
- `app/src/main/java/com/lanzou/manga/downloader/data`: config, network, repository, prefs
- `app/src/main/java/com/lanzou/manga/downloader/domain`: challenge, resolver, downloader, use cases
- `app/src/main/java/com/lanzou/manga/downloader/ui`: Compose UI, state, selectors, view model

## Notes
- Project tracks source files only; local caches and build outputs should be ignored.
- If download behavior changes, update both resolver and parser paths together.
