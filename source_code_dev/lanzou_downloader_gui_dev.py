import time
import os
import sys
import requests
import threading
import re
from DrissionPage import Chromium, ChromiumOptions, SessionOptions
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import base64
import hashlib
from urllib.parse import urlparse, parse_qs, urljoin


class _PrefetchManager:
    """后台预取真实下载链接。"""

    def __init__(self, downloader, max_queue_size=50):
        from queue import Queue
        self.downloader = downloader
        self.q = Queue(maxsize=max_queue_size)
        self.cache = {}  # file_index -> real_url
        self._stop = threading.Event()
        self._worker = None

    def start(self):
        if self._worker and self._worker.is_alive():
            return
        self._stop.clear()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def stop(self):
        self._stop.set()

    def enqueue(self, file_info):
        key = file_info.get("index")
        if key is None or key in self.cache:
            return
        try:
            self.q.put_nowait(file_info)
        except Exception:
            return

    def get_cached(self, file_index):
        return self.cache.get(file_index)

    def _run(self):
        from queue import Empty
        while not self._stop.is_set():
            try:
                f = self.q.get(timeout=0.2)
            except Empty:
                continue
            try:
                key = f.get("index")
                if key is None or key in self.cache:
                    continue
                real = self.downloader.get_real_download_url(f.get("link"))
                if real:
                    self.cache[key] = real
            except Exception:
                pass
            finally:
                try:
                    self.q.task_done()
                except Exception:
                    pass


