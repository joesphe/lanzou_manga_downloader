import os
import sys
import re
import time
import hashlib
import argparse
from DrissionPage import Chromium, ChromiumOptions
import feapder
from feapder.utils.log import log
from concurrent.futures import ThreadPoolExecutor, as_completed


def safe_print(*args, **kwargs):
    """
    安全打印函数，处理编码问题
    """
    import sys
    import os
    
    # 获取当前环境的编码，优先使用环境变量指定的编码
    encoding = os.environ.get('PYTHONIOENCODING', '')
    if not encoding:
        # 检测当前环境的编码
        encoding = getattr(sys.stdout, 'encoding', '')
    
    # 如果仍没有检测到编码，默认使用utf-8
    if not encoding:
        encoding = 'utf-8'
    
    # 将所有参数转换为字符串并处理编码
    processed_args = []
    for arg in args:
        if isinstance(arg, str):
            # 对字符串进行编码处理
            try:
                # 尝试按当前编码处理
                processed_arg = arg.encode(encoding, errors='replace').decode(encoding)
            except (UnicodeEncodeError, UnicodeDecodeError):
                # 如果失败，使用utf-8作为备选方案
                processed_arg = arg.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        else:
            str_arg = str(arg)
            try:
                processed_arg = str_arg.encode(encoding, errors='replace').decode(encoding)
            except (UnicodeEncodeError, UnicodeDecodeError):
                processed_arg = str_arg.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        
        processed_args.append(processed_arg)
    
    # 执行打印，使用内置的print函数
    import builtins
    try:
        builtins.print(*processed_args, **kwargs)
        sys.stdout.flush()  # 立即刷新输出
    except UnicodeEncodeError:
        # 如果还是失败，最终处理：移除或转义特殊字符
        final_args = []
        for arg in processed_args:
            # 移除或替换特殊字符
            final_arg = arg.encode('ascii', errors='replace').decode('ascii')
            final_args.append(final_arg)
        builtins.print(*final_args, **kwargs)
        sys.stdout.flush()


