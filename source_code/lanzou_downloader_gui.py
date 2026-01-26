import time
import os
import sys
import requests
import threading
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from DrissionPage import Chromium, ChromiumOptions, SessionOptions
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import base64
import hashlib

# 配置日志
# 创建logs目录（如果不存在）
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 生成带时间戳的日志文件名
import datetime
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"lanzou_downloader_{timestamp}.log"
log_filepath = os.path.join(log_dir, log_filename)

# 配置日志格式
log_format = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler(log_filepath, encoding='utf-8'),
        # 在GUI版本中，我们不会直接输出到控制台
    ]
)
logger = logging.getLogger(__name__)


class LanzouDownloader:
    def __init__(self, chrome_driver_path=None, edge_driver_path=None, headless=True, max_workers=3, browser="edge", 
                 browser_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", default_url=None, 
                 default_password=None):
        # 检查是否为打包后的exe（生产环境）
        if getattr(sys, 'frozen', False):
            # 生产环境：使用混淆解密
            if default_url is None or default_password is None:
                self.default_url, self.default_password = self._get_obfuscated_credentials()
            else:
                self.default_url = default_url
                self.default_password = default_password
        else:
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
        
    def login_and_get_files(self, url=None, password=None):
        """登录并获取文件列表"""
        # 如果没有传入url和password，则使用默认值
        url = url or self.default_url
        password = password or self.default_password
        
        try:
            logger.info(f"正在访问链接: {url}")
            # 访问链接 - 使用正确的DrissionPage API
            self.driver.latest_tab.get(url)
            time.sleep(3)
            
            # 输入密码
            logger.info("正在输入密码")
            # 等待密码输入框出现
            self.driver.latest_tab.wait.ele_displayed('xpath://input[@id="pwd"]', timeout=10)
            password_input = self.driver.latest_tab.ele('xpath://input[@id="pwd"]')
            if password_input:
                password_input.clear(by_js=True)
                password_input.input(password)
            else:
                raise Exception("未找到密码输入框")
            
            # 点击提交按钮
            logger.info("正在提交密码")
            # 等待提交按钮出现 - 实际上是input元素，不是button
            self.driver.latest_tab.wait.ele_displayed('xpath://input[@id="sub"]', timeout=10)
            submit_button = self.driver.latest_tab.ele('xpath://input[@id="sub"]')
            if submit_button:
                submit_button.click(by_js=True)
            else:
                raise Exception("未找到提交按钮")
            
            # 等待页面加载完成
            logger.info("等待页面加载完成")
            time.sleep(5)
            
            # 获取文件列表
            # 等待文件容器出现
            self.driver.latest_tab.wait.ele_displayed('xpath://div[@id="infos"]', timeout=10)
            files_container = self.driver.latest_tab.ele('xpath://div[@id="infos"]')
            if not files_container:
                raise Exception("未找到文件容器")
            
            # 等待文件元素加载 - 使用更稳定的等待方式
            file_elements = []
            for _ in range(10):  # 最多重试10次
                file_elements = files_container.eles('xpath:.//div[@id="ready"]')
                if file_elements:
                    break
                time.sleep(1)
            
            print(f"找到 {len(file_elements)} 个文件:")
            logger.info(f"找到 {len(file_elements)} 个文件")
            
            for i, file_element in enumerate(file_elements, 1):
                try:
                    # 等待元素完全加载后再操作
                    # 获取文件名和下载链接
                    # 等待名称元素出现
                    self.driver.latest_tab.wait.ele_displayed('xpath:.//div[@id="name"]', timeout=5)
                    name_element = file_element.ele('xpath:.//div[@id="name"]')
                    if name_element:
                        link_element = name_element.ele('tag:a', timeout=5)
                        
                        if link_element:
                            file_name = link_element.text
                            file_link = link_element.attr('href')
                        else:
                            raise Exception("未找到文件链接")
                    else:
                        raise Exception("未找到文件名元素")
                    
                    # 获取文件大小
                    self.driver.latest_tab.wait.ele_displayed('xpath:.//div[@id="size"]', timeout=5)
                    size_element = file_element.ele('xpath:.//div[@id="size"]', timeout=5)
                    file_size = size_element.text if size_element else "未知大小"
                    
                    # 获取文件时间
                    self.driver.latest_tab.wait.ele_displayed('xpath:.//div[@id="time"]', timeout=5)
                    time_element = file_element.ele('xpath:.//div[@id="time"]', timeout=5)
                    file_time = time_element.text if time_element else "未知时间"
                    
                    file_info = {
                        "index": i,
                        "name": file_name,
                        "link": file_link,
                        "size": file_size,
                        "time": file_time
                    }
                    
                    self.files.append(file_info)
                    
                except Exception as e:
                    error_msg = f"解析第 {i} 个文件时出错: {e}"
                    print(error_msg)
                    logger.error(error_msg)
                    
        except Exception as e:
            error_msg = f"获取文件列表时出错: {e}"
            print(error_msg)
            logger.error(error_msg)
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
            logger.info(f"开始处理文件: {file_info['name']}")
            
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
                                
                            except Exception as download_error:
                                # 尝试通过点击链接的方式
                                try:
                                    link.click(by_js=True)
                                    # 标记已经开始下载，避免重复点击
                                    download_found = True
                                    
                                    # 等待下载完成并显示进度
                                    success = self.monitor_download_progress(expected_file, clean_filename)
                                    if success:
                                        if self.progress_callback:
                                            self.progress_callback(clean_filename, os.path.getsize(expected_file), expected_file, "下载完成", 100)
                                    break  # 点击后立即跳出，不再尝试其他链接
                                except Exception as click_error:
                                    continue
                    except Exception as e:
                        continue
            
            if not download_found:
                if self.progress_callback:
                    self.progress_callback(clean_filename, 0, expected_file, "未找到下载链接", 0)
                return False
            
            return download_found
            
        except Exception as e:
            error_msg = f"下载文件 {file_info['name']} 时出错: {e}"
            logger.error(error_msg)
            if self.progress_callback:
                self.progress_callback(file_info['name'], 0, os.path.join(download_dir, self.sanitize_filename(file_info['name'])), f"错误: {str(e)}", 0)
            return False

    def monitor_download_progress(self, expected_file, clean_filename, timeout=90):
        """
        监控下载进度并显示进度条
        :param expected_file: 期望的文件路径
        :param clean_filename: 文件名（用于显示）
        :param timeout: 超时时间（秒）
        :return: 是否成功下载
        """
        start_time = time.time()
        last_size = 0
        stable_count = 0  # 文件大小稳定计数器
        max_stable_count = 3  # 大小稳定多少次后认为下载完成
        size_history = []  # 记录文件大小历史，用于判断下载速度
        max_history_length = 5  # 保留最近5次的大小记录
        initial_size = 0  # 初始文件大小
        
        # 如果文件已存在，记录初始大小
        if os.path.exists(expected_file):
            initial_size = os.path.getsize(expected_file)
        
        try:
            # 等待文件开始下载（最多等待10秒）
            wait_start = time.time()
            while time.time() - wait_start < 10:
                if os.path.exists(expected_file):
                    break
                time.sleep(0.1)
            else:
                # 即使超过10秒还没开始下载，也要继续监控
                pass
            
            # 开始监控下载进度
            while time.time() - start_time < timeout:
                if os.path.exists(expected_file):
                    current_size = os.path.getsize(expected_file)
                    
                    # 更新文件大小历史记录
                    size_history.append(current_size)
                    if len(size_history) > max_history_length:
                        size_history.pop(0)  # 移除最旧的记录
                    
                    # 计算下载速度（基于历史记录）
                    if len(size_history) >= 2:
                        time_elapsed = min(1.0, len(size_history) * 0.5)  # 基于采样间隔计算时间
                        size_change = size_history[-1] - size_history[0]
                        speed = size_change / time_elapsed if time_elapsed > 0 else 0
                        speed_str = f"{speed / 1024:.1f}KB/s" if speed > 0 else "0B/s"
                    else:
                        speed_str = "计算中..."
                    
                    # 更新进度回调
                    if self.progress_callback:
                        # 计算下载百分比（这是一个估算，因为无法预知最终文件大小）
                        # 我们可以基于下载速度和当前大小进行动态估算
                        file_size_mb = current_size / (1024 * 1024)
                        # 更精确的进度计算 - track progress by estimating total size based on growth rate
                        estimated_progress = 0
                        if len(size_history) > 1:
                            # Estimate based on recent growth trend
                            recent_growth = size_history[-1] - size_history[0]
                            if recent_growth > 0:
                                # Simple estimation: if file grew by X in Y seconds, estimate total size
                                estimated_total = current_size + (recent_growth * 2)  # Assume similar growth
                                estimated_progress = min(100, (current_size / estimated_total) * 100)
                            else:
                                estimated_progress = min(100, (current_size / (1024 * 1024)) % 50)  # Fallback
                        else:
                            estimated_progress = 0
                        
                        self.progress_callback(clean_filename, current_size, expected_file, speed_str, estimated_progress)
                    
                    # 检查文件大小是否稳定（不再增长）
                    if current_size == last_size and current_size > 0:
                        stable_count += 1
                        if stable_count >= max_stable_count:
                            # 文件大小连续稳定多次，认为下载完成
                            if self.progress_callback:
                                self.progress_callback(clean_filename, current_size, expected_file, "完成", 100)
                            return True
                    else:
                        # 文件大小还在变化，重置稳定计数器
                        stable_count = 0
                    
                    last_size = current_size
                else:
                    # 文件还未开始下载，稍等
                    time.sleep(0.1)
                    continue
                
                time.sleep(0.5)  # 每0.5秒检查一次文件大小
            
            return False
            
        except KeyboardInterrupt:
            raise
        except Exception as e:
            # 在GUI版本中不直接打印到控制台
            logger.error(f"监控下载进度时出错: {e}")
            return False

    def download_files_concurrent(self, selected_files, download_dir="downloads", total_files_count=None):
        """并发下载选中的文件"""
        if not selected_files:
            print("没有选中的文件")
            return
            
        # 创建下载目录
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            
        print(f"\n开始并发下载 {len(selected_files)} 个文件，最大并发数: {self.max_workers}...")
        
        # 初始化下载统计（使用线程安全的锁）
        import threading
        total_files = len(selected_files)
        self.completed_files = 0
        self.success_count = 0
        self.failed_files = []
        self.progress_lock = threading.Lock()
        
        # 使用线程池并发下载
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有下载任务
            future_to_file = {
                executor.submit(self.download_single_file_with_global_progress, file_info, download_dir, total_files): file_info 
                for file_info in selected_files
            }
            
            # 等待所有任务完成
            for future in as_completed(future_to_file):
                file_info = future_to_file[future]
                try:
                    if future.result():
                        with self.progress_lock:
                            self.success_count += 1
                    else:
                        with self.progress_lock:
                            self.failed_files.append(file_info['name'])
                except Exception as e:
                    print(f"下载 {file_info['name']} 时发生异常: {e}")
                    with self.progress_lock:
                        self.failed_files.append(file_info['name'])
        
        print(f"\n下载完成! 成功下载 {self.success_count}/{len(selected_files)} 个文件")
        
        if self.failed_files:
            print(f"\n以下文件下载失败:")
            for file_name in self.failed_files:
                print(f"  - {file_name}")
        
        return self.success_count, self.failed_files
    
    def download_single_file_with_global_progress(self, file_info, download_dir, total_files_count):
        """下载单个文件并更新全局进度"""
        # 更新全局进度：开始下载此文件
        if self.global_progress_callback:
            with self.progress_lock:
                progress_percentage = (self.completed_files / total_files_count) * 100
                self.global_progress_callback(f"正在下载: {file_info['name']}", progress_percentage)
        
        result = self.download_single_file(file_info, download_dir)
        
        # 更新全局进度：此文件下载完成
        if self.global_progress_callback:
            with self.progress_lock:
                self.completed_files += 1
                progress_percentage = (self.completed_files / total_files_count) * 100
                status_text = f"{'已完成' if result else '已失败'}: {file_info['name']}"
                self.global_progress_callback(status_text, progress_percentage)
        
        return result

    def close(self):
        """关闭浏览器"""
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
            except:
                pass  # 如果浏览器已经关闭，忽略错误


class LanzouDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("蓝奏云漫画下载器")
        self.root.geometry("800x700")
        
        # 初始化下载器 - 使用固定的默认值
        # 检查是否为打包后的exe（生产环境）
        if getattr(sys, 'frozen', False):
            # 生产环境：使用混淆解密
            # 创建一个临时的LanzouDownloader实例来获取混淆凭据
            temp_downloader = LanzouDownloader()
            default_url, default_password = temp_downloader._get_obfuscated_credentials()
        else:
            # 开发环境：从环境变量读取（不提供默认值，强制用户设置环境变量）
            url_from_env = os.environ.get('LANZOU_URL')
            password_from_env = os.environ.get('LANZOU_PASSWORD')
            if not url_from_env or not password_from_env:
                raise ValueError("在开发环境中必须设置环境变量 LANZOU_URL 和 LANZOU_PASSWORD")
            default_url = url_from_env
            default_password = password_from_env
        
        self.downloader = LanzouDownloader(headless=True, default_url=default_url, default_password=default_password)  # 强制无头模式
        self.selected_files = []
        self.download_thread = None
        self.is_downloading = False
        
        self.setup_ui()
        
    def setup_ui(self):
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
        
        # 配置主框架的权重以允许扩展
        main_frame.rowconfigure(2, weight=1)  # 文件列表区域可以扩展
        
        # 绑定进度回调
        self.downloader.set_progress_callback(self.update_current_progress)
        self.downloader.set_global_progress_callback(self.update_global_progress)
        

        
    def get_files(self):
        """获取文件列表"""
        if self.is_downloading:
            messagebox.showwarning("警告", "正在下载中，请先停止下载！")
            return
            
        # 使用默认的URL和密码
        url = self.downloader.default_url
        password = self.downloader.default_password
        
        # 禁用获取按钮，防止重复点击
        self.get_files_btn.config(state=tk.DISABLED)
        
        # 启动获取文件的线程
        self.get_files_thread = threading.Thread(target=self._get_files_worker, args=(url, password))
        self.get_files_thread.daemon = True
        self.get_files_thread.start()
        
    def _get_files_worker(self, url, password):
        """获取文件的工作线程"""
        try:
            print("正在启动浏览器...")  # 在控制台输出，用户不可见
            self.downloader.setup_driver()
            print("浏览器启动成功！")
            
            print(f"正在访问链接: {url}")
            self.downloader.login_and_get_files(url, password)
            
            # 在主线程中更新UI
            self.root.after(0, self._update_file_list_ui)
            
        except Exception as e:
            error_msg = f"获取文件列表时出错: {str(e)}"
            print(error_msg)  # 在控制台输出，用户不可见
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
        finally:
            self.root.after(0, lambda: self.get_files_btn.config(state=tk.NORMAL))
    
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

    def _update_file_list_ui(self):
        """更新文件列表UI"""
        # 清空现有项目
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # 获取当前下载目录
        download_dir = self.download_dir_entry.get().strip()
        if not download_dir:
            download_dir = "downloads"
        
        # 检查哪些文件已经下载了
        downloaded_files = self.check_downloaded_files(download_dir)
        
        # 添加新文件
        for file_info in self.downloader.files:
            clean_name = self.downloader.sanitize_filename(file_info['name'])
            # 如果文件已存在，添加已下载标识
            if clean_name in downloaded_files:
                display_name = f"{file_info['name']} [已下载]"
                tag = 'downloaded'
            else:
                display_name = file_info['name']
                tag = 'unchecked'
                
            self.file_tree.insert('', tk.END, values=(
                file_info['index'],
                display_name,
                file_info['size'],
                file_info['time']
            ), tags=(tag,))
        
        # 配置Treeview样式以区分已下载文件
        self.file_tree.tag_configure('downloaded', foreground='green')
        self.file_tree.tag_configure('unchecked', foreground='black')
        
        messagebox.showinfo("成功", f"成功获取 {len(self.downloader.files)} 个文件！")
    

    

        
        self.download_btn.config(state=tk.NORMAL)
        self.log_message(f"已选择 {len(self.selected_files)} 个文件准备下载")
        messagebox.showinfo("提示", f"已选择 {len(self.selected_files)} 个文件，可以开始下载了！")
    
    def manual_refresh_files(self):
        """手动刷新文件列表，标记已下载文件"""
        self.refresh_file_list_display()
        
        # 检查是否有选中的文件，如果有则启用下载按钮
        selected_items = self.file_tree.selection()
        if selected_items:
            self.download_btn.config(state=tk.NORMAL)
        else:
            self.download_btn.config(state=tk.DISABLED)
        
        messagebox.showinfo("提示", "文件列表已刷新，已下载文件已标记")
    
    def browse_directory(self):
        """浏览并选择下载目录"""
        directory = filedialog.askdirectory(initialdir=self.download_dir_entry.get())
        if directory:
            self.download_dir_entry.delete(0, tk.END)
            self.download_dir_entry.insert(0, directory)
    
    def start_download(self):
        """开始下载"""
        if self.is_downloading:
            messagebox.showwarning("警告", "正在下载中，请先停止下载！")
            return
            
        # 获取当前在文件树中选中的项目
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先在文件列表中选择要下载的文件！")
            return
        
        # 创建下载文件信息列表
        self.selected_files = []
        for item in selected_items:
            item_values = self.file_tree.item(item)['values']
            # 找到对应的文件信息
            for file_info in self.downloader.files:
                if str(file_info['index']) == str(item_values[0]):
                    # 添加全局索引用于进度跟踪
                    file_info_with_index = file_info.copy()
                    file_info_with_index['global_index'] = len(self.selected_files) + 1
                    self.selected_files.append(file_info_with_index)
                    break
        
        download_dir = self.download_dir_entry.get().strip()
        if not download_dir:
            messagebox.showerror("错误", "请输入下载目录！")
            return
        
        # 创建下载目录
        os.makedirs(download_dir, exist_ok=True)
        
        # 设置下载器参数 - 固定为1个worker（单线下载）
        self.downloader.max_workers = 1
        
        # 禁用相关按钮，防止重复点击
        self.download_btn.config(state=tk.DISABLED)
        self.get_files_btn.config(state=tk.DISABLED)
        self.is_downloading = True
        
        # 启动下载线程
        self.download_thread = threading.Thread(
            target=self._download_worker,
            args=(self.selected_files, download_dir)
        )
        self.download_thread.daemon = True
        self.download_thread.start()
    
    def _download_worker(self, selected_files, download_dir):
        """下载工作线程"""
        try:
            # 初始化全局进度
            self.root.after(0, lambda: self.update_global_progress(f"开始下载 {len(selected_files)} 个文件", 0))
            
            # 执行下载
            success_count, failed_files = self.downloader.download_files_concurrent(
                selected_files, 
                download_dir, 
                total_files_count=len(selected_files)
            )
            
            # 下载完成，在主线程中更新UI
            def download_complete():
                self.log_message(f"下载完成！成功: {success_count}, 失败: {len(failed_files)}")
                self.download_btn.config(state=tk.NORMAL)
                self.get_files_btn.config(state=tk.NORMAL)
                self.is_downloading = False
                
                # 稍作延迟后再刷新文件列表，确保文件完全写入磁盘
                self.root.after(1000, self.refresh_file_list_display)  # 延迟1秒刷新
                
                if failed_files:
                    messagebox.showwarning("部分失败", f"下载完成，但有 {len(failed_files)} 个文件下载失败！")
                else:
                    messagebox.showinfo("成功", f"所有 {success_count} 个文件都下载成功！")
            
            self.root.after(0, download_complete)
            
        except Exception as e:
            error_msg = f"下载过程中出错: {str(e)}"
            self.log_message(error_msg)
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
            self.root.after(0, self.reset_download_state)
    
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