package com.lanzou.manga.downloader.data.model

data class LanzouFile(
    val index: Int,
    val name: String,
    val size: String,
    val time: String,
    val link: String,
    val ajaxFileId: String? = null
)
