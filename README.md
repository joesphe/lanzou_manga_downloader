# 蓝奏云漫画下载器 (Lanzou Manga Downloader)

一个专门用于从蓝奏云网盘批量下载漫画或文件的工具。

## 项目结构

本项目采用双模式设计：

### 开发版本 (Development Version)
- 文件位置：`source_code_dev/lanzou_downloader_gui_dev.py`
- 特点：
  - 无自动日志生成
  - 从环境变量读取配置
  - 便于调试和开发
- 需要设置环境变量：
  - `LANZOU_URL`: 蓝奏云分享链接
  - `LANZOU_PASSWORD`: 分享密码

### 生产版本 (Production Version)
- 文件位置：`lanzou_downloader_gui_prod.py`（未公开）
- 特点：
  - 无自动日志生成
  - 使用混淆技术保护链接和密码
  - 适用于打包分发
- 已添加到 `.gitignore`，不会被提交到版本控制系统

## 功能特性

- 图形用户界面 (GUI)
- 自动登录蓝奏云分享链接
- 批量下载文件
- 多线程下载支持
- 下载进度显示
- 文件名安全处理（移除非法字符）

## 环境要求

- Python 3.12+
- Microsoft Edge 浏览器（用于自动化下载）

## 安装依赖

```bash
pip install -r requirements.txt
```

## 开发版本使用方法

1. 设置环境变量：

### 在Linux/macOS/Bash中：
```bash
export LANZOU_URL="你的蓝奏云链接"
export LANZOU_PASSWORD="你的密码"
```

### 在Windows PowerShell中：
```powershell
$env:LANZOU_URL="你的蓝奏云链接"
$env:LANZOU_PASSWORD="你的密码"
```

2. 运行开发版本：
```bash
python source_code_dev/lanzou_downloader_gui_dev.py
```

## 配置说明

### 开发环境配置
- 通过环境变量 `LANZOU_URL` 和 `LANZOU_PASSWORD` 配置蓝奏云链接和密码
- 适用于开发和测试阶段

### 生产环境配置
- 使用内置的混淆算法保护链接和密码
- 链接和密码硬编码在混淆数据中
- 适用于分发给最终用户

## 技术栈

- Python 3.12+
- Tkinter (GUI)
- DrissionPage (网页自动化)
- PyInstaller (打包工具)

## 注意事项

1. 由于使用了浏览器自动化技术，请确保 Microsoft Edge 浏览器已安装
2. 生产版本使用了代码混淆技术来保护敏感信息
3. 开发版本需要手动设置环境变量，便于修改和调试
4. 自动日志功能已被移除，可通过命令行重定向输出到日志文件

## 项目文件说明

- `source_code_dev/`: 存放开发版本源代码
- `lanzou_downloader_gui_prod.py`: 生产版本源代码（已加入 .gitignore）
- `package_exe.py`: 打包脚本
- `requirements.txt`: Python 依赖包列表
- `.gitignore`: 版本控制忽略规则，已包含生产版本文件

## 日志管理

项目不再自动生成日志文件，如需日志记录，可使用命令行重定向：

### 在Linux/macOS/Bash中：
```bash
# 将输出重定向到日志文件（缓冲模式）
python lanzou_downloader_gui_dev.py > lanzou_downloader.log 2>&1 &

# 实时输出重定向（无缓冲模式）- 推荐
python -u lanzou_downloader_gui_dev.py 2>&1 | tee lanzou_downloader.log &

# 或者后台运行并实时输出
nohup python -u lanzou_downloader_gui_dev.py | tee lanzou_downloader.log &
```

### 在Windows PowerShell中：
```powershell
# 将输出重定向到日志文件
Start-Process -FilePath "python" -ArgumentList "lanzou_downloader_gui_dev.py" -RedirectStandardOutput "lanzou_downloader.log" -RedirectStandardError "lanzou_downloader_err.log"

# 或者使用管道重定向（适用于交互式运行）
python lanzou_downloader_gui_dev.py *> lanzou_downloader.log

# 实时输出重定向（PowerShell 7+）- 推荐
python -u lanzou_downloader_gui_dev.py 2>&1 | Tee-Object -FilePath "lanzou_downloader.log"

# 后台运行（不阻塞当前终端）
Start-Process -FilePath "python" -ArgumentList "lanzou_downloader_gui_dev.py" -WindowStyle Hidden
```

