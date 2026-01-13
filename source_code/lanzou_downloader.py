import time
import os
import sys
import requests
import threading
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
    def __init__(self, chrome_driver_path=None, edge_driver_path=None, headless=True, max_workers=3, browser="chrome"):
        self.chrome_driver_path = chrome_driver_path
        self.edge_driver_path = edge_driver_path
        self.headless = headless
        self.max_workers = max_workers
        self.browser = browser.lower()  # "chrome" or "edge"
        self.files = []
        
    def setup_driver(self):
        """设置浏览器驱动"""
        if self.browser == "edge" and self.edge_driver_path:
            options = EdgeOptions()
            service = EdgeService(self.edge_driver_path)
            if self.headless:
                options.add_argument('--headless')
            # 禁用日志和警告信息
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-logging')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--silent')
            options.add_argument('--log-level=3')  # 禁用日志输出 (0=INFO, 1=WARNING, 2=ERROR, 3=FATAL)
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_experimental_option('useAutomationExtension', False)
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            self.driver = webdriver.Edge(service=service, options=options)
        else:
            # 默认使用Chrome
            options = ChromeOptions()
            service = ChromeService(self.chrome_driver_path) if self.chrome_driver_path else None
            if self.headless:
                options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--window-size=1920,1080')
            # 禁用日志和警告信息
            options.add_argument('--disable-logging')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--silent')
            options.add_experimental_option('useAutomationExtension', False)
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            if service:
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                self.driver = webdriver.Chrome(options=options)
        
    def login_and_get_files(self, url, password):
        """登录并获取文件列表"""
        try:
            logger.info(f"正在访问链接: {url}")
            # 访问链接
            self.driver.get(url)
            time.sleep(3)
            
            # 输入密码
            logger.info("正在输入密码")
            password_input = self.driver.find_element(By.ID, "pwd")
            password_input.send_keys(password)
            
            # 点击提交按钮
            logger.info("正在提交密码")
            submit_button = self.driver.find_element(By.ID, "sub")
            submit_button.click()
            
            # 等待页面加载完成
            logger.info("等待页面加载完成")
            time.sleep(5)
            
            # 获取文件列表
            files_container = self.driver.find_element(By.ID, "infos")
            file_elements = files_container.find_elements(By.XPATH, ".//div[@id='ready']")
            
            print(f"找到 {len(file_elements)} 个文件:")
            logger.info(f"找到 {len(file_elements)} 个文件")
            
            for i, file_element in enumerate(file_elements, 1):
                try:
                    # 获取文件名和下载链接
                    name_element = file_element.find_element(By.ID, "name")
                    link_element = name_element.find_element(By.TAG_NAME, "a")
                    
                    file_name = link_element.text
                    file_link = link_element.get_attribute("href")
                    
                    # 获取文件大小
                    size_element = file_element.find_element(By.ID, "size")
                    file_size = size_element.text
                    
                    # 获取文件时间
                    time_element = file_element.find_element(By.ID, "time")
                    file_time = time_element.text
                    
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
            
            # 尝试多次下载
            for attempt in range(max_retries):
                driver = None
                try:
                    logger.info(f"第 {attempt + 1} 次尝试下载文件: {file_info['name']}")
                    
                    # 根据配置选择浏览器类型
                    if self.browser == "edge" and self.edge_driver_path:
                        options = EdgeOptions()
                        service = EdgeService(self.edge_driver_path)
                        if self.headless:
                            options.add_argument('--headless')
                        # 禁用日志和警告信息
                        options.add_argument('--disable-gpu')
                        options.add_argument('--no-sandbox')
                        options.add_argument('--window-size=1920,1080')
                        options.add_argument('--disable-logging')
                        options.add_argument('--disable-dev-shm-usage')
                        options.add_argument('--silent')
                        options.add_argument('--log-level=3')  # 禁用日志输出
                        options.add_argument('--disable-extensions')
                        options.add_argument('--disable-plugins')
                        options.add_experimental_option('useAutomationExtension', False)
                        options.add_experimental_option("excludeSwitches", ["enable-automation"])
                        options.add_experimental_option('excludeSwitches', ['enable-logging'])
                        # 设置下载目录
                        prefs = {
                            "download.default_directory": os.path.abspath(download_dir),
                            "download.prompt_for_download": False,
                            "download.directory_upgrade": True,
                            "safebrowsing.enabled": True
                        }
                        options.add_experimental_option("prefs", prefs)
                        driver = webdriver.Edge(service=service, options=options)
                    else:
                        # 默认使用Chrome
                        options = ChromeOptions()
                        service = ChromeService(self.chrome_driver_path) if self.chrome_driver_path else None
                        if self.headless:
                            options.add_argument('--headless')
                        options.add_argument('--disable-gpu')
                        options.add_argument('--no-sandbox')
                        options.add_argument('--window-size=1920,1080')
                        # 禁用日志和警告信息
                        options.add_argument('--disable-logging')
                        options.add_argument('--disable-dev-shm-usage')
                        options.add_argument('--silent')
                        options.add_experimental_option('useAutomationExtension', False)
                        options.add_experimental_option("excludeSwitches", ["enable-automation"])
                        # 设置下载目录
                        prefs = {
                            "download.default_directory": os.path.abspath(download_dir),
                            "download.prompt_for_download": False,
                            "download.directory_upgrade": True,
                            "safebrowsing.enabled": True
                        }
                        options.add_experimental_option("prefs", prefs)
                        if service:
                            driver = webdriver.Chrome(service=service, options=options)
                        else:
                            driver = webdriver.Chrome(options=options)
                    
                    # 访问文件链接
                    driver.get(file_info['link'])
                    print("已访问文件链接，等待页面加载...")
                    time.sleep(10)  # 延长等待时间
                    
                    # 等待加载动画消失
                    try:
                        WebDriverWait(driver, 15).until(
                            EC.invisibility_of_element_located((By.ID, "load2"))
                        )
                        print("加载动画已消失")
                    except Exception as e:
                        print(f"等待加载动画消失超时: {e}")
                    
                    # 添加调试信息 - 查看页面完整结构
                    print("\n=== 页面调试信息 ===")
                    print(f"页面标题: {driver.title}")
                    print(f"当前URL: {driver.current_url}")
                    
                    # 查看页面源码（前1000字符）
                    print("\n页面源码前1000字符:")
                    page_source = driver.page_source
                    print(page_source[:1000])
                    
                    # 查找所有iframe
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    print(f"\n找到 {len(iframes)} 个iframe")
                    
                    # 尝试切换到iframe查看内容
                    for i, iframe in enumerate(iframes):
                        try:
                            print(f"\n切换到iframe {i+1}...")
                            driver.switch_to.frame(iframe)
                            
                            # 查看iframe内容
                            iframe_source = driver.page_source
                            print(f"iframe {i+1} 源码前500字符:")
                            print(iframe_source[:500])
                            
                            # 查找iframe中的下载元素
                            iframe_elems = driver.find_elements(By.XPATH, "//*[@onclick or contains(@class, 'submit') or contains(@class, 'goto') or contains(text(), '下载') or contains(text(), '验证')]")
                            print(f"在iframe {i+1} 中找到 {len(iframe_elems)} 个可点击元素")
                            
                            # 切回主文档
                            driver.switch_to.default_content()
                        except Exception as e:
                            print(f"处理iframe {i+1} 时出错: {e}")
                            driver.switch_to.default_content()
                            continue
                    
                    # 查找并点击所有可能的下载按钮
                    download_found = False
                    
                    # 查找所有iframe
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    
                    # 处理iframe中的下载链接
                    for iframe in iframes:
                        try:
                            print("\n=== 处理iframe中的下载链接 ===")
                            # 切换到iframe
                            driver.switch_to.frame(iframe)
                            
                            # 在iframe中查找下载链接
                            print("在iframe中查找下载链接...")
                            
                            # 查找所有a标签
                            all_links = driver.find_elements(By.TAG_NAME, "a")
                            print(f"在iframe中找到 {len(all_links)} 个链接")
                            
                            # 查找所有带有href属性的元素
                            for link in all_links:
                                try:
                                    href = link.get_attribute("href")
                                    if href and href.startswith("http"):
                                        text = link.text.strip()
                                        print(f"找到链接: '{text}' -> {href}")
                                        
                                        # 检查是否为下载链接
                                        if "developer-oss" in href or "file" in href or any(ext in href for ext in [".zip", ".rar", ".exe", ".pdf"]):
                                            print(f"✓ 找到下载链接: {href}")
                                            
                                            # 尝试直接访问下载链接
                                            print("尝试直接访问下载链接...")
                                            driver.get(href)
                                            print("已访问下载链接，等待下载开始...")
                                            time.sleep(15)  # 等待下载完成
                                            
                                            # 检查文件是否已下载
                                            expected_file = os.path.join(download_dir, clean_filename)
                                            if os.path.exists(expected_file):
                                                print(f"✓ 文件已下载: {expected_file}")
                                                print(f"✓ 文件大小: {os.path.getsize(expected_file)} 字节")
                                                download_found = True
                                                break
                                            
                                            # 检查是否有其他可能的文件名（如临时文件名）
                                            for filename in os.listdir(download_dir):
                                                if filename.endswith(('.zip', '.rar', '.exe', '.pdf')):
                                                    full_path = os.path.join(download_dir, filename)
                                                    file_size = os.path.getsize(full_path)
                                                    if file_size > 1024:  # 排除太小的文件
                                                        print(f"✓ 找到可能的下载文件: {full_path}")
                                                        print(f"✓ 文件大小: {file_size} 字节")
                                                        # 重命名为正确的文件名
                                                        os.rename(full_path, expected_file)
                                                        download_found = True
                                                        break
                                            
                                            if download_found:
                                                break
                                except Exception as e:
                                    print(f"处理链接时出错: {e}")
                                    continue
                            
                            if download_found:
                                break
                            
                            # 切回主文档
                            driver.switch_to.default_content()
                        except Exception as e:
                            print(f"处理iframe时出错: {e}")
                            driver.switch_to.default_content()
                            continue
                    
                    # 如果在iframe中没有找到，尝试在主文档中查找
                    if not download_found:
                        print("\n=== 在主文档中查找下载链接 ===")
                        
                        # 切回主文档
                        driver.switch_to.default_content()
                        
                        # 查找所有a标签
                        all_links = driver.find_elements(By.TAG_NAME, "a")
                        print(f"在主文档中找到 {len(all_links)} 个链接")
                        
                        for link in all_links:
                            try:
                                href = link.get_attribute("href")
                                if href and href.startswith("http"):
                                    text = link.text.strip()
                                    print(f"找到链接: '{text}' -> {href}")
                                    
                                    # 检查是否为下载链接
                                    if "developer-oss" in href or "file" in href or any(ext in href for ext in [".zip", ".rar", ".exe", ".pdf"]):
                                        print(f"✓ 找到下载链接: {href}")
                                        
                                        # 尝试直接访问下载链接
                                        driver.get(href)
                                        print("已访问下载链接，等待下载开始...")
                                        time.sleep(15)
                                        
                                        # 检查文件是否已下载
                                        expected_file = os.path.join(download_dir, clean_filename)
                                        if os.path.exists(expected_file):
                                            print(f"✓ 文件已下载: {expected_file}")
                                            print(f"✓ 文件大小: {os.path.getsize(expected_file)} 字节")
                                            download_found = True
                                            break
                            except Exception as e:
                                print(f"处理链接时出错: {e}")
                                continue
                    
                    if download_found:
                        success_msg = f"{clean_filename} 下载完成!"
                        print(f"\n{success_msg}")
                        logger.info(success_msg)
                        return True
                    else:
                        print(f"第 {attempt + 1} 次尝试下载未找到文件")
                        
                except Exception as e:
                    error_msg = f"第 {attempt + 1} 次下载 {file_info['name']} 时出错: {e}"
                    print(f"\n{error_msg}")
                    logger.error(error_msg)
                finally:
                    if driver:
                        driver.quit()
                
                if attempt < max_retries - 1:
                    retry_msg = f"等待3秒后进行第 {attempt + 2} 次重试..."
                    print(retry_msg)
                    logger.info(retry_msg)
                    time.sleep(3)
            
            fail_msg = f"经过 {max_retries} 次尝试后下载仍然失败"
            print(fail_msg)
            logger.error(fail_msg)
            return False
            
        except Exception as e:
            error_msg = f"下载文件 {file_info['name']} 时发生未知错误: {e}"
            print(f"\n{error_msg}")
            logger.error(error_msg)
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
        if hasattr(self, 'driver'):
            self.driver.quit()

