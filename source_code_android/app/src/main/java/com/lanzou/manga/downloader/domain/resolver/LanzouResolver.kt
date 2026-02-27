package com.lanzou.manga.downloader.domain.resolver

import android.util.Log
import com.lanzou.manga.downloader.data.network.AppHttp
import com.lanzou.manga.downloader.data.network.OkHttpProvider
import com.lanzou.manga.downloader.domain.challenge.AcwSolver
import okhttp3.FormBody
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject

class LanzouResolver(private val client: OkHttpClient) {

    fun resolveRealUrl(fileLink: String, ajaxFileId: String? = null): String? {
        val commonUa = AppHttp.UA_CHROME
        val page = requestTextWithChallenge(fileLink, commonUa) ?: return null
        val p = java.net.URL(fileLink)
        val origin = "${p.protocol}://${p.host}"

        val fnCandidate = extractFnUrl(page) ?: return null
        val fnUrl = java.net.URL(java.net.URL("$origin/"), fnCandidate).toString()
        var params: FnParams? = null
        repeat(2) { idx ->
            val fnHtml = requestTextWithChallenge(fnUrl, commonUa, fileLink) ?: return@repeat
            params = extractParamsFromFnScripts(fnHtml, origin, fnUrl, commonUa, ajaxFileId)
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
        val websign = pms.websign ?: ""

        val ajaxUrl = "$origin/ajaxm.php?file=$fileId"
        val body = FormBody.Builder()
            .add("action", "downprocess")
            .add("websignkey", ajaxData)
            .add("signs", ajaxData)
            .add("sign", sign)
            .add("websign", websign)
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
            if (dom.isBlank() || path.isBlank()) return null
            Log.d("LanzouResolver", "resolve success fileId=$fileId")
            return "$dom/file/$path&toolsdown"
        }
    }

    private fun requestTextWithChallenge(
        url: String,
        userAgent: String,
        referer: String? = null
    ): String? {
        val host = runCatching { java.net.URL(url).host }.getOrNull() ?: return null
        OkHttpProvider.upsertCookie(host, "codelen", "1")

        repeat(2) { round ->
            val reqBuilder = Request.Builder()
                .url(url)
                .get()
                .addHeader("User-Agent", userAgent)
                .addHeader("Accept", AppHttp.ACCEPT_HTML)
            if (!referer.isNullOrBlank()) reqBuilder.addHeader("Referer", referer)
            val cookieHeader = OkHttpProvider.buildCookieHeader(host)
            if (cookieHeader.isNotBlank()) reqBuilder.addHeader("Cookie", cookieHeader)

            client.newCall(reqBuilder.build()).execute().use { resp ->
                if (!resp.isSuccessful) return null
                val body = resp.body?.string() ?: return null
                if (!AcwSolver.hasChallenge(body)) return body
                val token = AcwSolver.solveAcwScV2(body)
                if (token.isNullOrBlank()) return null
                OkHttpProvider.upsertCookie(host, "acw_sc__v2", token)
                if (round == 0) {
                    Log.d("LanzouResolver", "challenge detected and solved, retrying page")
                }
            }
        }
        return null
    }

    private fun extractFnUrl(html: String): String? {
        val iframe = Regex("<iframe[^>]+src=['\"]([^'\"]+)").find(html)?.groupValues?.get(1)
        if (!iframe.isNullOrBlank() && iframe.contains("fn?")) return iframe.replace("\\/", "/")
        return Regex("((?:https?://[^\\s'\"]+)?/?fn\\?[A-Za-z0-9_\\-+=/%?&]+)")
            .find(html)?.groupValues?.get(1)?.replace("\\/", "/")
    }

    private fun extractParamsFromFnScripts(
        fnHtml: String,
        origin: String,
        fnUrl: String,
        ua: String,
        ajaxFileId: String?
    ): FnParams? {
        var best: FnParams? = null
        if (!ajaxFileId.isNullOrBlank() && ajaxFileId.all { it.isDigit() }) {
            best = FnParams(fileId = ajaxFileId, ajaxData = null, sign = null, websign = null)
        }
        val scripts = Regex("<script[^>]*>([\\s\\S]*?)</script>", RegexOption.IGNORE_CASE)
            .findAll(fnHtml).map { it.groupValues[1] }.toList()
        scripts.forEach {
            extractParamsFromJsText(it)?.let { p ->
                best = merge(best, p)
                if (best.isComplete()) return best
            }
        }

        val srcs = Regex("<script[^>]+src=['\"]([^'\"]+)['\"]", RegexOption.IGNORE_CASE)
            .findAll(fnHtml).map { it.groupValues[1] }.toList()
        for (src in srcs.take(12)) {
            val full = java.net.URL(java.net.URL("$origin/"), src).toString()
            val js = requestTextWithChallenge(full, ua, fnUrl) ?: continue
            extractParamsFromJsText(js)?.let { p ->
                best = merge(best, p)
                if (best.isComplete()) return best
            }
        }
        return best
    }

    private fun extractParamsFromJsText(text: String): FnParams? {
        val fileId = Regex("ajaxm\\.php\\?file=(\\d{6,})").find(text)?.groupValues?.get(1)
            ?: Regex("url\\s*:\\s*['\"]/ajaxm\\.php\\?file=['\"]\\s*\\+\\s*(\\d{6,})")
                .find(text)?.groupValues?.get(1)
        val ajaxData = Regex("var\\s+ajaxdata\\s*=\\s*['\"]([^'\"]+)['\"]").find(text)?.groupValues?.get(1)
            ?: Regex("websignkey\\s*[:=]\\s*['\"]([^'\"]+)['\"]").find(text)?.groupValues?.get(1)
        val sign = Regex("var\\s+wp_sign\\s*=\\s*['\"]([^'\"]+)['\"]").find(text)?.groupValues?.get(1)
            ?: Regex("\\bsign\\s*[:=]\\s*['\"]([^'\"]+)['\"]").find(text)?.groupValues?.get(1)
        val websign = Regex("var\\s+websign\\s*=\\s*['\"]([^'\"]*)['\"]").find(text)?.groupValues?.get(1)
            ?: Regex("['\"]websign['\"]\\s*[:=]\\s*['\"]([^'\"]*)['\"]").find(text)?.groupValues?.get(1)
            ?: Regex("['\"]websign['\"]\\s*[:=]\\s*(\\d+)").find(text)?.groupValues?.get(1)
        return FnParams(fileId, ajaxData, sign, websign)
    }

    private fun merge(old: FnParams?, newer: FnParams?): FnParams {
        return FnParams(
            fileId = old?.fileId ?: newer?.fileId,
            ajaxData = old?.ajaxData ?: newer?.ajaxData,
            sign = old?.sign ?: newer?.sign,
            websign = old?.websign ?: newer?.websign
        )
    }
}

private data class FnParams(
    val fileId: String?,
    val ajaxData: String?,
    val sign: String?,
    val websign: String?
) {
    fun isComplete(): Boolean = !fileId.isNullOrBlank() && !ajaxData.isNullOrBlank() && !sign.isNullOrBlank()
}
