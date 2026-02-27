"""
蓝奏云下载器优化：获取真实下载链接后使用requests下载
界面布局优化版

通过DrissionPage获取真实下载链接，然后使用requests直接下载文件
"""

import time
import random
import os
import sys
import requests
import threading
import re
import json
import hmac
try:
    from DrissionPage import Chromium, ChromiumOptions, SessionOptions
except Exception:
    Chromium = None
    ChromiumOptions = None
    SessionOptions = None
import base64
import hashlib
import html
from urllib.parse import urlparse, parse_qs, urljoin
try:
    from source_code_common.lanzou_types import FileItem, ListFetchConfig
    from source_code_common.lanzou_list_fetcher import LanzouListFetcher
    from source_code_common.lanzou_download_core import LanzouDownloadCore
except Exception:
    from lanzou_types import FileItem, ListFetchConfig
    from lanzou_list_fetcher import LanzouListFetcher
    from lanzou_download_core import LanzouDownloadCore


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
                real = self.downloader._get_real_download_url_impl(f.get("link"))
                if real:
                    self.cache[key] = real
            except Exception:
                pass
            finally:
                try:
                    self.q.task_done()
                except Exception:
                    pass


class OptimizedLanzouDownloader:
    def __init__(self, chrome_driver_path=None, edge_driver_path=None, headless=True, max_workers=3, browser="edge", 
                 browser_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", default_url=None, 
                 default_password=None):
        # 生产环境：使用混淆解密（无论是否打包）
        if default_url is None or default_password is None:
            self.default_url, self.default_password = self._get_obfuscated_credentials()
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
        self.file_items = []
        self.driver = None
        self.progress_callback = None  # 用于GUI回调的进度更新函数
        self.global_progress_callback = None  # 用于全局进度更新的回调函数
        # 串行化浏览器访问，避免多处调用时互相干扰
        self.browser_lock = threading.RLock()
        # 复用HTTP会话，减少频繁建连
        self.http = requests.Session()
        self.http.trust_env = False
        # 直链校验自适应策略：记录域名的“校验误杀”情况，必要时跳过预校验
        self.validation_policy = {}  # host -> {"false_negative": int, "skip_validation": bool}
        self.list_config = ListFetchConfig()
        self.list_fetcher = LanzouListFetcher(self)
        self.download_core = LanzouDownloadCore(self)

    def _sleep_range(self, seconds_range):
        low, high = seconds_range
        if high <= low:
            time.sleep(max(0.0, low))
            return
        time.sleep(low + (high - low) * random.random())

    def _make_common_headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        
    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def set_global_progress_callback(self, callback):
        """设置全局进度回调函数"""
        self.global_progress_callback = callback

    def _mask_url(self, raw):
        if not raw:
            return "<empty>"
        try:
            secret = b"lanzou_log_mask_v1"
            digest = hmac.new(secret, raw.encode("utf-8"), hashlib.sha256).hexdigest()[:12]
            return f"<url_hash:{digest}>"
        except Exception:
            pass
        return "<masked>"
        
    def setup_driver(self):
        """设置浏览器驱动"""
        if Chromium is None or ChromiumOptions is None or SessionOptions is None:
            raise RuntimeError("未安装DrissionPage，无法启用浏览器兜底。")
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
    
    def _get_obfuscated_credentials(self):
        """使用AES-GCM + 分片密钥重组获取凭证。"""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key_part1 = bytes([
            0xF8, 0xD5, 0x0B, 0x48, 0x0D, 0xC7, 0xE4, 0x41, 0x47, 0xE1, 0x98, 0xDE
        ])
        key_part2 = bytes([
            0xD3, 0x36, 0x12, 0x29, 0x45, 0x02, 0x25, 0x51, 0xBC, 0x8E
        ])
        key_part3 = bytes([
            0xFF, 0x57, 0x52, 0x0B, 0x17, 0x0D, 0xE7, 0xC0, 0x3D, 0xEB, 0x76, 0x2B,
            0x55, 0xF2, 0xAD, 0xF8, 0x15, 0xF6, 0x4E, 0xDF, 0x4E, 0xA9, 0x65, 0xC8,
            0x01, 0x63, 0xED, 0xCB, 0x75, 0xE5, 0x65, 0x56
        ])
        encrypted_blob_b64 = (
            "xrOk8r07sRpstrBGB+httG44WDGEHTTt1Ty7XKrzmL17SQRWjX7RYfJ+A/Oh2H76"
            "TAUbQ0B2OXLXyzyIrPzVOsGXthHBRG3aQGd4EMalWX2eFs0="
        )

        key = bytearray(len(key_part3))
        for i in range(len(key_part3)):
            mixer = key_part1[i % len(key_part1)] if i < len(key_part1) else key_part2[i % len(key_part2)]
            key[i] = key_part3[i] ^ mixer

        blob = base64.b64decode(encrypted_blob_b64)
        nonce, ciphertext = blob[:12], blob[12:]
        payload = AESGCM(bytes(key)).decrypt(nonce, ciphertext, b"lanzou-v2")
        data = json.loads(payload.decode("utf-8"))
        return data["u"], data["p"]
    
    def _get_real_download_url_by_browser(self, file_link):
        """浏览器路径（临时兜底）。"""
        if not file_link or not self.driver:
            print("浏览器兜底不可用：driver未初始化或file_link为空")
            return None

        with self.browser_lock:
            tab = None
            try:
                print("进入浏览器兜底提链流程")
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
                                print(f"浏览器兜底提链成功: {self._mask_url(href)}")
                                return href
                    except Exception:
                        continue
                print("浏览器兜底提链失败：未匹配到下载链接")
                return None
            except Exception as e:
                print(f"浏览器兜底提链异常: {e}")
                return None
            finally:
                try:
                    if tab:
                        tab.close()
                except Exception:
                    pass

    def _extract_ajax_file_id_from_js_text(self, text):
        """从一段JS文本中提取 ajaxm.php 的 file 参数。"""
        if not text:
            return None

        def _ok(v):
            s = str(v).strip()
            return s if s.isdigit() and s != "1" and len(s) >= 6 else None

        direct_patterns = [
            r"url\s*:\s*['\"]/ajaxm\.php\?file=(\d{6,})['\"]",
            r"/ajaxm\.php\?file=(\d{6,})",
            r"\bfile\s*[:=]\s*['\"]?(\d{6,})['\"]?",
            r"\bfid\s*[:=]\s*['\"]?(\d{6,})['\"]?",
        ]
        for p in direct_patterns:
            m = re.search(p, text)
            if m:
                v = _ok(m.group(1))
                if v:
                    return v

        # 处理 url:'/ajaxm.php?file=' + someVar 这类拼接
        m_var = re.search(r"/ajaxm\.php\?file=['\"]\s*\+\s*([A-Za-z_][A-Za-z0-9_]*)", text)
        if m_var:
            var_name = m_var.group(1)
            m_val = re.search(
                rf"\b(?:var\s+)?{re.escape(var_name)}\s*=\s*['\"]?(\d{{6,}})['\"]?",
                text
            )
            if m_val:
                v = _ok(m_val.group(1))
                if v:
                    return v

        return None

    def _extract_ajax_file_id_from_fn_assets(self, fn_html, origin, fn_url, headers):
        """从 fn 页内联脚本与外链JS中提取 file_id。"""
        # 1) 先扫内联 script
        inline_scripts = re.findall(r"<script[^>]*>([\s\S]*?)</script>", fn_html, re.I)
        for js in inline_scripts:
            fid = self._extract_ajax_file_id_from_js_text(js)
            if fid:
                print(f"从fn内联脚本提取file_id: {fid}")
                return fid

        # 2) 再扫外链 script src
        script_srcs = re.findall(r"<script[^>]+src=['\"]([^'\"]+)['\"]", fn_html, re.I)
        seen = set()
        for src in script_srcs[:12]:
            full = urljoin(origin + "/", html.unescape(src).strip())
            if not full or full in seen:
                continue
            seen.add(full)
            try:
                h = dict(headers)
                h["Referer"] = fn_url
                r = self.http.get(full, headers=h, timeout=12)
                if r.status_code != 200:
                    continue
                fid = self._extract_ajax_file_id_from_js_text(r.text)
                if fid:
                    print(f"从fn外链脚本提取file_id: {fid}")
                    return fid
            except Exception:
                continue
        return None

    def _extract_ajax_params_from_js_text(self, text):
        """从JS文本中提取 downprocess 参数。"""
        if not text:
            return {}

        out = {}

        # file_id
        fid = self._extract_ajax_file_id_from_js_text(text)
        if fid:
            out["file_id"] = fid

        # websignkey / signs / ajaxdata
        for p in [
            r"var\s+ajaxdata\s*=\s*['\"]([^'\"]+)['\"]",
            r"websignkey\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r"signs\s*[:=]\s*['\"]([^'\"]+)['\"]",
        ]:
            m = re.search(p, text, re.I)
            if m:
                out["ajaxdata"] = html.unescape(m.group(1)).strip()
                break

        # wp_sign / sign
        for p in [
            r"var\s+wp_sign\s*=\s*['\"]([^'\"]+)['\"]",
            r"\bsign\s*[:=]\s*['\"]([^'\"]+)['\"]",
        ]:
            m = re.search(p, text, re.I)
            if m:
                out["wp_sign"] = html.unescape(m.group(1)).strip()
                break

        # websign（部分站点要求固定值，如 "2"）
        for p in [
            r"var\s+websign\s*=\s*['\"]([^'\"]*)['\"]",
            r"['\"]websign['\"]\s*[:=]\s*['\"]([^'\"]*)['\"]",
            r"['\"]websign['\"]\s*[:=]\s*(\d+)",
        ]:
            m = re.search(p, text, re.I)
            if m:
                out["websign"] = html.unescape(m.group(1)).strip()
                break

        return out

    def _extract_ajax_params_from_fn_assets(self, fn_html, origin, fn_url, headers):
        """从 fn 页内联脚本与外链JS中联合提取 ajax 参数。"""
        best = {}

        def _merge(d):
            nonlocal best
            if not d:
                return
            for k in ("file_id", "ajaxdata", "wp_sign", "websign"):
                if k not in best and d.get(k):
                    best[k] = d.get(k)

        # 1) 内联脚本
        inline_scripts = re.findall(r"<script[^>]*>([\s\S]*?)</script>", fn_html, re.I)
        for js in inline_scripts:
            _merge(self._extract_ajax_params_from_js_text(js))
            if all(best.get(k) for k in ("file_id", "ajaxdata", "wp_sign")):
                print(f"从fn内联脚本提取参数成功: file_id={best.get('file_id')}")
                return best

        # 2) 外链脚本
        script_srcs = re.findall(r"<script[^>]+src=['\"]([^'\"]+)['\"]", fn_html, re.I)
        seen = set()
        for src in script_srcs[:12]:
            full = urljoin(origin + "/", html.unescape(src).strip())
            if not full or full in seen:
                continue
            seen.add(full)
            try:
                h = dict(headers)
                h["Referer"] = fn_url
                r = self.http.get(full, headers=h, timeout=12)
                if r.status_code != 200:
                    continue
                _merge(self._extract_ajax_params_from_js_text(r.text))
                if all(best.get(k) for k in ("file_id", "ajaxdata", "wp_sign")):
                    print(f"从fn外链脚本提取参数成功: file_id={best.get('file_id')}")
                    return best
            except Exception:
                continue

        if best:
            print(
                "从fn脚本资产提取到部分参数: "
                f"file_id={bool(best.get('file_id'))}, "
                f"ajaxdata={bool(best.get('ajaxdata'))}, "
                f"wp_sign={bool(best.get('wp_sign'))}, "
                f"websign={bool(best.get('websign'))}"
            )
        return best

    def _get_real_download_url_impl(self, file_link, ajax_file_id=None):
        """下载核心实现（由 download_core 调用）。"""
        if not file_link:
            return None

        print(f"正在获取文件的真实下载链接: {self._mask_url(file_link)}")
        try:
            common_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }

            # 1) 访问分享页，提取 fn 页面链接
            r1 = self.http.get(file_link, headers=common_headers, timeout=15)
            r1.raise_for_status()
            page_html = r1.text
            parsed = urlparse(file_link)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            host = parsed.netloc

            # 处理简单的挑战页
            if self._is_html_challenge_response(r1, page_html):
                token = self._solve_acw_sc_v2(page_html)
                if token:
                    self.http.cookies.set("acw_sc__v2", token, domain=host, path="/")
                    r1 = self.http.get(file_link, headers=common_headers, timeout=15)
                    r1.raise_for_status()
                    page_html = r1.text
            # 补齐常见 cookie
            self.http.cookies.set("codelen", "1", domain=host, path="/")

            def _decode_html(text):
                if not text:
                    return ""
                s = html.unescape(text)
                s = s.replace("\\/", "/")
                s = s.replace("\\u002F", "/").replace("\\u002f", "/")
                s = s.replace("\\x2f", "/").replace("\\x2F", "/")
                s = s.replace("\\u003a", ":").replace("\\u003A", ":")
                return s

            def _find_fn_url(text):
                if not text:
                    return None
                # iframe src
                m_iframe = re.search(r'<iframe[^>]+src=[\'"]([^\'"]+)', text, re.I)
                if m_iframe:
                    src_val = html.unescape(m_iframe.group(1)).replace("\\/", "/").strip()
                    if "fn?" in src_val:
                        return src_val
                # script 中直接赋值
                m_fn = re.search(r'((?:https?://[^\s\'"]+)?/?fn\?[A-Za-z0-9_\-+=/%\?&]+)', text, re.I)
                if m_fn:
                    return html.unescape(m_fn.group(1)).replace("\\/", "/").strip()
                # 更宽松的匹配
                m_fn2 = re.search(r'(/fn\?[^\'"\s]+)', text, re.I)
                if m_fn2:
                    return html.unescape(m_fn2.group(1)).replace("\\/", "/").strip()
                return None

            fn_candidate = None
            # 先尝试原始 HTML
            fn_candidate = _find_fn_url(page_html)
            # 尝试解码后的 HTML
            if not fn_candidate:
                fn_candidate = _find_fn_url(_decode_html(page_html))

            # 兜底：处理 JS 跳转
            if not fn_candidate:
                m_loc = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", page_html)
                if m_loc:
                    jump_url = urljoin(origin + "/", html.unescape(m_loc.group(1)).replace("\\/", "/").strip())
                    try:
                        r1b = self.http.get(jump_url, headers=common_headers, timeout=15)
                        r1b.raise_for_status()
                        html2 = r1b.text
                        fn_candidate = _find_fn_url(html2) or _find_fn_url(_decode_html(html2))
                    except Exception:
                        pass

            if not fn_candidate:
                print("警告: 分享页未找到 fn 链接")
                print("requests主路径提链失败，尝试浏览器兜底")
                return self._get_real_download_url_by_browser(file_link)

            fn_url = urljoin(origin + "/", fn_candidate)

            # 2) 访问 fn 页面，仅从脚本资产提取 ajaxdata/wp_sign/file_id（失败自动重试一次）
            ajaxdata = None
            wp_sign = None
            websign = None
            file_id = str(ajax_file_id).strip() if ajax_file_id is not None else None
            if file_id and not file_id.isdigit():
                file_id = None
            if file_id:
                print(f"使用列表缓存file_id: {file_id}")

            for attempt in (1, 2):
                h2 = dict(common_headers)
                h2["Referer"] = file_link
                r2 = self.http.get(fn_url, headers=h2, timeout=15)
                r2.raise_for_status()
                fn_html = r2.text

                # 仅从脚本资产提取（内联 <script> + 外链 script src）
                p1 = self._extract_ajax_params_from_fn_assets(
                    fn_html=fn_html,
                    origin=origin,
                    fn_url=fn_url,
                    headers=common_headers
                )
                if not ajaxdata:
                    ajaxdata = p1.get("ajaxdata")
                if not wp_sign:
                    wp_sign = p1.get("wp_sign")
                if websign is None:
                    # 允许空字符串作为合法值（部分站点为 websign:''）
                    if "websign" in p1:
                        websign = p1.get("websign")
                if not file_id:
                    file_id = p1.get("file_id")

                if file_id == "1":
                    file_id = None

                if ajaxdata and wp_sign and file_id:
                    break

                if attempt == 1:
                    print("fn参数提取首轮未完整，刷新后重试一次")
                    time.sleep(0.35)

            if not (ajaxdata and wp_sign and file_id):
                print("警告: fn页面参数提取失败")
                print("requests主路径提链失败，尝试浏览器兜底")
                return self._get_real_download_url_by_browser(file_link)

            # 3) 调用 ajaxm.php 获取 dom + url
            ajax_url = f"{origin}/ajaxm.php"
            params = {"file": file_id}
            post_headers = {
                "Accept": "application/json, text/javascript, */*",
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": origin,
                "Referer": fn_url,
                "User-Agent": common_headers["User-Agent"],
                "Accept-Language": common_headers["Accept-Language"],
            }
            payload = {
                "action": "downprocess",
                "websignkey": ajaxdata,
                "signs": ajaxdata,
                "sign": wp_sign,
                "websign": websign if websign is not None else "",
                "kd": "1",
                "ves": "1",
            }
            r3 = self.http.post(ajax_url, params=params, data=payload, headers=post_headers, timeout=15)
            r3.raise_for_status()
            data = r3.json()
            if str(data.get("zt")) != "1":
                print(f"警告: ajaxm返回异常 zt={data.get('zt')}, info={data.get('inf')}")
                print("requests主路径提链失败，尝试浏览器兜底")
                return self._get_real_download_url_by_browser(file_link)

            dom = str(data.get("dom", "")).strip().rstrip("/")
            path = str(data.get("url", "")).strip()
            if not dom or not path:
                print("警告: ajaxm缺少 dom/url")
                print("requests主路径提链失败，尝试浏览器兜底")
                return self._get_real_download_url_by_browser(file_link)

            real_url = f"{dom}/file/{path}&toolsdown"
            print("requests主路径提链成功")
            print(f"找到真实下载链接: {self._mask_url(real_url)}")
            return real_url
        except Exception as e:
            print(f"requests链路获取真实下载链接失败: {e}")
            print("requests主路径提链失败，尝试浏览器兜底")
            return self._get_real_download_url_by_browser(file_link)

    def _is_download_url_valid_impl(self, url, timeout=8):
        """下载核心实现（由 download_core 调用）。"""
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

    def _is_html_challenge_response(self, response, body_text=None):
        """判断响应是否为反爬挑战HTML页。"""
        ctype = (response.headers.get("Content-Type") or "").lower()
        if "text/html" not in ctype:
            return False
        text = body_text or ""
        markers = ("acw_sc__v2", "document.cookie", "location.reload", "var arg1=")
        return any(m in text for m in markers)

    def _decode_acw_item(self, s):
        """解码挑战脚本里 a0i 数组单项（兼容其 atob 变体）。"""
        alpha = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/="
        q = 0
        r = 0
        t = 0
        out = ""
        while True:
            ch = s[t:t + 1]
            t += 1
            if not ch:
                break
            idx = alpha.find(ch)
            if ~idx:
                r = (r * 64 + idx) if (q % 4) else idx
                old_q = q
                q += 1
                if old_q % 4:
                    c = 255 & (r >> ((-2 * q) & 6))
                    if c != 0:
                        out += chr(c)
        try:
            return requests.utils.unquote("".join(f"%{ord(c):02x}" for c in out))
        except Exception:
            return out

    def _solve_acw_sc_v2(self, challenge_html):
        """从挑战页计算 acw_sc__v2 cookie 值。"""
        try:
            m_arg1 = re.search(r"var\s+arg1='([0-9A-Fa-f]+)'", challenge_html)
            m_perm = re.search(r"var\s+m=\[([^\]]+)\]", challenge_html)
            m_arr = re.search(r"var\s+N=\[(.*?)\];a0i=function", challenge_html, re.S)
            if not (m_arg1 and m_perm and m_arr):
                return None

            arg1 = m_arg1.group(1)
            perm = [int(x.strip(), 0) for x in m_perm.group(1).split(",") if x.strip()]
            encoded_items = re.findall(r"'([^']*)'", "[" + m_arr.group(1) + "]")
            decoded_items = [self._decode_acw_item(x) for x in encoded_items]

            # 常见挑战中 key 为 40 位十六进制常量
            key_candidates = [x for x in decoded_items if re.fullmatch(r"[0-9a-fA-F]{40}", x or "")]
            if not key_candidates:
                return None
            key_hex = key_candidates[0]

            q = [""] * len(perm)
            for i, ch in enumerate(arg1):
                target = i + 1
                for z, val in enumerate(perm):
                    if val == target:
                        q[z] = ch
                        break
            u = "".join(q)
            n = min(len(u), len(key_hex))
            if n < 2:
                return None
            n -= (n % 2)

            out = []
            for i in range(0, n, 2):
                a = int(u[i:i + 2], 16)
                b = int(key_hex[i:i + 2], 16)
                out.append(f"{(a ^ b):02x}")
            v = "".join(out)
            return v if v else None
        except Exception:
            return None

    def _get_host(self, url):
        try:
            return urlparse(url).netloc.lower().strip()
        except Exception:
            return ""

    def _should_skip_validation(self, url):
        host = self._get_host(url)
        if not host:
            return False
        return bool(self.validation_policy.get(host, {}).get("skip_validation"))

    def _record_validation_false_negative(self, url):
        host = self._get_host(url)
        if not host:
            return
        state = self.validation_policy.setdefault(host, {"false_negative": 0, "skip_validation": False})
        state["false_negative"] += 1
        if state["false_negative"] >= 2 and not state["skip_validation"]:
            state["skip_validation"] = True
            print(f"校验策略自适应: 检测到 {host} 存在校验误杀，后续将跳过预校验")
    
    def download_with_requests(self, url, file_path, file_name):
        return self.download_core.download_with_requests(url, file_path, file_name)

    def download_single_file_optimized(self, file_info, download_dir="downloads", prefetched_real_url=None):
        return self.download_core.download_single_file_optimized(file_info, download_dir, prefetched_real_url)

    def download_single_file_legacy(self, file_info, download_dir="downloads", max_retries=3):
        return self.download_core.download_single_file_legacy(file_info, download_dir, max_retries)

    def login_and_get_files(self, url=None, password=None, on_batch=None, stop_event=None):
        """代理到列表获取器，保持 API 不变。"""
        return self.list_fetcher.fetch(url=url, password=password, on_batch=on_batch, stop_event=stop_event)
    
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
                
    def download_single_file(self, file_info, download_dir="downloads", max_retries=3):
        return self.download_core.download_single_file(file_info, download_dir, max_retries)

    def monitor_download_progress(self, expected_file, filename, timeout=60):
        return self.download_core.monitor_download_progress(expected_file, filename, timeout)

    def get_real_download_url(self, file_link, ajax_file_id=None):
        return self.download_core.get_real_download_url(file_link, ajax_file_id)

    def is_download_url_valid(self, url, timeout=8):
        return self.download_core.is_download_url_valid(url, timeout)
