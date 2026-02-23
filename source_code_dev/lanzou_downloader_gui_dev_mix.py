"""开发版混合入口：使用环境变量凭证，requests 主链路 + 浏览器兜底。"""

import os
import sys
import tkinter as tk

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from source_code_common import lanzou_gui_core as base


def _build_dev_downloader(downloader_cls=base.OptimizedLanzouDownloader):
    url = os.environ.get("LANZOU_URL")
    pwd = os.environ.get("LANZOU_PASSWORD")
    if not url or not pwd:
        raise ValueError("开发版需要设置环境变量 LANZOU_URL 和 LANZOU_PASSWORD")
    return downloader_cls(default_url=url, default_password=pwd)


class DevMixGUI(base.LanzouDownloaderGUI):
    def __init__(self, root):
        super().__init__(root)
        self.downloader = _build_dev_downloader()


def main():
    root = tk.Tk()
    DevMixGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
