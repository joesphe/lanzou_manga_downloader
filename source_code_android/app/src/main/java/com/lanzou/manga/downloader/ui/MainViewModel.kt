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
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class MainViewModel(app: Application) : AndroidViewModel(app) {

    private val container = AppContainer(app)
    private val fetchFilesUseCase = container.fetchFilesUseCase
    private val downloadSelectedUseCase = container.downloadSelectedUseCase
    private val historyStore = container.historyStore
    private val settingsStore = container.settingsStore
    private val effectiveAllowRedownloadAfterDownload = settingsStore.loadAllowRedownloadAfterDownload()
    private val effectiveUseThirdPartyLinks = settingsStore.loadUseThirdPartyLinks()
    private val initialDownloadedNames = if (effectiveAllowRedownloadAfterDownload) {
        historyStore.clearDownloadedNames()
        emptySet()
    } else {
        historyStore.loadDownloadedNames()
    }

    private val _state = MutableStateFlow(
        UiState(
            downloadedNames = initialDownloadedNames,
            useCustomSource = effectiveUseThirdPartyLinks,
            allowRedownloadAfterDownload = effectiveAllowRedownloadAfterDownload
        )
    )
    val state: StateFlow<UiState> = _state.asStateFlow()

    fun fetchFiles() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                if (_state.value.useCustomSource) {
                    val url = _state.value.customUrl.trim()
                    if (url.isBlank()) {
                        _state.update { it.copy(status = UiMessages.CUSTOM_URL_REQUIRED, isLoadingList = false) }
                        return@launch
                    }
                    if (!url.startsWith("http://") && !url.startsWith("https://")) {
                        _state.update { it.copy(status = UiMessages.CUSTOM_URL_INVALID, isLoadingList = false) }
                        return@launch
                    }
                    container.repo.useCustomSource(url = url, password = _state.value.customPassword.trim())
                } else {
                    container.repo.usePresetSource()
                }

                _state.update {
                    it.copy(
                    status = UiMessages.FETCHING_LIST,
                    isLoadingList = true,
                    files = emptyList(),
                    selectedIndices = emptySet()
                    )
                }
                val files = fetchFilesUseCase { batch ->
                    if (batch.isEmpty()) return@fetchFilesUseCase
                    _state.update { current ->
                        val merged = current.files + batch
                        current.copy(
                            files = merged,
                            status = "正在获取文件列表... 已加载 ${merged.size} 个文件",
                            isLoadingList = true
                        )
                    }
                }
                _state.update { it.copy(files = files, status = UiMessages.listUpdated(files.size), isLoadingList = false) }
            } catch (e: Exception) {
                _state.update { it.copy(isLoadingList = false, status = UiMessages.listFailed(e.message)) }
            }
        }
    }

    fun toggleSelection(index: Int) {
        val file = _state.value.files.firstOrNull { it.index == index } ?: return
        if (_state.value.downloadedNames.contains(file.name)) return
        _state.update { state ->
            val current = state.selectedIndices.toMutableSet()
            if (current.contains(index)) current.remove(index) else current.add(index)
            state.copy(selectedIndices = current)
        }
    }

    fun selectAll() {
        val all = UiSelectors.selectableVisibleIndices(_state.value)
        _state.update { it.copy(selectedIndices = all) }
    }

    fun invertSelection() {
        val visibleSelectable = UiSelectors.selectableVisibleIndices(_state.value)
        if (visibleSelectable.isEmpty()) return

        _state.update { state ->
            val current = state.selectedIndices.toMutableSet()
            visibleSelectable.forEach { idx ->
                if (current.contains(idx)) current.remove(idx) else current.add(idx)
            }
            state.copy(selectedIndices = current)
        }
    }

    fun clearSelection() {
        _state.update { it.copy(selectedIndices = emptySet()) }
    }

    fun updateSearchQuery(query: String) {
        _state.update { it.copy(searchQuery = query) }
    }

    fun toggleUseCustomSource(enabled: Boolean) {
        settingsStore.saveUseThirdPartyLinks(enabled)
        _state.update { it.copy(useCustomSource = enabled) }
    }

    fun updateCustomUrl(url: String) {
        _state.update { it.copy(customUrl = url) }
    }

    fun updateCustomPassword(password: String) {
        _state.update { it.copy(customPassword = password) }
    }

    fun toggleAllowRedownloadAfterDownload(enabled: Boolean) {
        settingsStore.saveAllowRedownloadAfterDownload(enabled)
        _state.update { state ->
            if (enabled) {
                historyStore.clearDownloadedNames()
                state.copy(
                    allowRedownloadAfterDownload = true,
                    downloadedNames = emptySet()
                )
            } else {
                val persisted = historyStore.loadDownloadedNames()
                state.copy(
                    allowRedownloadAfterDownload = false,
                    downloadedNames = persisted,
                    selectedIndices = state.selectedIndices.filterTo(mutableSetOf()) { idx ->
                        val f = state.files.firstOrNull { it.index == idx } ?: return@filterTo false
                        !persisted.contains(f.name)
                    }
                )
            }
        }
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
        _state.update { it.copy(onlyUndownloaded = enabled, selectedIndices = selected) }
    }

    fun downloadSelected() {
        viewModelScope.launch(Dispatchers.IO) {
            val selected = selectedUndownloadedFiles()
            if (selected.isEmpty()) {
                _state.update { it.copy(status = UiMessages.SELECT_AT_LEAST_ONE) }
                return@launch
            }
            _state.update { it.copy(isDownloading = true) }

            try {
                val stateSnapshot = _state.value
                val result = downloadSelectedUseCase.execute(
                    params = DownloadSelectedUseCase.Params(
                        context = getApplication(),
                        selectedFiles = selected,
                        downloadedNames = stateSnapshot.downloadedNames,
                        selectedIndices = stateSnapshot.selectedIndices,
                        trackDownloadedNames = !stateSnapshot.allowRedownloadAfterDownload
                    ),
                    onStatus = { msg ->
                        _state.update { it.copy(status = msg) }
                    }
                )
                _state.update {
                    it.copy(
                    isDownloading = false,
                    downloadedNames = result.downloadedNames,
                    selectedIndices = result.selectedIndices,
                    status = UiMessages.summary(result.successCount, result.failCount, result.total)
                    )
                }
            } catch (e: Exception) {
                _state.update { it.copy(isDownloading = false, status = UiMessages.downloadException(e.message)) }
            }
        }
    }

    private fun selectedUndownloadedFiles(): List<LanzouFile> = _state.value.files.filter { f ->
        _state.value.selectedIndices.contains(f.index) && !_state.value.downloadedNames.contains(f.name)
    }
}
