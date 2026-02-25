from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class FileItem:
    """统一的文件元数据结构（便于迁移到安卓端）。"""
    index: int
    name: str
    link: str
    size: str
    time: str
    ajax_file_id: Optional[str] = None

    def to_dict(self):
        return {
            "index": self.index,
            "name": self.name,
            "link": self.link,
            "size": self.size,
            "time": self.time,
            "ajax_file_id": self.ajax_file_id,
        }


@dataclass
class ListFetchConfig:
    """列表获取的节奏与策略配置。"""
    page_interval_s: Tuple[float, float] = (1.0, 2.0)  # 模拟“点更多”
    zt4_wait_s: Tuple[float, float] = (1.0, 2.0)
    max_pages: int = 500
    page_size: int = 50
    ctx_refresh_cooldown_s: float = 3.0
