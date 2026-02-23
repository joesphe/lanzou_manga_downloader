# source_code_common 结构说明

## 目录定位
- 该目录用于放置 `dev/prod` 共享的核心实现，避免重复维护。

## 文件说明
- `lanzou_gui_core.py`
  - 项目核心代码（GUI + 下载器主逻辑）。
  - 包含：
    - 文件列表获取（`filemoreajax.php`）
    - 真实下载链接提取（requests 主链路）
    - `acw_sc__v2` 挑战识别与计算
    - 下载与进度回调
    - 浏览器兜底提链（可选）
- `__init__.py`
  - 包标记文件。

## 依赖关系
- `source_code_prod/*` 和 `source_code_dev/*` 的入口文件都依赖本目录核心模块。

## 维护建议
- 新功能优先改这里，避免在 `dev/prod` 两边各改一份。
- 如果后续继续重构，可把该文件再拆分为：
  - `resolver`（提链）
  - `challenge`（风控挑战）
  - `downloader`（下载与重试）
  - `gui`（界面层）
