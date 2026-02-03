import os
import sys
import time
import threading
import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import feapder
from feapder.utils.log import log
from DrissionPage import Chromium, ChromiumOptions
import json
import base64
import hashlib
import re


def safe_print(*args, **kwargs):
    """
    安全打印函数，处理编码问题，适配GUI模式
    """
    import os
    import builtins
    
    # 检查是否在GUI模式下运行（sys.stdout可能不可用）
    stdout_available = hasattr(sys, 'stdout') and sys.stdout is not None
    
    # 处理参数编码
    processed_args = []
    for arg in args:
        if isinstance(arg, str):
            processed_arg = arg
        else:
            processed_arg = str(arg)
        processed_args.append(processed_arg)
    
    # 组合输出内容
    output = ' '.join(processed_args)
    
    # 如果有额外的关键字参数，也处理它们
    sep = kwargs.get('sep', ' ')
    end = kwargs.get('end', '\\n')
    
    if stdout_available:
        # 在控制台模式下正常输出
        try:
            builtins.print(*processed_args, **kwargs)
            sys.stdout.flush()
        except (UnicodeEncodeError, AttributeError, OSError):
            # 如果控制台输出失败，尝试写入日志文件
            try:
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                log_entry = f"[{timestamp}] {output}\\n"
                with open('lanzou_downloader.log', 'a', encoding='utf-8') as f:
                    f.write(log_entry)
            except:
                pass  # 如果日志写入也失败，则忽略
    else:
        # 在GUI模式下，将输出写入日志文件
        try:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"[{timestamp}] {output}\\n"
            with open('lanzou_downloader.log', 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except:
            pass  # 如果日志写入失败，则忽略


class LanZouFeapderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("蓝奏云下载器 - feapder增强版")
        self.root.geometry("900x700")
        
        # 检查是否为打包后的exe（生产环境）
        if getattr(sys, 'frozen', False):
            # 生产环境：使用混淆解密
            # 创建一个临时的实例来获取混淆凭据
            temp_downloader = LanZouFeapderSpider()
            self.default_url, self.default_password = temp_downloader._get_obfuscated_credentials()
        else:
            # 开发环境：从环境变量读取（不提供默认值，强制用户设置环境变量）
            url_from_env = os.environ.get('LANZOU_URL')
            password_from_env = os.environ.get('LANZOU_PASSWORD')
            if not url_from_env or not password_from_env:
                raise ValueError("在开发环境中必须设置环境变量 LANZOU_URL 和 LANZOU_PASSWORD")
            self.default_url = url_from_env
            self.default_password = password_from_env
        
        # 创建爬虫实例但暂不初始化浏览器
        self.spider = LanZouFeapderSpider(default_url=self.default_url, default_password=self.default_password, logger=log)
        self.selected_files = []
        self.download_thread = None
        self.is_downloading = False
        
        self.setup_ui()

    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)

        # 获取文件按钮 - 直接调用内部预设的URL和密码
        self.get_files_btn = ttk.Button(main_frame, text="获取文件列表", command=self.get_files)
        self.get_files_btn.grid(row=0, column=0, columnspan=2, sticky=tk.E, pady=(0, 5))

        # 文件列表
        # 创建文件列表标题和多选提示
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        
        ttk.Label(title_frame, text="文件列表:").pack(side=tk.LEFT)
        ttk.Label(title_frame, text=" (可按住Ctrl键多选)", foreground="gray").pack(side=tk.LEFT)

        # 创建树形视图和滚动条
        tree_frame = ttk.Frame(main_frame)
        tree_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        # 创建带滚动条的Treeview
        columns = ("#", "文件名", "大小", "时间")
        self.file_tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings", height=12, selectmode='extended')  # 启用多选模式
        
        # 定义列
        self.file_tree.heading("#0", text="选择")
        self.file_tree.column("#0", width=50, anchor=tk.CENTER)
        self.file_tree.heading("#", text="#")
        self.file_tree.column("#", width=50, anchor=tk.CENTER)
        self.file_tree.heading("文件名", text="文件名")
        self.file_tree.column("文件名", width=400, anchor=tk.W)
        self.file_tree.heading("大小", text="大小")
        self.file_tree.column("大小", width=100, anchor=tk.CENTER)
        self.file_tree.heading("时间", text="时间")
        self.file_tree.column("时间", width=120, anchor=tk.CENTER)

        # 滚动条
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.file_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.file_tree.xview)
        self.file_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # 布局
        self.file_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # 下载目录选择
        ttk.Label(main_frame, text="下载目录:").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        self.download_dir_entry = ttk.Entry(main_frame, width=50)
        self.download_dir_entry.insert(0, os.path.abspath("downloads"))
        self.download_dir_entry.grid(row=4, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(0, 5))
        
        self.browse_btn = ttk.Button(main_frame, text="浏览...", command=self.browse_directory)
        self.browse_btn.grid(row=4, column=1, sticky=tk.E, pady=(0, 5))

        # 进度条
        self.progress_label = ttk.Label(main_frame, text="准备就绪")
        self.progress_label.grid(row=5, column=0, sticky=tk.W, pady=(5, 5))
        
        self.progress_var = tk.StringVar(value="准备就绪")
        self.progress_bar = ttk.Progressbar(main_frame, mode='determinate', length=400)
        self.progress_bar.grid(row=5, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(5, 5))

        # 下载按钮
        self.download_btn = ttk.Button(main_frame, text="下载选中文件", command=self.start_download)
        self.download_btn.grid(row=6, column=1, sticky=tk.E, pady=(10, 0))

        # 配置主框架行权重 - 让文件列表区域可以扩展
        main_frame.rowconfigure(3, weight=1)

    def log_message(self, message):
        """向日志文本框添加消息"""
        # 日志功能已移除，保留此方法以兼容现有代码
        pass

    def get_files(self):
        """获取文件列表"""
        self.get_files_btn.config(state=tk.DISABLED)
        
        # 更新界面以确保按钮变灰
        self.root.update_idletasks()
        
        # 直接使用内部预设的URL和密码，不再从界面获取
        url = self.default_url
        password = self.default_password
        
        # 在新线程中获取文件列表
        self.get_files_thread = threading.Thread(target=self._get_files_worker, args=(url, password))
        self.get_files_thread.daemon = True
        self.get_files_thread.start()

    def _get_files_worker(self, url, password):
        """获取文件的工作线程"""
        try:
            safe_print("正在启动浏览器...")
            self.spider.setup_driver()  # 初始化浏览器
            safe_print("浏览器启动成功！")

            safe_print("正在访问蓝奏云链接...")
            self.spider.url = url
            self.spider.password = password
            
            # 临时设置爬虫的文件列表，以便在GUI中使用
            self.spider.login_and_get_files()
            
            # 在主线程中更新UI
            self.root.after(0, self._update_file_list_ui)
            
        except FileNotFoundError as e:
            error_msg = f"浏览器启动失败: {str(e)}\\n请确保已安装 Microsoft Edge 浏览器。"
            safe_print(error_msg)
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
        except Exception as e:
            error_msg = f"获取文件列表时出错: {str(e)}"
            safe_print(error_msg)
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
        finally:
            # 确保在主线程中更新UI元素
            self.root.after(0, lambda: self.get_files_btn.config(state=tk.NORMAL))

    def _update_file_list_ui(self):
        """在主线程中更新文件列表UI"""
        # 清空现有项目
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # 添加新文件
        for file_info in self.spider.files:
            self.file_tree.insert("", tk.END, values=(
                file_info["index"], 
                file_info["name"], 
                file_info["size"], 
                file_info["time"]
            ))
        
        safe_print(f"成功获取 {len(self.spider.files)} 个文件")
        
        # 检查已下载的文件并标记
        download_dir = self.download_dir_entry.get().strip()
        if download_dir:
            downloaded_files = self.check_downloaded_files(download_dir)
            safe_print(f"已在下载目录找到 {len(downloaded_files)} 个已下载文件")

    def check_downloaded_files(self, download_dir):
        """检查哪些文件已经下载了"""
        downloaded_files = set()
        if os.path.exists(download_dir):
            downloaded_files = {f for f in os.listdir(download_dir) if os.path.isfile(os.path.join(download_dir, f))}
        
        downloaded_file_names = set()
        for file_name in downloaded_files:
            # 检查是否与蓝奏云文件名匹配（考虑文件名被清理的情况）
            for file_info in self.spider.files:
                clean_name = self.spider.sanitize_filename(file_info['name'])
                if clean_name == file_name:
                    downloaded_file_names.add(clean_name)
                    break
        
        return downloaded_file_names

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
            for file_info in self.spider.files:
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
        self.spider.download_dir = download_dir
        
        # 在新线程中开始下载
        self.download_thread = threading.Thread(target=self._download_worker)
        self.download_thread.daemon = True
        self.download_thread.start()

    def _download_worker(self):
        """下载工作线程"""
        self.is_downloading = True
        total_files = len(self.selected_files)
        
        try:
            self.root.after(0, lambda: self.download_btn.config(text="下载中...", state=tk.DISABLED))
            self.root.after(0, lambda: self.progress_label.config(text=f"开始下载 {total_files} 个文件..."))
            
            # 使用线程池下载文件
            with ThreadPoolExecutor(max_workers=self.spider.max_workers) as executor:
                # 提交所有下载任务
                future_to_file = {
                    executor.submit(self.spider.download_single_file, file_info): file_info 
                    for file_info in self.selected_files
                }
                
                completed = 0
                # 等待所有任务完成
                for future in as_completed(future_to_file):
                    file_info = future_to_file[future]
                    completed += 1
                    progress_percent = (completed / total_files) * 100
                    
                    try:
                        success = future.result()
                        if success:
                            safe_print(f"✓ 文件下载完成: {file_info['name']}")
                        else:
                            safe_print(f"✗ 文件下载失败: {file_info['name']}")
                    except Exception as e:
                        safe_print(f"✗ 下载文件 {file_info['name']} 时发生异常: {e}")
                    
                    # 更新进度条
                    def update_progress(val):
                        self.progress_bar['value'] = val
                    self.root.after(0, update_progress, progress_percent)
                    self.root.after(0, lambda c=completed, t=total_files: self.progress_label.config(
                        text=f"正在下载... ({c}/{t})"))
                    self.root.update_idletasks()
            
            safe_print(f"所有文件下载完成！成功: {total_files} 个")
            self.root.after(0, lambda: messagebox.showinfo("完成", f"下载完成！共下载 {total_files} 个文件"))
            
        except Exception as e:
            error_msg = f"下载过程中发生错误: {str(e)}"
            safe_print(error_msg)
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
        finally:
            self.is_downloading = False
            # 确保下载按钮恢复到原始状态
            self.root.after(0, lambda: self.download_btn.config(text="下载选中文件", state=tk.NORMAL))
            # 恢复进度标签
            self.root.after(0, lambda: self.progress_label.config(text="准备就绪"))
            # 重置进度条
            def reset_progress():
                self.progress_bar['value'] = 0
            self.root.after(0, reset_progress)
            # 确保UI更新完成
            self.root.after(0, lambda: self.root.update_idletasks())


