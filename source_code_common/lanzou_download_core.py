import os
import time
from urllib.parse import urlparse


class LanzouDownloadCore:
    def __init__(self, downloader):
        self.d = downloader

    def get_real_download_url(self, file_link, ajax_file_id=None):
        return self.d._get_real_download_url_impl(file_link, ajax_file_id)

    def is_download_url_valid(self, url, timeout=8):
        return self.d._is_download_url_valid_impl(url, timeout)

    def download_with_requests(self, url, file_path, file_name):
        d = self.d
        try:
            if os.path.exists(file_path):
                if d.progress_callback:
                    d.progress_callback(file_name, os.path.getsize(file_path), file_path, "跳过(已存在)", 100)
                return True

            print(f"开始使用requests下载: {file_name}")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }

            def _request_download(target_url):
                return d.http.get(target_url, headers=headers, stream=True, timeout=30, allow_redirects=True)

            response = _request_download(url)
            response.raise_for_status()

            ctype = (response.headers.get("Content-Type") or "").lower()
            if "text/html" in ctype:
                challenge_body = response.text
                if d._is_html_challenge_response(response, challenge_body):
                    token = d._solve_acw_sc_v2(challenge_body)
                    response.close()
                    if token:
                        host = urlparse(url).hostname
                        if host:
                            d.http.cookies.set("acw_sc__v2", token, domain=host, path="/")
                        print(f"检测到挑战页，已计算acw_sc__v2并重试下载: {file_name}")
                        response = _request_download(url)
                        response.raise_for_status()
                    else:
                        print(f"检测到挑战页，但未能计算acw_sc__v2: {file_name}")
                        return False

            final_ctype = (response.headers.get("Content-Type") or "").lower()
            if "text/html" in final_ctype:
                response.close()
                print(f"下载响应仍为HTML，已阻止保存假文件: {file_name}")
                return False

            total_size = int(response.headers.get('content-length', 0))
            os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)

            downloaded_size = 0
            with response:
                with open(file_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)
                            downloaded_size += len(chunk)
                            if total_size > 0 and d.progress_callback:
                                progress = int((downloaded_size / total_size) * 100)
                                d.progress_callback(file_name, downloaded_size, file_path, "下载中...", progress)

            if d.progress_callback:
                d.progress_callback(file_name, downloaded_size, file_path, "下载完成", 100)
            print(f"文件下载完成: {file_name}")
            return True

        except Exception as e:
            print(f"使用requests下载文件 {file_name} 时出错: {e}")
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            return False

    def download_single_file_optimized(self, file_info, download_dir="downloads", prefetched_real_url=None):
        d = self.d
        try:
            print(f"开始优化下载流程: {file_info['name']}")
            clean_filename = d.sanitize_filename(file_info['name'])
            file_path = os.path.join(download_dir, clean_filename)

            real_url = prefetched_real_url
            last_validation_result = None

            if real_url and not d._should_skip_validation(real_url):
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
                if not d._should_skip_validation(real_url):
                    last_validation_result = self.is_download_url_valid(real_url)
                    if not last_validation_result:
                        print(f"真实链接校验未通过，先尝试直接下载: {file_info['name']}")
                else:
                    print("已启用自适应策略：跳过直链预校验")

            success = self.download_with_requests(real_url, file_path, clean_filename)
            if success:
                if last_validation_result is False:
                    d._record_validation_false_negative(real_url)
                return True

            print(f"首次直链下载失败，重新提链后重试: {file_info['name']}")
            fresh_url = self.get_real_download_url(
                file_info['link'],
                ajax_file_id=file_info.get("ajax_file_id")
            )
            if not fresh_url:
                print(f"重新提链失败，跳过该文件: {file_info['name']}")
                return False

            if not d._should_skip_validation(fresh_url):
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
        print(f"浏览器下载兜底已禁用，跳过该文件: {file_info['name']}")
        return False

    def download_single_file(self, file_info, download_dir="downloads", max_retries=3):
        d = self.d
        try:
            print(f"开始处理文件: {file_info['name']}")

            clean_filename = d.sanitize_filename(file_info['name'])
            os.makedirs(download_dir, exist_ok=True)

            expected_file = os.path.join(download_dir, clean_filename)
            if os.path.exists(expected_file):
                if d.progress_callback:
                    d.progress_callback(clean_filename, os.path.getsize(expected_file), expected_file, "跳过(已存在)", 100)
                return True

            abs_download_path = os.path.abspath(download_dir)
            d.driver.set.download_path(abs_download_path)

            d.driver.latest_tab.get(file_info['link'])
            time.sleep(8)

            download_found = False
            download_selectors = [
                'xpath://a[contains(text(), "电信") or contains(text(), "联通") or contains(text(), "移动") or contains(text(), "普通") or contains(text(), "下载")]',
                'xpath://a[contains(@class, "down") or contains(@class, "download")]',
                'xpath://a[contains(@href, "developer-oss") and contains(@href, "toolsdown")]',
                'xpath://*[contains(@onclick, "down") or contains(@onclick, "download")]',
                'css:a[href*="developer-oss"]',
            ]

            for selector in download_selectors:
                if download_found:
                    break
                try:
                    elements = d.driver.latest_tab.eles(selector, timeout=5)
                    if elements:
                        for element in elements:
                            if download_found:
                                break
                            try:
                                try:
                                    rect = element.rect
                                    width = rect.size['width']
                                    height = rect.size['height']
                                    if width > 0 and height > 0:
                                        if d.progress_callback:
                                            d.progress_callback(clean_filename, 0, expected_file, "开始下载...", 0)
                                        element.click(by_js=True)
                                        download_found = True
                                        success = self.monitor_download_progress(expected_file, clean_filename)
                                        if success and d.progress_callback:
                                            d.progress_callback(clean_filename, os.path.getsize(expected_file), expected_file, "下载完成", 100)
                                        break
                                except Exception:
                                    if d.progress_callback:
                                        d.progress_callback(clean_filename, 0, expected_file, "开始下载...", 0)
                                    element.click(by_js=True)
                                    download_found = True
                                    success = self.monitor_download_progress(expected_file, clean_filename)
                                    if success and d.progress_callback:
                                        d.progress_callback(clean_filename, os.path.getsize(expected_file), expected_file, "下载完成", 100)
                                    break
                            except Exception:
                                continue
                    if download_found:
                        break
                except Exception:
                    continue

            if not download_found:
                all_links = d.driver.latest_tab.eles('tag:a')
                for link in all_links:
                    if download_found:
                        break
                    try:
                        href = link.attr('href')
                        if href and ('developer-oss.lanrar.com' in href and 'toolsdown' in href):
                            try:
                                d.driver.latest_tab.download(href)
                                download_found = True
                                success = self.monitor_download_progress(expected_file, clean_filename)
                                if success and d.progress_callback:
                                    d.progress_callback(clean_filename, os.path.getsize(expected_file), expected_file, "下载完成", 100)
                                break
                            except Exception as e:
                                print(f"直接下载失败: {e}")
                                continue
                    except Exception as e:
                        print(f"处理链接时出错: {e}")
                        continue

            if not download_found:
                print(f"警告: 未能找到 {file_info['name']} 的下载链接")
                return False

            return download_found

        except Exception as e:
            print(f"下载文件 {file_info['name']} 时出错: {e}")
            return False

    def monitor_download_progress(self, expected_file, filename, timeout=60):
        d = self.d
        start_time = time.time()
        initial_size = 0
        if os.path.exists(expected_file):
            initial_size = os.path.getsize(expected_file)

        while time.time() - start_time < timeout:
            if os.path.exists(expected_file):
                current_size = os.path.getsize(expected_file)
                if current_size > initial_size:
                    if d.progress_callback:
                        progress = min(95, int((current_size - initial_size) * 100 / (initial_size + current_size + 1)))
                        d.progress_callback(filename, current_size, expected_file, "下载中...", progress)
                    initial_size = current_size
                elif current_size > 0:
                    if d.progress_callback:
                        d.progress_callback(filename, current_size, expected_file, "下载完成", 100)
                    return True
            time.sleep(1)

        if os.path.exists(expected_file) and os.path.getsize(expected_file) > 0:
            if d.progress_callback:
                d.progress_callback(filename, os.path.getsize(expected_file), expected_file, "下载完成", 100)
            return True

        return False
