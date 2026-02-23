package com.lanzou.manga.downloader.domain.resolver

import android.util.Log
import com.lanzou.manga.downloader.data.network.AppHttp
import com.lanzou.manga.downloader.domain.challenge.AcwSolver
import okhttp3.FormBody
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject

class LanzouResolver(private val client: OkHttpClient) {

    fun resolveRealUrl(fileLink: String): String? {
        val commonUa = AppHttp.UA_CHROME

        val page = getText(fileLink, mapOf("User-Agent" to commonUa)) ?: return null
        val p = java.net.URL(fileLink)
        val origin = "${p.protocol}://${p.host}"

        val fnCandidate = extractFnUrl(page) ?: return null
        val fnUrl = java.net.URL(java.net.URL(origin + "/"), fnCandidate).toString()
        var params: FnParams? = null
        repeat(2) { idx ->
            val fnHtml = getText(fnUrl, mapOf("User-Agent" to commonUa, "Referer" to fileLink)) ?: return@repeat
            params = extractParamsFromFnScripts(fnHtml, origin, fnUrl, commonUa)
            if (params?.isComplete() == true) return@repeat
            if (idx == 0) {
                Log.d("LanzouResolver", "fn params incomplete, retry once")
                Thread.sleep(350)
            }
        }
        val pms = params ?: return null
        val ajaxData = pms.ajaxData ?: return null
        val sign = pms.sign ?: return null
        val fileId = pms.fileId ?: return null

        val ajaxUrl = "$origin/ajaxm.php?file=$fileId"
        val body = FormBody.Builder()
            .add("action", "downprocess")
            .add("websignkey", ajaxData)
            .add("signs", ajaxData)
            .add("sign", sign)
            .add("websign", "")
            .add("kd", "1")
            .add("ves", "1")
            .build()
        val req = Request.Builder()
            .url(ajaxUrl)
            .post(body)
            .addHeader("Accept", AppHttp.ACCEPT_JSON)
            .addHeader("X-Requested-With", "XMLHttpRequest")
            .addHeader("Origin", origin)
            .addHeader("Referer", fnUrl)
            .addHeader("User-Agent", commonUa)
            .build()
        client.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) return null
            val txt = resp.body?.string() ?: return null
            val json = try {
                JSONObject(txt)
            } catch (_: Exception) {
                return null
            }
            val zt = json.optInt("zt", -1)
            if (zt != 1) {
                Log.e("LanzouResolver", "ajaxm zt=$zt info=${json.optString("inf")}")
                return null
            }
            val dom = json.optString("dom", "").trim().trimEnd('/')
            val path = json.optString("url", "").trim()
            if (dom.isNullOrBlank() || path.isNullOrBlank()) return null
            Log.d("LanzouResolver", "resolve success fileId=$fileId")
            return "$dom/file/$path&toolsdown"
        }
    }

    fun solveChallengeIfNeeded(html: String): String? {
        if (!AcwSolver.hasChallenge(html)) return null
        return AcwSolver.solveAcwScV2(html)
    }

    private fun getText(url: String, headers: Map<String, String>): String? {
        val reqBuilder = Request.Builder().url(url).get()
        headers.forEach { (k, v) -> reqBuilder.addHeader(k, v) }
        client.newCall(reqBuilder.build()).execute().use { resp ->
            if (!resp.isSuccessful) return null
            return resp.body?.string()
        }
    }

    private fun extractFnUrl(html: String): String? {
        val iframe = Regex("<iframe[^>]+src=['\"]([^'\"]+)").find(html)?.groupValues?.get(1)
        if (!iframe.isNullOrBlank() && iframe.contains("fn?")) return iframe.replace("\\/", "/")
        return Regex("((?:https?://[^\\s'\"]+)?/?fn\\?[A-Za-z0-9_\\-+=/%?&]+)")
            .find(html)?.groupValues?.get(1)?.replace("\\/", "/")
    }

    private fun extractParamsFromFnScripts(fnHtml: String, origin: String, fnUrl: String, ua: String): FnParams? {
        var best: FnParams? = null
        val scripts = Regex("<script[^>]*>([\\s\\S]*?)</script>", RegexOption.IGNORE_CASE)
            .findAll(fnHtml).map { it.groupValues[1] }.toList()
        scripts.forEach {
            extractParamsFromJsText(it)?.let { p ->
                best = merge(best, p)
                if (best?.isComplete() == true) {
                    Log.d("LanzouResolver", "params from inline scripts fileId=${best?.fileId}")
                    return best
                }
            }
        }

        val srcs = Regex("<script[^>]+src=['\"]([^'\"]+)['\"]", RegexOption.IGNORE_CASE)
            .findAll(fnHtml).map { it.groupValues[1] }.toList()
        for (src in srcs.take(12)) {
            val full = java.net.URL(java.net.URL(origin + "/"), src).toString()
            val js = getText(full, mapOf("User-Agent" to ua, "Referer" to fnUrl)) ?: continue
            extractParamsFromJsText(js)?.let { p ->
                best = merge(best, p)
                if (best?.isComplete() == true) {
                    Log.d("LanzouResolver", "params from external scripts fileId=${best?.fileId}")
                    return best
                }
            }
        }
        return best
    }

    private fun extractParamsFromJsText(text: String): FnParams? {
        val fileId = Regex("ajaxm\\.php\\?file=(\\d{6,})").find(text)?.groupValues?.get(1)
            ?: Regex("url\\s*:\\s*['\"]/ajaxm\\.php\\?file=['\"]\\s*\\+\\s*(\\d{6,})").find(text)?.groupValues?.get(1)
        val ajaxData = Regex("var\\s+ajaxdata\\s*=\\s*['\"]([^'\"]+)['\"]").find(text)?.groupValues?.get(1)
            ?: Regex("websignkey\\s*[:=]\\s*['\"]([^'\"]+)['\"]").find(text)?.groupValues?.get(1)
        val sign = Regex("var\\s+wp_sign\\s*=\\s*['\"]([^'\"]+)['\"]").find(text)?.groupValues?.get(1)
            ?: Regex("\\bsign\\s*[:=]\\s*['\"]([^'\"]+)['\"]").find(text)?.groupValues?.get(1)
        return FnParams(fileId, ajaxData, sign)
    }

    private fun merge(old: FnParams?, newer: FnParams?): FnParams {
        return FnParams(
            fileId = old?.fileId ?: newer?.fileId,
            ajaxData = old?.ajaxData ?: newer?.ajaxData,
            sign = old?.sign ?: newer?.sign
        )
    }
}

data class FnParams(
    val fileId: String?,
    val ajaxData: String?,
    val sign: String?
) {
    fun isComplete(): Boolean = !fileId.isNullOrBlank() && !ajaxData.isNullOrBlank() && !sign.isNullOrBlank()
}
