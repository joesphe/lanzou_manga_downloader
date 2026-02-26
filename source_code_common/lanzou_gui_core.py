"""
蓝奏云下载器优化：获取真实下载链接后使用requests下载
界面布局优化版

通过DrissionPage获取真实下载链接，然后使用requests直接下载文件
"""

import os
import re
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox, filedialog

import requests

try:
    from source_code_common.lanzou_core import OptimizedLanzouDownloader
except Exception:
    from lanzou_core import OptimizedLanzouDownloader


RELEASES_PAGE_URL = "https://gitee.com/greovity/lanzou_manga_downloader/releases"
GITEE_LATEST_RELEASE_API = "https://gitee.com/api/v5/repos/greovity/lanzou_manga_downloader/releases/latest"
GITEE_RELEASES_API = "https://gitee.com/api/v5/repos/greovity/lanzou_manga_downloader/releases"
APP_VERSION_FALLBACK = "v6.2.0"
APP_VERSION_FILENAME = "app_version.txt"


def _normalize_version_text(raw):
    if not raw:
        return None
    text = str(raw).strip().lower()
    # 优先匹配带 v 前缀的版本，避免把 x64 误识别为版本号
    m = re.search(r"(?<![A-Za-z0-9])v\d+(?:[._-]\d+)*(?![A-Za-z0-9])", text, re.I)
    if m:
        token = m.group(0)
    elif re.fullmatch(r"\d+(?:[._-]\d+)*", text):
        token = text
    else:
        return None
    v = token.lower().replace("_", ".").replace("-", ".")
    if not v.startswith("v"):
        v = f"v{v}"
    return v


def _extract_version_candidates(text):
    if not text:
        return []
    s = str(text)
    out = []
    seen = set()

    # 优先提取 v1.2 / v1_2_3 这类明确语义版本
    for m in re.finditer(r"(?<![A-Za-z0-9])v\d+(?:[._-]\d+){1,3}(?![A-Za-z0-9])", s, re.I):
        n = _normalize_version_text(m.group(0))
        if n and n not in seen:
            seen.add(n)
            out.append(n)

    # 回退到 v7 这类主版本格式
    if not out:
        for m in re.finditer(r"(?<![A-Za-z0-9])v\d+(?![A-Za-z0-9])", s, re.I):
            n = _normalize_version_text(m.group(0))
            if n and n not in seen:
                seen.add(n)
                out.append(n)
    return out


def _version_key(version):
    normalized = _normalize_version_text(version)
    if not normalized:
        return ()
    body = normalized[1:]
    parts = []
    for p in body.split("."):
        if p.isdigit():
            parts.append(int(p))
        else:
            digits = re.findall(r"\d+", p)
            parts.append(int(digits[0]) if digits else 0)
    return tuple(parts)


def _is_version_less(current_version, latest_version):
    a = list(_version_key(current_version))
    b = list(_version_key(latest_version))
    if not a or not b:
        return False
    n = max(len(a), len(b))
    a.extend([0] * (n - len(a)))
    b.extend([0] * (n - len(b)))
    return tuple(a) < tuple(b)


def _detect_current_version():
    env_version = _normalize_version_text(os.environ.get("LANZOU_APP_VERSION"))
    if env_version:
        return env_version

    # 优先从版本文件读取，便于发版时仅修改文本文件
    try:
        candidates = []
        if getattr(sys, "frozen", False):
            candidates.append(os.path.join(os.path.dirname(sys.executable), APP_VERSION_FILENAME))
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        candidates.append(os.path.join(project_root, APP_VERSION_FILENAME))
        candidates.append(os.path.join(os.getcwd(), APP_VERSION_FILENAME))

        seen = set()
        for fp in candidates:
            if not fp or fp in seen:
                continue
            seen.add(fp)
            if not os.path.isfile(fp):
                continue
            with open(fp, "r", encoding="utf-8") as f:
                text = f.read().strip()
            parsed = _normalize_version_text(text)
            if parsed:
                return parsed
    except Exception:
        pass

    candidate_names = []
    try:
        if getattr(sys, "frozen", False):
            candidate_names.append(os.path.basename(sys.executable))
    except Exception:
        pass
    candidate_names.append(os.path.basename(__file__))

    for name in candidate_names:
        parsed = _normalize_version_text(name)
        if parsed:
            return parsed
    return APP_VERSION_FALLBACK


