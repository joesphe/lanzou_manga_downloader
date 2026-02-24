package com.lanzou.manga.downloader.data.repo

import com.lanzou.manga.downloader.data.model.LanzouFile

interface FilesRepository {
    fun fetchFiles(): List<LanzouFile>
    fun resolveRealUrl(link: String): String?
}

