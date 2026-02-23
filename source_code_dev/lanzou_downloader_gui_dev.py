"""开发版默认入口（混合模式，依赖环境变量凭证）。"""

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from source_code_dev.lanzou_downloader_gui_dev_mix import main


if __name__ == "__main__":
    main()