class _UpdateChecker:
    def _extract_version_from_release(self, release_obj):
        if not isinstance(release_obj, dict):
            return None
        candidates = []
        for key in ("tag_name", "name", "tag"):
            candidates.extend(_extract_version_candidates(release_obj.get(key)))

        assets = release_obj.get("assets")
        if isinstance(assets, list):
            for asset in assets:
                if not isinstance(asset, dict):
                    continue
                candidates.extend(_extract_version_candidates(asset.get("name")))
                candidates.extend(_extract_version_candidates(asset.get("browser_download_url")))

        if not candidates:
            return None
        best = candidates[0]
        for v in candidates[1:]:
            if _is_version_less(best, v):
                best = v
        return best

    def _extract_release_url(self, release_obj):
        if not isinstance(release_obj, dict):
            return RELEASES_PAGE_URL
        for key in ("html_url", "url"):
            val = release_obj.get(key)
            if isinstance(val, str) and val.startswith("http"):
                return val
        tag_name = release_obj.get("tag_name")
        if tag_name:
            return f"{RELEASES_PAGE_URL}/tag/{tag_name}"
        return RELEASES_PAGE_URL

    def fetch_latest_release(self, timeout=8):
        # 1) 首选官方 latest API
        try:
            resp = requests.get(GITEE_LATEST_RELEASE_API, timeout=timeout)
            resp.raise_for_status()
            obj = resp.json()
            ver = self._extract_version_from_release(obj)
            if ver:
                return ver, self._extract_release_url(obj)
        except Exception:
            pass

        # 2) 回退到 releases 列表 API，按语义版本取最大值
        try:
            resp = requests.get(f"{GITEE_RELEASES_API}?page=1&per_page=30", timeout=timeout)
            resp.raise_for_status()
            arr = resp.json()
            if isinstance(arr, list):
                best_ver = None
                best_url = RELEASES_PAGE_URL
                for item in arr:
                    ver = self._extract_version_from_release(item)
                    if not ver:
                        continue
                    if best_ver is None or _is_version_less(best_ver, ver):
                        best_ver = ver
                        best_url = self._extract_release_url(item)
                if best_ver:
                    return best_ver, best_url
        except Exception:
            pass

        # 3) 最后回退 HTML 页正则提取
        try:
            resp = requests.get(RELEASES_PAGE_URL, timeout=timeout)
            resp.raise_for_status()
            tags = re.findall(r"/releases/tag/(v?\d+(?:[._-]\d+)*)", resp.text, re.I)
            versions = [_normalize_version_text(t) for t in tags]
            versions = [v for v in versions if v]
            if versions:
                best_ver = versions[0]
                for v in versions[1:]:
                    if _is_version_less(best_ver, v):
                        best_ver = v
                return best_ver, f"{RELEASES_PAGE_URL}/tag/{best_ver}"
        except Exception:
            pass

        return None, RELEASES_PAGE_URL

