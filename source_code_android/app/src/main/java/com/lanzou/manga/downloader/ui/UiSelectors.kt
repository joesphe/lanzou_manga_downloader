package com.lanzou.manga.downloader.ui

import com.lanzou.manga.downloader.data.model.LanzouFile

object UiSelectors {
    private fun normalizeFolder(path: String): String {
        val p = path.replace("\\", "/").trim('/')
        return if (p.isBlank()) "" else "$p/"
    }

    private fun immediateChildFolder(currentFolder: String, fileFolderPath: String): String? {
        val current = normalizeFolder(currentFolder)
        val folder = normalizeFolder(fileFolderPath)
        if (folder.isBlank()) return null
        if (!folder.startsWith(current)) return null

        val remain = folder.removePrefix(current)
        val next = remain.substringBefore('/').trim()
        if (next.isBlank()) return null
        return next
    }

    fun filteredFiles(state: UiState): List<LanzouFile> {
        val q = state.searchQuery.trim()
        val currentFolder = normalizeFolder(state.currentFolderPath)
        return state.files.filter { f ->
            val fileFolder = normalizeFolder(f.folderPath)
            fileFolder == currentFolder &&
            (q.isBlank() || f.name.contains(q, ignoreCase = true)) &&
                (!state.onlyUndownloaded || !state.downloadedNames.contains(f.name))
        }
    }

    fun childFolders(state: UiState): List<String> {
        val currentFolder = normalizeFolder(state.currentFolderPath)
        return state.files.asSequence()
            .mapNotNull { immediateChildFolder(currentFolder, it.folderPath) }
            .distinct()
            .sortedBy { it.lowercase() }
            .toList()
    }

    fun selectableVisibleIndices(state: UiState): Set<Int> {
        return filteredFiles(state)
            .asSequence()
            .filter { !state.downloadedNames.contains(it.name) }
            .map { it.index }
            .toSet()
    }

    fun selectedUndownloadedCount(state: UiState): Int {
        return state.files.count {
            state.selectedIndices.contains(it.index) && !state.downloadedNames.contains(it.name)
        }
    }
}
