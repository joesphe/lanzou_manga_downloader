package com.lanzou.manga.downloader.data.repo

import com.lanzou.manga.downloader.data.network.AppHttp
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import org.json.JSONObject

class ListApiClient(private val client: OkHttpClient) {
    fun getPageHtml(url: String): String? {
        val req = Request.Builder()
            .url(url)
            .get()
            .addHeader("User-Agent", AppHttp.UA_CHROME)
            .addHeader("Accept", AppHttp.ACCEPT_HTML)
            .build()
        client.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) return null
            return resp.body?.string()
        }
    }

    fun postListPage(
        ajaxUrl: String,
        origin: String,
        referer: String,
        body: RequestBody
    ): Triple<Int, String, JSONObject>? {
        val req = Request.Builder()
            .url(ajaxUrl)
            .post(body)
            .addHeader("User-Agent", AppHttp.UA_CHROME)
            .addHeader("Accept", AppHttp.ACCEPT_JSON)
            .addHeader("X-Requested-With", "XMLHttpRequest")
            .addHeader("Origin", origin)
            .addHeader("Referer", referer)
            .build()

        client.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) return null
            val txt = resp.body?.string() ?: return null
            val json = try {
                JSONObject(txt)
            } catch (_: Exception) {
                return null
            }
            return Triple(json.optInt("zt", -1), json.optString("info", ""), json)
        }
    }
}

