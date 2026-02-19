package com.lanzou.downloader.data

data class LanzouFile(
    val index: Int,
    val id: String,
    val name: String,
    val size: String,
    val time: String,
    val link: String
)

data class DownloadProgress(
    val fileName: String,
    val percent: Int,
    val downloadedBytes: Long,
    val totalBytes: Long,
    val status: String
)
