package com.lanzou.manga.downloader.data.repo

import com.lanzou.manga.downloader.data.model.LanzouFile

interface FilesRepository {
    fun usePresetSource()
    fun useCustomSource(url: String, password: String)
    fun fetchFiles(): List<LanzouFile>
    fun resolveRealUrl(link: String): String?
}
