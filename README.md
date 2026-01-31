# 蓝奏云漫画下载器

蓝奏云漫画下载器是一个专门用于从蓝奏云网盘批量下载漫画或文件的Python工具，支持图形界面(GUI)和无界面(命令行)两种模式。

## 功能特性

- **双模式运行**：提供图形界面和命令行两种操作模式，满足不同用户需求
- **批量下载**：支持批量获取和下载蓝奏云文件夹中的所有文件
- **多线程下载**：使用多线程技术提高下载效率
- **安全设计**：采用双模式安全系统，在开发环境中使用环境变量，在生产环境中使用混淆技术
- **进度跟踪**：实时显示下载进度和日志记录
- **跨平台支持**：基于Python开发，支持Windows、macOS和Linux系统

## 系统要求

- Python 3.7 或更高版本
- Microsoft Edge 浏览器（推荐）
- 稳定的网络连接

## 依赖库

- `DrissionPage`: 用于网页自动化操作
- `requests`: HTTP请求处理
- `tqdm`: 进度条显示（仅命令行版）
- `tkinter`: GUI界面组件（仅GUI版）
- `concurrent.futures`: 多线程支持
- `logging`: 日志记录

## 安装步骤

### 使用 uv (推荐)

1. 克隆或下载项目到本地：
   ```bash
   git clone https://github.com/your-repo/lanzou_manga_downloader.git
   cd lanzou_manga_downloader
   ```

2. 使用 uv 安装依赖（需要 Python 3.12+）：
   ```bash
   uv sync
   ```

3. 安装开发依赖：
   ```bash
   uv sync --group dev
   ```

4. 设置环境变量（开发环境）：
   
   **Windows (PowerShell):**
   ```powershell
   $env:LANZOU_URL='your_lanzou_folder_url'
   $env:LANZOU_PASSWORD='your_password'
   ```
   
   **Windows (CMD):**
   ```cmd
   set LANZOU_URL=your_lanzou_folder_url
   set LANZOU_PASSWORD=your_password
   ```
   
   **macOS/Linux (Bash/Zsh):**
   ```bash
   export LANZOU_URL=your_lanzou_folder_url
   export LANZOU_PASSWORD=your_password
   ```

### 使用 pip

1. 克隆或下载项目到本地：
   ```bash
   git clone https://github.com/your-repo/lanzou_manga_downloader.git
   cd lanzou_manga_downloader
   ```

2. 安装依赖库：
   ```bash
   pip install -r requirements.txt
   ```

## 使用方法

### 使用 uv 运行 (推荐)

#### GUI模式
```bash
uv run python source_code/lanzou_downloader_gui.py
```

或者使用项目定义的命令：
```bash
uv run gui
```

#### 命令行模式
```bash
uv run python source_code/lanzou_downloader_guiless.py
```

或者使用项目定义的命令：
```bash
uv run cli
```

### 传统方式运行

#### GUI模式
1. 运行GUI版本：
   ```bash
   python source_code/lanzou_downloader_gui.py
   ```

2. 点击"获取文件列表"按钮加载文件
3. 在文件列表中选择需要下载的文件（支持Ctrl多选）
4. 设置下载目录
5. 点击"开始下载"按钮

#### 命令行模式
1. 运行无界面版本：
   ```bash
   python source_code/lanzou_downloader_guiless.py
   ```

2. 程序将自动使用环境变量中配置的URL和密码进行下载

## 安全特性

本项目采用了双模式安全系统：

- **开发环境模式**：强制使用环境变量存储敏感信息，避免硬编码在源代码中
- **生产环境模式**：当代码打包成exe时，使用深度混淆技术保护敏感信息

## 配置选项

- `LANZOU_URL`: 蓝奏云分享链接地址
- `LANZOU_PASSWORD`: 蓝奏云分享密码
- `max_workers`: 最大并发下载数（默认为3）
- `headless`: 是否启用无头浏览器模式（默认为True）

## 日志记录

程序会自动生成日志文件保存在`logs`目录下，文件名包含时间戳，便于问题排查和下载历史追踪。

## 故障排除

1. **浏览器问题**：确保已安装Microsoft Edge浏览器（版本至少要大于100）
2. **环境变量错误**：检查LANZOU_URL和LANZOU_PASSWORD是否正确设置
3. **网络连接问题**：确认网络连接正常且蓝奏云链接有效



## 作者
曜曜