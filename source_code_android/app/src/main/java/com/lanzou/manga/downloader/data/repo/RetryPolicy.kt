package com.lanzou.manga.downloader.data.repo

class RetryPolicy(
    private val maxAttempts: Int = 6,
    private val baseDelayMs: Long = 250L,
    private val maxDelayMs: Long = 2500L
) {
    fun <T> run(block: (attempt: Int) -> T?): T? {
        var last: T? = null
        var attempt = 1
        while (attempt <= maxAttempts) {
            val result = block(attempt)
            if (result != null) return result
            last = result
            attempt += 1
            Thread.sleep((baseDelayMs * attempt).coerceAtMost(maxDelayMs))
        }
        return last
    }
}

