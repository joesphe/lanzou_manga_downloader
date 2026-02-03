# 蓝奏云下载器 - feapder版本

## 概述

蓝奏云下载器现在提供了基于feapder框架的新版本，具有以下优势：

- 更完善的日志记录系统
- 更好的命令行参数支持
- 更清晰的错误提示
- 改进的并发下载管理

## 新增功能

### 1. feapder命令行版本 (`feapder`)
```bash
uv run feapder --help
```

支持以下参数：
- `--url`: 蓝奏云分享链接
- `--password`: 分享密码
- `--download-dir`: 下载目录（默认：downloads）
- `--workers`: 并发数（默认：3）
- `--log-level`: 日志级别（DEBUG/INFO/WARNING/ERROR，默认：INFO）

### 2. feapder GUI版本 (`feapder-gui`)
```bash
uv run feapder-gui
```

提供图形界面，结合了GUI的便利性和feapder的强大日志功能。

- 功能特点：
  - 图形化界面操作
  - 实时日志显示
  - 进度条监控
  - 多线程下载支持
  - 通过环境变量或混淆解密设置提取码（界面不再显示密码输入框）
  - 支持设置蓝奏云链接
  - 可选择下载目录
  - 可选择性下载特定文件

## 使用示例

### 命令行版本
```bash
# 使用环境变量中的URL和密码
uv run feapder

# 指定URL和密码
uv run feapder --url "https://example.com/share" --password "1234" --download-dir "./my_downloads" --log-level DEBUG

# 使用特定的并发数
uv run feapder --workers 5 --log-level INFO
```

### GUI版本
```bash
uv run feapder-gui
```

## 技术特点

### 1. 改进的日志系统
- 更详细的日志记录
- 支持不同级别的日志输出
- 更好的错误追踪能力

### 2. 保持原有功能
- 保留了原有的"显示更多文件"分页功能
- 保持了文件名清理功能
- 继续支持混淆解密技术

### 3. 兼容性
- 与现有的GUI和CLI版本完全兼容
- 使用相同的混淆解密机制
- 保持相同的文件下载逻辑

## 安装和运行

### 开发环境
```bash
# 确保已安装依赖
uv sync

# 运行命令行版本
uv run feapder

# 运行GUI版本
uv run feapder-gui
```

### 生产环境（打包后）
- 可以像以前一样打包成exe文件
- 保持相同的混淆解密功能
- 支持命令行参数传递

## 总结

feapder版本提供了更强大的日志管理和命令行支持，同时保持了原有功能的完整性。用户可以选择使用传统的GUI/CLI版本，或者使用新的feapder版本以获得更好的日志记录和参数控制功能。