# 以下是GUI部分的代码（优化布局并添加用户提示）
class LanzouDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.current_version = _detect_current_version()
        self.root.title(f"蓝奏云下载器 {self.current_version}")
        self.root.geometry("1200x800")
        
        # 初始化下载器实例
        self.downloader = OptimizedLanzouDownloader()
        # 记录自定义链接（未设置时为None）
        self.custom_url = None
        self.custom_password = None
        self.default_url = self.downloader.default_url
        self.default_password = self.downloader.default_password
        
        # 当前选中的文件列表
        self.selected_files = []
        self.is_loading = False
        self.stop_event = threading.Event()
        
        # 创建界面
        self.setup_gui()
        # 启动后自动检查更新（静默：仅发现新版本时提示）
        self.root.after(600, lambda: self.check_updates(silent_if_latest=True))
        # 启动后自动获取文件列表
        self.root.after(100, self.auto_refresh_files_on_start)
        
    def setup_gui(self):
        """设置图形用户界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置主窗口的权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=3)  # 文件列表区域占更大空间
        main_frame.rowconfigure(2, weight=1)  # 进度区域占较小空间
        
        # 创建控制框架
        control_frame = ttk.LabelFrame(main_frame, text="控制", padding="10")
        control_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        control_frame.columnconfigure(2, weight=1)
        
        # 添加使用说明标签
        instruction_label = ttk.Label(control_frame, 
                                     text="提示: 按住Ctrl键可多选文件，选择完成后点击'选择文件'按钮确认，然后点击'开始下载'",
                                     foreground="blue")
        instruction_label.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 6))

        loading_hint_label = ttk.Label(
            control_frame,
            text="提示: 文件列表加载过程中也可直接选择并下载已加载文件",
            foreground="blue"
        )
        loading_hint_label.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 6))

        # 右上角自定义链接按钮
        self.custom_link_btn = ttk.Button(
            control_frame,
            text="自定义蓝奏云链接",
            command=self.show_custom_link_dialog
        )
        self.custom_link_btn.grid(row=0, column=4, sticky=tk.E, pady=(0, 6))

        # 当前链接提示
        self.current_link_var = tk.StringVar(value="当前链接: 默认预设链接")
        current_link_label = ttk.Label(
            control_frame,
            textvariable=self.current_link_var,
            foreground="gray"
        )
        current_link_label.grid(row=1, column=3, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6))

        # 恢复默认链接按钮
        self.reset_link_btn = ttk.Button(
            control_frame,
            text="恢复默认链接",
            command=self.reset_to_default_link
        )
        self.reset_link_btn.grid(row=1, column=4, sticky=tk.E, pady=(0, 6))

        self.check_update_btn = ttk.Button(
            control_frame,
            text="检查更新",
            command=lambda: self.check_updates(silent_if_latest=False),
        )
        self.check_update_btn.grid(row=0, column=5, sticky=tk.E, pady=(0, 6))
        
        # 获取文件列表按钮
        self.refresh_btn = ttk.Button(control_frame, text="获取文件列表", command=self.manual_refresh_files)
        self.refresh_btn.grid(row=2, column=0, padx=(0, 10))

        # 停止加载按钮
        self.stop_load_btn = ttk.Button(control_frame, text="停止加载", command=self.stop_loading)
        self.stop_load_btn.grid(row=2, column=1, padx=(0, 10))
        
        # 选择下载目录按钮
        self.browse_btn = ttk.Button(control_frame, text="浏览...", command=self.browse_directory)
        self.browse_btn.grid(row=2, column=2, padx=(0, 10))
        
        # 下载目录输入框
        self.download_dir_var = tk.StringVar(value=os.path.join(os.getcwd(), "downloads"))
        self.download_dir_entry = ttk.Entry(control_frame, textvariable=self.download_dir_var, state="readonly")
        self.download_dir_entry.grid(row=2, column=3, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # 选择文件按钮
        self.select_files_btn = ttk.Button(control_frame, text="选择文件", command=self.select_files)
        self.select_files_btn.grid(row=2, column=4, padx=(0, 10))
        
        # 开始下载按钮
        self.download_btn = ttk.Button(control_frame, text="开始下载", command=self.start_download)
        self.download_btn.grid(row=2, column=5)
        
        # 创建文件列表框架
        files_frame = ttk.LabelFrame(main_frame, text="文件列表", padding="10")
        files_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview和滚动条
        columns = ("序号", "文件名", "大小", "时间")
        self.tree = ttk.Treeview(files_frame, columns=columns, show="headings", height=20)  # 增加高度
        
        # 设置列标题和宽度
        self.tree.heading("序号", text="序号")
        self.tree.heading("文件名", text="文件名")
        self.tree.heading("大小", text="大小")
        self.tree.heading("时间", text="时间")
        
        self.tree.column("序号", width=50, anchor=tk.CENTER)
        self.tree.column("文件名", width=500)
        self.tree.column("大小", width=100, anchor=tk.CENTER)
        self.tree.column("时间", width=100, anchor=tk.CENTER)
        
        # 创建垂直滚动条
        v_scrollbar = ttk.Scrollbar(files_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scrollbar.set)
        
        # 布局Treeview和滚动条
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 进度框架
        progress_frame = ttk.LabelFrame(main_frame, text="下载进度", padding="10")
        progress_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.rowconfigure(2, weight=1)  # 总体进度标签占更多空间
        
        # 当前文件进度
        current_progress_frame = ttk.Frame(progress_frame)
        current_progress_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        current_progress_frame.columnconfigure(1, weight=1)
        
        ttk.Label(current_progress_frame, text="当前文件:").grid(row=0, column=0, sticky=tk.W)
        self.current_file_var = tk.StringVar(value="无")
        self.current_file_label = ttk.Label(current_progress_frame, textvariable=self.current_file_var, wraplength=800)
        self.current_file_label.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 总体进度
        total_progress_frame = ttk.Frame(progress_frame)
        total_progress_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        total_progress_frame.columnconfigure(1, weight=1)
        
        ttk.Label(total_progress_frame, text="总体进度:").grid(row=0, column=0, sticky=tk.W)
        self.total_progress_var = tk.StringVar(value="0/0 (0%)")
        ttk.Label(total_progress_frame, textvariable=self.total_progress_var).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E))
    
    def browse_directory(self):
        """浏览并选择下载目录"""
        directory = filedialog.askdirectory(initialdir=self.download_dir_var.get())
        if directory:
            self.download_dir_var.set(directory)
    
    def manual_refresh_files(self):
        """手动刷新文件列表"""
        self.refresh_files()

    def auto_refresh_files_on_start(self):
        """启动后自动获取文件列表"""
        messagebox.showinfo(
            "提示",
            "默认获取神秘链接的资源。\n如需自定义，请点击右上角“自定义蓝奏云链接”按钮。"
        )
        self.refresh_files(show_popup=True)
    
    def refresh_files(self, show_popup=False):
        """刷新文件列表"""
        if self.is_loading:
            return
        self.is_loading = True
        self.stop_event.clear()
        self.status_var.set("正在获取文件列表...")
        self.root.update()

        # 在列表区域显示获取状态
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree.insert("", "end", values=("", "正在获取文件列表中...", "", ""))
        self.root.update()

        def _add_batch(batch):
            for item in self.tree.get_children():
                self.tree.delete(item)
            for file_info in batch:
                self.tree.insert("", "end", values=(
                    file_info["index"],
                    file_info["name"],
                    file_info["size"],
                    file_info["time"],
                ))

        def _append_batch(batch):
            for file_info in batch:
                self.tree.insert("", "end", values=(
                    file_info["index"],
                    file_info["name"],
                    file_info["size"],
                    file_info["time"],
                ))

        def _on_batch(batch):
            self.root.after(0, lambda b=batch: _append_batch(b))
            self.root.after(0, lambda: self.status_var.set(f"正在获取文件列表... 已加载 {len(self.downloader.files)} 个文件"))

        def _worker():
            try:
                self.root.after(0, _add_batch, [])
                if self.custom_url:
                    self.downloader.login_and_get_files(
                        url=self.custom_url,
                        password=self.custom_password,
                        on_batch=_on_batch,
                        stop_event=self.stop_event
                    )
                else:
                    self.downloader.login_and_get_files(on_batch=_on_batch, stop_event=self.stop_event)
                if self.stop_event.is_set():
                    self.root.after(0, lambda: self.status_var.set(f"已停止加载 - 已加载 {len(self.downloader.files)} 个文件"))
                else:
                    self.root.after(0, lambda: self.status_var.set(f"就绪 - 共 {len(self.downloader.files)} 个文件"))
                if show_popup:
                    self.root.after(0, lambda: messagebox.showinfo("提示", f"文件列表获取完成，共 {len(self.downloader.files)} 个文件"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"获取文件列表时出错: {str(e)}"))
                self.root.after(0, lambda: self.status_var.set("错误"))
            finally:
                self.root.after(0, lambda: setattr(self, "is_loading", False))

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def stop_loading(self):
        """手动停止加载文件列表"""
        if self.is_loading:
            self.stop_event.set()

    def show_custom_link_dialog(self):
        """弹出自定义链接输入框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("自定义蓝奏云链接")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding="12")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="链接:").grid(row=0, column=0, sticky=tk.W, pady=(0, 6))
        url_var = tk.StringVar(value=self.custom_url or "")
        url_entry = ttk.Entry(frame, textvariable=url_var, width=60)
        url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 6))

        ttk.Label(frame, text="密码(可留空):").grid(row=1, column=0, sticky=tk.W, pady=(0, 6))
        pwd_var = tk.StringVar(value=self.custom_password or "")
        pwd_entry = ttk.Entry(frame, textvariable=pwd_var, width=60)
        pwd_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 6))

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, sticky=tk.E)

        def _on_ok():
            url = url_var.get().strip()
            pwd = pwd_var.get().strip()
            if not url:
                messagebox.showwarning("提示", "请输入有效的蓝奏云链接")
                return
            # 仅在确认时切换预设链接
            self.custom_url = url
            self.custom_password = pwd
            self.downloader.default_url = url
            self.downloader.default_password = pwd
            self.current_link_var.set("当前链接: 自定义")
            dialog.destroy()
            self.refresh_files(show_popup=True)

        def _on_cancel():
            dialog.destroy()

        ok_btn = ttk.Button(btn_frame, text="确定", command=_on_ok)
        ok_btn.grid(row=0, column=0, padx=(0, 6))
        cancel_btn = ttk.Button(btn_frame, text="取消", command=_on_cancel)
        cancel_btn.grid(row=0, column=1)

        url_entry.focus_set()

    def reset_to_default_link(self):
        """恢复默认预设链接"""
        self.custom_url = None
        self.custom_password = None
        self.downloader.default_url = self.default_url
        self.downloader.default_password = self.default_password
        self.current_link_var.set("当前链接: 默认预设链接")
        self.refresh_files(show_popup=True)

    def check_updates(self, silent_if_latest=True):
        """检查是否有可用更新。"""
        def _worker():
            checker = _UpdateChecker()
            latest_version, release_url = checker.fetch_latest_release()

            def _notify():
                if not latest_version:
                    if not silent_if_latest:
                        messagebox.showwarning("检查更新", "无法获取最新版本信息，请稍后重试。")
                    return

                if _is_version_less(self.current_version, latest_version):
                    should_open = messagebox.askyesno(
                        "发现新版本",
                        f"当前版本: {self.current_version}\n最新版本: {latest_version}\n\n是否打开发布页？"
                    )
                    if should_open:
                        webbrowser.open(release_url or RELEASES_PAGE_URL)
                elif not silent_if_latest:
                    messagebox.showinfo("检查更新", f"当前已是最新版本（{self.current_version}）。")

            self.root.after(0, _notify)

        threading.Thread(target=_worker, daemon=True).start()
    
    def select_files(self):
        """选择要下载的文件"""
        # 获取所有选中的项目
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要下载的文件")
            return
        
        # 清空当前选中列表
        self.selected_files = []
        
        # 添加选中的文件到列表
        for item in selected_items:
            values = self.tree.item(item)["values"]
            file_info = {
                "index": values[0],
                "name": values[1],
                "size": values[2],
                "time": values[3],
            }
            # 从完整文件列表补齐隐藏字段（如 ajax_file_id）
            selected_index = str(values[0])
            matched = next(
                (f for f in self.downloader.files if str(f.get("index")) == selected_index),
                None
            )
            if matched:
                file_info["link"] = matched.get("link")
                if matched.get("ajax_file_id"):
                    file_info["ajax_file_id"] = matched.get("ajax_file_id")
            self.selected_files.append(file_info)
        
        # 更新当前文件标签显示选中的文件
        selected_names = [f["name"] for f in self.selected_files]
        if len(selected_names) <= 5:  # 如果选中文件不多，全部显示
            display_text = "已选中: " + ", ".join(selected_names)
        else:  # 如果选中文件太多，只显示前5个和总数
            display_text = f"已选中: {', '.join(selected_names[:5])} 等{len(selected_names)}个文件"
        
        self.current_file_var.set(display_text)
        messagebox.showinfo("提示", f"已选择 {len(self.selected_files)} 个文件，点击'开始下载'按钮开始下载")
    
    def start_download(self):
        """开始下载选中的文件"""
        if not self.selected_files:
            messagebox.showwarning("警告", "请先选择要下载的文件（点击'选择文件'按钮确认）")
            return
        
        download_dir = self.download_dir_var.get()
        if not download_dir:
            messagebox.showwarning("警告", "请选择下载目录")
            return
        
        # 创建下载线程
        thread = threading.Thread(target=self.download_files_thread, args=(download_dir,))
        thread.daemon = True
        thread.start()
    
    def download_files_thread(self, download_dir):
        """下载文件的线程函数"""
        try:
            self.root.after(0, lambda: self.status_var.set("正在下载..."))
            
            # 初始化浏览器（仅用于获取真实链接）
            self.downloader.setup_driver()
            
            # 设置进度回调
            self.downloader.set_progress_callback(self.update_progress)
            
            total_files = len(self.selected_files)
            completed_files = 0
            for i, file_info in enumerate(self.selected_files):
                # 更新总体进度
                self.root.after(0, lambda i=i, total=total_files:
                    self.total_progress_var.set(f"{i}/{total_files} ({int(i/total*100)}%)"))

                # 严格串行：当前文件实时提链并下载，不做预取
                success = self.downloader.download_single_file_optimized(
                    file_info,
                    download_dir,
                    prefetched_real_url=None
                )

                if success:
                    completed_files += 1

                # 更新总体进度
                self.root.after(0, lambda comp=completed_files, total=total_files:
                    self.total_progress_var.set(f"{comp}/{total_files} ({int(comp/total*100)}%)"))
            
            self.root.after(0, lambda: self.status_var.set(f"下载完成 - {completed_files}/{total_files} 个文件"))

            def _ask_open_download_dir():
                if completed_files <= 0:
                    return
                should_open = messagebox.askyesno(
                    "下载完成",
                    f"下载完成 - {completed_files}/{total_files} 个文件。\n是否打开下载目录？"
                )
                if should_open:
                    try:
                        os.startfile(download_dir)
                    except Exception as e:
                        messagebox.showerror("错误", f"打开下载目录失败: {str(e)}")

            self.root.after(0, _ask_open_download_dir)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"下载过程中出错: {str(e)}"))
            self.root.after(0, lambda: self.status_var.set("下载出错"))
        finally:
            # 关闭浏览器
            if self.downloader.driver:
                try:
                    self.downloader.driver.quit()
                except:
                    pass
    
    def update_progress(self, filename, downloaded_size, filepath, status, progress):
        """更新进度回调"""
        self.root.after(0, lambda: self.current_file_var.set(f"{filename} - {status}"))
        self.root.after(0, lambda: self.progress_var.set(progress))
    
    def on_closing(self):
        """关闭窗口时的处理"""
        # 关闭浏览器
        if self.downloader.driver:
            try:
                self.downloader.driver.quit()
            except:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = LanzouDownloaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
