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
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class MainViewModel(app: Application) : AndroidViewModel(app) {

    private val container = AppContainer(app)
    private val fetchFilesUseCase = container.fetchFilesUseCase
    private val downloadSelectedUseCase = container.downloadSelectedUseCase
    private val updateChecker = container.updateChecker
    private val historyStore = container.historyStore
    private val settingsStore = container.settingsStore
    private val effectiveAllowRedownloadAfterDownload = settingsStore.loadAllowRedownloadAfterDownload()
    private val effectiveUseThirdPartyLinks = settingsStore.loadUseThirdPartyLinks()
    private var ignoredUpdateVersion: String? = settingsStore.loadIgnoredUpdateVersion()
    private val initialDownloadedNames = if (effectiveAllowRedownloadAfterDownload) {
        historyStore.clearDownloadedNames()
        emptySet()
    } else {
        historyStore.loadDownloadedNames()
    }
    private var hasPromptedUpdateThisSession: Boolean = false

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

    fun checkForUpdates(currentVersion: String, silentIfUpToDate: Boolean) {
        viewModelScope.launch(Dispatchers.IO) {
            _state.update { it.copy(isCheckingUpdate = true) }
            val result = updateChecker.check(currentVersion)
            _state.update { state ->
                val isIgnoredVersion = result.latestVersion != null && result.latestVersion == ignoredUpdateVersion
                val shouldPrompt = result.hasUpdate &&
                    silentIfUpToDate &&
                    !hasPromptedUpdateThisSession &&
                    !isIgnoredVersion
                if (shouldPrompt) {
                    hasPromptedUpdateThisSession = true
                }
                val base = state.copy(
                    isCheckingUpdate = false,
                    latestAndroidVersion = result.latestVersion,
                    hasUpdate = result.hasUpdate,
                    updateUrl = result.releaseUrl,
                    androidUpdateUrl = result.androidDownloadUrl,
                    windowsUpdateUrl = result.windowsDownloadUrl,
                    showUpdateDialog = shouldPrompt || state.showUpdateDialog
                )
                when {
                    result.error != null && !silentIfUpToDate -> base.copy(status = "检查更新失败: ${result.error}")
                    result.hasUpdate -> base.copy(
                        status = if (isIgnoredVersion && !silentIfUpToDate) {
                            "发现新版本: ${result.latestVersion}（已忽略自动提醒）"
                        } else {
                            "发现新版本: ${result.latestVersion}（当前: $currentVersion）"
                        }
                    )
                    !silentIfUpToDate -> base.copy(status = "当前已是最新版本（$currentVersion）")
                    else -> base
                }
            }
            if (silentIfUpToDate && result.error == null && !result.hasUpdate) {
                val tip = "已是最新版本"
                _state.update { it.copy(startupUpdateTip = tip) }
                delay(2000)
                _state.update { state ->
                    if (state.startupUpdateTip == tip) state.copy(startupUpdateTip = null) else state
                }
            }
        }
    }

    fun dismissUpdateDialog() {
        _state.update { it.copy(showUpdateDialog = false) }
    }

    fun ignoreCurrentUpdateVersion() {
        val latest = _state.value.latestAndroidVersion ?: return
        ignoredUpdateVersion = latest
        settingsStore.saveIgnoredUpdateVersion(latest)
        _state.update {
            it.copy(
                showUpdateDialog = false,
                status = "已忽略版本 $latest 的自动提醒"
            )
        }
    }

    private fun selectedUndownloadedFiles(): List<LanzouFile> = _state.value.files.filter { f ->
        _state.value.selectedIndices.contains(f.index) && !_state.value.downloadedNames.contains(f.name)
    }
}