class LanZouFeapderSpider(feapder.AirSpider):
    def __init__(self, url=None, password=None, download_dir="downloads", max_workers=3, logger=None, **kwargs):
        super().__init__(**kwargs)
        
        # 设置URL和密码
        if getattr(sys, 'frozen', False):
            # 生产环境：使用混淆解密
            if url is None or password is None:
                self.url, self.password = self._get_obfuscated_credentials()
            else:
                self.url = url
                self.password = password
        else:
            # 开发环境：从环境变量读取（不提供默认值，强制用户设置环境变量）
            if url is None or password is None:
                url_from_env = os.environ.get('LANZOU_URL')
                password_from_env = os.environ.get('LANZOU_PASSWORD')
                if not url_from_env or not password_from_env:
                    raise ValueError("在开发环境中必须设置环境变量 LANZOU_URL 和 LANZOU_PASSWORD")
                self.url = url_from_env
                self.password = password_from_env
            else:
                self.url = url
                self.password = password
        
        self.download_dir = download_dir
        self.max_workers = max_workers
        self.files = []  # 存储获取到的文件列表
        self.driver = None
        self.logger = logger or self.logger  # 使用传入的日志对象，否则使用默认的 feapder 日志

    def _get_obfuscated_credentials(self):
        """使用深度混淆技术获取凭证"""
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

    def setup_driver(self):
        """设置浏览器驱动"""
        try:
            co = ChromiumOptions(read_file=False)  # 不读取文件方式新建配置对象
            
            # 设置浏览器路径为Edge
            possible_paths = [
                r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
            ]
            browser_found = False
            for path in possible_paths:
                if os.path.exists(path):
                    co.set_browser_path(path)
                    browser_found = True
                    break
            
            # 如果没有找到Edge浏览器，抛出异常
            if not browser_found:
                raise FileNotFoundError("未找到 Microsoft Edge 浏览器，请先安装后再运行程序。")
        
            # 启用无头模式
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
            
            self.driver = Chromium(addr_or_opts=co)
        except Exception as e:
            self.logger.error(f"浏览器初始化失败: {str(e)}")
            raise  # 重新抛出异常

    def login_and_get_files(self):
        """登录并获取文件列表 - 使用DrissionPage实现"""
        try:
            self.logger.info(f"正在访问链接: {self.url}")
            # 访问链接
            self.driver.latest_tab.get(self.url)
            time.sleep(3)
            
            # 输入密码
            self.logger.info("正在输入密码")
            # 等待密码输入框出现
            self.driver.latest_tab.wait.ele_displayed('xpath://input[@id="pwd"]', timeout=10)
            password_input = self.driver.latest_tab.ele('xpath://input[@id="pwd"]')
            if password_input:
                password_input.clear(by_js=True)
                password_input.input(self.password)
            else:
                raise Exception("未找到密码输入框")
            
            # 点击提交按钮
            self.logger.info("正在提交密码")
            # 等待提交按钮出现
            self.driver.latest_tab.wait.ele_displayed('xpath://input[@id="sub"]', timeout=10)
            submit_button = self.driver.latest_tab.ele('xpath://input[@id="sub"]')
            if submit_button:
                submit_button.click(by_js=True)
            else:
                raise Exception("未找到提交按钮")
            
            # 等待页面加载完成
            self.logger.info("等待页面加载完成")
            time.sleep(5)
            
            # 获取文件列表
            # 等待文件容器出现
            self.driver.latest_tab.wait.ele_displayed('xpath://div[@id="infos"]', timeout=10)
            files_container = self.driver.latest_tab.ele('xpath://div[@id="infos"]')
            if not files_container:
                raise Exception("未找到文件容器")
            
            # 循环点击"显示更多文件"按钮，直到所有文件都加载完毕
            more_button_selector = 'xpath://div[@id="infomores"]//span[@id="filemore"]'
            click_count = 0
            max_clicks = 20  # 设置最大点击次数，防止无限循环
            
            while click_count < max_clicks:
                # 检查是否存在"显示更多文件"按钮
                more_button = self.driver.latest_tab.ele(more_button_selector, timeout=2)
                if not more_button:
                    self.logger.info("未找到'显示更多文件'按钮，可能所有文件已加载")
                    break
                
                try:
                    self.logger.info(f"发现'显示更多文件'按钮，正在进行第 {click_count + 1} 次点击")
                    more_button.click(by_js=True)
                    click_count += 1
                    
                    # 等待新文件加载
                    time.sleep(3)
                except Exception as e:
                    self.logger.warning(f"点击'显示更多文件'按钮时出错: {e}，可能所有文件已加载")
                    break
            
            self.logger.info(f"共点击了 {click_count} 次'显示更多文件'按钮")
            
            # 获取所有文件元素
            file_elements = []
            for _ in range(10):  # 最多重试10次
                file_elements = files_container.eles('xpath:.//div[@id="ready"]')
                if file_elements:
                    break
                time.sleep(1)
            
            self.logger.info(f"找到 {len(file_elements)} 个文件")
            
            for i, file_element in enumerate(file_elements, 1):
                try:
                    # 获取文件名和下载链接
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
                    size_element = file_element.ele('xpath:.//div[@id="size"]', timeout=5)
                    file_size = size_element.text if size_element else "未知大小"
                    
                    # 获取文件时间
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
                    self.logger.error(error_msg)
                    
        except Exception as e:
            error_msg = f"获取文件列表时出错: {e}"
            self.logger.error(error_msg)
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

    def download_single_file(self, file_info):
        """使用浏览器直接下载单个文件"""
        try:
            self.logger.info(f"开始处理文件: {file_info['name']}")
            
            # 清理文件名
            clean_filename = self.sanitize_filename(file_info['name'])
            
            # 确保下载目录存在
            os.makedirs(self.download_dir, exist_ok=True)
            
            # 检查文件是否已经存在，如果存在则跳过下载
            expected_file = os.path.join(self.download_dir, clean_filename)
            if os.path.exists(expected_file):
                self.logger.info(f"文件已存在，跳过: {clean_filename}")
                return True
            
            # 设置下载路径
            abs_download_path = os.path.abspath(self.download_dir)
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
                                        self.logger.info(f"正在下载: {clean_filename}")
                                        element.click(by_js=True)  # 使用JavaScript点击
                                        # 标记已经开始下载，避免重复点击
                                        download_found = True
                                        break  # 点击后立即跳出，不再尝试同类型下载
                                    else:
                                        # 元素尺寸为0，跳过
                                        pass
                                except:
                                    # 如果无法获取元素尺寸，仍然尝试点击（兼容旧版本或特殊元素）
                                    self.logger.info(f"正在下载: {clean_filename}")
                                    element.click(by_js=True)  # 使用JavaScript点击
                                    # 标记已经开始下载，避免重复点击
                                    download_found = True
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
                            # 直接下载文件
                            try:
                                self.logger.info(f"正在下载: {clean_filename}")
                                # 使用Tab的download方法
                                download_id = self.driver.latest_tab.download(href)
                                # 标记已经开始下载，避免重复下载
                                download_found = True
                                break  # 下载请求发出后立即跳出，不再尝试其他链接
                            except Exception as e:
                                self.logger.error(f"直接下载失败: {e}")
                                continue
                    except:
                        continue
            
            if not download_found:
                self.logger.error(f"未找到 {file_info['name']} 的下载链接")
                return False
            
            # 等待下载完成
            time.sleep(5)  # 给予一些时间让下载开始
            
            # 监控下载进度
            max_wait_time = 60 * 5  # 最多等待5分钟
            wait_time = 0
            while wait_time < max_wait_time:
                if os.path.exists(expected_file) and os.path.getsize(expected_file) > 0:
                    # 检查文件是否还在增长（是否还在下载）
                    initial_size = os.path.getsize(expected_file)
                    time.sleep(2)
                    current_size = os.path.getsize(expected_file)
                    if initial_size == current_size:
                        # 文件大小没有变化，认为下载完成
                        break
                time.sleep(1)
                wait_time += 1
            
            if os.path.exists(expected_file) and os.path.getsize(expected_file) > 0:
                self.logger.info(f"✓ 文件下载成功: {clean_filename}")
                return True
            else:
                self.logger.error(f"✗ 文件下载失败: {clean_filename}")
                return False
                
        except Exception as e:
            self.logger.error(f"下载文件 {file_info['name']} 时出错: {e}")
            return False

    def start_requests(self):
        """开始请求 - 在AirSpider中这是入口点"""
        # 设置浏览器
        self.setup_driver()
        
        try:
            # 获取文件列表
            self.login_and_get_files()
            
            # 输出找到的文件信息
            self.logger.info(f"总共找到 {len(self.files)} 个文件:")
            for file_info in self.files:
                self.logger.info(f"  {file_info['index']}. {file_info['name']} ({file_info['size']}) - {file_info['time']}")
            
            # 如果有文件，则开始下载
            if self.files:
                # 使用线程池下载文件
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # 提交所有下载任务
                    future_to_file = {
                        executor.submit(self.download_single_file, file_info): file_info 
                        for file_info in self.files
                    }
                    
                    # 等待所有任务完成
                    for future in as_completed(future_to_file):
                        file_info = future_to_file[future]
                        try:
                            success = future.result()
                            if success:
                                self.logger.info(f"文件下载完成: {file_info['name']}")
                            else:
                                self.logger.error(f"文件下载失败: {file_info['name']}")
                        except Exception as e:
                            self.logger.error(f"下载文件 {file_info['name']} 时发生异常: {e}")
            else:
                self.logger.warning("没有找到任何文件")
                
        finally:
            # 关闭浏览器
            if self.driver:
                self.driver.quit()

    def finish(self):
        """爬虫结束时调用"""
        self.logger.info(f"爬虫运行完成，总共处理了 {len(self.files)} 个文件")


def main():
    parser = argparse.ArgumentParser(description='蓝奏云下载器 - feapder版本')
    parser.add_argument('--url', type=str, help='蓝奏云分享链接（通过环境变量LANZOU_URL或混淆解密设置可获得更好的安全性）')
    parser.add_argument('--password', type=str, help='分享密码（建议通过环境变量LANZOU_PASSWORD或混淆解密设置，命令行传递可能有安全风险）')
    parser.add_argument('--download-dir', type=str, default='downloads', help='下载目录 (默认: downloads)')
    parser.add_argument('--workers', type=int, default=3, help='并发数 (默认: 3)')
    parser.add_argument('--log-level', type=str, default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       help='日志级别 (默认: INFO)')
    
    args = parser.parse_args()
    
    # 创建爬虫实例
    spider = LanZouFeapderSpider(
        url=args.url,
        password=args.password,
        download_dir=args.download_dir,
        max_workers=args.workers
    )
    
    # 设置日志级别
    import logging
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))
    
    # 运行爬虫
    spider.start()


if __name__ == "__main__":
    main()