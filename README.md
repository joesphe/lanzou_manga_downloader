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
- 网络环境可访问蓝奏云分享页
- Microsoft Edge 浏览器（可选，仅在 requests 提链异常时用于兜底）

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
- requests (主下载链路与主提链链路)
- DrissionPage (浏览器兜底提链，低频触发)
- PyInstaller (打包工具)

## 注意事项

1. 当前主方法为 `requests` 直连提链 + 直连下载；浏览器仅作为接口异常时的兜底方案
2. 生产版本使用了代码混淆技术来保护敏感信息
3. 开发版本需要手动设置环境变量，便于修改和调试
4. 若触发浏览器兜底，请确保 Microsoft Edge 浏览器已安装
5. 自动日志功能已被移除，可通过命令行重定向输出到日志文件

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


## 版本历史

### Android 版本更迭
#### v1.2.0
- 新增版本更新检查功能（检查源：`https://gitee.com/greovity/lanzou_manga_downloader/releases`）：
  - 启动后自动静默检查更新（发现新版本时提示）
  - 设置页新增“检查更新”与“打开发布页”
  - 支持“忽略此版本”持久化（同一版本后续不再自动弹窗）
- 版本配置更新：
  - `versionName` 调整为 `v1.2.0`
  - `versionCode` 递增为 `3`
- APK 发布：
  - `release/apks/v1.2.0/lanzouMangaDownloader_android_v1.2.0.apk`

#### v1.1.0
- Android 凭证加载方式调整为“默认读取私有配置文件 `source_code_android/private_credentials.properties`”
- 公共仓库不再保存 `prod` 相关混淆常量，降低源码泄露风险
- 构建流程收敛为单通道输出：
  - 构建命令：`./gradlew --no-daemon clean assembleDebug`
  - 产物目录：`app/build/outputs/apk/debug/`
- 交互与可用性优化：
  - 新增右下角“回到确认下载”悬浮上箭头
  - 顶部设置入口改为悬浮按钮
- APK 发布：
  - `release/apks/v1.1.0/lanzouMangaDownloader_android_v1.1.0.apk`
#### v1.0.1 
- 完成 Android 端结构化重构（不改变核心业务行为）：
  - 统一筛选/选择逻辑（`UiSelectors`）
  - UI 拆分为 `MainScreen` + `FileList`
  - 下载流程拆分为更小函数，便于维护
  - 网络请求头常量统一（`AppHttp`）
  - 下载历史存储抽离（`DownloadHistoryStore`）
  - UI 文案集中管理（`UiMessages`）
  - 轻量依赖容器（`AppContainer`）
- 新增交互：
  - `反选`
  - `只看未下载`
  - `按名称搜索`
  - 记住已下载状态并跳过已下载文件
- APK 发布：
  - `release/apks/v1.0.1/lanzouMangaDownloader.apk`

### Windows 版本更迭
#### v6.2.0
- GUI 交互增强：
  - 新增“自定义蓝奏云链接 / 密码”入口，可在运行时切换目标分享页
  - 新增“恢复默认链接”按钮，支持快速回退到内置预设
- 文件列表获取体验优化：
  - 列表改为后台线程分批追加到界面，支持“边加载边选择并下载已加载文件”
  - 新增“停止加载”能力，可在拉取过程中主动中断
- 核心代码进一步模块化：
  - 从单文件核心继续拆分为 `lanzou_core` / `lanzou_list_fetcher` / `lanzou_download_core` / `lanzou_types` / `lanzou_errors`
  - 新增统一错误码与数据结构，便于后续维护与跨端迁移
- 安全与可运维性增强：
  - 预设凭证混淆升级为 `AES-GCM + 分片密钥重组`
  - 日志中的真实链接改为哈希掩码输出，降低敏感信息泄露风险
  - 运行依赖新增 `cryptography`

#### v6.0 
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

#### v5.1
- 下载链路升级为“浏览器仅负责获取真实下载链接”，文件下载统一走 `requests`，并移除浏览器下载兜底路径
- 新增真实链接有效性校验：下载前基于 `HEAD` + `Range GET (bytes=0-0)` 与 `Content-Type` 做轻量判断
- 新增“校验失败先直下”策略：为避免误判可用链接，校验不通过时仍先尝试直链下载，失败后再判定该文件失败
- 新增滚动预取（pipeline）：下载第 1 个文件时后台并发预取后续文件真实链接，后续文件优先使用缓存直链
- 预取与下载时序优化：第 1 个文件始终实时取链下载，后续文件下载前自动校验链接，过期则自动重新获取
- GUI 交互与进度显示优化：统一控制区布局、当前文件进度条、总体进度文本与状态栏实时更新

#### v5.0
- 文件列表获取改为优先使用 `filemoreajax.php` 直连分页模式，不再依赖持续点击“显示更多”
- 完整支持 `pg` 分页拉取（每页最多 50 条），可自动适配后续文件数量增长
- 增强稳定性：新增 `zt=4` 与网络异常重试机制，失败时自动刷新页面上下文后继续请求
- 自动刷新请求上下文参数，降低会话失效导致的分页中断概率
- 文件列表结果增加去重处理，避免跨页重复项影响 UI 展示
- 下载链路保留已验证稳定的 requests 下载流程，并保留浏览器兜底逻辑
- 开发版与生产版核心列表分页逻辑同步，行为一致性更好
- 依赖清单按用途拆分：运行依赖 `requirements.txt`，开发分析依赖 `requirements_reverse.txt`

#### v4.2
- 新增优化的下载功能：通过DrissionPage获取真实下载链接后使用requests进行下载
- 当获取到真实下载链接时，使用requests库直接下载，提高下载速度和稳定性
- 当无法获取真实链接时，自动回退到原始的浏览器下载方法，保证兼容性
- 优化了下载流程，减少页面交互步骤，提升用户体验

#### v4.1 
- 对获取文件内容进行了优化，大大减少了获取时间
- 通过智能检测文件加载状态，减少不必要的等待时间
- 优化了"显示更多文件"按钮的点击策略，提高加载效率
- 改进了文件列表解析算法，提升整体性能

## 许可证

本项目仅供学习和研究使用，请遵守相关法律法规，合理使用网络资源。

## 作者
曜曜

## GitHub Release 发布规范（Win/Android）

建议每次发布遵循以下规则：

1. 版本号
- 统一使用语义化版本：`v主版本.次版本.修订号`（示例：`v6.0.0`、`v1.0.1`）
- Windows 与 Android 共用同一发布标签时，可在资产名中区分平台。

2. Tag 与 Release 命名
- Tag：`vX.Y.Z`
- Release 标题：`vX.Y.Z - Windows/Android`

3. 资产命名（Assets）
- Windows：
  - `lanzouMangaDownloader_win_x64_vX.Y.Z.exe`
- Android：
  - `lanzouMangaDownloader_android_vX.Y.Z.apk`

4. Release Notes 建议模板
- `新增`：新功能
- `优化`：性能/体验/结构优化
- `修复`：关键 Bug 修复
- `兼容性`：系统版本与依赖变化
- `已知问题`：暂未解决的问题
- `校验信息`：文件大小、SHA256（建议）

5. 分支与提交建议
- 先在主分支完成可编译状态，再打 Tag 发布
- Tag 对应 commit 必须可复现构建产物

6. 最低发布检查清单
- Windows 可启动、可获取列表、可下载 1 小文件 + 1 大文件
- Android 可启动、可获取列表、可下载并落盘到 `Download/MangaDownload`
- README 版本历史与资产路径已更新