def main():
    while True:
        # 初始化下载器，支持Chrome和Edge浏览器
        # 使用相对路径，假设驱动文件与脚本在同一目录或子目录中
        # 检查是否在PyInstaller环境中运行
        if getattr(sys, 'frozen', False):
            # 如果是打包后的exe，驱动文件应该在exe同目录下的相应子目录中
            # 获取exe文件所在的目录
            current_dir = os.path.dirname(sys.executable)
        else:
            # 如果是直接运行的Python脚本
            current_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
            
        chrome_driver_path = os.path.join(current_dir, 'chromedriver-win64', 'chromedriver.exe')
        edge_driver_path = os.path.join(current_dir, 'edgedriver_win64', 'msedgedriver.exe')
        
        # 检查驱动文件是否存在，如果不存在则尝试使用系统PATH中的驱动
        if not os.path.exists(chrome_driver_path):
            print(f"警告: 未找到Chrome驱动文件 {chrome_driver_path}")
            chrome_driver_path = None
            
        if not os.path.exists(edge_driver_path):
            print(f"警告: 未找到Edge驱动文件 {edge_driver_path}")
            edge_driver_path = None
        
        # 可以选择使用Chrome或Edge浏览器，提供默认值
        print("请选择浏览器:")
        print("1. Chrome (默认)")
        print("2. Edge")
        print("\n注意：如果遇到驱动启动失败，请检查浏览器版本是否与驱动兼容。")
        print("当前Chrome驱动版本：ChromeDriver 142.0.7444.175")
        print("当前Edge驱动版本：Microsoft Edge WebDriver 143.0.3650.80")
        print("请确保您的浏览器版本与此驱动版本兼容，或手动下载对应版本的驱动。")
        browser_choice = input("请输入选择 (1/2): ").strip()
        
        # 如果用户直接按回车，默认选择Chrome
        if not browser_choice:
            browser_choice = "1"
        
        browser = "edge" if browser_choice == "2" else "chrome"
        
        # 允许用户自定义最大并发数
        max_workers_input = input("请输入最大并发下载数 (默认为3): ").strip()
        max_workers = 3
        if max_workers_input.isdigit():
            max_workers = int(max_workers_input)
            # 限制最大并发数在合理范围内
            max_workers = max(1, min(max_workers, 10))
        
        # 允许用户自定义下载目录
        download_dir = input("请输入下载目录 (默认为downloads): ").strip()
        if not download_dir:
            download_dir = "downloads"
        
        downloader = LanzouDownloader(
            chrome_driver_path=chrome_driver_path,
            edge_driver_path=edge_driver_path,
            headless=True,
            max_workers=max_workers,
            browser=browser
        )
        
        try:
            # 设置驱动
            downloader.setup_driver()
            
            # 登录并获取文件列表
            url = 'https://wwzc.lanzoub.com/b00tc1sz4b'
            password = '8255'
            print(f"正在访问蓝奏云链接: {url}")
            downloader.login_and_get_files(url, password)
            
            # 让用户选择文件
            selected_files = downloader.select_files_for_download()
            
            # 下载文件
            if selected_files:
                print(f"\n下载设置:")
                print(f"- 浏览器: {browser}")
                print(f"- 最大并发数: {max_workers}")
                print(f"- 下载目录: {download_dir}")
                
                confirm = input("\n是否开始下载选中的文件? (y/n): ").strip().lower()
                if confirm == 'y' or confirm == 'yes':
                    downloader.download_files_concurrent(selected_files, download_dir)
                    print("\n所有文件下载任务已完成!")
                else:
                    print("已取消下载")
            else:
                print("未选择任何文件")
                
        except KeyboardInterrupt:
            print("\n\n用户中断了下载过程")
            logger.info("用户中断了下载过程")
        except Exception as e:
            error_msg = f"\n程序运行时发生错误: {e}"
            print(error_msg)
            logger.error(error_msg)
        finally:
            downloader.close()
            print("浏览器已关闭")
            logger.info("浏览器已关闭")
        
        # 询问用户是否继续
        continue_choice = input("\n是否继续下载其他文件? (y/n): ").strip().lower()
        if continue_choice != 'y' and continue_choice != 'yes':
            print("程序已退出，感谢使用!")
            break

if __name__ == "__main__":
    main()