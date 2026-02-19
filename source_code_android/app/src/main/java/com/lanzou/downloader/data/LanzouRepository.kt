package com.lanzou.downloader.data

import android.app.DownloadManager
import android.content.Context
import android.os.Environment
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import okhttp3.FormBody
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.net.URI
import java.util.concurrent.TimeUnit
import java.net.CookieManager
import java.net.CookiePolicy
import okhttp3.JavaNetCookieJar

class LanzouRepository {
    private val cookieManager = CookieManager().apply {
        setCookiePolicy(CookiePolicy.ACCEPT_ALL)
    }

    private val client = OkHttpClient.Builder()
        .cookieJar(JavaNetCookieJar(cookieManager))
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    private val ua = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36"

    suspend fun fetchFileList(
        shareUrl: String,
        password: String,
        logger: (String) -> Unit
    ): List<LanzouFile> = withContext(Dispatchers.IO) {
        val files = mutableListOf<LanzouFile>()
        val seen = hashSetOf<String>()

        var context = extractContext(getText(shareUrl), shareUrl)
        val ajaxUrl = "${context.origin}/filemoreajax.php?file=${context.fid}"

        logger("参数提取成功 fid=${context.fid} uid=${context.uid}")

        var index = 1
        var page = 1

        while (page <= 500) {
            var pageJson: JSONObject? = null
            var pageOk = false
            var zt = ""

            for (attempt in 0 until 15) {
                val body = FormBody.Builder()
                    .add("lx", "2")
                    .add("fid", context.fid)
                    .add("uid", context.uid)
                    .add("pg", page.toString())
                    .add("rep", "0")
                    .add("t", context.t)
                    .add("k", context.k)
                    .add("up", "1")
                    .add("ls", "1")
                    .add("pwd", password)
                    .build()

                val req = Request.Builder()
                    .url(ajaxUrl)
                    .post(body)
                    .header("User-Agent", ua)
                    .header("Accept", "application/json, text/javascript, */*")
                    .header("X-Requested-With", "XMLHttpRequest")
                    .header("Referer", shareUrl)
                    .header("Origin", context.origin)
                    .build()

                runCatching {
                    client.newCall(req).execute().use { resp ->
                        if (!resp.isSuccessful) error("HTTP ${resp.code}")
                        JSONObject(resp.body.string())
                    }
                }.onSuccess {
                    pageJson = it
                    zt = it.optString("zt")
                }.onFailure {
                    zt = ""
                }

                if (zt == "1") {
                    pageOk = true
                    break
                }
                if (zt == "3") {
                    error("密码错误: ${pageJson?.optString("info") ?: "unknown"}")
                }

                if (zt == "4" || zt.isBlank()) {
                    runCatching {
                        context = extractContext(getText(shareUrl), shareUrl)
                    }
                    delay(minOf(1800L, 250L * (attempt + 1)))
                }
            }

            if (!pageOk) {
                error("第 $page 页请求失败，zt=$zt, info=${pageJson?.optString("info") ?: ""}")
            }

            val rows = pageJson?.optJSONArray("text") ?: JSONArray()
            if (rows.length() == 0) break

            for (i in 0 until rows.length()) {
                val row = rows.optJSONObject(i) ?: continue
                val id = row.optString("id").trim()
                if (id.isBlank() || id == "-1" || seen.contains(id)) continue
                seen.add(id)

                val fileLink = if (row.optString("t") == "1" && id.startsWith("http")) {
                    id
                } else {
                    "${context.origin}/${id.trimStart('/')}"
                }

                files += LanzouFile(
                    index = index,
                    id = id,
                    name = row.optString("name_all"),
                    size = row.optString("size", "未知大小"),
                    time = row.optString("time", "未知时间"),
                    link = fileLink
                )
                index += 1
            }

            if (rows.length() < 50) break
            page += 1
        }

        files
    }

    suspend fun downloadFile(
        context: Context,
        file: LanzouFile,
        outputDir: File,
        progress: (DownloadProgress) -> Unit,
        logger: (String) -> Unit
    ): Boolean = withContext(Dispatchers.IO) {
        outputDir.mkdirs()
        val safeName = sanitizeFileName(file.name)
        val outFile = File(outputDir, safeName)
        if (outFile.exists()) {
            progress(DownloadProgress(safeName, 100, outFile.length(), outFile.length(), "跳过(已存在)"))
            return@withContext true
        }

        val resolveResult = resolveRealDownloadUrls(file.link, logger)
        if (resolveResult.candidates.isEmpty()) {
            logger("未拿到可用下载链接，回退系统下载器: ${file.name}")
            return@withContext enqueueSystemDownload(context, file.link, safeName, logger)
        }

        logger("解析到 ${resolveResult.candidates.size} 个候选下载链接")
        for (candidate in resolveResult.candidates) {
            val ok = runCatching {
                streamDownload(candidate, file.link, safeName, outFile, progress)
            }.onFailure {
                logger("候选链接下载失败: ${it.message}")
            }.getOrDefault(false)

            if (ok) return@withContext true
        }

        val fallbackUrl = resolveResult.fallbackUrl ?: file.link
        logger("候选下载均失败，回退系统下载器: $fallbackUrl")
        enqueueSystemDownload(context, fallbackUrl, safeName, logger)
    }

