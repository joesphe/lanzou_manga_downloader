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
```bash
export LANZOU_URL="你的蓝奏云链接"
export LANZOU_PASSWORD="你的密码"
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

### v4.1 (最新版本)
- 对获取文件内容进行了优化，大大减少了获取时间
- 通过智能检测文件加载状态，减少不必要的等待时间
- 优化了"显示更多文件"按钮的点击策略，提高加载效率
- 改进了文件列表解析算法，提升整体性能

## 许可证

本项目仅供学习和研究使用，请遵守相关法律法规，合理使用网络资源。

## 作者
曜曜