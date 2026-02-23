"""开发版纯 requests 入口：禁用浏览器初始化与浏览器兜底下载链路。"""

import os
import sys
import tkinter as tk

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from source_code_common import lanzou_gui_core as base


class PureRequestsDownloader(base.OptimizedLanzouDownloader):
    def setup_driver(self):
        self.driver = None
        print("pure_requests模式：已禁用浏览器初始化")

    def _get_real_download_url_by_browser(self, file_link):
        print("pure_requests模式：浏览器兜底已禁用")
        return None


class PureRequestsGUI(base.LanzouDownloaderGUI):
    def __init__(self, root):
        super().__init__(root)
        url = os.environ.get("LANZOU_URL")
        pwd = os.environ.get("LANZOU_PASSWORD")
        if not url or not pwd:
            raise ValueError("开发版需要设置环境变量 LANZOU_URL 和 LANZOU_PASSWORD")
        self.downloader = PureRequestsDownloader(default_url=url, default_password=pwd)


def main():
    root = tk.Tk()
    PureRequestsGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
