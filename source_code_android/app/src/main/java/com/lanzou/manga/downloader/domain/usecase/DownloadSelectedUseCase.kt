package com.lanzou.manga.downloader.domain.usecase

import android.content.Context
import com.lanzou.manga.downloader.data.model.LanzouFile
import com.lanzou.manga.downloader.data.prefs.DownloadHistoryStore
import com.lanzou.manga.downloader.data.repo.FilesRepository
import com.lanzou.manga.downloader.domain.download.FileDownloader
import com.lanzou.manga.downloader.ui.UiMessages

class DownloadSelectedUseCase(
    private val repository: FilesRepository,
    private val downloader: FileDownloader,
    private val historyStore: DownloadHistoryStore
) {
    data class Params(
        val context: Context,
        val selectedFiles: List<LanzouFile>,
        val downloadedNames: Set<String>,
        val selectedIndices: Set<Int>,
        val trackDownloadedNames: Boolean
    )

    data class Result(
        val successCount: Int,
        val failCount: Int,
        val total: Int,
        val downloadedNames: Set<String>,
        val selectedIndices: Set<Int>
    )

    fun execute(
        params: Params,
        onStatus: (String) -> Unit
    ): Result {
        val total = params.selectedFiles.size
        var successCount = 0
        var failCount = 0
        val downloadedNow = params.downloadedNames.toMutableSet()
        val selectedNow = params.selectedIndices.toMutableSet()

        params.selectedFiles.forEachIndexed { i, file ->
            val order = i + 1
            val ok = processSingleFile(
                context = params.context,
                file = file,
                order = order,
                total = total,
                onStatus = onStatus
            )
            if (ok) {
                successCount += 1
                if (params.trackDownloadedNames) {
                    downloadedNow.add(file.name)
                }
                selectedNow.remove(file.index)
                onStatus(UiMessages.downloadDone(order, total, file.name))
            } else {
                failCount += 1
                onStatus(UiMessages.downloadFailed(order, total, file.name))
            }
        }

        historyStore.saveDownloadedNames(downloadedNow)
        return Result(
            successCount = successCount,
            failCount = failCount,
            total = total,
            downloadedNames = downloadedNow,
            selectedIndices = selectedNow
        )
    }

    private fun processSingleFile(
        context: Context,
        file: LanzouFile,
        order: Int,
        total: Int,
        onStatus: (String) -> Unit
    ): Boolean {
        val real = repository.resolveRealUrl(file.link, file.ajaxFileId)
        if (real.isNullOrBlank()) return false

        val firstTryOk = downloadWithProgress(
            context = context,
            url = real,
            fileName = file.name,
            order = order,
            total = total,
            retry = false,
            onStatus = onStatus
        )
        if (firstTryOk) return true

        val fresh = repository.resolveRealUrl(file.link, file.ajaxFileId) ?: return false
        return downloadWithProgress(
            context = context,
            url = fresh,
            fileName = file.name,
            order = order,
            total = total,
            retry = true,
            onStatus = onStatus
        )
    }

    private fun downloadWithProgress(
        context: Context,
        url: String,
        fileName: String,
        order: Int,
        total: Int,
        retry: Boolean,
        onStatus: (String) -> Unit
    ): Boolean {
        val result = downloader.downloadToPublicDownloads(
            context = context,
            url = url,
            fileName = fileName,
            subDir = "MangaDownload"
        ) { p ->
            onStatus(
                if (retry) {
                    UiMessages.redownloading(order, total, p, fileName)
                } else {
                    UiMessages.downloading(order, total, p, fileName)
                }
            )
        }
        return result.first
    }
}
