package com.lanzou.manga.downloader.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.lanzou.manga.downloader.data.AppContainer
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class MainViewModel(app: Application) : AndroidViewModel(app) {

    private val container = AppContainer(app)
    private val repo = container.repo
    private val downloader = container.downloader
    private val historyStore = container.historyStore

    init {
        // Clear stale history on startup so files remain selectable after app restart.
        historyStore.clearDownloadedNames()
    }

    private val _state = MutableStateFlow(UiState(downloadedNames = emptySet()))
    val state: StateFlow<UiState> = _state.asStateFlow()

    fun fetchFiles() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                _state.value = _state.value.copy(status = UiMessages.FETCHING_LIST, isLoadingList = true)
                val files = repo.fetchFiles()
                _state.value = _state.value.copy(
                    files = files,
                    selectedIndices = emptySet(),
                    status = UiMessages.listUpdated(files.size),
                    isLoadingList = false
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    isLoadingList = false,
                    status = UiMessages.listFailed(e.message)
                )
            }
        }
    }

    fun toggleSelection(index: Int) {
        val file = _state.value.files.firstOrNull { it.index == index } ?: return
        if (_state.value.downloadedNames.contains(file.name)) return
        val current = _state.value.selectedIndices.toMutableSet()
        if (current.contains(index)) current.remove(index) else current.add(index)
        _state.value = _state.value.copy(selectedIndices = current)
    }

    fun selectAll() {
        val all = UiSelectors.selectableVisibleIndices(_state.value)
        _state.value = _state.value.copy(selectedIndices = all)
    }

    fun invertSelection() {
        val visibleSelectable = UiSelectors.selectableVisibleIndices(_state.value)
        if (visibleSelectable.isEmpty()) return

        val current = _state.value.selectedIndices.toMutableSet()
        visibleSelectable.forEach { idx ->
            if (current.contains(idx)) current.remove(idx) else current.add(idx)
        }
        _state.value = _state.value.copy(selectedIndices = current)
    }

    fun clearSelection() {
        _state.value = _state.value.copy(selectedIndices = emptySet())
    }

    fun updateSearchQuery(query: String) {
        _state.value = _state.value.copy(searchQuery = query)
    }

    fun toggleOnlyUndownloaded(enabled: Boolean) {
        val downloaded = _state.value.downloadedNames
        val selected = if (enabled) {
            _state.value.selectedIndices.filterTo(mutableSetOf()) { idx ->
                val f = _state.value.files.firstOrNull { it.index == idx } ?: return@filterTo false
                !downloaded.contains(f.name)
            }
        } else {
            _state.value.selectedIndices
        }
        _state.value = _state.value.copy(
            onlyUndownloaded = enabled,
            selectedIndices = selected
        )
    }

    fun downloadSelected() {
        viewModelScope.launch(Dispatchers.IO) {
            val selected = selectedUndownloadedFiles()
            if (selected.isEmpty()) {
                _state.value = _state.value.copy(status = UiMessages.SELECT_AT_LEAST_ONE)
                return@launch
            }
            _state.value = _state.value.copy(isDownloading = true)

            try {
                val total = selected.size
                var successCount = 0
                var failCount = 0
                val downloadedNow = _state.value.downloadedNames.toMutableSet()
                val selectedNow = _state.value.selectedIndices.toMutableSet()

                selected.forEachIndexed { i, file ->
                    val ok = processSingleFile(
                        file = file,
                        order = i + 1,
                        total = total
                    )
                    if (ok) {
                        successCount += 1
                        downloadedNow.add(file.name)
                        selectedNow.remove(file.index)
                        _state.value = _state.value.copy(status = UiMessages.downloadDone(i + 1, total, file.name))
                    } else {
                        failCount += 1
                        _state.value = _state.value.copy(status = UiMessages.downloadFailed(i + 1, total, file.name))
                    }
                }
                _state.value = _state.value.copy(
                    isDownloading = false,
                    downloadedNames = downloadedNow,
                    selectedIndices = selectedNow,
                    status = UiMessages.summary(successCount, failCount, total)
                )
                historyStore.saveDownloadedNames(downloadedNow)
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    isDownloading = false,
                    status = UiMessages.downloadException(e.message)
                )
            }
        }
    }

    private fun selectedUndownloadedFiles() = _state.value.files.filter { f ->
        _state.value.selectedIndices.contains(f.index) && !_state.value.downloadedNames.contains(f.name)
    }

    private fun processSingleFile(
        file: com.lanzou.manga.downloader.data.model.LanzouFile,
        order: Int,
        total: Int
    ): Boolean {
        val real = repo.resolveRealUrl(file.link)
        if (real.isNullOrBlank()) {
            return false
        }

        val firstTryOk = downloadWithProgress(
            url = real,
            fileName = file.name,
            order = order,
            total = total,
            retry = false
        )
        if (firstTryOk) return true

        val fresh = repo.resolveRealUrl(file.link) ?: return false
        return downloadWithProgress(
            url = fresh,
            fileName = file.name,
            order = order,
            total = total,
            retry = true
        )
    }

    private fun downloadWithProgress(
        url: String,
        fileName: String,
        order: Int,
        total: Int,
        retry: Boolean
    ): Boolean {
        val result = downloader.downloadToPublicDownloads(
            context = getApplication(),
            url = url,
            fileName = fileName,
            subDir = "MangaDownload"
        ) { p ->
            _state.value = _state.value.copy(
                status = if (retry) {
                    UiMessages.redownloading(order, total, p, fileName)
                } else {
                    UiMessages.downloading(order, total, p, fileName)
                }
            )
        }
        return result.first
    }

}
