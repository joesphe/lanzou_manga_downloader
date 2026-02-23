package com.lanzou.manga.downloader.ui

object UiMessages {
    const val READY = "就绪"
    const val FETCHING_LIST = "正在获取文件列表..."
    const val SELECT_AT_LEAST_ONE = "请先选择至少一个未下载文件"

    fun listUpdated(count: Int) = "文件列表已更新: $count 个"
    fun listFailed(reason: String?) = "获取文件列表失败: $reason"
    fun downloading(order: Int, total: Int, progress: Int, name: String) = "[$order/$total] 下载中 ${progress}%: $name"
    fun redownloading(order: Int, total: Int, progress: Int, name: String) = "[$order/$total] 重试下载中 ${progress}%: $name"
    fun downloadDone(order: Int, total: Int, name: String) = "[$order/$total] 下载完成: $name"
    fun downloadFailed(order: Int, total: Int, name: String) = "[$order/$total] 下载失败: $name"
    fun summary(success: Int, fail: Int, total: Int) = "任务完成：成功 $success，失败 $fail，总计 $total"
    fun downloadException(reason: String?) = "下载异常: $reason"
}
