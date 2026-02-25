package com.lanzou.manga.downloader.data

import android.content.Context
import com.lanzou.manga.downloader.data.config.CredentialsProvider
import com.lanzou.manga.downloader.data.config.CredentialsSource
import com.lanzou.manga.downloader.data.network.OkHttpProvider
import com.lanzou.manga.downloader.data.prefs.DownloadHistoryStore
import com.lanzou.manga.downloader.data.repo.FilesRepository
import com.lanzou.manga.downloader.data.repo.LanzouRepository
import com.lanzou.manga.downloader.domain.download.FileDownloader
import com.lanzou.manga.downloader.domain.download.DownloadManager
import com.lanzou.manga.downloader.domain.resolver.LanzouResolver
import com.lanzou.manga.downloader.domain.usecase.DownloadSelectedUseCase
import com.lanzou.manga.downloader.domain.usecase.FetchFilesUseCase

class AppContainer(context: Context) {
    val client = OkHttpProvider.client
    private val resolver = LanzouResolver(client)
    private val credentialsSource: CredentialsSource = CredentialsProvider
    val downloader: FileDownloader = DownloadManager(client)
    val historyStore = DownloadHistoryStore(context)

    val repo: FilesRepository = LanzouRepository(client, resolver).apply {
        val (defaultUrl, defaultPassword) = credentialsSource.getDefaultUrlAndPassword()
        this.setPreset(defaultUrl, defaultPassword)
    }

    val fetchFilesUseCase = FetchFilesUseCase(repo)
    val downloadSelectedUseCase = DownloadSelectedUseCase(repo, downloader, historyStore)
}
