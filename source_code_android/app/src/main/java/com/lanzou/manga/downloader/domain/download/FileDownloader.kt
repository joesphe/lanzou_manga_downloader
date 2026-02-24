package com.lanzou.manga.downloader.domain.download

import android.content.Context

interface FileDownloader {
    fun downloadToPublicDownloads(
        context: Context,
        url: String,
        fileName: String,
        subDir: String = "MangaDownload",
        onProgress: (Int) -> Unit = {}
    ): Pair<Boolean, String>
}

