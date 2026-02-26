package com.lanzou.manga.downloader.data.config

import com.lanzou.manga.downloader.BuildConfig

object CredentialsProvider : CredentialsSource {
    override fun getDefaultUrlAndPassword(): Pair<String, String> {
        val url = BuildConfig.DEFAULT_SHARE_URL.trim()
        val pwd = BuildConfig.DEFAULT_SHARE_PASSWORD.trim()
        require(url.isNotBlank()) {
            if (BuildConfig.FLAVOR.contains("prod", ignoreCase = true)) {
                "prod flavor requires LANZOU_PROD_URL (via private_credentials.properties / -P / env)"
            } else {
                "dev flavor requires DEFAULT_SHARE_URL (or LANZOU_DEV_URL) to be configured"
            }
        }
        return url to pwd
    }
}
