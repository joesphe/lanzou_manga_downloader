package com.lanzou.manga.downloader.data.prefs

import android.content.Context

class DownloadHistoryStore(context: Context) {
    private val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun loadDownloadedNames(): Set<String> {
        return prefs.getStringSet(KEY_DOWNLOADED_NAMES, emptySet()) ?: emptySet()
    }

    fun saveDownloadedNames(names: Set<String>) {
        prefs.edit().putStringSet(KEY_DOWNLOADED_NAMES, names).apply()
    }

    private companion object {
        const val PREFS_NAME = "lanzou_downloader_prefs"
        const val KEY_DOWNLOADED_NAMES = "downloaded_names"
    }
}
