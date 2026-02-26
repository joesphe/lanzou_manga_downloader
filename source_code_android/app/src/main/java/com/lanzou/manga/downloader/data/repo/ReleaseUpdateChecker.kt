package com.lanzou.manga.downloader.data.repo

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject

data class UpdateCheckResult(
    val latestVersion: String? = null,
    val releaseUrl: String = RELEASES_PAGE_URL,
    val hasUpdate: Boolean = false,
    val error: String? = null
)

private const val RELEASES_PAGE_URL = "https://gitee.com/greovity/lanzou_manga_downloader/releases"
private const val LATEST_API_URL = "https://gitee.com/api/v5/repos/greovity/lanzou_manga_downloader/releases/latest"
private const val RELEASES_API_URL = "https://gitee.com/api/v5/repos/greovity/lanzou_manga_downloader/releases?page=1&per_page=30"

class ReleaseUpdateChecker(
    private val client: OkHttpClient
) {
    suspend fun check(currentVersion: String): UpdateCheckResult = withContext(Dispatchers.IO) {
        runCatching {
            val latest = fetchLatestAndroidRelease()
            if (latest == null) {
                UpdateCheckResult(error = "无法获取最新版本信息")
            } else {
                UpdateCheckResult(
                    latestVersion = latest.first,
                    releaseUrl = latest.second,
                    hasUpdate = isVersionLess(currentVersion, latest.first)
                )
            }
        }.getOrElse { e ->
            UpdateCheckResult(error = e.message ?: "检查更新失败")
        }
    }

    private fun fetchLatestAndroidRelease(): Pair<String, String>? {
        parseLatestFromObject(fetchJsonObject(LATEST_API_URL))?.let { return it }

        val list = fetchJsonArray(RELEASES_API_URL) ?: return null
        var bestVersion: String? = null
        var bestUrl = RELEASES_PAGE_URL
        for (i in 0 until list.length()) {
            val obj = list.optJSONObject(i) ?: continue
            val pair = parseLatestFromObject(obj) ?: continue
            if (bestVersion == null || isVersionLess(bestVersion, pair.first)) {
                bestVersion = pair.first
                bestUrl = pair.second
            }
        }
        return bestVersion?.let { it to bestUrl }
    }

    private fun parseLatestFromObject(obj: JSONObject?): Pair<String, String>? {
        if (obj == null) return null
        val candidates = mutableListOf<String>()
        val tagName = obj.optString("tag_name")
        val name = obj.optString("name")
        val body = obj.optString("body")
        candidates += extractAndroidVersions(tagName)
        candidates += extractAndroidVersions(name)
        candidates += extractAndroidVersions(body)

        val assets = obj.optJSONArray("assets")
        if (assets != null) {
            for (i in 0 until assets.length()) {
                val asset = assets.optJSONObject(i) ?: continue
                candidates += extractAndroidVersions(asset.optString("name"))
                candidates += extractAndroidVersions(asset.optString("browser_download_url"))
            }
        }

        if (candidates.isEmpty()) {
            candidates += extractGenericVersions(tagName)
            candidates += extractGenericVersions(name)
            candidates += extractGenericVersions(body)
            if (assets != null) {
                for (i in 0 until assets.length()) {
                    val asset = assets.optJSONObject(i) ?: continue
                    candidates += extractGenericVersions(asset.optString("name"))
                    candidates += extractGenericVersions(asset.optString("browser_download_url"))
                }
            }
        }

        if (candidates.isEmpty()) return null
        var best = candidates.first()
        for (v in candidates.drop(1)) {
            if (isVersionLess(best, v)) best = v
        }

        val tag = obj.optString("tag_name")
        val htmlUrl = obj.optString("html_url")
        val url = when {
            htmlUrl.startsWith("http") -> htmlUrl
            tag.isNotBlank() -> "$RELEASES_PAGE_URL/tag/$tag"
            else -> RELEASES_PAGE_URL
        }
        return best to url
    }

    private fun fetchJsonObject(url: String): JSONObject? {
        val req = Request.Builder()
            .url(url)
            .header("Accept", "application/json")
            .header("User-Agent", "LanzouMangaDownloader-Android")
            .build()
        client.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) return null
            val body = resp.body?.string()?.trim().orEmpty()
            if (body.isEmpty()) return null
            return runCatching { JSONObject(body) }.getOrNull()
        }
    }

    private fun fetchJsonArray(url: String): JSONArray? {
        val req = Request.Builder()
            .url(url)
            .header("Accept", "application/json")
            .header("User-Agent", "LanzouMangaDownloader-Android")
            .build()
        client.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) return null
            val body = resp.body?.string()?.trim().orEmpty()
            if (body.isEmpty()) return null
            return runCatching { JSONArray(body) }.getOrNull()
        }
    }

    private fun extractAndroidVersions(raw: String?): List<String> {
        if (raw.isNullOrBlank()) return emptyList()
        val s = raw.lowercase()
        val out = mutableListOf<String>()
        val seen = mutableSetOf<String>()

        Regex("""android[^a-z0-9]*_?v(\d+(?:[._-]\d+)*)""", RegexOption.IGNORE_CASE)
            .findAll(s)
            .forEach { m ->
                val normalized = normalizeVersion("v${m.groupValues[1]}")
                if (normalized != null && seen.add(normalized)) out += normalized
            }

        return out
    }

    private fun extractGenericVersions(raw: String?): List<String> {
        if (raw.isNullOrBlank()) return emptyList()
        val out = mutableListOf<String>()
        val seen = mutableSetOf<String>()
        Regex("""(?<![A-Za-z0-9])v\d+(?:[._-]\d+){1,3}(?![A-Za-z0-9])""", RegexOption.IGNORE_CASE)
            .findAll(raw)
            .forEach { m ->
                val normalized = normalizeVersion(m.value)
                if (normalized != null && seen.add(normalized)) out += normalized
            }
        return out
    }

    private fun normalizeVersion(raw: String?): String? {
        if (raw.isNullOrBlank()) return null
        val token = Regex("""(?<![A-Za-z0-9])v\d+(?:[._-]\d+)*(?![A-Za-z0-9])""", RegexOption.IGNORE_CASE)
            .find(raw)?.value
            ?: return null
        return token.lowercase().replace('_', '.').replace('-', '.')
    }

    private fun isVersionLess(current: String?, latest: String?): Boolean {
        val a = versionParts(current)
        val b = versionParts(latest)
        if (a.isEmpty() || b.isEmpty()) return false
        val n = maxOf(a.size, b.size)
        val aa = a + List(n - a.size) { 0 }
        val bb = b + List(n - b.size) { 0 }
        for (i in 0 until n) {
            if (aa[i] < bb[i]) return true
            if (aa[i] > bb[i]) return false
        }
        return false
    }

    private fun versionParts(raw: String?): List<Int> {
        val v = normalizeVersion(raw) ?: return emptyList()
        return v.removePrefix("v")
            .split(".")
            .map { part -> part.filter { it.isDigit() } }
            .filter { it.isNotBlank() }
            .map { it.toInt() }
    }
}
