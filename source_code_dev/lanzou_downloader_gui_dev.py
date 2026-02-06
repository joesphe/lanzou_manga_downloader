import time
import os
import sys
import requests
import threading
import re
import threading
from DrissionPage import Chromium, ChromiumOptions, SessionOptions
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import base64
import hashlib


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
        
        try:
            print(f"正在访问链接: {url}")
            # 访问链接 - 使用正确的DrissionPage API
            self.driver.latest_tab.get(url)
            time.sleep(1)  # 减少等待时间
            
            # 输入密码
            print("正在输入密码")
            # 等待密码输入框出现
            password_input = self.driver.latest_tab.ele('xpath://input[@id="pwd"]', timeout=10)
            if password_input:
                password_input.clear(by_js=True)
                password_input.input(password)
            else:
                raise Exception("未找到密码输入框")
            
            # 点击提交按钮
            print("正在提交密码")
            # 等待提交按钮出现 - 实际上是input元素，不是button
            submit_button = self.driver.latest_tab.ele('xpath://input[@id="sub"]', timeout=10)
            if submit_button:
                submit_button.click(by_js=True)
            else:
                raise Exception("未找到提交按钮")
            
            # 等待页面加载完成
            print("等待页面加载完成")
            time.sleep(3)  # 减少等待时间
            
            # 获取文件列表
            # 等待文件容器出现
            files_container = self.driver.latest_tab.ele('xpath://div[@id="infos"]', timeout=10)
            if not files_container:
                raise Exception("未找到文件容器")
            
            # 记录初始文件数量
            prev_file_count = len(files_container.eles('xpath:.//div[@id="ready"]'))
            print(f"初始文件数量: {prev_file_count}")
            
            # 循环点击"显示更多文件"按钮，直到所有文件都加载完毕
            click_count = 0
            max_clicks = 100  # 设置足够大的最大点击次数
            
            while click_count < max_clicks:
                # 直接查找按钮，不等待
                more_button = self.driver.latest_tab.ele('xpath://div[@id="infomores"]//span[@id="filemore"]', timeout=1)
                if not more_button:
                    print("未找到'显示更多文件'按钮，可能所有文件已加载")
                    break
                
                try:
                    print(f"点击'显示更多文件'按钮第 {click_count + 1} 次")
                    # 使用JavaScript直接点击，避免元素交互问题
                    self.driver.latest_tab.run_js("document.getElementById('filemore').click();")
                    click_count += 1
                    
                    # 极短的等待时间
                    time.sleep(0.8)
                    
                    # 检查文件数量是否有变化
                    current_file_count = len(files_container.eles('xpath:.//div[@id="ready"]'))
                    if current_file_count > prev_file_count:
                        print(f"文件数量从 {prev_file_count} 增加到 {current_file_count}")
                        prev_file_count = current_file_count
                    else:
                        # 再等等看是否有延迟加载
                        time.sleep(1.5)
                        current_file_count = len(files_container.eles('xpath:.//div[@id="ready"]'))
                        if current_file_count == prev_file_count:
                            print("文件数量没有变化，可能所有文件已加载")
                            break
                        else:
                            print(f"文件数量从 {prev_file_count} 增加到 {current_file_count}")
                            prev_file_count = current_file_count
                    
                except Exception as e:
                    print(f"点击'显示更多文件'按钮时出错: {e}")
                    break
            
            print(f"共点击了 {click_count} 次'显示更多文件'按钮")
            
            # 快速获取所有文件元素
            file_elements = files_container.eles('xpath:.//div[@id="ready"]')
            print(f"找到 {len(file_elements)} 个文件:")
            
            for i, file_element in enumerate(file_elements, 1):
                try:
                    # 快速获取文件信息
                    name_element = file_element.ele('xpath:.//div[@id="name"]//a', timeout=1)
                    if name_element:
                        file_name = name_element.text
                        file_link = name_element.attr('href')
                    else:
                        continue  # 跳过无法解析的文件
                    
                    # 获取文件大小
                    size_element = file_element.ele('xpath:.//div[@id="size"]', timeout=1)
                    file_size = size_element.text if size_element else "未知大小"
                    
                    # 获取文件时间
                    time_element = file_element.ele('xpath:.//div[@id="time"]', timeout=1)
                    file_time = time_element.text if time_element else "未知时间"
                    
                    file_info = {
                        "index": i,
                        "name": file_name,
                        "link": file_link,
                        "size": file_size,
                        "time": file_time
                    }
                    
                    self.files.append(file_info)
                    
                    if i <= 50:  # 只打印前50个文件名以避免过多输出
                        print(f"  {i:3d}. {file_name} ({file_size})")
                    
                except Exception as e:
                    error_msg = f"解析第 {i} 个文件时出错: {e}"
                    print(error_msg)
                    
        except Exception as e:
            error_msg = f"获取文件列表时出错: {e}"
            print(error_msg)
            raise  # 重新抛出异常以便上层处理
            
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
        """
        使用DrissionPage获取真实的下载链接
        """
        try:
            print(f"正在获取文件的真实下载链接: {file_link}")
            
            # 访问文件详情页面
            self.driver.latest_tab.get(file_link)
            time.sleep(5)  # 等待页面完全加载
            
            # 查找真实的下载链接
            # 尝试多种可能的选择器来获取真实下载链接
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
                    elements = self.driver.latest_tab.eles(selector, timeout=3)
                    if elements:
                        for element in elements:
                            href = element.attr('href')
                            if href and ('developer-oss' in href or 'lanzoug.com' in href or 'downserver' in href):
                                print(f"找到真实下载链接: {href}")
                                return href
                except:
                    continue
            
            # 如果上面的方法都没有找到，尝试获取页面源码，从中提取链接
            page_source = self.driver.latest_tab.html
            import re
            
            # 查找可能包含真实下载链接的模式
            patterns = [
                r'https?://[^\s"<>\']*(?:developer-oss|lanzoug\.com|downserver)[^\s"<>\']*',
                r'https?://[^\s"<>\']*toolsdown[^\s"<>\']*',
                r'https?://[^\s"<>\']*\.lanzou[^\s"<>\']*'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, page_source)
                if matches:
                    # 返回第一个看起来像是真实下载链接的URL
                    for match in matches:
                        if 'developer-oss' in match or 'toolsdown' in match or 'lanzoug.com' in match:
                            print(f"从页面源码中找到真实下载链接: {match}")
                            return match
            
            print("警告: 未能找到真实下载链接")
            return None
            
        except Exception as e:
            print(f"获取真实下载链接时出错: {e}")
            return None

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
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # 获取文件总大小
            total_size = int(response.headers.get('content-length', 0))
            
            # 创建目录
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 开始下载
            downloaded_size = 0
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

    def download_single_file_optimized(self, file_info, download_dir="downloads"):
        """
        优化的下载方法：先获取真实下载链接，再用requests下载
        """
        try:
            print(f"开始优化下载流程: {file_info['name']}")
            
            # 清理文件名
            clean_filename = self.sanitize_filename(file_info['name'])
            file_path = os.path.join(download_dir, clean_filename)
            
            # 首先尝试获取真实下载链接
            real_url = self.get_real_download_url(file_info['link'])
            
            if not real_url:
                print(f"未能获取到 {file_info['name']} 的真实下载链接，回退到原方法")
                # 如果获取不到真实链接，则回退到原始的浏览器下载方法
                return self.download_single_file_legacy(file_info, download_dir)
            
            # 使用requests下载真实链接
            success = self.download_with_requests(real_url, file_path, clean_filename)
            
            return success
            
        except Exception as e:
            print(f"优化下载文件 {file_info['name']} 时出错: {e}")
            return False

    def download_single_file_legacy(self, file_info, download_dir="downloads", max_retries=3):
        """
        原始的下载方法（保留作为备选方案）
        """
        print(f"使用原始方法下载: {file_info['name']}")
        # 这里保留原始的下载逻辑
        # 为了简洁，这里只显示主要逻辑，实际实现应复制原始download_single_file方法
        return self.download_single_file(file_info, download_dir, max_retries)

    def download_multiple_files(self, selected_indices, download_dir="downloads", max_workers=None):
        """批量下载文件"""
        selected_files = [f for f in self.files if f['index'] in selected_indices]
        
        if not selected_files:
            print("没有选择任何文件")
            return []
        
        print(f"准备下载 {len(selected_files)} 个文件")
        
        # 单线程顺序下载
        results = []
        total_files = len(selected_files)
        
        for i, file_info in enumerate(selected_files):
            print(f"正在下载第 {i+1}/{total_files} 个文件: {file_info['name']}")
            
            # 使用优化的下载方法
            success = self.download_single_file_optimized(file_info, download_dir)
            results.append((file_info['name'], success))
            
            # 更新全局进度
            if self.global_progress_callback:
                progress = int(((i + 1) / total_files) * 100)
                self.global_progress_callback(f"正在下载: {file_info['name']}", progress)
        
        return results


class LanzouDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("蓝奏云漫画下载器 - 开发版")
        self.root.geometry("1000x700")
        
        # 初始化下载器实例
        self.downloader = LanzouDownloader()
        self.is_downloading = False
        
        # 设置GUI组件
        self.setup_gui()
        
        # 设置进度回调
        self.downloader.set_progress_callback(self.update_current_progress)
        self.downloader.set_global_progress_callback(self.update_global_progress)
    
    def setup_gui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置行和列的权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 获取文件按钮
        self.get_files_btn = ttk.Button(main_frame, text="获取文件列表", command=self.get_files)
        self.get_files_btn.grid(row=0, column=0, columnspan=2, pady=5)
        
        # 添加全选/取消全选按钮
        self.select_files_btn = ttk.Button(main_frame, text="全选/取消全选", command=self.toggle_select_all)
        self.select_files_btn.grid(row=1, column=0, columnspan=2, pady=5)
        self.select_files_btn.config(state=tk.DISABLED)  # 初始禁用
        
        # 文件列表框架
        files_frame = ttk.LabelFrame(main_frame, text="文件列表", padding="5")
        files_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(0, weight=1)
        
        # 添加多选提示标签
        hint_label = ttk.Label(files_frame, text="提示：按住 Ctrl 键可多选文件", foreground="gray")
        hint_label.grid(row=0, column=0, sticky=tk.W, padx=(5, 0), pady=(0, 5))
        
        # 创建Treeview来显示文件列表
        columns = ('序号', '文件名', '大小', '时间')
        self.file_tree = ttk.Treeview(files_frame, columns=columns, show='headings', height=10)
        
        # 定义列标题
        for col in columns:
            self.file_tree.heading(col, text=col)
            self.file_tree.column(col, width=150)
        
        # 添加滚动条
        tree_scroll = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.file_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        tree_scroll.grid(row=1, column=1, sticky=(tk.N, tk.S), pady=(5, 0))
        

        
        # 使用说明
        instruction_frame = ttk.LabelFrame(main_frame, text="使用说明", padding="5")
        instruction_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        instructions = [
            "1. 先点击上方的\"获取文件列表\"加载出所有可下载的文件",
            "2. 在文件列表中，单击选中你想下载的文件",
            "3. 按住ctrl键再单击可以实现多选",
            "4. 选择完毕后，点击下方\"开始下载\"按钮"
        ]
        
        for i, instruction in enumerate(instructions):
            ttk.Label(instruction_frame, text=instruction, foreground="blue").grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
        
        # 下载设置区域
        download_frame = ttk.LabelFrame(main_frame, text="下载设置", padding="5")
        download_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        download_frame.columnconfigure(1, weight=1)
        
        ttk.Label(download_frame, text="下载目录:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.download_dir_entry = ttk.Entry(download_frame)
        self.download_dir_entry.insert(0, os.path.abspath("downloads"))
        self.download_dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=5)
        
        self.browse_btn = ttk.Button(download_frame, text="浏览...", command=self.browse_directory)
        self.browse_btn.grid(row=0, column=2, padx=(5, 0), pady=5)
        
        # 开始下载按钮
        self.download_btn = ttk.Button(download_frame, text="开始下载", command=self.start_download, state=tk.DISABLED)
        self.download_btn.grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.W)
        
        # 刷新文件列表按钮
        self.refresh_btn = ttk.Button(download_frame, text="刷新文件列表", command=self.manual_refresh_files)
        self.refresh_btn.grid(row=1, column=2, padx=(5, 0), pady=5, sticky=tk.E)
        

        
        # 全局进度条
        ttk.Label(main_frame, text="总体进度:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.global_progress = ttk.Progressbar(main_frame, mode='determinate')
        self.global_progress.grid(row=5, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        
        # 当前下载状态标签
        self.global_status_label = ttk.Label(main_frame, text="准备就绪")
        self.global_status_label.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 单个文件进度显示
        ttk.Label(main_frame, text="当前文件进度:").grid(row=7, column=0, sticky=tk.W, pady=5)
        self.current_progress = ttk.Progressbar(main_frame, mode='determinate')
        self.current_progress.grid(row=7, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        
        # 当前文件状态标签
        self.current_status_label = ttk.Label(main_frame, text="等待下载")
        self.current_status_label.grid(row=8, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 绑定双击事件以切换选择状态
        self.file_tree.bind('<Double-1>', self.on_item_double_click)
        
        # 初始化下载目录
        self.download_dir = "downloads"
    
    def choose_download_dir(self):
        """选择下载目录"""
        dir_path = filedialog.askdirectory(initialdir=self.download_dir)
        if dir_path:
            self.download_dir = dir_path
            self.download_dir_label.config(text=f"下载目录: {self.download_dir}")
    
    def get_files(self):
        """获取文件列表"""
        try:
            # 设置为忙碌状态
            self.get_files_btn.config(state=tk.DISABLED)
            self.select_files_btn.config(state=tk.DISABLED)
            self.download_btn.config(state=tk.DISABLED)
            
            # 更新状态
            self.global_status_label.config(text="正在获取文件列表...")
            self.global_progress['value'] = 0
            
            # 设置浏览器驱动
            self.downloader.setup_driver()
            
            # 获取文件
            self.downloader.login_and_get_files()
            
            # 显示文件列表
            self.display_files()
            
            # 启用选择和下载按钮
            self.select_files_btn.config(state=tk.NORMAL)
            self.download_btn.config(state=tk.NORMAL)
            
            # 更新状态
            self.global_status_label.config(text=f"获取完成，共 {len(self.downloader.files)} 个文件")
            self.global_progress['value'] = 100
            
        except Exception as e:
            messagebox.showerror("错误", f"获取文件列表失败: {str(e)}")
            self.global_status_label.config(text="获取失败")
            self.global_progress['value'] = 0
        finally:
            # 恢复按钮状态
            self.get_files_btn.config(state=tk.NORMAL)
    
    def display_files(self):
        """显示文件列表"""
        # 清空现有项目
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # 添加文件到树形视图
        for file_info in self.downloader.files:
            self.file_tree.insert('', tk.END, values=(
                file_info['index'],
                file_info['name'],
                file_info['size'],
                file_info['time']
            ))
        
        # 保存原始文件名用于后续比较
        self.original_filenames = {f['index']: f['name'] for f in self.downloader.files}
    
    def toggle_select_all(self):
        """全选或取消全选"""
        children = self.file_tree.get_children()
        if children:
            if len(self.file_tree.selection()) == len(children):
                # 如果全部选中，则取消选择
                self.file_tree.selection_remove(children)
            else:
                # 否则全选
                self.file_tree.selection_set(children)
    
    def on_item_double_click(self, event):
        """双击项目切换选择状态"""
        item = self.file_tree.identify_row(event.y)
        if item:
            if item in self.file_tree.selection():
                self.file_tree.selection_remove(item)
            else:
                self.file_tree.selection_add(item)
    
    def browse_directory(self):
        """浏览并选择下载目录"""
        directory = filedialog.askdirectory(initialdir=self.download_dir_entry.get())
        if directory:
            self.download_dir_entry.delete(0, tk.END)
            self.download_dir_entry.insert(0, directory)
    
    def start_download(self):
        """开始下载选中的文件"""
        if self.is_downloading:
            return
        
        # 获取选中的文件索引
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要下载的文件")
            return
        
        # 获取文件索引
        selected_indices = []
        for item in selected_items:
            values = self.file_tree.item(item)['values']
            selected_indices.append(int(values[0]))
        
        # 确认下载
        if not messagebox.askyesno("确认", f"确定要下载选中的 {len(selected_indices)} 个文件吗？"):
            return
        
        # 启动下载线程
        self.is_downloading = True
        self.download_btn.config(state=tk.DISABLED)
        self.select_files_btn.config(state=tk.DISABLED)
        self.get_files_btn.config(state=tk.DISABLED)
        
        download_thread = threading.Thread(
            target=self.download_files_thread,
            args=(selected_indices, self.download_dir)
        )
        download_thread.daemon = True
        download_thread.start()
    
    def download_files_thread(self, selected_indices, download_dir):
        """下载文件的线程函数"""
        try:
            # 更新全局进度
            self.update_global_progress("开始下载...", 0)
            
            # 执行下载
            results = self.downloader.download_multiple_files(selected_indices, download_dir)
            
            # 统计结果
            successful = sum(1 for _, success in results if success)
            total = len(results)
            
            # 更新最终状态
            self.update_global_progress(f"下载完成: {successful}/{total}", 100)
            
            # 更新文件列表显示状态
            self.update_file_list_display()
            
        except Exception as e:
            print(f"下载过程中出错: {e}")
            self.update_global_progress(f"下载出错: {str(e)}", 0)
        finally:
            # 恢复界面状态
            self.root.after(0, self.reset_download_state)
    
    def update_file_list_display(self):
        """更新文件列表显示状态"""
        # 获取当前选中项
        current_selection = self.file_tree.selection()
        
        # 获取已下载的文件
        downloaded_files = set()
        if os.path.exists(self.download_dir):
            downloaded_files = set(os.listdir(self.download_dir))
        
        # 获取所有项目
        items = self.file_tree.get_children()
        
        # 更新每个项目的显示
        for item in items:
            item_values = self.file_tree.item(item)['values']
            file_index = item_values[0]
            
            # 找到对应的文件信息
            file_info = None
            for f_info in self.downloader.files:
                if str(f_info['index']) == str(file_index):
                    file_info = f_info
                    break
            
            if file_info:
                clean_name = self.downloader.sanitize_filename(file_info['name'])
                # 如果文件已存在，添加已下载标识
                if clean_name in downloaded_files:
                    display_name = f"{file_info['name']} [已下载]"
                    tag = 'downloaded'
                else:
                    display_name = file_info['name']
                    tag = 'unchecked'
                
                # 更新项目
                self.file_tree.item(item, values=(
                    file_info['index'],
                    display_name,
                    file_info['size'],
                    file_info['time']
                ), tags=(tag,))
        
        # 恢复之前的选中状态
        for item_id in current_selection:
            if item_id in self.file_tree.get_children():  # 确保项目还存在
                self.file_tree.selection_add(item_id)
    
    def check_downloaded_files(self, download_dir):
        """检查哪些文件已经下载了"""
        downloaded_files = set()
        if os.path.exists(download_dir):
            downloaded_files = {f for f in os.listdir(download_dir) if os.path.isfile(os.path.join(download_dir, f))}
        
        downloaded_file_names = set()
        for file_name in downloaded_files:
            # 检查是否与蓝奏云文件名匹配（考虑文件名被清理的情况）
            for file_info in self.downloader.files:
                clean_name = self.downloader.sanitize_filename(file_info['name'])
                if clean_name == file_name:
                    downloaded_file_names.add(clean_name)
                    break
        
        return downloaded_file_names

    def refresh_file_list_display(self):
        """刷新文件列表显示，更新已下载文件的状态"""
        # 保存当前选中的项目
        current_selection = self.file_tree.selection()
        
        # 重新获取文件列表（但不重新获取网络数据，只是更新显示）
        download_dir = self.download_dir_entry.get().strip()
        if not download_dir:
            download_dir = "downloads"
        
        # 检查哪些文件已经下载了
        downloaded_files = self.check_downloaded_files(download_dir)
        
        # 获取当前所有项目
        items = self.file_tree.get_children()
        
        # 更新每个项目的显示
        for item in items:
            item_values = self.file_tree.item(item)['values']
            file_index = item_values[0]
            
            # 找到对应的文件信息
            file_info = None
            for f_info in self.downloader.files:
                if str(f_info['index']) == str(file_index):
                    file_info = f_info
                    break
            
            if file_info:
                clean_name = self.downloader.sanitize_filename(file_info['name'])
                # 如果文件已存在，添加已下载标识
                if clean_name in downloaded_files:
                    display_name = f"{file_info['name']} [已下载]"
                    tag = 'downloaded'
                else:
                    display_name = file_info['name']
                    tag = 'unchecked'
                
                # 更新项目
                self.file_tree.item(item, values=(
                    file_info['index'],
                    display_name,
                    file_info['size'],
                    file_info['time']
                ), tags=(tag,))
        
        # 恢复之前的选中状态
        for item_id in current_selection:
            if item_id in self.file_tree.get_children():  # 确保项目还存在
                self.file_tree.selection_add(item_id)

    def manual_refresh_files(self):
        """手动刷新文件列表，标记已下载文件"""
        self.refresh_file_list_display()
        
        # 检查是否有选中的文件，如果有则启用下载按钮
        selected_items = self.file_tree.selection()
        if selected_items:
            self.download_btn.config(state=tk.NORMAL)
        else:
            self.download_btn.config(state=tk.DISABLED)

    def reset_download_state(self):
        """重置下载状态"""
        self.download_btn.config(state=tk.NORMAL)
        self.select_files_btn.config(state=tk.NORMAL)
        self.get_files_btn.config(state=tk.NORMAL)
        self.is_downloading = False
    
    def update_global_progress(self, status_text, percentage):
        """更新全局进度"""
        self.global_status_label.config(text=status_text)
        self.global_progress['value'] = percentage
    
    def update_current_progress(self, filename, current_bytes, filepath, speed, progress_percent):
        """更新当前文件进度"""
        # 更新状态文本
        size_mb = current_bytes / (1024 * 1024)
        self.current_status_label.config(text=f"{filename} - {size_mb:.2f}MB, 速度: {speed}")
        
        # 更新进度条
        self.current_progress['value'] = progress_percent
    
    def on_closing(self):
        """窗口关闭事件"""
        if self.is_downloading:
            if messagebox.askokcancel("确认", "正在下载中，确定要退出吗？"):
                # 关闭浏览器
                if hasattr(self.downloader, 'driver'):
                    try:
                        self.downloader.driver.quit()
                    except:
                        pass
                self.root.destroy()
        else:
            # 关闭浏览器
            if hasattr(self.downloader, 'driver'):
                try:
                    self.downloader.driver.quit()
                except:
                    pass
            self.root.destroy()


def main():
    root = tk.Tk()
    app = LanzouDownloaderGUI(root)
    
    # 设置窗口关闭事件
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # 启动GUI
    root.mainloop()


if __name__ == "__main__":
    main()