    private fun streamDownload(
        directUrl: String,
        refererUrl: String,
        safeName: String,
        outFile: File,
        progress: (DownloadProgress) -> Unit
    ): Boolean {
        val req = Request.Builder()
            .url(directUrl)
            .get()
            .header("User-Agent", ua)
            .header("Referer", refererUrl)
            .header("Accept", "*/*")
            .build()

        client.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) error("下载失败 HTTP ${resp.code}")
            val body = resp.body ?: error("空响应体")
            val contentType = resp.header("Content-Type", "")
            if (contentType.contains("text/html", ignoreCase = true)) {
                error("返回 HTML 页面，非文件流")
            }

            val total = body.contentLength().coerceAtLeast(0)
            body.byteStream().use { input ->
                FileOutputStream(outFile).use { output ->
                    val buf = ByteArray(8192)
                    var downloaded = 0L
                    while (true) {
                        val read = input.read(buf)
                        if (read <= 0) break
                        output.write(buf, 0, read)
                        downloaded += read
                        val pct = if (total > 0) ((downloaded * 100) / total).toInt() else 0
                        progress(DownloadProgress(safeName, pct, downloaded, total, "下载中"))
                    }
                }
            }
            progress(DownloadProgress(safeName, 100, outFile.length(), outFile.length(), "下载完成"))
            return outFile.exists() && outFile.length() > 0
        }
    }

    private fun enqueueSystemDownload(
        context: Context,
        url: String,
        safeName: String,
        logger: (String) -> Unit
    ): Boolean {
        return runCatching {
            val dm = context.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
            val req = DownloadManager.Request(android.net.Uri.parse(url))
                .setTitle(safeName)
                .setDescription("蓝奏云下载回退任务")
                .setMimeType("application/octet-stream")
                .addRequestHeader("User-Agent", ua)
                .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                .setDestinationInExternalFilesDir(
                    context,
                    Environment.DIRECTORY_DOWNLOADS,
                    safeName
                )
            dm.enqueue(req)
            logger("已提交系统下载器任务: $safeName")
            true
        }.onFailure {
            logger("系统下载器回退失败: ${it.message}")
        }.getOrDefault(false)
    }

    private fun resolveRealDownloadUrls(filePageUrl: String, logger: (String) -> Unit): ResolveResult {
        val candidates = linkedSetOf<String>()
        val pageHtml = getText(filePageUrl)

        findAllDirectUrls(pageHtml).forEach { candidates.add(it) }

        val iframeSrc = extractIframeSrc(filePageUrl, pageHtml)
        val iframeHtml = iframeSrc?.let { runCatching { getText(it) }.getOrNull() }

        if (!iframeHtml.isNullOrBlank()) {
            findAllDirectUrls(iframeHtml).forEach { candidates.add(it) }

            val ajaxUrl = buildAjaxUrl(iframeSrc, iframeHtml)
            val signData = extractSignData(iframeHtml)

            if (ajaxUrl != null && signData.sign.isNotBlank()) {
                logger("尝试 ajaxm 解析真实下载链接")
                val ajaxCandidates = callAjaxmForCandidates(ajaxUrl, iframeSrc, signData)
                ajaxCandidates.forEach { candidates.add(it) }
            }
        }

        return ResolveResult(
            candidates = candidates.toList(),
            fallbackUrl = iframeSrc ?: filePageUrl
        )
    }

    private fun extractIframeSrc(baseUrl: String, html: String): String? {
        val src = Regex("<iframe[^>]+src=['\"]([^'\"]+)['\"]", RegexOption.IGNORE_CASE)
            .find(html)
            ?.groupValues?.get(1)
            ?: return null
        return if (src.startsWith("http")) src else URI(baseUrl).resolve(src).toString()
    }

    private fun buildAjaxUrl(iframeUrl: String, iframeHtml: String): String? {
        val ajaxPath = Regex("url\\s*:\\s*['\"]([^'\"]*ajaxm\\.php[^'\"]*)['\"]", RegexOption.IGNORE_CASE)
            .find(iframeHtml)?.groupValues?.get(1)
            ?: "/ajaxm.php?file=1"
        return runCatching { URI(iframeUrl).resolve(ajaxPath).toString() }.getOrNull()
    }

    private fun extractSignData(iframeHtml: String): SignData {
        fun pick(names: List<String>): String {
            for (name in names) {
                val direct = Regex("(?:var|let|const)\\s+$name\\s*=\\s*['\"]([^'\"]*)['\"]")
                    .find(iframeHtml)?.groupValues?.get(1)
                if (!direct.isNullOrBlank()) return direct
                val jsonStyle = Regex("'$name'\\s*:\\s*'([^']*)'").find(iframeHtml)?.groupValues?.get(1)
                if (!jsonStyle.isNullOrBlank()) return jsonStyle
            }
            return ""
        }

        return SignData(
            signs = pick(listOf("signs")),
            sign = pick(listOf("sign")),
            websign = pick(listOf("websign")),
            websignkey = pick(listOf("websignkey")),
            ves = pick(listOf("ves")).ifBlank { "1" }
        )
    }

    private fun callAjaxmForCandidates(ajaxUrl: String, referer: String, signData: SignData): List<String> {
        val candidates = linkedSetOf<String>()

        val payloads = listOf(
            FormBody.Builder()
                .add("action", "downprocess")
                .add("signs", signData.signs)
                .add("sign", signData.sign)
                .add("ves", signData.ves)
                .add("websign", signData.websign)
                .add("websignkey", signData.websignkey)
                .build(),
            FormBody.Builder()
                .add("action", "downprocess")
                .add("sign", signData.sign)
                .add("ves", signData.ves)
                .build()
        )

        for (body in payloads) {
            runCatching {
                val req = Request.Builder()
                    .url(ajaxUrl)
                    .post(body)
                    .header("User-Agent", ua)
                    .header("X-Requested-With", "XMLHttpRequest")
                    .header("Referer", referer)
                    .header("Accept", "application/json, text/javascript, */*")
                    .build()
                client.newCall(req).execute().use { resp ->
                    if (!resp.isSuccessful) error("HTTP ${resp.code}")
                    JSONObject(resp.body.string())
                }
            }.onSuccess { json ->
                if (json.optString("zt") == "1") {
                    val dom = json.optString("dom")
                    val url = json.optString("url")
                    if (dom.isNotBlank() && url.isNotBlank()) {
                        val base = if (dom.endsWith("/")) dom else "$dom/"
                        candidates.add("${base}file/$url")
                        candidates.add("$base$url")
                    }
                    val full = json.optString("inf")
                    if (full.startsWith("http")) candidates.add(full)
                }
            }
        }
        return candidates.toList()
    }

    private data class ResolveResult(
        val candidates: List<String>,
        val fallbackUrl: String?
    )

    private data class SignData(
        val signs: String,
        val sign: String,
        val websign: String,
        val websignkey: String,
        val ves: String
    )

    private fun findAllDirectUrls(html: String): List<String> {
        val out = linkedSetOf<String>()
        val patterns = listOf(
            "https?://[^\\s\"'<>]*(?:developer-oss|lanrar|lanzoug|downserver)[^\\s\"'<>]*",
            "https?://[^\\s\"'<>]*toolsdown[^\\s\"'<>]*"
        )
        for (p in patterns) {
            Regex(p, RegexOption.IGNORE_CASE).findAll(html).forEach { m ->
                out.add(m.value.replace("&amp;", "&"))
            }
        }
        return out.toList()
    }

    private fun sanitizeFileName(name: String): String {
        val cleaned = name.replace(Regex("[<>:\"/\\\\|?*\\u0000-\\u001F]"), "_").trim('.', ' ')
        return if (cleaned.isBlank()) "unnamed_file" else cleaned
    }

    private fun extractContext(html: String, shareUrl: String): ShareContext {
        val uri = URI(shareUrl)
        val origin = "${uri.scheme}://${uri.host}" + if (uri.port > 0) ":${uri.port}" else ""

        val fidByUrl = Regex("[?&]file=(\\d+)").find(shareUrl)?.groupValues?.get(1)
        val fid = fidByUrl
            ?: Regex("/filemoreajax\\.php\\?file=(\\d+)").find(html)?.groupValues?.get(1)
            ?: Regex("'fid'\\s*:\\s*(\\d+)").find(html)?.groupValues?.get(1)
            ?: error("无法提取 fid")

        val uid = Regex("'uid'\\s*:\\s*'?(\\d+)'?").find(html)?.groupValues?.get(1)
            ?: error("无法提取 uid")

        val tVar = Regex("'t'\\s*:\\s*([A-Za-z_][A-Za-z0-9_]*)").find(html)?.groupValues?.get(1)
        val kVar = Regex("'k'\\s*:\\s*([A-Za-z_][A-Za-z0-9_]*)").find(html)?.groupValues?.get(1)

        fun pickVar(varName: String?): String? {
            if (varName.isNullOrBlank()) return null
            return Regex("var\\s+${Regex.escape(varName)}\\s*=\\s*['\"]([^'\"]+)['\"]").find(html)?.groupValues?.get(1)
        }

        val t = pickVar(tVar)
            ?: Regex("'t'\\s*:\\s*'([^']+)'").find(html)?.groupValues?.get(1)
            ?: error("无法提取 t")

        val k = pickVar(kVar)
            ?: Regex("'k'\\s*:\\s*'([^']+)'").find(html)?.groupValues?.get(1)
            ?: error("无法提取 k")

        return ShareContext(origin = origin, fid = fid, uid = uid, t = t, k = k)
    }

    private fun getText(url: String): String {
        val req = Request.Builder()
            .url(url)
            .get()
            .header("User-Agent", ua)
            .header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
            .build()
        client.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) error("请求失败 HTTP ${resp.code}: $url")
            return resp.body.string()
        }
    }

    private data class ShareContext(
        val origin: String,
        val fid: String,
        val uid: String,
        val t: String,
        val k: String
    )
}