### Windows命令提示符(cmd)：
```cmd
# 将输出重定向到日志文件
python lanzou_downloader_gui_dev.py > lanzou_downloader.log 2>&1

# 实时输出重定向 - 推荐
python -u lanzou_downloader_gui_dev.py > lanzou_downloader.log 2>&1 &
```

### 实时日志监控
如果需要实时监控日志文件，可以使用以下命令：

#### Linux/macOS:
```bash
# 实时监控日志文件变化
tail -f lanzou_downloader.log
```

#### Windows PowerShell:
```powershell
# 实时监控日志文件变化
Get-Content lanzou_downloader.log -Wait
```

## EXE文件使用说明

项目已提供打包好的EXE文件，已经发布到release

### 运行EXE文件

1. 双击 `lanzou_downloader_gui.exe` 文件即可启动应用
2. 或在命令行中运行：
```cmd
dist\lanzou_downloader_gui.exe
```

### EXE文件特点

- 独立可执行文件，无需安装Python环境
- 内置混淆保护的链接和密码
- 包含所有必要依赖项
- 文件大小约24MB

## 版本历史

### v6.0 (最新版本)
- 代码架构重构：将核心逻辑抽离至 `source_code_common/lanzou_gui_core.py`，`dev/prod` 目录改为轻量入口层
- 新增双模式入口：
  - 生产版：`source_code_prod/lanzoub_downloader_gui_mix.py`（requests + 浏览器兜底）
  - 生产版：`source_code_prod/lanzoub_downloader_gui_pure_requests.py`（纯 requests）
  - 开发版：`source_code_dev/lanzou_downloader_gui_dev_mix.py`（requests + 浏览器兜底）
  - 开发版：`source_code_dev/lanzou_downloader_gui_dev_pure_requests.py`（纯 requests）
- 纯 requests 下载链路增强：新增 `acw_sc__v2` 挑战识别与自动求解，避免将挑战 HTML 误保存为文件
- 下载可靠性提升：增加“响应仍为 HTML 时阻止落盘”的保护，避免 5KB 假文件
- 入口可执行性优化：支持以绝对路径直接启动脚本（自动注入项目根路径）
- 发布产物：
  - `release/v6.0/lanzoub_downloader_gui_mix_v6_0.exe`

### v5.1
- 下载链路升级为“浏览器仅负责获取真实下载链接”，文件下载统一走 `requests`，并移除浏览器下载兜底路径
- 新增真实链接有效性校验：下载前基于 `HEAD` + `Range GET (bytes=0-0)` 与 `Content-Type` 做轻量判断
- 新增“校验失败先直下”策略：为避免误判可用链接，校验不通过时仍先尝试直链下载，失败后再判定该文件失败
- 新增滚动预取（pipeline）：下载第 1 个文件时后台并发预取后续文件真实链接，后续文件优先使用缓存直链
- 预取与下载时序优化：第 1 个文件始终实时取链下载，后续文件下载前自动校验链接，过期则自动重新获取
- GUI 交互与进度显示优化：统一控制区布局、当前文件进度条、总体进度文本与状态栏实时更新

### v5.0
- 文件列表获取改为优先使用 `filemoreajax.php` 直连分页模式，不再依赖持续点击“显示更多”
- 完整支持 `pg` 分页拉取（每页最多 50 条），可自动适配后续文件数量增长
- 增强稳定性：新增 `zt=4` 与网络异常重试机制，失败时自动刷新页面上下文后继续请求
- 自动刷新请求上下文参数，降低会话失效导致的分页中断概率
- 文件列表结果增加去重处理，避免跨页重复项影响 UI 展示
- 下载链路保留已验证稳定的 requests 下载流程，并保留浏览器兜底逻辑
- 开发版与生产版核心列表分页逻辑同步，行为一致性更好
- 依赖清单按用途拆分：运行依赖 `requirements.txt`，开发分析依赖 `requirements_reverse.txt`

### v4.2
- 新增优化的下载功能：通过DrissionPage获取真实下载链接后使用requests进行下载
- 当获取到真实下载链接时，使用requests库直接下载，提高下载速度和稳定性
- 当无法获取真实链接时，自动回退到原始的浏览器下载方法，保证兼容性
- 优化了下载流程，减少页面交互步骤，提升用户体验

### v4.1 
- 对获取文件内容进行了优化，大大减少了获取时间
- 通过智能检测文件加载状态，减少不必要的等待时间
- 优化了"显示更多文件"按钮的点击策略，提高加载效率
- 改进了文件列表解析算法，提升整体性能

## 许可证

本项目仅供学习和研究使用，请遵守相关法律法规，合理使用网络资源。

## 作者
曜曜
