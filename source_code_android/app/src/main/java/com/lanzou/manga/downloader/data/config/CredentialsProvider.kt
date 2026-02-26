package com.lanzou.manga.downloader.data.config

import com.lanzou.manga.downloader.BuildConfig

object CredentialsProvider : CredentialsSource {
    override fun getDefaultUrlAndPassword(): Pair<String, String> {
        val url = BuildConfig.DEFAULT_SHARE_URL.trim()
        val pwd = BuildConfig.DEFAULT_SHARE_PASSWORD.trim()
        require(url.isNotBlank()) {
            "missing credentials: set LANZOU_PROD_URL/LANZOU_PROD_PASSWORD in source_code_android/private_credentials.properties (or via -P / env)"
        }
        return url to pwd
    }
}
