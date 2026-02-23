# Android Migration Skeleton

This module is a starter Android project for migrating the current Python downloader logic.

## Goals (MVP)
- Fetch Lanzou file list
- Resolve real download URL via requests flow (`i -> fn -> ajaxm.php`)
- Download files with progress
- Handle `acw_sc__v2` challenge in pure network mode

## Current status
- Project skeleton and core interfaces are created.
- Resolver/challenge/download paths are scaffolded with pragmatic defaults and TODO markers.
- Default URL/password are injected from obfuscated constants (same algorithm as desktop production).

## Recommended next steps
1. Open this folder in Android Studio.
2. Set your package name if needed.
3. Fill constants in `BuildConfig` or local storage for default URL/password.
4. Complete parser edge-cases in `LanzouResolver`.
5. Wire UI actions in `MainViewModel`.
6. Add instrumentation tests for resolver/challenge functions.
