package com.lanzou.manga.downloader.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.lanzou.manga.downloader.data.model.LanzouFile

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

    Surface(color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(text = "Lanzou Downloader Android")
            Button(
                onClick = onFetchFiles,
                enabled = !ui.isLoadingList && !ui.isDownloading
            ) { Text(if (ui.isLoadingList) "获取中..." else "获取文件列表") }

            OutlinedTextField(
                value = ui.searchQuery,
                onValueChange = onUpdateSearchQuery,
                label = { Text("按名称搜索") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                enabled = !ui.isDownloading
            )

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    onClick = onSelectAll,
                    enabled = ui.files.isNotEmpty() && !ui.isDownloading
                ) { Text("全选") }
                Button(
                    onClick = onInvertSelection,
                    enabled = filteredFiles.isNotEmpty() && !ui.isDownloading
                ) { Text("反选") }
                Button(
                    onClick = onClearSelection,
                    enabled = ui.selectedIndices.isNotEmpty() && !ui.isDownloading
                ) { Text("清空选择") }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("只看未下载")
                Switch(
                    checked = ui.onlyUndownloaded,
                    onCheckedChange = onToggleOnlyUndownloaded,
                    enabled = !ui.isDownloading
                )
            }

            Button(
                onClick = onDownloadSelected,
                enabled = selectableSelectedCount > 0 && !ui.isDownloading && !ui.isLoadingList
            ) { Text(if (ui.isDownloading) "下载中..." else "确认下载") }

            Button(onClick = onOpenDownloadDirectory) { Text("打开下载目录") }
            Text(text = "状态: ${ui.status}")
            Text(
                text = "文件数: ${ui.files.size}，搜索结果: ${filteredFiles.size}，已选(未下载): $selectableSelectedCount，已下载: ${ui.downloadedNames.size}"
            )

            FileList(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f, fill = true),
                files = filteredFiles,
                selectedIndices = ui.selectedIndices,
                downloadedNames = ui.downloadedNames,
                isDownloading = ui.isDownloading,
                onToggleSelection = onToggleSelection
            )
        }
    }
}

@Composable
private fun FileList(
    modifier: Modifier = Modifier,
    files: List<LanzouFile>,
    selectedIndices: Set<Int>,
    downloadedNames: Set<String>,
    isDownloading: Boolean,
    onToggleSelection: (Int) -> Unit
) {
    LazyColumn(
        modifier = modifier,
        verticalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        items(files, key = { it.index }) { f ->
            val checked = selectedIndices.contains(f.index)
            val downloaded = downloadedNames.contains(f.name)
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable(enabled = !isDownloading && !downloaded) { onToggleSelection(f.index) }
                    .padding(vertical = 4.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Checkbox(
                    checked = checked,
                    onCheckedChange = { onToggleSelection(f.index) },
                    enabled = !isDownloading && !downloaded
                )
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = if (downloaded) "${f.index}. ${f.name} [已下载]" else "${f.index}. ${f.name}",
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    Text(
                        text = "大小: ${f.size}  时间: ${f.time}",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }
    }
}
