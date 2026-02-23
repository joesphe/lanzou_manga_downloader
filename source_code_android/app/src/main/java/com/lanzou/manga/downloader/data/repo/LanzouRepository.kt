package com.lanzou.manga.downloader.data.repo

import android.util.Log
import com.lanzou.manga.downloader.data.model.LanzouFile
import com.lanzou.manga.downloader.data.network.AppHttp
import com.lanzou.manga.downloader.domain.resolver.LanzouResolver
import okhttp3.FormBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import org.json.JSONObject

class LanzouRepository(
    private val client: OkHttpClient,
    private val resolver: LanzouResolver
) {
    // TODO: Replace with secure local config strategy.
    var defaultUrl: String = ""
    var defaultPassword: String = ""

    fun fetchFiles(): List<LanzouFile> {
        if (defaultUrl.isBlank()) {
            Log.e("LanzouRepo", "defaultUrl is blank")
            return emptyList()
        }
        Log.d("LanzouRepo", "fetchFiles start, url=$defaultUrl, pwdLen=${defaultPassword.length}")

        val pageHtml = get(defaultUrl) ?: return emptyList()
        val origin = java.net.URL(defaultUrl).let { "${it.protocol}://${it.host}" }
        val ctx = extractContext(pageHtml) ?: run {
            Log.e("LanzouRepo", "context parse failed")
            return emptyList()
        }

        val ajaxUrl = "$origin/filemoreajax.php?file=${ctx.fid}"
        val allFiles = mutableListOf<LanzouFile>()
        val seen = HashSet<String>()
        var page = 1
        var index = 1
        val maxPages = 500

        while (page <= maxPages) {
            val result = fetchPageWithRetry(
                ajaxUrl = ajaxUrl,
                origin = origin,
                referer = defaultUrl,
                ctx = ctx,
                page = page,
                maxAttempts = 6
            )
            if (result == null) {
                Log.e("LanzouRepo", "page=$page failed after retries")
                break
            }
            val (zt, info, json) = result
            if (zt != 1) {
                Log.e("LanzouRepo", "zt != 1 page=$page zt=$zt info=$info")
                break
            }
            val arr = json.optJSONArray("text")
            val count = arr?.length() ?: 0
            Log.d("LanzouRepo", "page=$page text_count=$count")
            if (arr == null || count == 0) break

            for (i in 0 until count) {
                val row = arr.optJSONObject(i) ?: continue
                val id = row.optString("id", "").trim()
                if (id.isBlank() || id == "-1" || seen.contains(id)) continue
                seen.add(id)
                val name = row.optString("name_all", "unknown")
                val size = row.optString("size", "")
                val time = row.optString("time", "")
                val link = if (id.startsWith("http")) id else "$origin/${id.trimStart('/')}"
                allFiles.add(LanzouFile(index = index, name = name, size = size, time = time, link = link))
                index += 1
            }

            if (count < 50) break
            page += 1
        }
        Log.d("LanzouRepo", "list done total=${allFiles.size}")
        return allFiles
    }

    fun resolveRealUrl(link: String): String? = resolver.resolveRealUrl(link)

    private fun extractContext(pageHtml: String): ListContext? {
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

        if (fid.isNullOrBlank() || uid.isNullOrBlank() || t.isNullOrBlank() || k.isNullOrBlank()) return null
        return ListContext(fid, uid, t, k)
    }

    private fun fetchPageWithRetry(
        ajaxUrl: String,
        origin: String,
        referer: String,
        ctx: ListContext,
        page: Int,
        maxAttempts: Int
    ): Triple<Int, String, JSONObject>? {
        var attempt = 1
        var last: Triple<Int, String, JSONObject>? = null
        while (attempt <= maxAttempts) {
            val data = postListPage(
                ajaxUrl = ajaxUrl,
                origin = origin,
                referer = referer,
                body = buildListBody(ctx, page, rep = 0, ls = 1, up = 1)
            ) ?: postListPage(
                ajaxUrl = ajaxUrl,
                origin = origin,
                referer = referer,
                body = buildListBody(ctx, page, rep = 0, ls = 0, up = 1)
            ) ?: postListPage(
                ajaxUrl = ajaxUrl,
                origin = origin,
                referer = referer,
                body = buildListBody(ctx, page, rep = 0, ls = 1, up = 0)
            )
            if (data != null) {
                last = data
                val zt = data.first
                if (zt == 1 || zt == 3) return data
            }
            attempt += 1
            Thread.sleep((250L * attempt).coerceAtMost(2500L))
        }
        return last
    }

    private fun buildListBody(ctx: ListContext, page: Int, rep: Int, ls: Int, up: Int): RequestBody {
        return FormBody.Builder()
            .add("lx", "2")
            .add("fid", ctx.fid)
            .add("uid", ctx.uid)
            .add("pg", page.toString())
            .add("rep", rep.toString())
            .add("t", ctx.t)
            .add("k", ctx.k)
            .add("up", up.toString())
            .add("ls", ls.toString())
            .add("pwd", defaultPassword)
            .build()
    }

    private fun postListPage(
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
            } catch (e: Exception) {
                return null
            }
            val zt = json.optInt("zt", -1)
            val info = json.optString("info", "")
            return Triple(zt, info, json)
        }
    }

    private fun get(url: String): String? {
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
}

private data class ListContext(
    val fid: String,
    val uid: String,
    val t: String,
    val k: String
)
