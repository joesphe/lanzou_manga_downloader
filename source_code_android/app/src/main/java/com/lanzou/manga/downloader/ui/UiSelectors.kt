package com.lanzou.manga.downloader.ui

import com.lanzou.manga.downloader.data.model.LanzouFile

object UiSelectors {
    fun filteredFiles(state: UiState): List<LanzouFile> {
        val q = state.searchQuery.trim()
        return state.files.filter { f ->
            (q.isBlank() || f.name.contains(q, ignoreCase = true)) &&
                (!state.onlyUndownloaded || !state.downloadedNames.contains(f.name))
        }
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
