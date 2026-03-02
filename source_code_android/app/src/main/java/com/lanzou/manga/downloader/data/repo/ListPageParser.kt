package com.lanzou.manga.downloader.data.repo

import org.json.JSONArray
import java.net.URL

data class ListContext(
    val fid: String,
    val uid: String,
    val t: String,
    val k: String
)

data class ParsedRow(
    val id: String,
    val name: String,
    val size: String,
    val time: String,
    val ajaxFileId: String?
)

data class ParsedFolder(
    val url: String,
    val name: String
)

class ListPageParser {
    fun extractContext(pageHtml: String): ListContext? {
        val fid = Regex("/filemoreajax\\.php\\?file=(\\d+)").find(pageHtml)?.groupValues?.get(1)
            ?: Regex("'fid'\\s*:\\s*(\\d+)").find(pageHtml)?.groupValues?.get(1)
        val uid = Regex("'uid'\\s*:\\s*'?(\\d+)'?").find(pageHtml)?.groupValues?.get(1)
        val tName = Regex("'t'\\s*:\\s*([A-Za-z_][A-Za-z0-9_]*)").find(pageHtml)?.groupValues?.get(1)
        val kName = Regex("'k'\\s*:\\s*([A-Za-z_][A-Za-z0-9_]*)").find(pageHtml)?.groupValues?.get(1)

        fun pickVarValue(name: String?): String? {
            if (name.isNullOrBlank()) return null
            return Regex("var\\s+${Regex.escape(name)}\\s*=\\s*['\"]([^'\"]+)['\"]")
                .find(pageHtml)?.groupValues?.get(1)
        }

        val t = pickVarValue(tName) ?: Regex("'t'\\s*:\\s*'([^']+)'").find(pageHtml)?.groupValues?.get(1)
        val k = pickVarValue(kName) ?: Regex("'k'\\s*:\\s*'([^']+)'").find(pageHtml)?.groupValues?.get(1)
        if (fid.isNullOrBlank() || uid.isNullOrBlank() || t.isNullOrBlank() || k.isNullOrBlank()) {
            return null
        }
        return ListContext(fid, uid, t, k)
    }

    fun parseRows(arr: JSONArray?): List<ParsedRow> {
        if (arr == null) return emptyList()
        val rows = ArrayList<ParsedRow>(arr.length())
        for (i in 0 until arr.length()) {
            val row = arr.optJSONObject(i) ?: continue
            val id = row.optString("id", "").trim()
            if (id.isBlank() || id == "-1") continue
            rows.add(
                ParsedRow(
                    id = id,
                    name = row.optString("name_all", "unknown"),
                    size = row.optString("size", ""),
                    time = row.optString("time", ""),
                    ajaxFileId = extractAjaxFileId(row)
                )
            )
        }
        return rows
    }

    fun extractSubFolders(pageHtml: String, baseUrl: String): List<ParsedFolder> {
        val out = mutableListOf<ParsedFolder>()
        val seen = HashSet<String>()
        val pattern = Regex(
            "<div[^>]*class=[\"'][^\"']*mbxfolder[^\"']*[\"'][^>]*>.*?<a[^>]*href=[\"']([^\"']+)[\"'][^>]*>.*?<div[^>]*class=[\"']filename[\"'][^>]*>(.*?)<div[^>]*class=[\"']filesize[\"']",
            setOf(RegexOption.IGNORE_CASE, RegexOption.DOT_MATCHES_ALL)
        )

        for (m in pattern.findAll(pageHtml)) {
            val href = m.groupValues.getOrNull(1)?.trim().orEmpty()
            if (href.isBlank()) continue
            if (!Regex("/b[0-9a-z]+", RegexOption.IGNORE_CASE).containsMatchIn(href)) continue

            val absoluteUrl = resolveUrl(baseUrl, href) ?: continue
            val normalized = normalizeShareUrl(absoluteUrl)
            if (!seen.add(normalized)) continue

            val rawName = m.groupValues.getOrNull(2).orEmpty()
            val plainName = htmlToText(rawName).ifBlank {
                normalized.substringAfterLast('/').ifBlank { "folder" }
            }
            out += ParsedFolder(url = absoluteUrl, name = plainName)
        }
        return out
    }

    private fun extractAjaxFileId(row: org.json.JSONObject): String? {
        val preferredKeys = listOf("file_id", "fid", "f_id", "down_id", "id")
        for (key in preferredKeys) {
            val value = row.optString(key, "").trim()
            if (value.isNotBlank() && value.all { it.isDigit() } && value != "0") {
                return value
            }
        }
        val keys = row.keys()
        while (keys.hasNext()) {
            val key = keys.next().orEmpty()
            val value = row.optString(key, "").trim()
            val keyLower = key.lowercase()
            if ((keyLower.contains("id") || keyLower == "file" || keyLower == "fid") &&
                value.isNotBlank() &&
                value.all { it.isDigit() } &&
                value != "0"
            ) {
                return value
            }
        }
        return null
    }

    private fun resolveUrl(baseUrl: String, href: String): String? {
        return runCatching {
            URL(URL(baseUrl), href).toString()
        }.getOrNull()
    }

    private fun normalizeShareUrl(url: String): String {
        return runCatching {
            val u = URL(url)
            "${u.protocol}://${u.host}${u.path}"
        }.getOrElse { url.trim() }
    }

    private fun htmlToText(raw: String): String {
        return raw
            .replace(Regex("<[^>]+>"), "")
            .replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", "\"")
            .replace("&#39;", "'")
            .trim()
    }
}
