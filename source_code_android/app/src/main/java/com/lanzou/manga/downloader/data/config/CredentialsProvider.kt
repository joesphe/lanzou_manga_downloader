package com.lanzou.manga.downloader.data.config

import android.util.Base64
import org.json.JSONObject
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

object CredentialsProvider : CredentialsSource {

    private val keyPart1 = byteArrayOf(
        0xF8.toByte(), 0xD5.toByte(), 0x0B.toByte(), 0x48.toByte(), 0x0D.toByte(), 0xC7.toByte(),
        0xE4.toByte(), 0x41.toByte(), 0x47.toByte(), 0xE1.toByte(), 0x98.toByte(), 0xDE.toByte()
    )
    private val keyPart2 = byteArrayOf(
        0xD3.toByte(), 0x36.toByte(), 0x12.toByte(), 0x29.toByte(), 0x45.toByte(),
        0x02.toByte(), 0x25.toByte(), 0x51.toByte(), 0xBC.toByte(), 0x8E.toByte()
    )
    private val keyPart3 = byteArrayOf(
        0xFF.toByte(), 0x57.toByte(), 0x52.toByte(), 0x0B.toByte(), 0x17.toByte(), 0x0D.toByte(),
        0xE7.toByte(), 0xC0.toByte(), 0x3D.toByte(), 0xEB.toByte(), 0x76.toByte(), 0x2B.toByte(),
        0x55.toByte(), 0xF2.toByte(), 0xAD.toByte(), 0xF8.toByte(), 0x15.toByte(), 0xF6.toByte(),
        0x4E.toByte(), 0xDF.toByte(), 0x4E.toByte(), 0xA9.toByte(), 0x65.toByte(), 0xC8.toByte(),
        0x01.toByte(), 0x63.toByte(), 0xED.toByte(), 0xCB.toByte(), 0x75.toByte(), 0xE5.toByte(),
        0x65.toByte(), 0x56.toByte()
    )
    private const val encryptedBlobB64 =
        "xrOk8r07sRpstrBGB+httG44WDGEHTTt1Ty7XKrzmL17SQRWjX7RYfJ+A/Oh2H76TAUbQ0B2OXLXyzyIrPzVOsGXthHBRG3aQGd4EMalWX2eFs0="

    override fun getDefaultUrlAndPassword(): Pair<String, String> {
        val key = ByteArray(keyPart3.size)
        for (i in key.indices) {
            val mixer = if (i < keyPart1.size) {
                keyPart1[i % keyPart1.size]
            } else {
                keyPart2[i % keyPart2.size]
            }
            key[i] = (keyPart3[i].toInt() xor mixer.toInt()).toByte()
        }

        val blob = Base64.decode(encryptedBlobB64, Base64.DEFAULT)
        val nonce = blob.copyOfRange(0, 12)
        val ciphertext = blob.copyOfRange(12, blob.size)

        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        val spec = GCMParameterSpec(128, nonce)
        cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(key, "AES"), spec)
        cipher.updateAAD("lanzou-v2".toByteArray(Charsets.UTF_8))
        val plaintext = cipher.doFinal(ciphertext).toString(Charsets.UTF_8)
        val obj = JSONObject(plaintext)

        return obj.getString("u") to obj.getString("p")
    }
}
