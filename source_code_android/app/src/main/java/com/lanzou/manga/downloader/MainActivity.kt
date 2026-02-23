package com.lanzou.manga.downloader

import android.app.DownloadManager
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.lifecycle.viewmodel.compose.viewModel
import com.lanzou.manga.downloader.ui.MainScreen
import com.lanzou.manga.downloader.ui.MainViewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val vm: MainViewModel = viewModel()
            val ui by vm.state.collectAsState()

            LaunchedEffect(Unit) {
                vm.fetchFiles()
            }

            MainScreen(
                ui = ui,
                onFetchFiles = vm::fetchFiles,
                onUpdateSearchQuery = vm::updateSearchQuery,
                onSelectAll = vm::selectAll,
                onInvertSelection = vm::invertSelection,
                onClearSelection = vm::clearSelection,
                onToggleOnlyUndownloaded = vm::toggleOnlyUndownloaded,
                onDownloadSelected = vm::downloadSelected,
                onOpenDownloadDirectory = ::openDownloadDirectory,
                onToggleSelection = vm::toggleSelection
            )
        }
    }

    private fun openDownloadDirectory() {
        // 打开系统下载页，用户可在其中访问 Download/MangaDownload。
        val intent = Intent(DownloadManager.ACTION_VIEW_DOWNLOADS).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        runCatching { startActivity(intent) }
    }
}
