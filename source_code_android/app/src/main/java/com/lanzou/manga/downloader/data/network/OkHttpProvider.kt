package com.lanzou.manga.downloader.data.network

import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit

object OkHttpProvider {

    private val inMemoryCookieStore = ConcurrentHashMap<String, MutableList<Cookie>>()

    private val cookieJar = object : CookieJar {
        override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
            inMemoryCookieStore[url.host] = cookies.toMutableList()
        }

        override fun loadForRequest(url: HttpUrl): List<Cookie> {
            return inMemoryCookieStore[url.host] ?: emptyList()
        }
    }

    val client: OkHttpClient by lazy {
        val logger = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }
        OkHttpClient.Builder()
            .cookieJar(cookieJar)
            .connectTimeout(20, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .addInterceptor(logger)
            .build()
    }

    fun upsertCookie(host: String, name: String, value: String) {
        val list = inMemoryCookieStore.getOrPut(host) { mutableListOf() }
        val idx = list.indexOfFirst { it.name == name }
        val cookie = Cookie.Builder()
            .name(name)
            .value(value)
            .domain(host)
            .path("/")
            .build()
        if (idx >= 0) {
            list[idx] = cookie
        } else {
            list.add(cookie)
        }
    }

    fun buildCookieHeader(host: String): String {
        val list = inMemoryCookieStore[host].orEmpty()
        return list.joinToString("; ") { "${it.name}=${it.value}" }
    }
}
