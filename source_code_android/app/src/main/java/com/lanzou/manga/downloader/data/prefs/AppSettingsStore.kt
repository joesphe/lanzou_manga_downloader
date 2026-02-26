package com.lanzou.manga.downloader.data.prefs

import android.content.Context

class AppSettingsStore(context: Context) {
    private val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun loadUseThirdPartyLinks(): Boolean {
        return prefs.getBoolean(KEY_USE_THIRD_PARTY_LINKS, false)
    }

    fun saveUseThirdPartyLinks(enabled: Boolean) {
        prefs.edit().putBoolean(KEY_USE_THIRD_PARTY_LINKS, enabled).apply()
    }

    fun loadAllowRedownloadAfterDownload(): Boolean {
        return prefs.getBoolean(KEY_ALLOW_REDOWNLOAD_AFTER_DOWNLOAD, false)
    }

    fun saveAllowRedownloadAfterDownload(enabled: Boolean) {
        prefs.edit().putBoolean(KEY_ALLOW_REDOWNLOAD_AFTER_DOWNLOAD, enabled).apply()
    }

    fun loadIgnoredUpdateVersion(): String? {
        return prefs.getString(KEY_IGNORED_UPDATE_VERSION, null)
    }

    fun saveIgnoredUpdateVersion(version: String?) {
        prefs.edit().putString(KEY_IGNORED_UPDATE_VERSION, version).apply()
    }

    private companion object {
        const val PREFS_NAME = "lanzou_settings_prefs"
        const val KEY_USE_THIRD_PARTY_LINKS = "use_third_party_links"
        const val KEY_ALLOW_REDOWNLOAD_AFTER_DOWNLOAD = "allow_redownload_after_download"
        const val KEY_IGNORED_UPDATE_VERSION = "ignored_update_version"
    }
}
