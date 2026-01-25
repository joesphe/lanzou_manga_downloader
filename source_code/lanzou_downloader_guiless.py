import time
import os
import sys
import requests
import threading
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from DrissionPage import Chromium, ChromiumOptions, SessionOptions
from tqdm import tqdm
import json

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
        logging.StreamHandler()  # 控制台输出
    ]
)
logger = logging.getLogger(__name__)

class LanzouDownloader:
    # 硬编码的默认链接和密码
    DEFAULT_URL = "https://wwzc.lanzoub.com/b00tc1sz4b"
    DEFAULT_PASSWORD = "8255"
    
    def __init__(self, chrome_driver_path=None, edge_driver_path=None, headless=True, max_workers=3, browser="edge", browser_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", default_url=None, default_password=None):
        self.chrome_driver_path = chrome_driver_path
        self.edge_driver_path = edge_driver_path
        self.headless = headless
        self.max_workers = max_workers
        self.browser = "edge"  # 固定使用Edge浏览器
        self.browser_path = browser_path  # 浏览器路径，默认为Edge
        self.default_url = default_url or self.DEFAULT_URL
        self.default_password = default_password or self.DEFAULT_PASSWORD
        self.files = []
        self.driver = None
        
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
        
        # 如果启用无头模式，使用官方推荐的headless()方法
        if self.headless:
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
                    print(f"{i}. {file_name} ({file_size}) - {file_time}")
                    
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
        
    def select_files_for_download(self):
        """让用户选择要下载的文件"""
        if not self.files:
            print("没有可下载的文件")
            return []
            
        print("\n请选择要下载的文件:")
        print("输入格式: 单个文件编号 或 1,3,5 或 1-5 或 1,3-5,7")
        print("例如: 1 或 1,3,5 或 1-10")
        
        selection = input("请输入选择: ").strip()
        
        if not selection:
            return []
            
        selected_indices = []
        
        # 解析用户输入
        parts = selection.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                # 范围选择
                try:
                    start, end = map(int, part.split('-'))
                    selected_indices.extend(range(start, end + 1))
                except ValueError:
                    print(f"无效的范围格式: {part}")
            else:
                # 单个文件
                try:
                    selected_indices.append(int(part))
                except ValueError:
                    print(f"无效的文件编号: {part}")
                    
        # 验证选择的索引
        valid_indices = []
        for idx in selected_indices:
            if 1 <= idx <= len(self.files):
                valid_indices.append(idx)
            else:
                print(f"警告: 文件编号 {idx} 超出范围 (1-{len(self.files)})")
                
        # 去重并排序
        valid_indices = sorted(list(set(valid_indices)))
        
        # 返回选中的文件
        selected_files = [self.files[idx - 1] for idx in valid_indices]
        
        print(f"\n您选择了 {len(selected_files)} 个文件:")
        for file_info in selected_files:
            print(f"{file_info['index']}. {file_info['name']} ({file_info['size']})")
            
        return selected_files
        
    def get_download_url(self, file_link, max_retries=3):
        """获取文件的真实下载URL - 简化版本
        注意：实际下载逻辑已集成到download_single_file函数中
        此函数保持向后兼容，返回原始链接
        """
        print("提示: get_download_url函数已简化，实际下载逻辑已集成到download_single_file函数中")
        return file_link
                
    def download_single_file(self, file_info, download_dir="downloads", max_retries=3):
        """使用浏览器直接下载单个文件"""
        try:
            logger.info(f"开始处理文件: {file_info['name']}")
            print(f"\n正在处理: {file_info['name']}")
            
            # 清理文件名
            clean_filename = self.sanitize_filename(file_info['name'])
            
            # 确保下载目录存在
            os.makedirs(download_dir, exist_ok=True)
            
            # 检查文件是否已经存在，如果存在则跳过下载
            expected_file = os.path.join(download_dir, clean_filename)
            if os.path.exists(expected_file):
                print(f"✓ 文件已存在，跳过下载: {clean_filename}")
                return True
            
            # 设置下载路径
            abs_download_path = os.path.abspath(download_dir)
            self.driver.set.download_path(abs_download_path)
            
            # 验证下载路径设置（仅在调试模式下显示）
            # print(f"下载路径设置为: {abs_download_path}")
            
            # 访问文件链接
            self.driver.latest_tab.get(file_info['link'])
            print("已访问文件链接，等待页面加载...")
            time.sleep(8)  # 等待页面加载
            
            # 添加调试信息 - 查看页面完整结构
            print(f"当前页面URL: {self.driver.latest_tab.url}")
            print(f"页面标题: {self.driver.latest_tab.title}")
            
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
                        # print(f"找到 {len(elements)} 个匹配 '{selector}' 的下载元素")  # 注释掉调试信息
                        for element in elements:
                            if download_found:  # 如果已经下载成功，则跳出循环
                                break
                            try:
                                # print(f"尝试点击下载元素: {element.text[:30]}... - {element.tag} {element.attrs}")  # 注释掉调试信息
                                
                                # 检查元素是否可见且可点击
                                try:
                                    rect = element.rect
                                    width = rect.size['width']
                                    height = rect.size['height']
                                    if width > 0 and height > 0:
                                        print(f"正在下载: {clean_filename}")
                                        element.click(by_js=True)  # 使用JavaScript点击
                                        # 标记已经开始下载，避免重复点击
                                        download_found = True
                                        
                                        # 等待下载完成并显示进度
                                        success = self.monitor_download_progress(expected_file, clean_filename)
                                        if success:
                                            print(f"✓ 文件下载成功: {clean_filename}")
                                        break  # 点击后立即跳出，不再尝试同类型下载
                                    else:
                                        # 元素尺寸为0，跳过
                                        pass
                                except:
                                    # 如果无法获取元素尺寸，仍然尝试点击（兼容旧版本或特殊元素）
                                    print(f"正在下载: {clean_filename}")
                                    element.click(by_js=True)  # 使用JavaScript点击
                                    # 标记已经开始下载，避免重复点击
                                    download_found = True
                                    
                                    # 等待下载完成并显示进度
                                    success = self.monitor_download_progress(expected_file, clean_filename)
                                    if success:
                                        print(f"✓ 文件下载成功: {clean_filename}")
                                    break  # 点击后立即跳出，不再尝试同类型下载
                            except Exception as e:
                                # print(f"点击下载元素时出错: {e}")  # 注释掉调试信息
                                continue
                    if download_found:
                        break
                except Exception as e:
                    # print(f"查找下载元素时出错 ({selector}): {e}")  # 注释掉调试信息
                    continue
            
            # 如果仍没有找到下载链接，尝试直接下载
            if not download_found:
                # print("尝试直接下载...")  # 注释掉调试信息
                # 查找所有包含实际下载链接的元素
                all_links = self.driver.latest_tab.eles('tag:a')
                for link in all_links:
                    if download_found:  # 如果已经下载成功，则跳出循环
                        break
                    try:
                        href = link.attr('href')
                        if href and ('developer-oss.lanrar.com' in href and 'toolsdown' in href):
                            # print(f"找到直接下载链接: {href[:50]}...")  # 注释掉调试信息
                            # 直接下载文件 - 使用更可靠的方法
                            try:
                                # 先记录下载前的文件列表
                                initial_files = set(os.listdir(download_dir))
                                
                                # 使用Tab的download方法，只提供URL，不指定路径
                                download_id = self.driver.latest_tab.download(href)
                                # print(f"✓ 已发送下载请求，ID: {download_id}")  # 注释掉调试信息
                                
                                # 标记已经开始下载，避免重复下载
                                download_found = True
                                
                                # 等待下载完成并显示进度
                                success = self.monitor_download_progress(expected_file, clean_filename)
                                if success:
                                    print(f"✓ 文件下载成功: {clean_filename}")
                                break  # 下载请求发出后立即跳出，不再尝试其他链接
                                
                            except Exception as download_error:
                                # print(f"直接下载失败: {download_error}")  # 注释掉调试信息
                                # 尝试通过点击链接的方式
                                try:
                                    link.click(by_js=True)
                                    # 标记已经开始下载，避免重复点击
                                    download_found = True
                                    
                                    # 等待下载完成并显示进度
                                    success = self.monitor_download_progress(expected_file, clean_filename)
                                    if success:
                                        print(f"✓ 文件下载成功: {clean_filename}")
                                    break  # 点击后立即跳出，不再尝试其他链接
                                except Exception as click_error:
                                    # print(f"点击下载也失败: {click_error}")  # 注释掉调试信息
                                    continue
                    except Exception as e:
                        # print(f"处理下载链接时出错: {e}")  # 注释掉调试信息
                        continue
            
            if download_found:
                print(f"✓ 成功处理文件: {file_info['name']}")
                return True
            else:
                print(f"✗ 未能下载文件: {file_info['name']}")
                return False
                
        except Exception as e:
            error_msg = f"下载文件 {file_info['name']} 时出错: {e}"
            print(error_msg)
            logger.error(error_msg)
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
        
        # 创建进度条
        pbar = tqdm(
            desc=f"下载 {clean_filename}",
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            leave=False  # 不保留进度条在输出后
        )
        
        try:
            # 等待文件开始下载（最多等待10秒）
            print(f"等待下载开始...")
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
                    
                    # 更新进度条
                    size_diff = current_size - last_size
                    pbar.update(size_diff)
                    pbar.set_postfix({
                        '大小': f'{current_size / (1024*1024):.2f}MB',
                        '速度': speed_str
                    })
                    
                    # 检查文件大小是否稳定（不再增长）
                    if current_size == last_size and current_size > 0:
                        stable_count += 1
                        if stable_count >= max_stable_count:
                            # 文件大小连续稳定多次，认为下载完成
                            pbar.total = current_size
                            pbar.n = current_size
                            pbar.refresh()
                            pbar.close()
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
            
            # 超时，关闭进度条
            pbar.close()
            return False
            
        except KeyboardInterrupt:
            pbar.close()
            raise
        except Exception as e:
            pbar.close()
            print(f"监控下载进度时出错: {e}")
            return False

    def download_files_concurrent(self, selected_files, download_dir="downloads"):
        """并发下载选中的文件"""
        if not selected_files:
            print("没有选中的文件")
            return
            
        # 创建下载目录
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            
        print(f"\n开始并发下载 {len(selected_files)} 个文件，最大并发数: {self.max_workers}...")
        
        # 使用线程池并发下载
        success_count = 0
        failed_files = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有下载任务
            future_to_file = {
                executor.submit(self.download_single_file, file_info, download_dir): file_info 
                for file_info in selected_files
            }
            
            # 等待所有任务完成
            for future in as_completed(future_to_file):
                file_info = future_to_file[future]
                try:
                    if future.result():
                        success_count += 1
                    else:
                        failed_files.append(file_info['name'])
                except Exception as e:
                    print(f"下载 {file_info['name']} 时发生异常: {e}")
                    failed_files.append(file_info['name'])
        
        print(f"\n下载完成! 成功下载 {success_count}/{len(selected_files)} 个文件")
        
        if failed_files:
            print(f"\n以下文件下载失败:")
            for file_name in failed_files:
                print(f"  - {file_name}")
            
            # 询问用户是否要重试失败的文件
            retry = input("\n是否要重试下载失败的文件? (y/n): ").strip().lower()
            if retry == 'y' or retry == 'yes':
                print("重新下载失败的文件...")
                # 重新筛选出失败的文件信息
                retry_files = [f for f in selected_files if f['name'] in failed_files]
                self.download_files_concurrent(retry_files, download_dir)
        
    def close(self):
        """关闭浏览器"""
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
            except:
                pass  # 如果浏览器已经关闭，忽略错误


def main():
    """主函数，使用硬编码的链接和密码"""
    print("=" * 60)
    print("蓝奏云漫画下载器")
    print("=" * 60)
    
    # 创建下载器实例，使用硬编码的默认值
    downloader = LanzouDownloader(
        headless=True,  # 默认就是无头模式运行
        max_workers=3
    )
    
    try:
        # 启动浏览器
        print("\n正在启动浏览器...")
        downloader.setup_driver()
        print("浏览器启动成功!")
        
        # 使用硬编码的链接和密码获取文件列表
        print(f"\n正在使用硬编码链接: {downloader.default_url}")
        print("正在获取文件列表...")
        downloader.login_and_get_files()
        
        if not downloader.files:
            print("错误: 没有找到任何文件")
            return
        
        # 让用户选择要下载的文件
        print("\n开始选择文件...")
        selected_files = downloader.select_files_for_download()
        
        if not selected_files:
            print("没有选择任何文件，退出程序")
            return
        
        # 开始下载选定的文件
        print(f"\n开始下载 {len(selected_files)} 个文件...")
        successful_downloads = 0
        
        for file_info in selected_files:
            print(f"\n正在下载: {file_info['name']}")
            success = downloader.download_single_file(file_info)
            if success:
                successful_downloads += 1
                print(f"✓ {file_info['name']} 下载成功!")
            else:
                print(f"✗ {file_info['name']} 下载失败!")
        
        print(f"\n下载完成! 成功下载 {successful_downloads}/{len(selected_files)} 个文件")
        
    except KeyboardInterrupt:
        print("\n\n用户取消操作")
    except Exception as e:
        print(f"程序执行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 确保浏览器被关闭
        if hasattr(downloader, 'driver'):
            try:
                downloader.driver.quit()
                print("\n浏览器已关闭")
            except:
                pass


if __name__ == "__main__":
    main()