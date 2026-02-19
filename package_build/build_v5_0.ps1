Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = "D:\lanzou_manga_downloader"
$SpecPath = Join-Path $RepoRoot "package_build\lanzou_downloader_gui_v5_0.spec"

pyinstaller --clean --noconfirm $SpecPath
