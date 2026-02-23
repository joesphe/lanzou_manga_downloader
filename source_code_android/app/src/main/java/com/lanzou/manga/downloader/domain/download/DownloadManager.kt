package com.lanzou.manga.downloader.domain.download

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.util.Log
import com.lanzou.manga.downloader.data.network.AppHttp
import com.lanzou.manga.downloader.data.network.OkHttpProvider
import com.lanzou.manga.downloader.domain.challenge.AcwSolver
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.util.concurrent.ConcurrentHashMap

class DownloadManager(private val client: OkHttpClient) {
    private val validationPolicy = ConcurrentHashMap<String, ValidationState>()

    fun isDownloadUrlValid(url: String, timeoutSec: Long = 8): Boolean {
        if (url.isBlank()) return false
        if (shouldSkipValidation(url)) return true

        val headers = mapOf(
            "User-Agent" to AppHttp.UA_CHROME,
            "Accept" to AppHttp.ACCEPT_ANY
        )

        val headReq = Request.Builder().url(url).head().apply {
            headers.forEach { (k, v) -> addHeader(k, v) }
        }.build()
        try {
            client.newCall(headReq).execute().use { resp ->
                val ctype = (resp.header("Content-Type") ?: "").lowercase()
                if (resp.code == 200 || resp.code == 206) return !ctype.contains("text/html")
                if (resp.code == 403 || resp.code == 404 || resp.code == 410) return false
            }
        } catch (_: Exception) {
        }

        val getReq = Request.Builder().url(url).get().apply {
            headers.forEach { (k, v) -> addHeader(k, v) }
            addHeader("Range", "bytes=0-0")
        }.build()
        return try {
            client.newCall(getReq).execute().use { resp ->
                val ctype = (resp.header("Content-Type") ?: "").lowercase()
                if (resp.code == 200 || resp.code == 206) !ctype.contains("text/html") else !(resp.code == 403 || resp.code == 404 || resp.code == 410)
            }
        } catch (_: Exception) {
            false
        }
    }

    fun download(url: String, outputFile: File, onProgress: (Int) -> Unit = {}): Boolean {
        val headers = mapOf(
            "User-Agent" to AppHttp.UA_CHROME,
            "Accept" to AppHttp.ACCEPT_ANY,
            "Accept-Language" to AppHttp.ACCEPT_LANG_ZH
        )
        val req = Request.Builder().url(url).get().apply {
            headers.forEach { (k, v) -> addHeader(k, v) }
        }.build()

        client.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) {
                Log.e("DownloadManager", "download failed status=${resp.code} url=$url")
                return false
            }
            val body = resp.body ?: return false
            val ctype = (resp.header("Content-Type") ?: "").lowercase()
            Log.d("DownloadManager", "first response status=${resp.code} ctype=$ctype")

