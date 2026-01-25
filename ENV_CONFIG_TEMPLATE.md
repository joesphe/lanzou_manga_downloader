# 环境变量配置示例

## 系统环境变量设置方法

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

## .env 文件格式

您也可以创建 .env 文件并在Python代码中使用 python-dotenv 库加载：

```
LANZOU_URL=your_lanzou_folder_url
LANZOU_PASSWORD=your_password
```

## 重要说明

# 蓝奏云链接和密码（开发环境必需）
# 注意：在开发环境中必须设置这些环境变量，否则程序启动后将抛出异常


