package com.lanzou.manga.downloader.ui

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performTouchInput
import androidx.compose.ui.test.swipeUp
import com.lanzou.manga.downloader.MainActivity
import org.junit.Rule
import org.junit.Test

class MainScreenUiTest {

    @get:Rule
    val composeRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun title_and_confirm_button_should_be_visible_and_scroll_stable() {
        composeRule.onNodeWithText("蓝奏云下载器").assertIsDisplayed()
        composeRule.onNodeWithText("确认下载 (0)").assertIsDisplayed()

        repeat(8) {
            composeRule.onRoot().performTouchInput { swipeUp() }
        }

        composeRule.onNodeWithText("蓝奏云下载器").assertIsDisplayed()
    }
}
