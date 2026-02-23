# source_code_dev 结构说明

## 目录定位
- 开发版入口目录。
- 主要特点：使用环境变量注入链接和密码，便于本地调试与验证。

## 文件说明
- `lanzou_downloader_gui_dev.py`
  - 开发版默认入口（当前指向 `mix` 模式）。
- `lanzou_downloader_gui_dev_mix.py`
  - 开发版混合模式入口：
    - requests 主链路
    - 失败时可走浏览器兜底提链
  - 需要环境变量：
    - `LANZOU_URL`
    - `LANZOU_PASSWORD`
- `lanzou_downloader_gui_dev_pure_requests.py`
  - 开发版纯 requests 入口：
    - 禁用浏览器初始化
    - 禁用浏览器兜底
  - 同样需要环境变量：
    - `LANZOU_URL`
    - `LANZOU_PASSWORD`

## 与核心模块关系
- 该目录只保留“入口层”，核心逻辑在：
  - `source_code_common/lanzou_gui_core.py`

## 运行方式
- 默认入口：
  - `python source_code_dev/lanzou_downloader_gui_dev.py`
- 混合模式：
  - `python source_code_dev/lanzou_downloader_gui_dev_mix.py`
- 纯 requests：
  - `python source_code_dev/lanzou_downloader_gui_dev_pure_requests.py`

## 维护建议
- 开发版只做调试参数、实验开关与验证流程。
- 业务逻辑改动尽量在 `source_code_common` 完成。
