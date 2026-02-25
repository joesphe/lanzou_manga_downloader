package com.lanzou.manga.downloader.data.repo

import android.util.Log
import com.lanzou.manga.downloader.data.model.LanzouFile
import com.lanzou.manga.downloader.domain.resolver.LanzouResolver
import okhttp3.FormBody
import okhttp3.OkHttpClient
import okhttp3.RequestBody
import org.json.JSONObject

class LanzouRepository(
    client: OkHttpClient,
    private val resolver: LanzouResolver,
    private val apiClient: ListApiClient = ListApiClient(client),
    private val pageParser: ListPageParser = ListPageParser()
) : FilesRepository {
    private var presetUrl: String = ""
    private var presetPassword: String = ""
    private var activeUrl: String = ""
    private var activePassword: String = ""

    fun setPreset(url: String, password: String) {
        presetUrl = url
        presetPassword = password
        usePresetSource()
    }

    override fun usePresetSource() {
        activeUrl = presetUrl
        activePassword = presetPassword
    }

    override fun useCustomSource(url: String, password: String) {
        activeUrl = url
        activePassword = password
    }

    override fun fetchFiles(): List<LanzouFile> {
        if (activeUrl.isBlank()) {
            Log.e("LanzouRepo", "activeUrl is blank")
            return emptyList()
        }
        Log.d("LanzouRepo", "fetchFiles start, pwdLen=${activePassword.length}")

        val pageHtml = apiClient.getPageHtml(activeUrl) ?: return emptyList()
        val origin = java.net.URL(activeUrl).let { "${it.protocol}://${it.host}" }
        val ctx = pageParser.extractContext(pageHtml) ?: run {
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
                referer = activeUrl,
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

            val rows = pageParser.parseRows(arr)
            for (row in rows) {
                if (seen.contains(row.id)) continue
                seen.add(row.id)
                val link = if (row.id.startsWith("http")) row.id else "$origin/${row.id.trimStart('/')}"
                allFiles.add(
                    LanzouFile(
                        index = index,
                        name = row.name,
                        size = row.size,
                        time = row.time,
                        link = link
                    )
                )
                index += 1
            }

            if (count < 50) break
            page += 1
        }
        Log.d("LanzouRepo", "list done total=${allFiles.size}")
        return allFiles
    }

    override fun resolveRealUrl(link: String): String? = resolver.resolveRealUrl(link)

    private fun fetchPageWithRetry(
        ajaxUrl: String,
        origin: String,
        referer: String,
        ctx: ListContext,
        page: Int,
        maxAttempts: Int
    ): Triple<Int, String, JSONObject>? {
        return RetryPolicy(maxAttempts = maxAttempts).run { _ ->
            val first = apiClient.postListPage(
                ajaxUrl = ajaxUrl,
                origin = origin,
                referer = referer,
                body = buildListBody(ctx, page, rep = 0, ls = 1, up = 1)
            )
            val second = first ?: apiClient.postListPage(
                ajaxUrl = ajaxUrl,
                origin = origin,
                referer = referer,
                body = buildListBody(ctx, page, rep = 0, ls = 0, up = 1)
            )
            val third = second ?: apiClient.postListPage(
                ajaxUrl = ajaxUrl,
                origin = origin,
                referer = referer,
                body = buildListBody(ctx, page, rep = 0, ls = 1, up = 0)
            )
            if (third != null && (third.first == 1 || third.first == 3)) third else null
        }
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
            .add("pwd", activePassword)
            .build()
    }
}
