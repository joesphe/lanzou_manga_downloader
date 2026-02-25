package com.lanzou.manga.downloader

import android.app.DownloadManager
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.lifecycle.viewmodel.compose.viewModel
import com.lanzou.manga.downloader.ui.MainScreen
import com.lanzou.manga.downloader.ui.MainViewModel
import top.yukonga.miuix.kmp.theme.ColorSchemeMode
import top.yukonga.miuix.kmp.theme.MiuixTheme
import top.yukonga.miuix.kmp.theme.ThemeController

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val vm: MainViewModel = viewModel()
            val ui by vm.state.collectAsState()

            LaunchedEffect(Unit) {
                vm.fetchFiles()
            }

            AppTheme {
                MainScreen(
                    ui = ui,
                    onFetchFiles = vm::fetchFiles,
                    onToggleUseCustomSource = vm::toggleUseCustomSource,
                    onUpdateCustomUrl = vm::updateCustomUrl,
                    onUpdateCustomPassword = vm::updateCustomPassword,
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
    }

    private fun openDownloadDirectory() {
        val intent = Intent(DownloadManager.ACTION_VIEW_DOWNLOADS).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        runCatching { startActivity(intent) }
    }
}

@Composable
fun AppTheme(
    content: @Composable () -> Unit
) {
    val controller = remember { ThemeController(ColorSchemeMode.System) }
    return MiuixTheme(
        controller = controller,
        content = content
    )
}
