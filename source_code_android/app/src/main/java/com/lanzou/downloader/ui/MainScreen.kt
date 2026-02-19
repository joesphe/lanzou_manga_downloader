package com.lanzou.downloader.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@Composable
fun MainScreen(viewModel: MainViewModel) {
    val context = LocalContext.current

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text("蓝奏云下载器 Android", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)

        OutlinedTextField(
            value = viewModel.shareUrl,
            onValueChange = { viewModel.shareUrl = it },
            label = { Text("分享链接") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        OutlinedTextField(
            value = viewModel.password,
            onValueChange = { viewModel.password = it },
            label = { Text("提取码") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = viewModel::fetchFiles, enabled = !viewModel.isLoading) { Text("获取列表") }
            Button(onClick = viewModel::selectAll, enabled = viewModel.files.isNotEmpty()) { Text("全选") }
            Button(onClick = viewModel::clearSelection, enabled = viewModel.selectedIds.isNotEmpty()) { Text("清空") }
            Button(onClick = { viewModel.downloadSelected(context) }, enabled = !viewModel.isLoading) { Text("下载已选") }
        }

        Text(viewModel.status)
        viewModel.currentProgress?.let {
            Text("${it.fileName}: ${it.percent}% (${it.status})")
        }

        Text("文件列表 (${viewModel.files.size})", fontWeight = FontWeight.Medium)
        LazyColumn(modifier = Modifier.weight(1f)) {
            items(viewModel.files, key = { it.id }) { file ->
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Checkbox(
                        checked = viewModel.selectedIds.contains(file.id),
                        onCheckedChange = { viewModel.toggleSelect(file.id) }
                    )
                    Column(modifier = Modifier.weight(1f)) {
                        Text(file.name)
                        Text("${file.size} | ${file.time}", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }

        Text("运行日志", fontWeight = FontWeight.Medium)
        LazyColumn(modifier = Modifier
            .fillMaxWidth()
            .height(140.dp)) {
            items(viewModel.logs) { line ->
                Text(line, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
