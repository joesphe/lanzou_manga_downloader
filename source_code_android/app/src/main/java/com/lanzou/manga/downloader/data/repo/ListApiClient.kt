package com.lanzou.manga.downloader.data.repo

import com.lanzou.manga.downloader.data.network.AppHttp
import com.lanzou.manga.downloader.data.network.OkHttpProvider
import com.lanzou.manga.downloader.domain.challenge.AcwSolver
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import org.json.JSONObject

class ListApiClient(private val client: OkHttpClient) {
    fun getPageHtml(url: String): String? {
        val host = runCatching { java.net.URL(url).host }.getOrNull() ?: return null
        OkHttpProvider.upsertCookie(host, "codelen", "1")

        repeat(2) {
            val req = Request.Builder()
                .url(url)
                .get()
                .addHeader("User-Agent", AppHttp.UA_CHROME)
                .addHeader("Accept", AppHttp.ACCEPT_HTML)
                .apply {
                    val cookieHeader = OkHttpProvider.buildCookieHeader(host)
                    if (cookieHeader.isNotBlank()) addHeader("Cookie", cookieHeader)
                }
                .build()
            client.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) return null
                val body = resp.body?.string() ?: return null
                if (!AcwSolver.hasChallenge(body)) return body
                val token = AcwSolver.solveAcwScV2(body) ?: return null
                OkHttpProvider.upsertCookie(host, "acw_sc__v2", token)
            }
        }
        return null
    }

    fun postListPage(
        ajaxUrl: String,
        origin: String,
        referer: String,
        body: RequestBody
    ): Triple<Int, String, JSONObject>? {
        val host = runCatching { java.net.URL(ajaxUrl).host }.getOrNull() ?: return null
        repeat(2) {
            val req = Request.Builder()
                .url(ajaxUrl)
                .post(body)
                .addHeader("User-Agent", AppHttp.UA_CHROME)
                .addHeader("Accept", AppHttp.ACCEPT_JSON)
                .addHeader("X-Requested-With", "XMLHttpRequest")
                .addHeader("Origin", origin)
                .addHeader("Referer", referer)
                .apply {
                    val cookieHeader = OkHttpProvider.buildCookieHeader(host)
                    if (cookieHeader.isNotBlank()) addHeader("Cookie", cookieHeader)
                }
                .build()

            client.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) return null
                val txt = resp.body?.string() ?: return null
                val json = try {
                    JSONObject(txt)
                } catch (_: Exception) {
                    if (AcwSolver.hasChallenge(txt)) {
                        val token = AcwSolver.solveAcwScV2(txt) ?: return null
                        OkHttpProvider.upsertCookie(host, "acw_sc__v2", token)
                        return@repeat
                    }
                    return null
                }
                return Triple(json.optInt("zt", -1), json.optString("info", ""), json)
            }
        }
        return null
    }
}
