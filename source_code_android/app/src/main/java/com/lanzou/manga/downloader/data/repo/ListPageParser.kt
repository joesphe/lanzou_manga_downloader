package com.lanzou.manga.downloader.data.repo

import org.json.JSONArray

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
    val time: String
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
                    time = row.optString("time", "")
                )
            )
        }
        return rows
    }
}

