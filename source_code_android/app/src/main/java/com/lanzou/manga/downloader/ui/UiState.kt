package com.lanzou.manga.downloader.ui

data class UiState(
    val status: String = UiMessages.READY,
    val files: List<UiFileItem> = emptyList(),
    val selectedIndices: Set<Int> = emptySet(),
    val isLoadingList: Boolean = false,
    val isDownloading: Boolean = false,
    val searchQuery: String = "",
    val downloadedNames: Set<String> = emptySet(),
    val onlyUndownloaded: Boolean = false
)
