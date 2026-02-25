import time
import random
import requests
import re
from urllib.parse import urlparse, parse_qs, urljoin

try:
    from source_code_common.lanzou_errors import LanzouError, ErrorCode
    from source_code_common.lanzou_types import FileItem
except Exception:
    from lanzou_errors import LanzouError, ErrorCode
    from lanzou_types import FileItem


class LanzouListFetcher:
    def __init__(self, downloader):
        self.d = downloader

    def fetch(self, url=None, password=None, on_batch=None, stop_event=None):
        """登录并获取文件列表（只做列表逻辑）。"""
        if url is None:
            url = self.d.default_url
        if password is None:
            password = self.d.default_password
        self.d.files = []
        self.d.file_items = []

        payload_debug_keys = None

        def _is_lanzou_share_link(share_url, page_html):
            parsed = urlparse(share_url)
            host = parsed.netloc.lower()
            if "lanzou" in host:
                return True
            if not page_html:
                return False
            html_lower = page_html.lower()
            strong_markers = ("filemoreajax.php", "/fn?", "ajaxm.php")
            if any(m in html_lower for m in strong_markers):
                return True
            weak_markers = ("woozooo", "lanzou", "lanzoul", "lanzoui", "ta@lanzou.com", "© lanzou")
            return sum(1 for m in weak_markers if m in html_lower) >= 2

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

            def _extract_payload_spec(html_text):
                base_keys = {"file", "lx", "fid", "uid", "pg", "rep", "t", "k", "up"}
                optional_keys = {"ls", "pwd", "vip", "webfoldersign"}
                found_keys = set()
                extra_values = {}

                for m in re.finditer(r"filemoreajax\.php", html_text):
                    start = max(0, m.start() - 500)
                    end = min(len(html_text), m.end() + 800)
                    snippet = html_text[start:end]
                    obj_match = re.search(r"data\s*:\s*\{([^}]+)\}", snippet, re.S)
                    if obj_match:
                        obj_text = obj_match.group(1)
                        for key_match in re.finditer(r"['\"]?([A-Za-z0-9_]+)['\"]?\s*:", obj_text):
                            found_keys.add(key_match.group(1))
                        break

                if not found_keys:
                    found_keys = set(base_keys)
                    for k in optional_keys:
                        if re.search(rf"\b{k}\b", html_text):
                            found_keys.add(k)

                def _pick_scalar(name):
                    m1 = re.search(rf"(?:var\s+)?{re.escape(name)}\s*=\s*['\"]([^'\"]+)['\"]", html_text)
                    if m1:
                        return m1.group(1)
                    m2 = re.search(rf"(?:var\s+)?{re.escape(name)}\s*=\s*(\d+)", html_text)
                    if m2:
                        return m2.group(1)
                    return None

                for key in ("ls", "vip", "webfoldersign"):
                    v = _pick_scalar(key)
                    if v is not None:
                        extra_values[key] = v

                return found_keys, extra_values

            missing = [k for k, v in {"fid": fid, "uid": uid, "t": t_val, "k": k_val}.items() if not v]
            if missing:
                raise LanzouError(ErrorCode.PARSE, f"页面参数提取失败，缺少: {', '.join(missing)}")

            payload_keys, extra_values = _extract_payload_spec(page_html)
            try:
                key_preview = ",".join(sorted(payload_keys))
            except Exception:
                key_preview = str(payload_keys)
            nonlocal payload_debug_keys
            if payload_debug_keys != key_preview:
                payload_debug_keys = key_preview
                print(f"调试: 列表接口字段 => {key_preview}")
                if extra_values:
                    print(f"调试: 额外字段取值 => {extra_values}")
            return {
                "origin": origin,
                "fid": fid,
                "uid": uid,
                "t": t_val,
                "k": k_val,
                "payload_keys": payload_keys,
                "extra_values": extra_values,
            }

        try:
            print(f"正在访问链接: {self.d._mask_url(url)}")
            session = requests.Session()
            session.trust_env = False
            common_headers = self.d._make_common_headers()

            parsed = urlparse(url)
            host = parsed.netloc

            def _get_share_page(cache_bust=False):
                req_url = url
                if cache_bust:
                    sep = "&" if "?" in req_url else "?"
                    req_url = f"{req_url}{sep}t={int(time.time()*1000)}"
                resp = session.get(req_url, headers=common_headers, timeout=20)
                resp.raise_for_status()
                body = resp.text
                if self.d._is_html_challenge_response(resp, body):
                    token = self.d._solve_acw_sc_v2(body)
                    if token:
                        session.cookies.set("acw_sc__v2", token, domain=host, path="/")
                        resp = session.get(req_url, headers=common_headers, timeout=20)
                        resp.raise_for_status()
                        body = resp.text
                session.cookies.set("codelen", "1", domain=host, path="/")
                return resp, body, req_url

            resp, page_html, share_url = _get_share_page()

            if not _is_lanzou_share_link(url, page_html):
                raise LanzouError(ErrorCode.INVALID_LINK, "链接不是蓝奏云分享页，请重新输入正确的蓝奏云链接")

            try:
                ctx = _extract_context(page_html, url)
            except LanzouError as e:
                if e.code == ErrorCode.PARSE:
                    raise LanzouError(ErrorCode.INVALID_LINK, "链接不是蓝奏云分享页，请重新输入正确的蓝奏云链接")
                raise
            ctx["share_url"] = share_url
            ctx["referer_url"] = url
            ajax_url = f"{ctx['origin']}/filemoreajax.php?file={ctx['fid']}"
            print(f"参数提取成功 fid={ctx['fid']} uid={ctx['uid']}")

            def _validate_lanzou_api():
                payload = {
                    "lx": 2,
                    "fid": ctx["fid"],
                    "uid": ctx["uid"],
                    "pg": 1,
                    "rep": 0,
                    "t": ctx["t"],
                    "k": ctx["k"],
                    "up": 1,
                }
                ajax_headers = {
                    "User-Agent": common_headers["User-Agent"],
                    "Accept": "application/json, text/javascript, */*",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": ctx.get("referer_url") or url,
                    "Origin": ctx["origin"],
                }
                try:
                    probe = session.post(ajax_url, data=payload, headers=ajax_headers, timeout=12)
                    probe.raise_for_status()
                    data = probe.json()
                    return isinstance(data, dict) and ("zt" in data)
                except Exception:
                    return False

            if not _validate_lanzou_api():
                raise LanzouError(ErrorCode.LIST_API_UNAVAILABLE, "链接不是蓝奏云分享页或列表接口不可用")

            def _new_session():
                s = requests.Session()
                s.trust_env = False
                return s

            def _refresh_context(force_new_session=False, cache_bust=False):
                nonlocal session, ctx
                if force_new_session:
                    session = _new_session()
                refresh_resp, refresh_html, share_url = _get_share_page(cache_bust=cache_bust)
                ctx = _extract_context(refresh_html, url)
                ctx["share_url"] = share_url
                ctx["referer_url"] = url

            def _post_page(pg, rep=0, ls=1, up=1):
                payload = {}
                keys = ctx.get("payload_keys") or {
                    "file", "lx", "fid", "uid", "pg", "rep", "t", "k", "up", "ls", "pwd"
                }

                def _set_if(key, value):
                    if key in keys:
                        payload[key] = value

                _set_if("file", ctx["fid"])
                _set_if("lx", 2)
                _set_if("fid", ctx["fid"])
                _set_if("uid", ctx["uid"])
                _set_if("pg", pg)
                _set_if("rep", rep)
                _set_if("t", ctx["t"])
                _set_if("k", ctx["k"])
                _set_if("up", up)
                if "ls" in keys:
                    payload["ls"] = ls if ls is not None else ctx.get("extra_values", {}).get("ls", 1)
                if "pwd" in keys:
                    payload["pwd"] = password or ""
                if "vip" in keys:
                    payload["vip"] = ctx.get("extra_values", {}).get("vip", "0")
                if "webfoldersign" in keys:
                    payload["webfoldersign"] = ctx.get("extra_values", {}).get("webfoldersign", "")
                ajax_headers = {
                    "User-Agent": common_headers["User-Agent"],
                    "Accept": "application/json, text/javascript, */*",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": ctx.get("referer_url") or url,
                    "Origin": ctx["origin"],
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                }
                page_resp = session.post(ajax_url, data=payload, headers=ajax_headers, timeout=20)
                body = page_resp.text or ""
                if self.d._is_html_challenge_response(page_resp, body) or "http_ratelimit" in page_resp.headers.get("x-tengine-error", ""):
                    token = self.d._solve_acw_sc_v2(body)
                    if token:
                        session.cookies.set("acw_sc__v2", token, domain=host, path="/")
                        time.sleep(0.6 + (0.6 * random.random()))
                        page_resp = session.post(ajax_url, data=payload, headers=ajax_headers, timeout=20)
                        body = page_resp.text or ""
                page_resp.raise_for_status()
                try:
                    data = page_resp.json()
                except Exception:
                    info = "rate limit challenge" if self.d._is_html_challenge_response(page_resp, body) else "non-json response"
                    return {"zt": "4", "info": info}, "4"
                return data, str(data.get("zt", ""))

            def _post_page_simple(pg, tries=6):
                last_data = None
                last_zt = ""
                for _ in range(tries):
                    try:
                        data, zt = _post_page(pg, rep=0, ls=1, up=1)
                        last_data, last_zt = data, zt
                        if zt == "1" or zt == "3":
                            return data, zt
                        if zt == "4":
                            try:
                                _refresh_context(force_new_session=True, cache_bust=True)
                            except Exception:
                                pass
                    except Exception:
                        last_data, last_zt = None, ""
                    time.sleep(0.25)
                return last_data, last_zt

            def _fetch_page_with_retry(target_page, max_attempts=24, allow_warmup=True):
                last_data = None
                last_zt = ""
                keys = ctx.get("payload_keys") or set()
                simple_payload = keys.issubset({"file", "lx", "fid", "uid", "pg", "rep", "t", "k", "up"})
                if simple_payload:
                    max_attempts = min(max_attempts, 6)
                primary_variants = [(0, 1, 1)]
                fallback_variants = [(0, 1, 1), (0, None, 1), (0, 0, 1), (0, None, 0)]
                payload_variants = primary_variants
                zt4_hits = 0

                for attempt in range(1, max_attempts + 1):
                    for rep, ls, up in payload_variants:
                        try:
                            data, zt = _post_page(target_page, rep=rep, ls=ls, up=up)
                            last_data, last_zt = data, zt
                        except Exception:
                            data, zt = None, ""
                            last_data, last_zt = None, ""

                        if zt == "1" or zt == "2":
                            return data, zt
                        if zt == "3":
                            raise LanzouError(ErrorCode.PASSWORD_INCORRECT, f"密码错误: {data.get('info', 'unknown') if data else 'unknown'}")
                        if zt == "4":
                            zt4_hits += 1
                            info = data.get("info", "") if isinstance(data, dict) else ""
                            print(f"调试: 第 {target_page} 页 zt=4 (attempt {attempt}/{max_attempts}) info={info}")
                            if zt4_hits in (2, 4):
                                try:
                                    _refresh_context(force_new_session=False, cache_bust=True)
                                except Exception:
                                    pass
                            time.sleep(0.2 + (0.8 * random.random()))
                            continue

                    if not simple_payload and attempt in (2, 4):
                        payload_variants = fallback_variants

                    if allow_warmup and target_page > 1 and attempt % 4 == 0:
                        try:
                            _post_page(target_page - 1)
                        except Exception:
                            pass
                    time.sleep(min(2.0, 0.2 * attempt))

                return last_data, last_zt

            index = 1
            page = 1
            max_pages = self.d.list_config.max_pages
            seen_ids = set()
            simple_mode = False
            zt4_global = 0
            last_ctx_refresh = 0.0

            while page <= max_pages:
                if stop_event is not None and stop_event.is_set():
                    print("调试: 已收到停止加载信号，提前结束")
                    break
                self.d._sleep_range(self.d.list_config.page_interval_s)
                print(f"调试: 正在获取第 {page} 页")
                data, zt = None, ""
                max_page_attempts = 4 if simple_mode else 8
                for page_attempt in range(1, max_page_attempts + 1):
                    if simple_mode:
                        data, zt = _post_page_simple(page, tries=6)
                        if zt != "1":
                            data, zt = _fetch_page_with_retry(page, max_attempts=24, allow_warmup=True)
                    else:
                        data, zt = _fetch_page_with_retry(page, max_attempts=24, allow_warmup=True)

                    if zt == "1" or zt == "2" or zt == "3":
                        break
                    if zt == "4":
                        zt4_global = min(12, zt4_global + 1)
                        self.d._sleep_range(self.d.list_config.zt4_wait_s)
                        print(f"调试: 第 {page} 页 zt=4，随机等待后重试")
                        now = time.time()
                        if now - last_ctx_refresh > self.d.list_config.ctx_refresh_cooldown_s:
                            try:
                                _refresh_context(force_new_session=False, cache_bust=True)
                                last_ctx_refresh = now
                            except Exception:
                                pass
                        continue
                    time.sleep(0.3)

                if zt == "2":
                    print(f"调试: 第 {page} 页 zt=2，列表结束")
                    break
                if zt != "1":
                    raise LanzouError(ErrorCode.UNKNOWN, f"第 {page} 页请求失败，zt={zt}, info={data.get('info', '') if data else ''}")
                if zt4_global > 0:
                    zt4_global = max(0, zt4_global - 1)

                rows = data.get("text") or []
                if not rows:
                    break
                if page == 1:
                    simple_mode = True

                added_count = 0
                batch = []
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

                    item = FileItem(
                        index=index,
                        name=row.get("name_all", ""),
                        link=file_link,
                        size=row.get("size", "未知大小"),
                        time=row.get("time", "未知时间"),
                        ajax_file_id=ajax_file_id,
                    )
                    self.d.file_items.append(item)
                    file_info = item.to_dict()
                    self.d.files.append(file_info)
                    batch.append(file_info)
                    if index <= 50:
                        print(f"  {index:3d}. {file_info['name']} ({file_info['size']})")
                    index += 1
                    added_count += 1
                if batch and callable(on_batch):
                    try:
                        on_batch(batch)
                    except Exception:
                        pass

                if added_count == 0:
                    print(f"调试: 第 {page} 页无新增文件，停止翻页以避免循环")
                    break
                if len(rows) < self.d.list_config.page_size:
                    print(f"调试: 第 {page} 页条目数 {len(rows)} < {self.d.list_config.page_size}，视为最后一页")
                    break
                page += 1

            print(f"直连获取完成，共 {len(self.d.files)} 个文件")

        except LanzouError:
            raise
        except Exception as e:
            raise LanzouError(ErrorCode.UNKNOWN, f"获取文件列表时出错: {e}")

        return self.d.files
