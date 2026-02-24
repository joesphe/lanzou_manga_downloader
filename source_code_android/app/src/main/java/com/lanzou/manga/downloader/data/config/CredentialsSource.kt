package com.lanzou.manga.downloader.data.config

interface CredentialsSource {
    fun getDefaultUrlAndPassword(): Pair<String, String>
}

