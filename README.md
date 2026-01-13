# 漫画下载器 Docker 部署指南

本项目是一个蓝奏云下载器，可以打包成Docker镜像运行。

## 构建和运行

### 使用Docker构建

```bash
# 构建镜像
docker build -t manga-downloader .

# 运行容器
docker run -it --privileged \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/logs:/app/logs \
  manga-downloader
```

### 使用Docker Compose

```bash
# 构建并运行
docker-compose up --build

# 后台运行
docker-compose up -d --build
```

## 注意事项

1. 本应用使用Selenium控制浏览器进行下载，需要特权模式运行
2. Chrome浏览器将在无头模式下运行
3. 下载的文件将保存在 `downloads` 目录中
4. 日志文件将保存在 `logs` 目录中

## 系统要求

- Docker 19.03 或更高版本
- 足够的磁盘空间用于下载文件
- 网络连接用于下载依赖和文件

## 文件结构

- `Dockerfile`: Docker镜像构建文件
- `requirements.txt`: Python依赖列表
- `docker-compose.yml`: Docker Compose配置文件
- `backup/源代码备份/v1.0/lanzou_downloader.py`: 主应用文件