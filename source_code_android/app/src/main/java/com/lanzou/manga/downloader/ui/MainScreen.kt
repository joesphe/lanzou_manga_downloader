package com.lanzou.manga.downloader.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
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

@Composable
fun MainScreen(
    ui: UiState,
    onFetchFiles: () -> Unit,
    onUpdateSearchQuery: (String) -> Unit,
    onSelectAll: () -> Unit,
    onInvertSelection: () -> Unit,
    onClearSelection: () -> Unit,
    onToggleOnlyUndownloaded: (Boolean) -> Unit,
    onDownloadSelected: () -> Unit,
    onOpenDownloadDirectory: () -> Unit,
    onToggleSelection: (Int) -> Unit
) {
    val filteredFiles = UiSelectors.filteredFiles(ui)
    val selectableSelectedCount = UiSelectors.selectedUndownloadedCount(ui)

    Scaffold(
        topBar = {
            SmallTopAppBar(title = "蓝奏云下载器")
        },
        content = { paddingValues ->
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues)
                    .padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                contentPadding = PaddingValues(bottom = 16.dp)
            ) {
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        insideMargin = PaddingValues(16.dp)
                    ) {
                        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
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
                        enabled = selectableSelectedCount > 0 && !ui.isDownloading && !ui.isLoadingList,
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

                if (filteredFiles.isNotEmpty()) {
                    item {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            insideMargin = PaddingValues(vertical = 8.dp)
                        ) {
                            Column {
                                filteredFiles.forEach { f ->
                                    val checked = ui.selectedIndices.contains(f.index)
                                    val downloaded = ui.downloadedNames.contains(f.name)
                                    val isEnabled = !ui.isDownloading && !downloaded

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
                }
            }
        }
    )
}
