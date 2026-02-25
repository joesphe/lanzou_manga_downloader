package com.lanzou.manga.downloader.ui

import com.lanzou.manga.downloader.data.model.LanzouFile

data class UiState(
    val status: String = UiMessages.READY,
    val files: List<LanzouFile> = emptyList(),
    val selectedIndices: Set<Int> = emptySet(),
    val isLoadingList: Boolean = false,
    val isDownloading: Boolean = false,
    val useCustomSource: Boolean = false,
    val customUrl: String = "",
    val customPassword: String = "",
    val allowRedownloadAfterDownload: Boolean = false,
    val searchQuery: String = "",
    val downloadedNames: Set<String> = emptySet(),
    val onlyUndownloaded: Boolean = false
)
