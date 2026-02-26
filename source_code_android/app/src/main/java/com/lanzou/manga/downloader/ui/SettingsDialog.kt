package com.lanzou.manga.downloader.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import top.yukonga.miuix.kmp.basic.Button
import top.yukonga.miuix.kmp.basic.ButtonDefaults
import top.yukonga.miuix.kmp.basic.Card
import top.yukonga.miuix.kmp.basic.Text
import top.yukonga.miuix.kmp.extra.SuperSwitch
import top.yukonga.miuix.kmp.theme.MiuixTheme

@Composable
fun SettingsDialogContent(
    useThirdPartyLinks: Boolean,
    allowRedownloadAfterDownload: Boolean,
    isCheckingUpdate: Boolean,
    latestAndroidVersion: String?,
    hasUpdate: Boolean,
    version: String,
    onToggleUseThirdPartyLinks: (Boolean) -> Unit,
    onToggleAllowRedownload: (Boolean) -> Unit,
    onCheckUpdates: () -> Unit,
    onOpenReleasePage: () -> Unit
) {
    Column(
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // General Settings Section
        Card(
            modifier = Modifier.fillMaxWidth(),
            insideMargin = PaddingValues(16.dp)
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    text = "通用设置",
                    style = MiuixTheme.textStyles.title3,
                    color = MiuixTheme.colorScheme.primary
                )
                
                SuperSwitch(
                    title = "使用第三方链接",
                    summary = "允许使用自定义的第三方蓝奏云链接",
                    checked = useThirdPartyLinks,
                    onCheckedChange = onToggleUseThirdPartyLinks,
                    insideMargin = PaddingValues(0.dp)
                )
                
                SuperSwitch(
                    title = "下载后可重新下载",
                    summary = "下载完成后仍然允许重新下载该文件（重启应用后生效）",
                    checked = allowRedownloadAfterDownload,
                    onCheckedChange = onToggleAllowRedownload,
                    insideMargin = PaddingValues(0.dp)
                )
            }
        }
        
        // About Section
        Card(
            modifier = Modifier.fillMaxWidth(),
            insideMargin = PaddingValues(16.dp)
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    text = "关于",
                    style = MiuixTheme.textStyles.title3,
                    color = MiuixTheme.colorScheme.primary
                )
                
                Text(
                    text = "蓝奏云下载器",
                    style = MiuixTheme.textStyles.body1
                )
                
                Text(
                    text = "版本: $version",
                    style = MiuixTheme.textStyles.footnote1,
                    color = MiuixTheme.colorScheme.onSurfaceVariantSummary
                )

                Button(
                    modifier = Modifier.fillMaxWidth(),
                    onClick = onCheckUpdates,
                    colors = ButtonDefaults.buttonColors(),
                    enabled = !isCheckingUpdate
                ) {
                    Text(if (isCheckingUpdate) "检查中..." else "检查更新")
                }

                if (latestAndroidVersion != null) {
                    Text(
                        text = if (hasUpdate) {
                            "发现新版本: $latestAndroidVersion"
                        } else {
                            "最新版本: $latestAndroidVersion"
                        },
                        style = MiuixTheme.textStyles.footnote1,
                        color = MiuixTheme.colorScheme.onSurfaceVariantSummary
                    )
                }

                if (hasUpdate) {
                    Button(
                        modifier = Modifier.fillMaxWidth(),
                        onClick = onOpenReleasePage,
                        colors = ButtonDefaults.buttonColorsPrimary()
                    ) {
                        Text("打开发布页")
                    }
                }
            }
        }
    }
}