            if (ctype.contains("text/html")) {
                var html = body.string()
                if (AcwSolver.hasChallenge(html)) {
                    Log.d("DownloadManager", "html challenge detected, start solving acw_sc__v2")
                    val host = url.toHttpUrl().host
                    var round = 1
                    while (round <= 3) {
                        val hasChallenge = AcwSolver.hasChallenge(html)
                        if (hasChallenge) {
                            val token = AcwSolver.solveAcwScV2(html)
                            if (token.isNullOrBlank()) {
                                Log.w("DownloadManager", "challenge solve returned null in round=$round, fallback passive retry")
                            } else {
                                OkHttpProvider.upsertCookie(host, "acw_sc__v2", token)
                            }
                        } else {
                            Log.w("DownloadManager", "html in round=$round has no recognizable acw markers, passive retry")
                        }
                        val cookieHeader = OkHttpProvider.buildCookieHeader(host)
                        Log.d(
                            "DownloadManager",
                            "challenge round=$round cookie_count=${cookieHeader.split(';').size}"
                        )

                        val req2 = Request.Builder()
                            .url(url)
                            .get()
                            .addHeader("User-Agent", headers["User-Agent"]!!)
                            .addHeader("Accept", headers["Accept"]!!)
                            .addHeader("Accept-Language", headers["Accept-Language"]!!)
                            .addHeader("Cookie", cookieHeader)
                            .build()
                        client.newCall(req2).execute().use { resp2 ->
                            if (!resp2.isSuccessful) {
                                Log.e("DownloadManager", "retry round=$round failed status=${resp2.code}")
                                return false
                            }
                            val body2 = resp2.body ?: return false
                            val ctype2 = (resp2.header("Content-Type") ?: "").lowercase()
                            Log.d("DownloadManager", "retry round=$round status=${resp2.code} ctype=$ctype2")
                            if (!ctype2.contains("text/html")) {
                                val ok = saveToFile(body2.contentLength(), body2.byteStream(), outputFile, onProgress)
                                if (ok) recordValidationFalseNegative(url)
                                if (!ok) Log.e("DownloadManager", "saveToFile failed after challenge")
                                return ok
                            }
                            html = body2.string()
                        }
                        Thread.sleep(150)
                        round += 1
                    }
                    Log.e("DownloadManager", "challenge retries exhausted, still html")
                    return false
                }
                Log.e("DownloadManager", "html response without recognizable challenge")
                return false
            }
            val ok = saveToFile(body.contentLength(), body.byteStream(), outputFile, onProgress)
            if (!ok) Log.e("DownloadManager", "saveToFile failed ctype=$ctype")
            return ok
        }
    }

    fun downloadToPublicDownloads(
        context: Context,
        url: String,
        fileName: String,
        subDir: String = "MangaDownload",
        onProgress: (Int) -> Unit = {}
    ): Pair<Boolean, String> {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val resolver = context.contentResolver
            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, fileName)
                put(MediaStore.Downloads.MIME_TYPE, "application/octet-stream")
                put(MediaStore.Downloads.RELATIVE_PATH, "${Environment.DIRECTORY_DOWNLOADS}/$subDir")
                put(MediaStore.Downloads.IS_PENDING, 1)
            }
            val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                ?: return false to "创建目标文件失败"
            return try {
                val ok = downloadToUri(url, resolver, uri, onProgress)
                if (ok) {
                    values.clear()
                    values.put(MediaStore.Downloads.IS_PENDING, 0)
                    resolver.update(uri, values, null, null)
                    true to "content://downloads/public_downloads (${Environment.DIRECTORY_DOWNLOADS}/$subDir/$fileName)"
                } else {
                    resolver.delete(uri, null, null)
                    false to "下载失败"
                }
            } catch (e: Exception) {
                resolver.delete(uri, null, null)
                false to "下载异常: ${e.message}"
            }
        }

        // API < 29 fallback (requires legacy storage permission)
        val dir = File(
            Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS),
            subDir
        )
        if (!dir.exists() && !dir.mkdirs()) {
            return false to "创建下载目录失败: ${dir.absolutePath}"
        }
        val outFile = File(dir, fileName)
        val ok = download(url, outFile, onProgress)
        return ok to outFile.absolutePath
    }

    private fun saveToFile(total: Long, input: java.io.InputStream, output: File, onProgress: (Int) -> Unit): Boolean {
        output.parentFile?.mkdirs()
        output.outputStream().use { out ->
            input.use { ins ->
                val buf = ByteArray(8192)
                var sum = 0L
                while (true) {
                    val len = ins.read(buf)
                    if (len <= 0) break
                    out.write(buf, 0, len)
                    sum += len
                    if (total > 0) {
                        onProgress(((sum * 100) / total).toInt().coerceIn(0, 100))
                    }
                }
            }
        }
        return output.exists() && output.length() > 0
    }

    private fun downloadToUri(
        url: String,
        resolver: android.content.ContentResolver,
        targetUri: Uri,
        onProgress: (Int) -> Unit
    ): Boolean {
        val tmp = File.createTempFile("lanzou_dl_", ".tmp")
        return try {
            val ok = download(url, tmp, onProgress)
            if (!ok) return false
            resolver.openOutputStream(targetUri, "w")?.use { out ->
                tmp.inputStream().use { ins ->
                    ins.copyTo(out)
                }
            } ?: return false
            true
        } finally {
            tmp.delete()
        }
    }

    private fun shouldSkipValidation(url: String): Boolean {
        val host = url.toHttpUrl().host.lowercase()
        return validationPolicy[host]?.skipValidation == true
    }

    private fun recordValidationFalseNegative(url: String) {
        val host = url.toHttpUrl().host.lowercase()
        val old = validationPolicy[host] ?: ValidationState(0, false)
        val next = old.copy(falseNegative = old.falseNegative + 1)
        val final = if (next.falseNegative >= 2) next.copy(skipValidation = true) else next
        validationPolicy[host] = final
        if (final.skipValidation) {
            Log.d("DownloadManager", "adaptive validation enabled for host=$host")
        }
    }
}

private data class ValidationState(
    val falseNegative: Int,
    val skipValidation: Boolean
)
