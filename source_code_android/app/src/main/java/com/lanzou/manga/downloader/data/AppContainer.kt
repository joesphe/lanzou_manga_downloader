package com.lanzou.manga.downloader.data

import android.content.Context
import com.lanzou.manga.downloader.data.config.CredentialsProvider
import com.lanzou.manga.downloader.data.network.OkHttpProvider
import com.lanzou.manga.downloader.data.prefs.DownloadHistoryStore
import com.lanzou.manga.downloader.data.repo.LanzouRepository
import com.lanzou.manga.downloader.domain.download.DownloadManager
import com.lanzou.manga.downloader.domain.resolver.LanzouResolver

class AppContainer(context: Context) {
    val client = OkHttpProvider.client
    private val resolver = LanzouResolver(client)
    val downloader = DownloadManager(client)
    val historyStore = DownloadHistoryStore(context)

    val repo: LanzouRepository = LanzouRepository(client, resolver).apply {
        val (defaultUrl, defaultPassword) = CredentialsProvider.getDefaultUrlAndPassword()
        this.defaultUrl = defaultUrl
        this.defaultPassword = defaultPassword
    }
}
