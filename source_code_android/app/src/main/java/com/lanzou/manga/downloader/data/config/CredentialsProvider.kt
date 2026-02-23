package com.lanzou.manga.downloader.data.config

import java.security.MessageDigest

object CredentialsProvider {

    // Same obfuscation data/logic as desktop production version.
    private val urlObfuscated = intArrayOf(
        0x0B, 0x30, 0xA2, 0x6D, 0x31, 0x15, 0x5A, 0x9F, 0x52, 0x1F, 0xC1, 0x28,
        0x36, 0x7E, 0x8C, 0xCA, 0x67, 0x18, 0x6C, 0x82, 0x57, 0x85, 0xF5, 0x9F,
        0x7C, 0x20, 0xC4, 0x17, 0x95, 0x5B, 0x89, 0xD7, 0x94, 0xED, 0x83
    )

    private val passwordObfuscated = intArrayOf(0xBD, 0xF2, 0xFD, 0xA7)

    fun getDefaultUrlAndPassword(): Pair<String, String> {
        val urlBytes = ByteArray(urlObfuscated.size)
        for (i in urlObfuscated.indices) {
            val key = getDynamicKey(i)
            urlBytes[i] = (urlObfuscated[i] xor key).toByte()
        }
        val url = urlBytes.toString(Charsets.UTF_8)

        val pwdBytes = ByteArray(passwordObfuscated.size)
        for (i in passwordObfuscated.indices) {
            val key = getDynamicKey(i + urlObfuscated.size)
            pwdBytes[i] = (passwordObfuscated[i] xor key).toByte()
        }
        val password = pwdBytes.toString(Charsets.UTF_8)

        return url to password
    }

    private fun getDynamicKey(index: Int): Int {
        val input = "dynamic_key_${index}_secret_salt".toByteArray(Charsets.UTF_8)
        val digest = MessageDigest.getInstance("SHA-256").digest(input)
        return digest[0].toInt() and 0xFF
    }
}
