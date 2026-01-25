# 蓝奏云漫画下载器 - 安全开发指南

## 双模式系统

本项目实现了双模式系统，以平衡开发便利性和生产安全性：

### 1. 开发环境模式
- 当代码在Python解释器中运行时（非打包状态）
- 必须从环境变量读取URL和密码
- 如果未设置环境变量，程序将抛出错误
- 便于开发和调试，同时确保敏感信息不在源码中

### 2. 生产环境模式
- 当代码被打包成exe文件后运行时
- 使用深度混淆技术解密内置的URL和密码
- 提供额外的安全保护
- 防止静态分析获取敏感信息

## 环境变量配置

在开发环境中，您必须设置以下环境变量。根据不同操作系统使用相应的命令：

### Windows (PowerShell)
```powershell
$env:LANZOU_URL='your_lanzou_folder_url'
$env:LANZOU_PASSWORD='your_password'
```

### Windows (CMD)
```cmd
set LANZOU_URL=your_lanzou_folder_url
set LANZOU_PASSWORD=your_password
```

### macOS/Linux (Bash/Zsh)
```bash
export LANZOU_URL=your_lanzou_folder_url
export LANZOU_PASSWORD=your_password
```

### 通用方法：创建 `.env` 文件
您也可以创建 `.env` 文件并在Python代码中使用 `python-dotenv` 库加载：
```
LANZOU_URL=https://your-lanzou-url.com/your-folder
LANZOU_PASSWORD=your-password
```

然后在Python代码开头添加：
```python
from dotenv import load_dotenv
load_dotenv()
```

## 安全特性

1. **动态检测**：自动检测运行环境（开发/生产）
2. **混淆保护**：生产环境中使用复杂算法保护敏感信息
3. **强制安全**：开发环境中不提供默认值，必须设置环境变量
4. **灵活部署**：开发时无需修改源码即可更换链接

## 上传到GitHub

由于采用了双模式系统，您可以安全地将源码上传到GitHub：
- 源码中不包含任何硬编码的敏感信息
- 生产环境的混淆数据只有在打包后才生效
- 开发者无法从源码中直接获取URL和密码

## 打包命令

```bash
pyinstaller --onefile --windowed --name="蓝奏云漫画下载器" lanzou_downloader_gui.py
```

## 注意事项

1. 仅在生产环境中使用混淆功能，开发环境必须设置环境变量
2. 保持 `.gitignore` 文件更新，避免意外提交敏感配置
3. 打包后的exe文件是唯一包含混淆数据的可执行文件
4. 在开发环境中不设置环境变量会导致程序启动失败