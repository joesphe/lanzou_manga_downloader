# 模块说明（Windows 端）

本目录当前按“核心逻辑 / 列表 / 下载 / UI”拆分，便于后续迁移到 Android。

## 核心入口
- `lanzou_core.py`
  - `OptimizedLanzouDownloader`：核心门面类
  - 仅保留轻量代理方法，具体逻辑分别委派给 list_fetcher / download_core

## 列表获取
- `lanzou_list_fetcher.py`
  - `LanzouListFetcher.fetch()`：列表抓取、风控处理、分页与节奏策略

## 下载逻辑
- `lanzou_download_core.py`
  - `download_with_requests`
  - `download_single_file_optimized`
  - `download_single_file`
  - `monitor_download_progress`
  - `get_real_download_url` / `is_download_url_valid`

## 数据结构
- `lanzou_types.py`
  - `FileItem`：统一文件元数据
  - `ListFetchConfig`：列表节奏配置

## 错误码
- `lanzou_errors.py`
  - `ErrorCode` / `LanzouError`

## GUI
- `lanzou_gui_core.py`
  - Windows UI 与线程调度
