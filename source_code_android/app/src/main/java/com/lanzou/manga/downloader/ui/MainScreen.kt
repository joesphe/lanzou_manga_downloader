package com.lanzou.manga.downloader.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.Image
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.ui.Alignment
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import com.lanzou.manga.downloader.R
import top.yukonga.miuix.kmp.basic.Button
import top.yukonga.miuix.kmp.basic.ButtonDefaults
import top.yukonga.miuix.kmp.basic.Card
import top.yukonga.miuix.kmp.basic.Icon
import top.yukonga.miuix.kmp.basic.LinearProgressIndicator
import top.yukonga.miuix.kmp.basic.Scaffold
import top.yukonga.miuix.kmp.basic.SmallTopAppBar
import top.yukonga.miuix.kmp.basic.Text
import top.yukonga.miuix.kmp.basic.TextField
import top.yukonga.miuix.kmp.extra.SuperCheckbox
import top.yukonga.miuix.kmp.extra.SuperSwitch
import top.yukonga.miuix.kmp.icon.MiuixIcons
import top.yukonga.miuix.kmp.icon.extended.Search
import top.yukonga.miuix.kmp.theme.MiuixTheme
import top.yukonga.miuix.kmp.utils.PressFeedbackType
import kotlinx.coroutines.launch

@Composable
fun MainScreen(
    ui: UiState,
    onFetchFiles: () -> Unit,
    onToggleUseCustomSource: (Boolean) -> Unit,
    onUpdateCustomUrl: (String) -> Unit,
    onUpdateCustomPassword: (String) -> Unit,
    onToggleAllowRedownloadAfterDownload: (Boolean) -> Unit,
    onUpdateSearchQuery: (String) -> Unit,
    onSelectAll: () -> Unit,
    onInvertSelection: () -> Unit,
    onClearSelection: () -> Unit,
    onToggleOnlyUndownloaded: (Boolean) -> Unit,
    onDownloadSelected: () -> Unit,
    onOpenDownloadDirectory: () -> Unit,
    onToggleSelection: (Int) -> Unit,
    onCheckUpdates: () -> Unit,
    onOpenReleasePage: (String) -> Unit,
    onDismissUpdateDialog: () -> Unit,
    onIgnoreUpdateVersion: () -> Unit,
    version: String
) {
    val filteredFiles = UiSelectors.filteredFiles(ui)
    val selectableSelectedCount = UiSelectors.selectedUndownloadedCount(ui)
    var showSettingsDialog by remember { mutableStateOf(false) }
    val listState = rememberLazyListState()
    val coroutineScope = rememberCoroutineScope()
    val showQuickToConfirm = listState.firstVisibleItemIndex > 2 || listState.firstVisibleItemScrollOffset > 360

    Box(modifier = Modifier.fillMaxSize()) {
        Scaffold(
            topBar = {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .statusBarsPadding()
                        .padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 6.dp),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    SmallTopAppBar(title = "蓝奏云下载器")
                }
            },
            content = { paddingValues ->
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(paddingValues)
                        .padding(horizontal = 16.dp),
                    state = listState,
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    contentPadding = PaddingValues(bottom = 16.dp)
                ) {
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        insideMargin = PaddingValues(16.dp)
                    ) {
                        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                            if (ui.useCustomSource) {
                                TextField(
                                    value = ui.customUrl,
                                    onValueChange = onUpdateCustomUrl,
                                    label = "自定义蓝奏云链接",
                                    modifier = Modifier.fillMaxWidth(),
                                    enabled = !ui.isLoadingList && !ui.isDownloading
                                )

                                TextField(
                                    value = ui.customPassword,
                                    onValueChange = onUpdateCustomPassword,
                                    label = "自定义密码（可留空）",
                                    modifier = Modifier.fillMaxWidth(),
                                    enabled = !ui.isLoadingList && !ui.isDownloading
                                )
                            }

                            Button(
                                modifier = Modifier.fillMaxWidth(),
                                onClick = onFetchFiles,
                                enabled = !ui.isLoadingList && !ui.isDownloading,
                                colors = ButtonDefaults.buttonColorsPrimary()
                            ) {
                                Text(if (ui.isLoadingList) "获取中..." else "获取文件列表")
                            }

                            TextField(
                                value = ui.searchQuery,
                                onValueChange = onUpdateSearchQuery,
                                label = "按名称搜索",
                                modifier = Modifier.fillMaxWidth(),
                                enabled = !ui.isDownloading,
                                leadingIcon = {
                                    Icon(
                                        modifier = Modifier.padding(start = 12.dp, end = 8.dp),
                                        imageVector = MiuixIcons.Search,
                                        contentDescription = "Search",
                                        tint = MiuixTheme.colorScheme.onSecondaryContainer
                                    )
                                }
                            )

                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Button(
                                    modifier = Modifier.weight(1f),
                                    onClick = onSelectAll,
                                    enabled = ui.files.isNotEmpty() && !ui.isDownloading,
                                    colors = ButtonDefaults.buttonColors()
                                ) { Text("全选") }

                                Button(
                                    modifier = Modifier.weight(1f),
                                    onClick = onInvertSelection,
                                    enabled = filteredFiles.isNotEmpty() && !ui.isDownloading,
                                    colors = ButtonDefaults.buttonColors()
                                ) { Text("反选") }

                                Button(
                                    modifier = Modifier.weight(1f),
                                    onClick = onClearSelection,
                                    enabled = ui.selectedIndices.isNotEmpty() && !ui.isDownloading,
                                    colors = ButtonDefaults.buttonColors()
                                ) { Text("清空") }
                            }

                            SuperSwitch(
                                title = "只看未下载",
                                checked = ui.onlyUndownloaded,
                                onCheckedChange = onToggleOnlyUndownloaded,
                                enabled = !ui.isDownloading,
                                insideMargin = PaddingValues(0.dp)
                            )

                            Button(
                                modifier = Modifier.fillMaxWidth(),
                                onClick = onOpenDownloadDirectory,
                                colors = ButtonDefaults.buttonColors()
                            ) { Text("打开下载目录") }
                        }
                    }
                }

                item {
                    Button(
                        modifier = Modifier.fillMaxWidth(),
                        onClick = onDownloadSelected,
                        enabled = selectableSelectedCount > 0 && !ui.isDownloading,
                        colors = ButtonDefaults.buttonColorsPrimary()
                    ) {
                        Text(if (ui.isDownloading) "下载中..." else "确认下载 (${selectableSelectedCount})")
                    }
                }

                item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        insideMargin = PaddingValues(16.dp),
                        showIndication = true,
                        pressFeedbackType = PressFeedbackType.Sink
                    ) {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            if (ui.isDownloading) {
                                LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                            }
                            Text(
                                text = "状态: ${ui.status}",
                                style = MiuixTheme.textStyles.body2
                            )
                            Text(
                                text = "文件: ${ui.files.size} | 结果: ${filteredFiles.size} | 已选: $selectableSelectedCount | 已下: ${ui.downloadedNames.size}",
                                style = MiuixTheme.textStyles.footnote1,
                                color = MiuixTheme.colorScheme.onSurfaceVariantSummary
                            )
                        }
                    }
                }

                items(filteredFiles, key = { it.index }) { f ->
                    val checked = ui.selectedIndices.contains(f.index)
                    val downloaded = ui.downloadedNames.contains(f.name)
                    val isEnabled = !ui.isDownloading && !downloaded

                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        insideMargin = PaddingValues(vertical = 8.dp)
                    ) {
                        SuperCheckbox(
                            title = "${f.index}. ${f.name}",
                            summary = "大小: ${f.size}  时间: ${f.time}",
                            checked = checked,
                            onCheckedChange = { onToggleSelection(f.index) },
                            enabled = isEnabled,
                            endActions = {
                                val statusText = when {
                                    downloaded -> "已下载"
                                    checked -> "待下载"
                                    else -> ""
                                }
                                if (statusText.isNotEmpty()) {
                                    Text(
                                        text = statusText,
                                        style = MiuixTheme.textStyles.footnote1,
                                        color = if (downloaded) MiuixTheme.colorScheme.onSurfaceVariantSummary else MiuixTheme.colorScheme.primary,
                                        modifier = Modifier.padding(end = 8.dp)
                                    )
                                }
                            }
                        )
                    }
                }
                }
            }
        )

        Box(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .statusBarsPadding()
                .padding(top = 8.dp, end = 16.dp)
                .size(44.dp)
                .background(
                    color = Color(0x33FFFFFF),
                    shape = CircleShape
                )
                .clickable { showSettingsDialog = true },
            contentAlignment = Alignment.Center
        ) {
            Image(
                painter = painterResource(id = R.drawable.ic_settings_24),
                contentDescription = "Settings",
                modifier = Modifier.size(22.dp)
            )
        }

        if (showQuickToConfirm) {
            Box(
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(end = 16.dp, bottom = 24.dp)
                    .size(44.dp)
                    .background(
                        color = Color(0xAA2F4A7A),
                        shape = CircleShape
                    )
                    .clickable {
                        coroutineScope.launch {
                            listState.animateScrollToItem(1)
                        }
                    },
                contentAlignment = Alignment.Center
            ) {
                Image(
                    painter = painterResource(id = R.drawable.ic_arrow_up_24),
                    contentDescription = "Back to confirm",
                    modifier = Modifier.size(22.dp)
                )
            }
        }
    }

    if (showSettingsDialog) {
        Dialog(onDismissRequest = { showSettingsDialog = false }) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                insideMargin = PaddingValues(16.dp)
            ) {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    SettingsDialogContent(
                        useThirdPartyLinks = ui.useCustomSource,
                        allowRedownloadAfterDownload = ui.allowRedownloadAfterDownload,
                        isCheckingUpdate = ui.isCheckingUpdate,
                        latestAndroidVersion = ui.latestAndroidVersion,
                        hasUpdate = ui.hasUpdate,
                        version = version,
                        onToggleUseThirdPartyLinks = onToggleUseCustomSource,
                        onToggleAllowRedownload = onToggleAllowRedownloadAfterDownload,
                        onCheckUpdates = onCheckUpdates,
                        onOpenReleasePage = { onOpenReleasePage(ui.updateUrl) }
                    )
                    Button(
                        modifier = Modifier.fillMaxWidth(),
                        onClick = { showSettingsDialog = false },
                        colors = ButtonDefaults.buttonColorsPrimary()
                    ) {
                        Text("关闭")
                    }
                }
            }
        }
    }

    if (ui.showUpdateDialog && ui.hasUpdate) {
        Dialog(onDismissRequest = onDismissUpdateDialog) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                insideMargin = PaddingValues(16.dp)
            ) {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text(
                        text = "发现新版本",
                        style = MiuixTheme.textStyles.title3,
                        color = MiuixTheme.colorScheme.primary
                    )
                    Text(
                        text = "当前版本: $version\n最新版本: ${ui.latestAndroidVersion ?: "未知"}",
                        style = MiuixTheme.textStyles.body2
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(
                            modifier = Modifier.weight(1f),
                            onClick = onDismissUpdateDialog,
                            colors = ButtonDefaults.buttonColors()
                        ) {
                            Text("稍后再说")
                        }
                        Button(
                            modifier = Modifier.weight(1f),
                            onClick = {
                                onDismissUpdateDialog()
                                onOpenReleasePage(ui.updateUrl)
                            },
                            colors = ButtonDefaults.buttonColorsPrimary()
                        ) {
                            Text("去更新")
                        }
                    }
                    Button(
                        modifier = Modifier.fillMaxWidth(),
                        onClick = onIgnoreUpdateVersion,
                        colors = ButtonDefaults.buttonColors()
                    ) {
                        Text("忽略此版本")
                    }
                }
            }
        }
    }
}
