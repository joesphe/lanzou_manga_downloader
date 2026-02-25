# source_code_common 结构说明

## 目录定位
- 该目录用于放置 `dev/prod` 共享的核心实现，避免重复维护。

## 文件说明
- `lanzou_gui_core.py`
  - Windows GUI 与线程调度（仅界面层）。
- `lanzou_core.py`
  - 核心门面类与通用工具方法。
- `lanzou_list_fetcher.py`
  - 文件列表获取逻辑（`filemoreajax.php`、分页、风控节奏）。
- `lanzou_download_core.py`
  - 真实下载链接提取与 requests 下载。
- `lanzou_types.py`
  - `FileItem` / `ListFetchConfig` 等数据结构。
- `lanzou_errors.py`
  - 错误码与异常类型。
- `__init__.py`
  - 包标记文件。

## 依赖关系
- `source_code_prod/*` 和 `source_code_dev/*` 的入口文件都依赖本目录核心模块。

## 维护建议
- 新功能优先改这里，避免在 `dev/prod` 两边各改一份。
- 列表与下载逻辑已拆分为独立模块，便于迁移到 Android 端复用。
