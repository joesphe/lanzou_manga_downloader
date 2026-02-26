package com.lanzou.manga.downloader

import android.app.DownloadManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.Settings
import android.widget.Toast
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
    private var updateApkDownloadId: Long? = null

    private val updateDownloadReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action != DownloadManager.ACTION_DOWNLOAD_COMPLETE) return
            val id = intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1L)
            if (id <= 0L || id != updateApkDownloadId) return
            handleApkDownloadFinished(id)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        registerUpdateDownloadReceiver()
        setContent {
            val vm: MainViewModel = viewModel()
            val ui by vm.state.collectAsState()

            LaunchedEffect(Unit) {
                vm.fetchFiles()
                vm.checkForUpdates(currentVersion = BuildConfig.VERSION_NAME, silentIfUpToDate = true)
            }

            AppTheme {
                MainScreen(
                    ui = ui,
                    onFetchFiles = vm::fetchFiles,
                    onToggleUseCustomSource = vm::toggleUseCustomSource,
                    onUpdateCustomUrl = vm::updateCustomUrl,
                    onUpdateCustomPassword = vm::updateCustomPassword,
                    onToggleAllowRedownloadAfterDownload = vm::toggleAllowRedownloadAfterDownload,
                    onUpdateSearchQuery = vm::updateSearchQuery,
                    onSelectAll = vm::selectAll,
                    onInvertSelection = vm::invertSelection,
                    onClearSelection = vm::clearSelection,
                    onToggleOnlyUndownloaded = vm::toggleOnlyUndownloaded,
                    onDownloadSelected = vm::downloadSelected,
                    onOpenDownloadDirectory = ::openDownloadDirectory,
                    onToggleSelection = vm::toggleSelection,
                    onCheckUpdates = { vm.checkForUpdates(BuildConfig.VERSION_NAME, silentIfUpToDate = false) },
                    onDownloadAndroidPackage = ::downloadAndInstallApk,
                    onOpenReleasePage = ::openReleasePage,
                    onDismissUpdateDialog = vm::dismissUpdateDialog,
                    onIgnoreUpdateVersion = vm::ignoreCurrentUpdateVersion,
                    version = BuildConfig.VERSION_NAME
                )
            }
        }
    }

    override fun onDestroy() {
        runCatching { unregisterReceiver(updateDownloadReceiver) }
        super.onDestroy()
    }

    private fun openDownloadDirectory() {
        val intent = Intent(DownloadManager.ACTION_VIEW_DOWNLOADS).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        runCatching { startActivity(intent) }
    }

    private fun openReleasePage(url: String) {
        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url)).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        runCatching { startActivity(intent) }
    }

    private fun downloadAndInstallApk(url: String) {
        val target = url.trim()
        if (target.isBlank()) {
            openReleasePage("https://gitee.com/greovity/lanzou_manga_downloader/releases")
            return
        }
        val dm = getSystemService(DOWNLOAD_SERVICE) as DownloadManager
        val fileName = sanitizeApkFilename(
            Uri.parse(target).getQueryParameter("attname")
                ?: Uri.parse(target).lastPathSegment
                ?: "lanzou_update.apk"
        )
        val request = DownloadManager.Request(Uri.parse(target))
            .setTitle("蓝奏云下载器更新")
            .setDescription("正在下载安装包...")
            .setMimeType("application/vnd.android.package-archive")
            .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
            .setAllowedOverMetered(true)
            .setAllowedOverRoaming(true)
            .setDestinationInExternalPublicDir(
                Environment.DIRECTORY_DOWNLOADS,
                "MangaDownload/$fileName"
            )

        runCatching {
            updateApkDownloadId = dm.enqueue(request)
            Toast.makeText(this, "开始下载更新安装包", Toast.LENGTH_SHORT).show()
        }.onFailure {
            Toast.makeText(this, "下载启动失败，已打开发布页", Toast.LENGTH_SHORT).show()
            openReleasePage(target)
        }
    }

    private fun handleApkDownloadFinished(downloadId: Long) {
        val dm = getSystemService(DOWNLOAD_SERVICE) as DownloadManager
        val query = DownloadManager.Query().setFilterById(downloadId)
        dm.query(query).use { cursor ->
            if (!cursor.moveToFirst()) {
                updateApkDownloadId = null
                return
            }
            val status = cursor.getInt(cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS))
            when (status) {
                DownloadManager.STATUS_SUCCESSFUL -> {
                    val uri = dm.getUriForDownloadedFile(downloadId)
                    if (uri != null) {
                        promptInstallApk(uri)
                    } else {
                        Toast.makeText(this, "下载完成，请手动安装", Toast.LENGTH_LONG).show()
                        openDownloadDirectory()
                    }
                }
                else -> {
                    Toast.makeText(this, "安装包下载失败，请重试", Toast.LENGTH_LONG).show()
                }
            }
        }
        updateApkDownloadId = null
    }

    private fun promptInstallApk(apkUri: Uri) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && !packageManager.canRequestPackageInstalls()) {
            Toast.makeText(this, "请先允许安装未知应用来源", Toast.LENGTH_LONG).show()
            val settingsIntent = Intent(
                Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                Uri.parse("package:$packageName")
            ).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            runCatching { startActivity(settingsIntent) }
            openDownloadDirectory()
            return
        }
        val installIntent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(apkUri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        runCatching { startActivity(installIntent) }
            .onFailure {
                Toast.makeText(this, "无法直接唤起安装，请手动安装", Toast.LENGTH_LONG).show()
                openDownloadDirectory()
            }
    }

    private fun sanitizeApkFilename(raw: String): String {
        val cleaned = raw.replace(Regex("""[<>:"/\\|?*\u0000-\u001F]"""), "_").trim().trim('.')
        val name = if (cleaned.isBlank()) "lanzou_update.apk" else cleaned
        return if (name.endsWith(".apk", ignoreCase = true)) name else "$name.apk"
    }

    private fun registerUpdateDownloadReceiver() {
        val filter = IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(updateDownloadReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(updateDownloadReceiver, filter)
        }
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
