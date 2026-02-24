package com.lanzou.manga.downloader.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.lanzou.manga.downloader.data.AppContainer
import com.lanzou.manga.downloader.data.model.LanzouFile
import com.lanzou.manga.downloader.domain.usecase.DownloadSelectedUseCase
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class MainViewModel(app: Application) : AndroidViewModel(app) {

    private val container = AppContainer(app)
    private val fetchFilesUseCase = container.fetchFilesUseCase
    private val downloadSelectedUseCase = container.downloadSelectedUseCase
    private val historyStore = container.historyStore
    private var rawFilesByIndex: Map<Int, LanzouFile> = emptyMap()

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
                val files = fetchFilesUseCase()
                rawFilesByIndex = files.associateBy { it.index }
                _state.value = _state.value.copy(
                    files = files.map { it.toUiFileItem() },
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
                val result = downloadSelectedUseCase.execute(
                    params = DownloadSelectedUseCase.Params(
                        context = getApplication(),
                        selectedFiles = selected,
                        downloadedNames = _state.value.downloadedNames,
                        selectedIndices = _state.value.selectedIndices
                    ),
                    onStatus = { msg ->
                        _state.value = _state.value.copy(status = msg)
                    }
                )
                _state.value = _state.value.copy(
                    isDownloading = false,
                    downloadedNames = result.downloadedNames,
                    selectedIndices = result.selectedIndices,
                    status = UiMessages.summary(result.successCount, result.failCount, result.total)
                ) 
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    isDownloading = false,
                    status = UiMessages.downloadException(e.message)
                )
            }
        }
    }

    private fun selectedUndownloadedFiles(): List<LanzouFile> = _state.value.files
        .asSequence()
        .filter { f ->
            _state.value.selectedIndices.contains(f.index) && !_state.value.downloadedNames.contains(f.name)
        }
        .mapNotNull { f -> rawFilesByIndex[f.index] }
        .toList()

    private fun LanzouFile.toUiFileItem(): UiFileItem = UiFileItem(
        index = index,
        name = name,
        size = size,
        time = time
    )
}
