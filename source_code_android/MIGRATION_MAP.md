# Python -> Android Migration Map

## Core mapping
- Python: `login_and_get_files`
  - Android target: `data/repo/LanzouRepository.fetchFiles`
- Python: `get_real_download_url`
  - Android target: `domain/resolver/LanzouResolver.resolveRealUrl`
- Python: `acw_sc__v2` challenge helpers
  - Android target: `domain/challenge/AcwSolver`
- Python: `download_with_requests`
  - Android target: `domain/download/DownloadManager.download`

## Strategy modes
- Mix mode (requests + browser fallback)
  - Android initial recommendation: do not implement browser fallback.
  - Keep pure network mode as baseline.
- Pure requests mode
  - Current Android skeleton aligns with this mode.

## Gaps to complete
1. Replace regex-based JSON extraction in `LanzouRepository` with robust parser.
2. Add pagination loop for file list (`pg=1..n`).
3. Add download queue with `WorkManager`.
4. Add persistent settings for URL/password.
5. Add tests using known HTML fixtures from desktop logs.