class LanZouFeapderSpider:
    def __init__(self, url=None, password=None, download_dir="downloads", max_workers=1, default_url=None, default_password=None, logger=None):
        # 设置URL和密码
        if getattr(sys, 'frozen', False):
            # 生产环境：使用混淆解密
            if default_url is None or default_password is None:
                self.url, self.password = self._get_obfuscated_credentials()
            else:
                self.url = default_url
                self.password = default_password
        else:
            # 开发环境：从环境变量读取（不提供默认值，强制用户设置环境变量）
            if default_url is None or default_password is None:
                url_from_env = os.environ.get('LANZOU_URL')
                password_from_env = os.environ.get('LANZOU_PASSWORD')
                if not url_from_env or not password_from_env:
                    raise ValueError("在开发环境中必须设置环境变量 LANZOU_URL 和 LANZOU_PASSWORD")
                self.url = url_from_env
                self.password = password_from_env
            else:
                self.url = default_url
                self.password = default_password
        
        self.download_dir = download_dir
        self.max_workers = max_workers
        self.files = []  # 存储获取到的文件列表
        self.driver = None
        self.logger = logger or log  # 使用传入的日志对象，否则使用默认的 feapder 日志

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
        co = ChromiumOptions(read_file=False)  # 不读取文件方式新建配置对象
        
        # 设置浏览器路径为Edge
        possible_paths = [
            r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
            r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
        ]
        for path in possible_paths:
            if os.path.exists(path):
                co.set_browser_path(path)
                break
        
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

    def login_and_get_files(self):
        """登录并获取文件列表 - 使用DrissionPage实现"""
        try:
            safe_print("正在访问蓝奏云链接...")  # 在控制台输出，用户可见
            # 访问链接
            self.driver.latest_tab.get(self.url)
            time.sleep(3)
            
            # 输入密码
            safe_print("正在输入密码")
            # 等待密码输入框出现
            self.driver.latest_tab.wait.ele_displayed('xpath://input[@id="pwd"]', timeout=10)
            password_input = self.driver.latest_tab.ele('xpath://input[@id="pwd"]')
            if password_input:
                password_input.clear(by_js=True)
                password_input.input(self.password)
            else:
                raise Exception("未找到密码输入框")
            
            # 点击提交按钮
            safe_print("正在提交密码")
            # 等待提交按钮出现
            self.driver.latest_tab.wait.ele_displayed('xpath://input[@id="sub"]', timeout=10)
            submit_button = self.driver.latest_tab.ele('xpath://input[@id="sub"]')
            if submit_button:
                submit_button.click(by_js=True)
            else:
                raise Exception("未找到提交按钮")
            
            # 等待页面加载完成
            safe_print("等待页面加载完成")
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
                    safe_print("未找到'显示更多文件'按钮，可能所有文件已加载")
                    break
                
                try:
                    safe_print(f"发现'显示更多文件'按钮，正在进行第 {click_count + 1} 次点击")
                    more_button.click(by_js=True)
                    click_count += 1
                    
                    # 等待新文件加载
                    time.sleep(3)
                except Exception as e:
                    safe_print(f"点击'显示更多文件'按钮时出错: {e}，可能所有文件已加载")
                    break
            
            safe_print(f"共点击了 {click_count} 次'显示更多文件'按钮")
            
            # 获取所有文件元素
            file_elements = []
            for _ in range(10):  # 最多重试10次
                file_elements = files_container.eles('xpath:.//div[@id="ready"]')
                if file_elements:
                    break
                time.sleep(1)
            
            safe_print(f"找到 {len(file_elements)} 个文件:")
            
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
                    safe_print(error_msg)
                    
        except Exception as e:
            error_msg = f"获取文件列表时出错: {e}"
            safe_print(error_msg)
            raise  # 重新抛出异常以便上层处理

    def sanitize_filename(self, filename):
        """清理文件名，移除非法字符"""
        # 移除或替换Windows不支持的字符
        illegal_chars = r'[<>:"/\\\\|?*\\x00-\\x1F]'
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
            safe_print(f"开始处理文件: {file_info['name']}")
            
            # 清理文件名
            clean_filename = self.sanitize_filename(file_info['name'])
            
            # 确保下载目录存在
            os.makedirs(self.download_dir, exist_ok=True)
            
            # 检查文件是否已经存在，如果存在则跳过下载
            expected_file = os.path.join(self.download_dir, clean_filename)
            if os.path.exists(expected_file):
                safe_print(f"文件已存在，跳过: {clean_filename}")
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
                                        safe_print(f"正在下载: {clean_filename}")
                                        element.click(by_js=True)  # 使用JavaScript点击
                                        # 标记已经开始下载，避免重复点击
                                        download_found = True
                                        break  # 点击后立即跳出，不再尝试同类型下载
                                    else:
                                        # 元素尺寸为0，跳过
                                        pass
                                except:
                                    # 如果无法获取元素尺寸，仍然尝试点击（兼容旧版本或特殊元素）
                                    safe_print(f"正在下载: {clean_filename}")
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
                                safe_print(f"正在下载: {clean_filename}")
                                # 使用Tab的download方法
                                download_id = self.driver.latest_tab.download(href)
                                # 标记已经开始下载，避免重复下载
                                download_found = True
                                break  # 下载请求发出后立即跳出，不再尝试其他链接
                            except Exception as e:
                                safe_print(f"直接下载失败: {e}")
                                continue
                    except:
                        continue
            
            if not download_found:
                safe_print(f"未找到 {file_info['name']} 的下载链接")
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
                safe_print(f"✓ 文件下载成功: {clean_filename}")
                return True
            else:
                safe_print(f"✗ 文件下载失败: {clean_filename}")
                return False
                
        except Exception as e:
            safe_print(f"下载文件 {file_info['name']} 时出错: {e}")
            return False


def main():
    root = tk.Tk()
    app = LanZouFeapderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()