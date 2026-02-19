package com.lanzou.downloader.ui

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.lanzou.downloader.data.DownloadProgress
import com.lanzou.downloader.data.LanzouFile
import com.lanzou.downloader.data.LanzouRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.io.File

class MainViewModel : ViewModel() {
    private val repository = LanzouRepository()

    var shareUrl by mutableStateOf("")
    var password by mutableStateOf("")
    var isLoading by mutableStateOf(false)
    var status by mutableStateOf("就绪")
    var currentProgress by mutableStateOf<DownloadProgress?>(null)

    val files = mutableStateListOf<LanzouFile>()
    val selectedIds = mutableStateListOf<String>()
    val logs = mutableStateListOf<String>()

    fun appendLog(line: String) {
        val msg = "[${System.currentTimeMillis() / 1000}] $line"
        logs.add(0, msg)
        if (logs.size > 120) logs.removeLast()
    }

    fun fetchFiles() {
        if (isLoading) return
        if (shareUrl.trim().isEmpty()) {
            status = "请先输入分享链接"
            appendLog(status)
            return
        }
        isLoading = true
        status = "正在获取文件列表"
        viewModelScope.launch {
            runCatching {
                repository.fetchFileList(shareUrl.trim(), password.trim(), ::appendLog)
            }.onSuccess { list ->
                files.clear()
                files.addAll(list)
                selectedIds.clear()
                status = "获取完成: ${list.size} 个文件"
                appendLog(status)
            }.onFailure {
                status = "获取失败: ${it.message}"
                appendLog(status)
            }
            isLoading = false
        }
    }

    fun toggleSelect(id: String) {
        if (selectedIds.contains(id)) selectedIds.remove(id) else selectedIds.add(id)
    }

    fun selectAll() {
        selectedIds.clear()
        selectedIds.addAll(files.map { it.id })
    }

    fun clearSelection() {
        selectedIds.clear()
    }

    fun downloadSelected(context: Context) {
        if (isLoading) return
        val selected = files.filter { selectedIds.contains(it.id) }
        if (selected.isEmpty()) {
            status = "请先选择文件"
            return
        }

        isLoading = true
        status = "开始下载 ${selected.size} 个文件"

        viewModelScope.launch {
            val targetDir = File(context.getExternalFilesDir(null), "downloads")
            var okCount = 0
            selected.forEachIndexed { idx, file ->
                appendLog("[${idx + 1}/${selected.size}] 下载 ${file.name}")
                val ok = runCatching {
                    repository.downloadFile(context, file, targetDir, { p ->
                        viewModelScope.launch(Dispatchers.Main.immediate) {
                            currentProgress = p
                        }
                    }, ::appendLog)
                }.getOrElse {
                    appendLog("下载失败 ${file.name}: ${it.message}")
                    false
                }
                if (ok) okCount += 1
            }
            status = "下载结束: 成功 $okCount / ${selected.size}"
            appendLog(status)
            isLoading = false
        }
    }
}
