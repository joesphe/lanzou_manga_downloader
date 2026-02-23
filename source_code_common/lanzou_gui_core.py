"""
蓝奏云下载器优化：获取真实下载链接后使用requests下载
界面布局优化版

通过DrissionPage获取真实下载链接，然后使用requests直接下载文件
"""

import time
import os
import sys
import requests
import threading
import re
import json
try:
    from DrissionPage import Chromium, ChromiumOptions, SessionOptions
except Exception:
    Chromium = None
    ChromiumOptions = None
    SessionOptions = None
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import base64
import hashlib
import html
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
        
    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def set_global_progress_callback(self, callback):
        """设置全局进度回调函数"""
        self.global_progress_callback = callback
        
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
        """使用深度混淆技术获取凭证"""
        import hashlib
        
        # 通过计算生成的正确混淆数据
        url_obfuscated = [
            0x0B, 0x30, 0xA2, 0x6D, 0x31, 0x15, 0x5A, 0x9F, 0x52, 0x1F, 0xC1, 0x28, 0x36, 0x7E, 0x8C, 0xCA, 
            0x67, 0x18, 0x6C, 0x82, 0x57, 0x85, 0xF5, 0x9F, 0x7C, 0x20, 0xC4, 0x17, 0x95, 0x5B, 0x89, 0xD7, 
            0x94, 0xED, 0x83
        ]
        
        # 密码 "8255" 混淆数据
        password_obfuscated = [0xBD, 0xF2, 0xFD, 0xA7]
        
        def get_dynamic_key(index, base_offset=0):
            # 基于复杂计算生成动态密钥
            hash_input = f"dynamic_key_{index + base_offset}_secret_salt".encode()
            hash_val = hashlib.sha256(hash_input).hexdigest()
            return int(hash_val[:2], 16)  # 取前两位十六进制作为密钥
        
        # 解密URL
        url_bytes = bytearray()
        for i, obf_byte in enumerate(url_obfuscated):
            key = get_dynamic_key(i, 0)
            decrypted_byte = obf_byte ^ key
            url_bytes.append(decrypted_byte)
        
        url = url_bytes.decode('utf-8', errors='ignore')
        
        # 解密密码
        password_bytes = bytearray()
        for i, obf_byte in enumerate(password_obfuscated):
            key = get_dynamic_key(i + len(url_obfuscated), 0)  # 使用相同的偏移基础
            decrypted_byte = obf_byte ^ key
            password_bytes.append(decrypted_byte)
        
        password = password_bytes.decode('utf-8', errors='ignore')
        
        return url, password
    
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
                                print(f"浏览器兜底提链成功: {href}")
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

        return out

    def _extract_ajax_params_from_fn_assets(self, fn_html, origin, fn_url, headers):
        """从 fn 页内联脚本与外链JS中联合提取 ajax 参数。"""
        best = {}

        def _merge(d):
            nonlocal best
            if not d:
                return
            for k in ("file_id", "ajaxdata", "wp_sign"):
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
                f"wp_sign={bool(best.get('wp_sign'))}"
            )
        return best

    def get_real_download_url(self, file_link, ajax_file_id=None):
        """优先使用requests链路获取真实下载链接：i页 -> fn页 -> ajaxm.php。"""
        if not file_link:
            return None

        print(f"正在获取文件的真实下载链接: {file_link}")
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

            fn_candidate = None
            # 先宽松提取 iframe src（支持 fn?... / /fn?... / https://.../fn?...）
            m_iframe_src = re.search(r'<iframe[^>]+src=[\'"]([^\'"]+)', page_html, re.I)
            if m_iframe_src:
                src_val = html.unescape(m_iframe_src.group(1)).replace("\\/", "/").strip()
                if "fn?" in src_val:
                    fn_candidate = src_val

            # 兜底：从源码中直接搜 fn 链接（绝对或相对）
            if not fn_candidate:
                m_fn = re.search(r'((?:https?://[^\s\'"]+)?/?fn\?[A-Za-z0-9_\-+=/%\?&]+)', page_html, re.I)
                if m_fn:
                    fn_candidate = html.unescape(m_fn.group(1)).replace("\\/", "/").strip()

            if not fn_candidate:
                print("警告: 分享页未找到 fn 链接")
                print("requests主路径提链失败，尝试浏览器兜底")
                return self._get_real_download_url_by_browser(file_link)

            fn_url = urljoin(origin + "/", fn_candidate)

            # 2) 访问 fn 页面，仅从脚本资产提取 ajaxdata/wp_sign/file_id（失败自动重试一次）
            ajaxdata = None
            wp_sign = None
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
                "websign": "",
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
            print(f"找到真实下载链接: {real_url}")
            return real_url
        except Exception as e:
            print(f"requests链路获取真实下载链接失败: {e}")
            print("requests主路径提链失败，尝试浏览器兜底")
            return self._get_real_download_url_by_browser(file_link)

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
            
            def _request_download(target_url):
                return self.http.get(target_url, headers=headers, stream=True, timeout=30, allow_redirects=True)

            # 第一次请求
            response = _request_download(url)
            response.raise_for_status()

            # 若命中反爬挑战页，尝试纯requests计算 acw_sc__v2 并重试一次
            ctype = (response.headers.get("Content-Type") or "").lower()
            if "text/html" in ctype:
                challenge_body = response.text
                if self._is_html_challenge_response(response, challenge_body):
                    token = self._solve_acw_sc_v2(challenge_body)
                    response.close()
                    if token:
                        host = urlparse(url).hostname
                        if host:
                            self.http.cookies.set("acw_sc__v2", token, domain=host, path="/")
                        print(f"检测到挑战页，已计算acw_sc__v2并重试下载: {file_name}")
                        response = _request_download(url)
                        response.raise_for_status()
                    else:
                        print(f"检测到挑战页，但未能计算acw_sc__v2: {file_name}")
                        return False

            # 二次保护：重试后若仍是HTML，直接判失败，避免保存假文件
            final_ctype = (response.headers.get("Content-Type") or "").lower()
            if "text/html" in final_ctype:
                body = response.text
                response.close()
                print(f"下载响应仍为HTML，已阻止保存假文件: {file_name}")
                return False
            
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
            
            # 首先尝试预取结果；对预取链接优先“直接下载一次”，减少校验误杀影响
            real_url = prefetched_real_url
            last_validation_result = None

            if real_url and not self._should_skip_validation(real_url):
                last_validation_result = self.is_download_url_valid(real_url)
                if not last_validation_result:
                    print(f"预取直链校验未通过，先尝试直接下载: {file_info['name']}")
            elif real_url:
                print("已启用自适应策略：跳过直链预校验")

            if not real_url:
                real_url = self.get_real_download_url(
                    file_info['link'],
                    ajax_file_id=file_info.get("ajax_file_id")
                )
                if not real_url:
                    print(f"未能获取到 {file_info['name']} 的真实下载链接，跳过该文件")
                    return False
                if not self._should_skip_validation(real_url):
                    last_validation_result = self.is_download_url_valid(real_url)
                    if not last_validation_result:
                        print(f"真实链接校验未通过，先尝试直接下载: {file_info['name']}")
                else:
                    print("已启用自适应策略：跳过直链预校验")

            # 第一次下载尝试
            success = self.download_with_requests(real_url, file_path, clean_filename)
            if success:
                if last_validation_result is False:
                    self._record_validation_false_negative(real_url)
                return True

            # 若预取链接首次下载失败，强制重新提链再试一次
            print(f"首次直链下载失败，重新提链后重试: {file_info['name']}")
            fresh_url = self.get_real_download_url(
                file_info['link'],
                ajax_file_id=file_info.get("ajax_file_id")
            )
            if not fresh_url:
                print(f"重新提链失败，跳过该文件: {file_info['name']}")
                return False

            if not self._should_skip_validation(fresh_url):
                fresh_valid = self.is_download_url_valid(fresh_url)
                if not fresh_valid:
                    print(f"重提直链校验未通过，继续尝试直接下载: {file_info['name']}")

            retry_success = self.download_with_requests(fresh_url, file_path, clean_filename)
            if not retry_success:
                print(f"requests下载失败，跳过该文件: {file_info['name']}")
            return retry_success
            
        except Exception as e:
            print(f"优化下载文件 {file_info['name']} 时出错: {e}")
            return False
    
    def download_single_file_legacy(self, file_info, download_dir="downloads", max_retries=3):
        """
        原始浏览器下载兜底（已禁用）
        """
        print(f"浏览器下载兜底已禁用，跳过该文件: {file_info['name']}")
        return False
    
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
                    # 每隔几次重试强制刷新上下文，避免 token/cookie 老化导致 zt=4
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

                    # zt=4 常见于上下文失效/风控刷新，尝试用上一页做一次轻量热身
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
                    # 强恢复：重新建会话并按顺序回放前序页，再重试当前页
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

                    # 列表接口中通常包含每个文件对应的数字 file_id，可直接用于 ajaxm.php?file=
                    ajax_file_id = None
                    for k in ("file_id", "fid", "f_id", "down_id", "id"):
                        v = row.get(k)
                        s = str(v).strip() if v is not None else ""
                        if s.isdigit() and s != "0":
                            ajax_file_id = s
                            break
                    if not ajax_file_id:
                        for k, v in row.items():
                            ks = str(k).lower()
                            s = str(v).strip() if v is not None else ""
                            if ("id" in ks or ks in ("fid", "file")) and s.isdigit() and s != "0":
                                ajax_file_id = s
                                break
                    if index <= 3:
                        key_preview = ", ".join(list(row.keys())[:12])
                        print(f"调试: 列表行键预览[{index}] => {key_preview}")
                        if ajax_file_id:
                            print(f"调试: 列表提取ajax_file_id[{index}] => {ajax_file_id}")
                        else:
                            print(f"调试: 列表未提取到ajax_file_id[{index}]")

                    file_info = {
                        "index": index,
                        "name": row.get("name_all", ""),
                        "link": file_link,
                        "size": row.get("size", "未知大小"),
                        "time": row.get("time", "未知时间"),
                        "ajax_file_id": ajax_file_id,
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
                
    def download_single_file(self, file_info, download_dir="downloads", max_retries=3):
        """使用浏览器直接下载单个文件（保留原方法）"""
        # 这是原始的下载方法，保持不变
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
                        progress = min(95, int((current_size - initial_size) * 100 / (initial_size + current_size + 1)))
                        self.progress_callback(filename, current_size, expected_file, "下载中...", progress)
                    initial_size = current_size
                elif current_size > 0:
                    # 文件存在且有内容，可能已下载完成
                    if self.progress_callback:
                        self.progress_callback(filename, current_size, expected_file, "下载完成", 100)
                    return True
            time.sleep(1)
        
        # 超时后再次检查文件是否已存在且有内容
        if os.path.exists(expected_file) and os.path.getsize(expected_file) > 0:
            if self.progress_callback:
                self.progress_callback(filename, os.path.getsize(expected_file), expected_file, "下载完成", 100)
            return True
        
        return False


# 以下是GUI部分的代码（优化布局并添加用户提示）
class LanzouDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("蓝奏云下载器")
        self.root.geometry("1200x800")
        
        # 初始化下载器实例
        self.downloader = OptimizedLanzouDownloader()
        
        # 当前选中的文件列表
        self.selected_files = []
        
        # 创建界面
        self.setup_gui()
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
        self.refresh_files(show_popup=True)
    
    def refresh_files(self, show_popup=False):
        """刷新文件列表"""
        try:
            self.status_var.set("正在获取文件列表...")
            self.root.update()

            # 在列表区域显示获取状态
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.tree.insert("", "end", values=("", "正在获取文件列表中...", "", ""))
            self.root.update()

            # 获取文件列表
            self.downloader.login_and_get_files()
            
            # 清空当前列表
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # 添加新文件到列表
            for file_info in self.downloader.files:
                self.tree.insert("", "end", values=(
                    file_info["index"],
                    file_info["name"],
                    file_info["size"],
                    file_info["time"],
                ))
            
            self.status_var.set(f"就绪 - 共 {len(self.downloader.files)} 个文件")
            if show_popup:
                messagebox.showinfo("提示", f"文件列表获取完成，共 {len(self.downloader.files)} 个文件")
            
        except Exception as e:
            messagebox.showerror("错误", f"获取文件列表时出错: {str(e)}")
            self.status_var.set("错误")
    
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
