# Manga Downloader Docker 部署指南

## 构建镜像
```bash
docker build -t manga-downloader .
```

## 运行容器
由于这是一个交互式应用，需要用户输入，使用以下命令运行：

```bash
docker run -it --rm -v ${PWD}/downloads:/app/downloads manga-downloader
```

或者在Windows PowerShell中：
```bash
docker run -it --rm -v $(Get-Location)/downloads:/app/downloads manga-downloader
```

这将：
- `-it` 分配一个伪TTY并保持STDIN开放，允许交互
- `--rm` 容器停止后自动删除
- `-v` 将本地downloads目录挂载到容器内，以便保存下载的文件

## 重要说明
此容器设计为一次性使用，当下载任务完成后容器会自动退出。下载的文件将保存在本地downloads目录中。