class LanzouDownloader:
    def __init__(self, chrome_driver_path=None, edge_driver_path=None, headless=True, max_workers=3, browser="edge", 
                 browser_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", default_url=None, 
                 default_password=None):
        # 开发环境：从环境变量读取（不提供默认值，强制用户设置环境变量）
        if default_url is None or default_password is None:
            url_from_env = os.environ.get('LANZOU_URL')
            password_from_env = os.environ.get('LANZOU_PASSWORD')
            if not url_from_env or not password_from_env:
                raise ValueError("在开发环境中必须设置环境变量 LANZOU_URL 和 LANZOU_PASSWORD")
            self.default_url = url_from_env
            self.default_password = password_from_env
        else:
            self.default_url = default_url
            self.default_password = default_password
            
        self.chrome_driver_path = chrome_driver_path
        self.edge_driver_path = edge_driver_path
        self.headless = headless
        self.max_workers = max_workers
        self.browser = "edge"  # 固定使用Edge浏览器
        self.browser_path = browser_path  # 浏览器路径，默认为Edge
        self.files = []
        self.driver = None
        self.progress_callback = None  # 用于GUI回调的进度更新函数
        self.global_progress_callback = None  # 用于全局进度更新的回调函数
        self.browser_lock = threading.RLock()
        self.http = requests.Session()
        self.http.trust_env = False
        
    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def set_global_progress_callback(self, callback):
        """设置全局进度回调函数"""
        self.global_progress_callback = callback
        
    def setup_driver(self):
        """设置浏览器驱动"""
        co = ChromiumOptions(read_file=False)  # 不读取文件方式新建配置对象
        
        # 设置浏览器路径为Edge
        if self.browser_path:
            co.set_browser_path(self.browser_path)
        else:
            # 默认使用Edge浏览器路径
            possible_paths = [
                r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    co.set_browser_path(path)
                    break
        
        # 强制启用无头模式
        co = co.headless()
        
        # 设置窗口大小
        co.set_argument('--window-size=1920,1080')
        
        # 其他设置
        co.set_argument('--disable-gpu')
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-logging')
        co.set_argument('--disable-dev-shm-usage')
        co.set_argument('--silent')
        co.set_argument('--log-level=3')
        co.set_argument('--disable-extensions')
        co.set_argument('--disable-plugins')
        co.remove_argument('--enable-automation')
        
        # 为无头模式添加特殊的下载设置
        co.set_argument('--disable-web-security')
        co.set_argument('--allow-running-insecure-content')
        co.set_argument('--disable-features=VizDisplayCompositor')
        
        so = SessionOptions(read_file=False)
        
        self.driver = Chromium(addr_or_opts=co, session_options=so)
    
    def login_and_get_files(self, url=None, password=None):
        """登录并获取文件列表"""
        # 如果没有传入url和password，则使用默认值
        url = url or self.default_url
        password = password or self.default_password
        self.files = []

        def _extract_context(page_html, share_url):
            parsed = urlparse(share_url)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            q = parse_qs(parsed.query)
            fid = q.get("file", [None])[0]

            if not fid:
                m = re.search(r"/filemoreajax\.php\?file=(\d+)", page_html)
                fid = m.group(1) if m else None
            if not fid:
                m = re.search(r"'fid'\s*:\s*(\d+)", page_html)
                fid = m.group(1) if m else None

            uid_match = re.search(r"'uid'\s*:\s*'?(\d+)'?", page_html)
            uid = uid_match.group(1) if uid_match else None

            t_name_match = re.search(r"'t'\s*:\s*([A-Za-z_][A-Za-z0-9_]*)", page_html)
            k_name_match = re.search(r"'k'\s*:\s*([A-Za-z_][A-Za-z0-9_]*)", page_html)

            def _pick_var_value(var_name):
                if not var_name:
                    return None
                var_match = re.search(
                    rf"var\s+{re.escape(var_name)}\s*=\s*['\"]([^'\"]+)['\"]",
                    page_html
                )
                return var_match.group(1) if var_match else None

            t_val = _pick_var_value(t_name_match.group(1) if t_name_match else None)
            k_val = _pick_var_value(k_name_match.group(1) if k_name_match else None)

            if not t_val:
                m = re.search(r"'t'\s*:\s*'([^']+)'", page_html)
                t_val = m.group(1) if m else None
            if not k_val:
                m = re.search(r"'k'\s*:\s*'([^']+)'", page_html)
                k_val = m.group(1) if m else None

            missing = [k for k, v in {"fid": fid, "uid": uid, "t": t_val, "k": k_val}.items() if not v]
            if missing:
                raise Exception(f"页面参数提取失败，缺少: {', '.join(missing)}")

            return {"origin": origin, "fid": fid, "uid": uid, "t": t_val, "k": k_val}

        try:
            print(f"正在访问链接: {url}")
            session = requests.Session()
            session.trust_env = False
            common_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }

            resp = session.get(url, headers=common_headers, timeout=20)
            resp.raise_for_status()
            page_html = resp.text

            ctx = _extract_context(page_html, url)
            ajax_url = f"{ctx['origin']}/filemoreajax.php?file={ctx['fid']}"
            print(f"参数提取成功 fid={ctx['fid']} uid={ctx['uid']}")

            def _new_session():
                s = requests.Session()
                s.trust_env = False
                return s

            def _refresh_context(force_new_session=False):
                nonlocal session, ctx
                if force_new_session:
                    session = _new_session()
                refresh_resp = session.get(url, headers=common_headers, timeout=20)
                refresh_resp.raise_for_status()
                ctx = _extract_context(refresh_resp.text, url)

            def _post_page(pg, rep=0, ls=1, up=1):
                payload = {
                    "lx": 2,
                    "fid": ctx["fid"],
                    "uid": ctx["uid"],
                    "pg": pg,
                    "rep": rep,
                    "t": ctx["t"],
                    "k": ctx["k"],
                    "up": up,
                    "ls": ls,
                    "pwd": password,
                }
                ajax_headers = {
                    "User-Agent": common_headers["User-Agent"],
                    "Accept": "application/json, text/javascript, */*",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": url,
                    "Origin": ctx["origin"],
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                }
                page_resp = session.post(ajax_url, data=payload, headers=ajax_headers, timeout=20)
                page_resp.raise_for_status()
                data = page_resp.json()
                return data, str(data.get("zt", ""))

            def _fetch_page_with_retry(target_page, max_attempts=24, allow_warmup=True):
                last_data = None
                last_zt = ""
                payload_variants = [(0, 1, 1), (0, 0, 1), (0, 1, 0)]

                for attempt in range(1, max_attempts + 1):
                    if attempt == 1 or attempt % 3 == 0:
                        try:
                            _refresh_context(force_new_session=(attempt % 6 == 0))
                        except Exception:
                            pass

                    for rep, ls, up in payload_variants:
                        try:
                            data, zt = _post_page(target_page, rep=rep, ls=ls, up=up)
                            last_data, last_zt = data, zt
                        except Exception:
                            data, zt = None, ""
                            last_data, last_zt = None, ""

                        if zt == "1":
                            return data, zt
                        if zt == "3":
                            raise Exception(f"密码错误: {data.get('info', 'unknown') if data else 'unknown'}")

                    if allow_warmup and target_page > 1 and attempt % 5 == 0:
                        try:
                            _post_page(target_page - 1)
                        except Exception:
                            pass
                    time.sleep(min(2.5, 0.25 * attempt))

                return last_data, last_zt

            index = 1
            page = 1
            max_pages = 500
            seen_ids = set()

            while page <= max_pages:
                data, zt = _fetch_page_with_retry(page, max_attempts=24, allow_warmup=True)

                if zt != "1":
                    if page > 1:
                        try:
                            _refresh_context(force_new_session=True)
                            replay_ok = True
                            for back_page in range(1, page):
                                back_data, back_zt = _fetch_page_with_retry(back_page, max_attempts=8, allow_warmup=False)
                                if back_zt != "1":
                                    replay_ok = False
                                    break
                                if not (back_data.get("text") or []):
                                    break
                            if replay_ok:
                                data, zt = _fetch_page_with_retry(page, max_attempts=24, allow_warmup=True)
                        except Exception:
                            pass

                if zt != "1":
                    raise Exception(f"第 {page} 页请求失败，zt={zt}, info={data.get('info', '') if data else ''}")

                rows = data.get("text") or []
                if not rows:
                    break

                for row in rows:
                    file_id = str(row.get("id", "")).strip()
                    if not file_id or file_id == "-1":
                        continue
                    if file_id in seen_ids:
                        continue
                    seen_ids.add(file_id)

                    if str(row.get("t", "0")) == "1" and file_id.startswith("http"):
                        file_link = file_id
                    else:
                        file_link = urljoin(f"{ctx['origin']}/", file_id.lstrip("/"))

                    file_info = {
                        "index": index,
                        "name": row.get("name_all", ""),
                        "link": file_link,
                        "size": row.get("size", "未知大小"),
                        "time": row.get("time", "未知时间"),
                    }
                    self.files.append(file_info)
                    if index <= 50:
                        print(f"  {index:3d}. {file_info['name']} ({file_info['size']})")
                    index += 1

                if len(rows) < 50:
                    break
                page += 1

            print(f"直连获取完成，共 {len(self.files)} 个文件")

        except Exception as e:
            error_msg = f"获取文件列表时出错: {e}"
            print(error_msg)
            raise
            
    def sanitize_filename(self, filename):
        """清理文件名，移除非法字符"""
        # 移除或替换Windows不支持的字符
        illegal_chars = r'[<>:"/\\|?*\x00-\x1F]'
        sanitized = re.sub(illegal_chars, '_', filename)
        
        # 移除开头和结尾的空格和点
        sanitized = sanitized.strip('. ')
        
        # 确保文件名不为空
        if not sanitized:
            sanitized = "unnamed_file"
            
        return sanitized

    def is_download_url_valid(self, url, timeout=8):
        """轻量校验真实下载链接是否仍有效。"""
        if not url:
            return False

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "*/*",
        }

        try:
            with self.http.head(url, allow_redirects=True, timeout=timeout, headers=headers) as r:
                if r.status_code in (200, 206):
                    return "text/html" not in (r.headers.get("Content-Type") or "").lower()
                if r.status_code in (403, 404, 410):
                    return False
        except Exception:
            pass

        try:
            h2 = dict(headers)
            h2["Range"] = "bytes=0-0"
            with self.http.get(url, headers=h2, stream=True, allow_redirects=True, timeout=timeout) as r:
                if r.status_code in (206, 200):
                    return "text/html" not in (r.headers.get("Content-Type") or "").lower()
                if r.status_code in (403, 404, 410):
                    return False
        except Exception:
            return False
        return False
                
    def download_single_file(self, file_info, download_dir="downloads", max_retries=3):
        """使用浏览器直接下载单个文件"""
        try:
            print(f"开始处理文件: {file_info['name']}")
            
            # 清理文件名
            clean_filename = self.sanitize_filename(file_info['name'])
            
            # 确保下载目录存在
            os.makedirs(download_dir, exist_ok=True)
            
            # 检查文件是否已经存在，如果存在则跳过下载
            expected_file = os.path.join(download_dir, clean_filename)
            if os.path.exists(expected_file):
                if self.progress_callback:
                    self.progress_callback(clean_filename, os.path.getsize(expected_file), expected_file, "跳过(已存在)", 100)
                return True
            
            # 设置下载路径
            abs_download_path = os.path.abspath(download_dir)
            self.driver.set.download_path(abs_download_path)
            
            # 访问文件链接
            self.driver.latest_tab.get(file_info['link'])
            time.sleep(8)  # 等待页面加载
            
            # 查找下载按钮 - 优先查找"电信下载"、"联通下载"、"普通下载"等
            download_found = False
            
            # 尝试各种可能的下载按钮选择器
            download_selectors = [
                'xpath://a[contains(text(), "电信") or contains(text(), "联通") or contains(text(), "移动") or contains(text(), "普通") or contains(text(), "下载")]',
                'xpath://a[contains(@class, "down") or contains(@class, "download")]',
                'xpath://a[contains(@href, "developer-oss") and contains(@href, "toolsdown")]',
                'xpath://*[contains(@onclick, "down") or contains(@onclick, "download")]',
                'css:a[href*="developer-oss"]',  # 包含开发者OSS的链接
            ]
            
            for selector in download_selectors:
                if download_found:  # 如果已经下载成功，则跳出循环
                    break
                try:
                    elements = self.driver.latest_tab.eles(selector, timeout=5)
                    if elements:
                        for element in elements:
                            if download_found:  # 如果已经下载成功，则跳出循环
                                break
                            try:
                                # 检查元素是否可见且可点击
                                try:
                                    rect = element.rect
                                    width = rect.size['width']
                                    height = rect.size['height']
                                    if width > 0 and height > 0:
                                        if self.progress_callback:
                                            self.progress_callback(clean_filename, 0, expected_file, "开始下载...", 0)
                                        element.click(by_js=True)  # 使用JavaScript点击
                                        # 标记已经开始下载，避免重复点击
                                        download_found = True
                                        
                                        # 等待下载完成并显示进度
                                        success = self.monitor_download_progress(expected_file, clean_filename)
                                        if success:
                                            if self.progress_callback:
                                                self.progress_callback(clean_filename, os.path.getsize(expected_file), expected_file, "下载完成", 100)
                                        break  # 点击后立即跳出，不再尝试同类型下载
                                    else:
                                        # 元素尺寸为0，跳过
                                        pass
                                except:
                                    # 如果无法获取元素尺寸，仍然尝试点击（兼容旧版本或特殊元素）
                                    if self.progress_callback:
                                        self.progress_callback(clean_filename, 0, expected_file, "开始下载...", 0)
                                    element.click(by_js=True)  # 使用JavaScript点击
                                    # 标记已经开始下载，避免重复点击
                                    download_found = True
                                    
                                    # 等待下载完成并显示进度
                                    success = self.monitor_download_progress(expected_file, clean_filename)
                                    if success:
                                        if self.progress_callback:
                                            self.progress_callback(clean_filename, os.path.getsize(expected_file), expected_file, "下载完成", 100)
                                    break  # 点击后立即跳出，不再尝试同类型下载
                            except Exception as e:
                                continue
                    if download_found:
                        break
                except Exception as e:
                    continue
            
            # 如果仍没有找到下载链接，尝试直接下载
            if not download_found:
                # 查找所有包含实际下载链接的元素
                all_links = self.driver.latest_tab.eles('tag:a')
                for link in all_links:
                    if download_found:  # 如果已经下载成功，则跳出循环
                        break
                    try:
                        href = link.attr('href')
                        if href and ('developer-oss.lanrar.com' in href and 'toolsdown' in href):
                            # 直接下载文件 - 使用更可靠的方法
                            try:
                                # 先记录下载前的文件列表
                                initial_files = set(os.listdir(download_dir))
                                
                                # 使用Tab的download方法，只提供URL，不指定路径
                                download_id = self.driver.latest_tab.download(href)
                                
                                # 标记已经开始下载，避免重复下载
                                download_found = True
                                
                                # 等待下载完成并显示进度
                                success = self.monitor_download_progress(expected_file, clean_filename)
                                if success:
                                    if self.progress_callback:
                                        self.progress_callback(clean_filename, os.path.getsize(expected_file), expected_file, "下载完成", 100)
                                break  # 下载请求发出后立即跳出，不再尝试其他链接
                            except Exception as e:
                                print(f"直接下载失败: {e}")
                                continue
                    except Exception as e:
                        print(f"处理链接时出错: {e}")
                        continue
            
            # 如果以上方法都失败，尝试等待并检查下载状态
            if not download_found:
                print(f"警告: 未能找到 {file_info['name']} 的下载链接")
                return False
            
            return download_found
            
        except Exception as e:
            error_msg = f"下载文件 {file_info['name']} 时出错: {e}"
            print(error_msg)
            return False
    
    def monitor_download_progress(self, expected_file, filename, timeout=60):
        """监控下载进度"""
        start_time = time.time()
        initial_size = 0
        if os.path.exists(expected_file):
            initial_size = os.path.getsize(expected_file)
        
        while time.time() - start_time < timeout:
            if os.path.exists(expected_file):
                current_size = os.path.getsize(expected_file)
                if current_size > initial_size:
                    # 文件在增长，说明下载进行中
                    if self.progress_callback:
                        self.progress_callback(filename, current_size, expected_file, "下载中...", min(95, int((current_size-initial_size)*100/(initial_size+current_size+1))))
                    initial_size = current_size
                elif os.path.getsize(expected_file) > 0:
                    # 文件存在且有内容，可能已下载完成
                    if self.progress_callback:
                        self.progress_callback(filename, os.path.getsize(expected_file), expected_file, "下载完成", 100)
                    return True
            time.sleep(1)
        
        # 超时后再次检查文件是否已存在且有内容
        if os.path.exists(expected_file) and os.path.getsize(expected_file) > 0:
            if self.progress_callback:
                self.progress_callback(filename, os.path.getsize(expected_file), expected_file, "下载完成", 100)
            return True
        
        return False
    
    def get_real_download_url(self, file_link):
        """使用DrissionPage获取真实下载链接。"""
        if not file_link or not self.driver:
            return None

        with self.browser_lock:
            tab = None
            try:
                print(f"正在获取文件的真实下载链接: {file_link}")
                tab = self.driver.new_tab()
                tab.get(file_link)
                time.sleep(3)

                selectors = [
                    'xpath://a[contains(@href, "developer-oss") and contains(@href, "toolsdown")]',
                    'xpath://a[contains(@href, "lanzoug.com") and contains(@href, "file")]',
                    'xpath://a[contains(@href, "lanzou")]',
                    'xpath://a[contains(@onclick, "down") or contains(@onclick, "download")]',
                    'css:a[href*="developer-oss"]',
                    'css:a[href*="lanzoug.com"]'
                ]

                for selector in selectors:
                    try:
                        elements = tab.eles(selector, timeout=3)
                        if not elements:
                            continue
                        for element in elements:
                            href = element.attr('href')
                            if href and ('developer-oss' in href or 'lanzoug.com' in href or 'downserver' in href):
                                print(f"找到真实下载链接: {href}")
                                return href
                    except Exception:
                        continue

                page_source = tab.html or ""
                patterns = [
                    r'https?://[^\s"<>\']*(?:developer-oss|lanzoug\.com|downserver)[^\s"<>\']*',
                    r'https?://[^\s"<>\']*toolsdown[^\s"<>\']*',
                    r'https?://[^\s"<>\']*\.lanzou[^\s"<>\']*'
                ]
                for pattern in patterns:
                    matches = re.findall(pattern, page_source)
                    if not matches:
                        continue
                    for match in matches:
                        if 'developer-oss' in match or 'toolsdown' in match or 'lanzoug.com' in match:
                            print(f"从页面源码中找到真实下载链接: {match}")
                            return match

                print("警告: 未能找到真实下载链接")
                return None
            except Exception as e:
                print(f"获取真实下载链接时出错: {e}")
                return None
            finally:
                try:
                    if tab:
                        tab.close()
                except Exception:
                    pass

    def download_with_requests(self, url, file_path, file_name):
        """
        使用requests下载文件并显示进度
        """
        try:
            # 检查文件是否已经存在
            if os.path.exists(file_path):
                if self.progress_callback:
                    self.progress_callback(file_name, os.path.getsize(file_path), file_path, "跳过(已存在)", 100)
                return True
            
            print(f"开始使用requests下载: {file_name}")
            
            # 设置请求头，模拟浏览器
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # 发起请求，流式下载
            response = self.http.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # 获取文件总大小
            total_size = int(response.headers.get('content-length', 0))
            
            # 创建目录
            os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
            
            # 开始下载
            downloaded_size = 0
            with response:
                with open(file_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)
                            downloaded_size += len(chunk)

                            # 更新进度
                            if total_size > 0:
                                progress = int((downloaded_size / total_size) * 100)
                                if self.progress_callback:
                                    self.progress_callback(file_name, downloaded_size, file_path, "下载中...", progress)
            
            # 下载完成
            if self.progress_callback:
                self.progress_callback(file_name, downloaded_size, file_path, "下载完成", 100)
                
            print(f"文件下载完成: {file_name}")
            return True
            
        except Exception as e:
            print(f"使用requests下载文件 {file_name} 时出错: {e}")
            # 如果下载失败，删除可能的部分下载文件
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            return False

    def download_single_file_optimized(self, file_info, download_dir="downloads", prefetched_real_url=None):
        """
        优化的下载方法：先获取真实下载链接，再用requests下载
        """
        try:
            print(f"开始优化下载流程: {file_info['name']}")
            
            # 清理文件名
            clean_filename = self.sanitize_filename(file_info['name'])
            file_path = os.path.join(download_dir, clean_filename)
            
            # 首先尝试预取结果，再回退到实时获取
            real_url = prefetched_real_url
            if not real_url or not self.is_download_url_valid(real_url):
                real_url = self.get_real_download_url(file_info['link'])

            if not real_url:
                print(f"未能获取到 {file_info['name']} 的真实下载链接，跳过该文件")
                return False

            # 轻校验失败不立即返回，先尝试直接下载，避免误杀可用链接
            if not self.is_download_url_valid(real_url):
                print(f"真实链接校验未通过，先尝试直接下载: {file_info['name']}")
            
            # 使用requests下载真实链接
            success = self.download_with_requests(real_url, file_path, clean_filename)
            if not success:
                print(f"requests下载失败，跳过该文件: {file_info['name']}")
            return success
            
        except Exception as e:
            print(f"优化下载文件 {file_info['name']} 时出错: {e}")
            return False

    def download_single_file_legacy(self, file_info, download_dir="downloads", max_retries=3):
        """
        原始浏览器下载兜底（已禁用）
        """
        print(f"浏览器下载兜底已禁用，跳过该文件: {file_info['name']}")
        return False

    def download_multiple_files(self, selected_indices, download_dir="downloads", max_workers=None, prefetch_ahead=3):
        """批量下载文件（滚动预取真实链接）。"""
        selected_files = [f for f in self.files if f['index'] in selected_indices]
        
        if not selected_files:
            print("没有选择任何文件")
            return []
        
        if prefetch_ahead is None or prefetch_ahead < 0:
            prefetch_ahead = 0

        print(f"准备下载 {len(selected_files)} 个文件（滚动预取 ahead={prefetch_ahead}）")

        prefetch = _PrefetchManager(self, max_queue_size=50)
        prefetch.start()

        results = []
        total_files = len(selected_files)

        def _enqueue_window(current_index: int):
            if prefetch_ahead <= 0:
                return
            start_i = current_index + 1
            end_i = min(total_files, current_index + 1 + prefetch_ahead)
            for j in range(start_i, end_i):
                prefetch.enqueue(selected_files[j])

        try:
            for i, file_info in enumerate(selected_files):
                print(f"正在下载第 {i+1}/{total_files} 个文件: {file_info['name']}")

                if i == 0:
                    _enqueue_window(current_index=0)
                    cached_real_url = None
                else:
                    cached_real_url = prefetch.get_cached(file_info["index"])

                success = self.download_single_file_optimized(
                    file_info,
                    download_dir,
                    prefetched_real_url=cached_real_url
                )
                results.append((file_info['name'], success))

                _enqueue_window(current_index=i)

                if self.global_progress_callback:
                    progress = int(((i + 1) / total_files) * 100)
                    self.global_progress_callback(f"正在下载: {file_info['name']}", progress)
        finally:
            prefetch.stop()
        
        return results


class LanzouDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("蓝奏云下载器 - 开发版")
        self.root.geometry("1200x800")

        # 初始化下载器实例
        self.downloader = LanzouDownloader()

        # 当前选中的文件列表
        self.selected_files = []

        # 创建界面
        self.setup_gui()
    
    def setup_gui(self):
        """设置图形用户界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置主窗口的权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=3)
        main_frame.rowconfigure(2, weight=1)

        # 创建控制框架
        control_frame = ttk.LabelFrame(main_frame, text="控制", padding="10")
        control_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        control_frame.columnconfigure(2, weight=1)

        # 添加使用说明标签
        instruction_label = ttk.Label(
            control_frame,
            text="提示: 按住Ctrl键可多选文件，选择完成后点击'选择文件'按钮确认，然后点击'开始下载'",
            foreground="blue"
        )
        instruction_label.grid(row=0, column=0, columnspan=5, sticky=(tk.W, tk.E), pady=(0, 10))

        # 获取文件列表按钮
        self.refresh_btn = ttk.Button(control_frame, text="获取文件列表", command=self.manual_refresh_files)
        self.refresh_btn.grid(row=1, column=0, padx=(0, 10))

        # 选择下载目录按钮
        self.browse_btn = ttk.Button(control_frame, text="浏览...", command=self.browse_directory)
        self.browse_btn.grid(row=1, column=1, padx=(0, 10))

        # 下载目录输入框
        self.download_dir_var = tk.StringVar(value=os.path.join(os.getcwd(), "downloads"))
        self.download_dir_entry = ttk.Entry(control_frame, textvariable=self.download_dir_var, state="readonly")
        self.download_dir_entry.grid(row=1, column=2, sticky=(tk.W, tk.E), padx=(0, 10))

        # 选择文件按钮
        self.select_files_btn = ttk.Button(control_frame, text="选择文件", command=self.select_files)
        self.select_files_btn.grid(row=1, column=3, padx=(0, 10))

        # 开始下载按钮
        self.download_btn = ttk.Button(control_frame, text="开始下载", command=self.start_download)
        self.download_btn.grid(row=1, column=4)

        # 创建文件列表框架
        files_frame = ttk.LabelFrame(main_frame, text="文件列表", padding="10")
        files_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(0, weight=1)

        # 创建Treeview和滚动条
        columns = ("序号", "文件名", "大小", "时间", "链接")
        self.tree = ttk.Treeview(files_frame, columns=columns, show="headings", height=20)

        # 设置列标题和宽度
        self.tree.heading("序号", text="序号")
        self.tree.heading("文件名", text="文件名")
        self.tree.heading("大小", text="大小")
        self.tree.heading("时间", text="时间")
        self.tree.heading("链接", text="链接")

        self.tree.column("序号", width=50, anchor=tk.CENTER)
        self.tree.column("文件名", width=500)
        self.tree.column("大小", width=100, anchor=tk.CENTER)
        self.tree.column("时间", width=100, anchor=tk.CENTER)
        self.tree.column("链接", width=200)

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
        progress_frame.rowconfigure(2, weight=1)

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

    def refresh_files(self):
        """刷新文件列表"""
        try:
            self.status_var.set("正在获取文件列表...")
            self.root.update()

            self.downloader.login_and_get_files()

            for item in self.tree.get_children():
                self.tree.delete(item)

            for file_info in self.downloader.files:
                self.tree.insert("", "end", values=(
                    file_info["index"],
                    file_info["name"],
                    file_info["size"],
                    file_info["time"],
                    file_info["link"]
                ))

            self.status_var.set(f"就绪 - 共 {len(self.downloader.files)} 个文件")

        except Exception as e:
            messagebox.showerror("错误", f"获取文件列表时出错: {str(e)}")
            self.status_var.set("错误")

    def select_files(self):
        """选择要下载的文件"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要下载的文件")
            return

        self.selected_files = []
        for item in selected_items:
            values = self.tree.item(item)["values"]
            file_info = {
                "index": values[0],
                "name": values[1],
                "size": values[2],
                "time": values[3],
                "link": values[4]
            }
            self.selected_files.append(file_info)

        selected_names = [f["name"] for f in self.selected_files]
        if len(selected_names) <= 5:
            display_text = "已选中: " + ", ".join(selected_names)
        else:
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

        thread = threading.Thread(target=self.download_files_thread, args=(download_dir,))
        thread.daemon = True
        thread.start()

    def download_files_thread(self, download_dir):
        """下载文件的线程函数"""
        try:
            self.root.after(0, lambda: self.status_var.set("正在下载..."))

            # 初始化浏览器（仅用于获取真实链接）
            self.downloader.setup_driver()

            self.downloader.set_progress_callback(self.update_progress)

            total_files = len(self.selected_files)
            completed_files = 0

            prefetch_ahead = 3
            prefetch = _PrefetchManager(self.downloader, max_queue_size=50)
            prefetch.start()

            def _enqueue_window(current_index: int):
                if prefetch_ahead <= 0:
                    return
                start_i = current_index + 1
                end_i = min(total_files, current_index + 1 + prefetch_ahead)
                for j in range(start_i, end_i):
                    prefetch.enqueue(self.selected_files[j])

            try:
                for i, file_info in enumerate(self.selected_files):
                    self.root.after(
                        0,
                        lambda i=i, total=total_files: self.total_progress_var.set(
                            f"{i}/{total_files} ({int(i/total*100)}%)"
                        )
                    )

                    if i == 0:
                        _enqueue_window(current_index=0)
                        cached_real_url = None
                    else:
                        cached_real_url = prefetch.get_cached(file_info["index"])

                    success = self.downloader.download_single_file_optimized(
                        file_info,
                        download_dir,
                        prefetched_real_url=cached_real_url
                    )

                    if success:
                        completed_files += 1

                    _enqueue_window(current_index=i)

                    self.root.after(
                        0,
                        lambda comp=completed_files, total=total_files: self.total_progress_var.set(
                            f"{comp}/{total_files} ({int(comp/total*100)}%)"
                        )
                    )
            finally:
                prefetch.stop()

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
            if self.downloader.driver:
                try:
                    self.downloader.driver.quit()
                except Exception:
                    pass

    def update_progress(self, filename, downloaded_size, filepath, status, progress):
        """更新进度回调"""
        self.root.after(0, lambda: self.current_file_var.set(f"{filename} - {status}"))
        self.root.after(0, lambda: self.progress_var.set(progress))

    def on_closing(self):
        """关闭窗口时的处理"""
        if self.downloader.driver:
            try:
                self.downloader.driver.quit()
            except Exception:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = LanzouDownloaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
