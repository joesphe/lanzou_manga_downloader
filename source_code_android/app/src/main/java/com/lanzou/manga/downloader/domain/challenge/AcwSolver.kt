package com.lanzou.manga.downloader.domain.challenge

import java.net.URLDecoder

object AcwSolver {

    private val alpha = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/="

    fun hasChallenge(html: String): Boolean {
        val markers = listOf("acw_sc__v2", "document.cookie", "location.reload", "var arg1=")
        return markers.any { html.contains(it) }
    }

    fun solveAcwScV2(html: String): String? {
        val arg1 = Regex("var\\s+arg1\\s*=\\s*['\"]([0-9A-Fa-f]+)['\"]").find(html)?.groupValues?.get(1)
            ?: return null
        val mRaw = extractPermutationArray(html) ?: return null
        val nRaw = extractEncodedArray(html) ?: return null

        val perm = mRaw.split(",").mapNotNull { parseIntFlexible(it.trim()) }
        val encoded = Regex("'([^']*)'").findAll(nRaw).map { it.groupValues[1] }.toList()
        val decoded = encoded.map { decodeAcwItem(it) }
        val keyHex = decoded.firstOrNull { Regex("^[0-9a-fA-F]{40}$").matches(it) } ?: return null

        val q = MutableList(perm.size) { "" }
        arg1.forEachIndexed { i, ch ->
            val target = i + 1
            val z = perm.indexOfFirst { it == target }
            if (z >= 0) q[z] = ch.toString()
        }

        val u = q.joinToString("")
        val n = minOf(u.length, keyHex.length).let { it - (it % 2) }
        if (n < 2) return null

        val sb = StringBuilder()
        var i = 0
        while (i < n) {
            val a = u.substring(i, i + 2).toInt(16)
            val b = keyHex.substring(i, i + 2).toInt(16)
            sb.append(((a xor b).toString(16)).padStart(2, '0'))
            i += 2
        }
        return sb.toString()
    }

    private fun extractPermutationArray(html: String): String? {
        // Case 1: var m=[...]
        Regex("var\\s+m\\s*=\\s*\\[([^\\]]+)]").find(html)?.let { return it.groupValues[1] }
        // Case 2: for(var m=[...],p=...)
        Regex("for\\s*\\(\\s*var\\s+[A-Za-z_][A-Za-z0-9_]*\\s*=\\s*\\[([^\\]]+)]\\s*,")
            .find(html)?.let { return it.groupValues[1] }
        return null
    }

    private fun extractEncodedArray(html: String): String? {
        // Preferred pattern: var N=[...];a0i=function...
        Regex("var\\s+[A-Za-z_][A-Za-z0-9_]*\\s*=\\s*\\[(.*?)]\\s*;\\s*a0i\\s*=\\s*function",
            setOf(RegexOption.DOT_MATCHES_ALL))
            .find(html)?.let { return it.groupValues[1] }

        // Fallback: first large quoted-string array in a0i function body
        Regex("function\\s+a0i\\s*\\(\\)\\s*\\{([\\s\\S]*?)return\\s+a0i\\s*\\(\\)\\s*;\\s*\\}",
            setOf(RegexOption.DOT_MATCHES_ALL))
            .find(html)
            ?.groupValues?.get(1)
            ?.let { body ->
                Regex("\\[\\s*'[^']+'(?:\\s*,\\s*'[^']+')+\\s*\\]").find(body)?.let { arr ->
                    return arr.value.removePrefix("[").removeSuffix("]")
                }
            }
        return null
    }

    private fun decodeAcwItem(s: String): String {
        var q = 0
        var r = 0
        var t = 0
        val out = StringBuilder()
        while (true) {
            val ch = s.getOrNull(t) ?: break
            t += 1
            val idx = alpha.indexOf(ch)
            if (idx != -1) {
                r = if (q % 4 != 0) r * 64 + idx else idx
                val oldQ = q
                q += 1
                if (oldQ % 4 != 0) {
                    val c = 255 and (r shr ((-2 * q) and 6))
                    if (c != 0) out.append(c.toChar())
                }
            }
        }
        return try {
            val encoded = buildString {
                out.forEach { append("%").append(it.code.toString(16).padStart(2, '0')) }
            }
            URLDecoder.decode(encoded, Charsets.UTF_8.name())
        } catch (_: Exception) {
            out.toString()
        }
    }

    private fun parseIntFlexible(raw: String): Int? {
        if (raw.isBlank()) return null
        return try {
            when {
                raw.startsWith("0x", ignoreCase = true) -> raw.substring(2).toInt(16)
                raw.startsWith("-0x", ignoreCase = true) -> -raw.substring(3).toInt(16)
                else -> raw.toInt()
            }
        } catch (_: Exception) {
            null
        }
    }
}
