import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import os
from source_code.lanzou_downloader import LanzouDownloader
import time


class LanzouDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("蓝奏云漫画下载器")
        self.root.geometry("1000x750")
        
        # 存储文件列表
        self.file_list = []
        
        # 下载器实例
        self.downloader = None
        
        # 当前状态
        self.is_logging_in = False
        self.is_downloading = False
        
        # 创建界面元素
        self.create_widgets()
        
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="蓝奏云漫画下载器", font=("微软雅黑", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # 使用说明
        instruction_label = ttk.Label(main_frame, text="使用说明：单击选择单个项目，Ctrl+单击选择多个项目，Shift+单击选择范围", 
                                     foreground="blue", font=("微软雅黑", 10))
        instruction_label.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        
        # 链接和密码输入区域
        input_frame = ttk.LabelFrame(main_frame, text="蓝奏云链接信息", padding="10")
        input_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 链接输入
        ttk.Label(input_frame, text="蓝奏云链接:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.url_var = tk.StringVar()
        self.url_var.set(LanzouDownloader.DEFAULT_URL)  # 在变量创建后设置值
        self.url_entry = ttk.Entry(input_frame, textvariable=self.url_var, width=50)
        self.url_entry.grid(row=0, column=1, padx=(0, 5))
        
        # 密码输入
        ttk.Label(input_frame, text="提取码:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.password_var = tk.StringVar()
        self.password_var.set(LanzouDownloader.DEFAULT_PASSWORD)  # 在变量创建后设置值
        self.password_entry = ttk.Entry(input_frame, textvariable=self.password_var, width=20)
        self.password_entry.grid(row=1, column=1, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        
        # 操作按钮区域
        button_frame = ttk.LabelFrame(main_frame, text="操作", padding="10")
        button_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 获取文件列表按钮
        self.get_files_btn = ttk.Button(button_frame, text="获取文件列表", command=self.get_files)
        self.get_files_btn.grid(row=0, column=0, padx=(0, 10))
        
        # 选择操作按钮
        self.select_all_btn = ttk.Button(button_frame, text="全选", command=self.select_all)
        self.select_all_btn.grid(row=0, column=1, padx=(0, 10))
        
        self.clear_selection_btn = ttk.Button(button_frame, text="取消选择", command=self.clear_selection)
        self.clear_selection_btn.grid(row=0, column=2, padx=(0, 10))
        
        # 下载按钮
        self.download_btn = ttk.Button(button_frame, text="下载选中文件", command=self.download_selected)
        self.download_btn.grid(row=0, column=3, padx=(0, 10))
        
        self.download_all_btn = ttk.Button(button_frame, text="下载全部", command=self.download_all)
        self.download_all_btn.grid(row=0, column=4)
        
        # 下载目录选择
        ttk.Label(button_frame, text="下载目录:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(10, 0))
        self.download_dir_var = tk.StringVar()
        self.download_dir_var.set(os.path.abspath("downloads"))
        self.download_dir_entry = ttk.Entry(button_frame, textvariable=self.download_dir_var, width=40)
        self.download_dir_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=(0, 5), pady=(10, 0))
        
        self.browse_dir_btn = ttk.Button(button_frame, text="浏览...", command=self.browse_directory)
        self.browse_dir_btn.grid(row=1, column=3, padx=(0, 10), pady=(10, 0))
        
        # 进度条
        progress_frame = ttk.LabelFrame(main_frame, text="下载进度", padding="10")
        progress_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.status_label = ttk.Label(progress_frame, text="就绪")
        self.status_label.grid(row=0, column=1)
        
        # 文件列表显示区域
        files_frame = ttk.LabelFrame(main_frame, text="文件列表", padding="10")
        files_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(0, weight=1)
        
        # 创建树形视图显示文件列表
        columns = ('序号', '文件名', '大小', '日期')
        self.tree = ttk.Treeview(files_frame, columns=columns, show='headings', height=12)
        
        # 定义列标题
        for col in columns:
            self.tree.heading(col, text=col)
            if col == '文件名':
                self.tree.column(col, width=500)
            elif col == '序号':
                self.tree.column(col, width=50)
            else:
                self.tree.column(col, width=100)
        
        # 添加滚动条
        tree_scroll = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 绑定双击事件，双击直接下载
        self.tree.bind('<Double-Button-1>', self.on_tree_double_click)
        
        # 添加右键菜单
        self.create_context_menu()
        
        # 日志输出区域
        log_frame = ttk.LabelFrame(main_frame, text="操作日志", padding="10")
        log_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, state='disabled')
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 添加无头模式选项
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.headless_var = tk.BooleanVar(value=True)
        self.headless_check = ttk.Checkbutton(options_frame, text="无头模式运行", variable=self.headless_var)
        self.headless_check.grid(row=0, column=0, padx=(0, 20))
        
        # 重试次数设置
        ttk.Label(options_frame, text="重试次数:").grid(row=0, column=1, padx=(0, 5))
        self.retry_var = tk.IntVar()
        self.retry_var.set(3)
        self.retry_spinbox = ttk.Spinbox(options_frame, from_=1, to=10, width=5, textvariable=self.retry_var)
        self.retry_spinbox.grid(row=0, column=2)
        
    def create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="下载选中", command=self.download_selected)
        self.context_menu.add_command(label="下载全部", command=self.download_all)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="全选", command=self.select_all)
        self.context_menu.add_command(label="取消选择", command=self.clear_selection)
        
        # 绑定右键菜单到树形视图
        self.tree.bind("<Button-3>", self.show_context_menu)  # Windows/Linux
        self.tree.bind("<Button-2>", self.show_context_menu)  # macOS (模拟右键)
        
    def show_context_menu(self, event):
        """显示右键菜单"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
        
    def on_tree_double_click(self, event):
        """双击树形视图项目时触发下载"""
        selection = self.tree.selection()
        if selection:
            self.download_selected()
        
    def select_all(self):
        """全选所有项目"""
        for item in self.tree.get_children():
            self.tree.selection_add(item)
        self.log_message("已全选所有文件")
        
    def clear_selection(self):
        """清除所有选择"""
        self.tree.selection_remove(*self.tree.selection())
        self.log_message("已取消所有选择")
        
    def browse_directory(self):
        """浏览并选择下载目录"""
        directory = filedialog.askdirectory(initialdir=self.download_dir_var.get())
        if directory:
            self.download_dir_var.set(directory)
        
    def log_message(self, message):
        """在日志区域添加消息"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update_idletasks()
        
    def get_files(self):
        """获取文件列表"""
        url = self.url_var.get().strip()
        password = self.password_var.get().strip()
        
        if not url:
            messagebox.showwarning("警告", "请输入蓝奏云链接！")
            return
            
        if not password:
            messagebox.showwarning("警告", "请输入提取码！")
            return
            
        # 清空之前的文件列表
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.file_list = []
        
        # 禁用按钮，防止重复点击
        self.get_files_btn.config(state='disabled')
        self.status_label.config(text="正在获取文件列表...")
        
        # 在新线程中执行获取文件操作
        get_files_thread = threading.Thread(target=self.perform_get_files, args=(url, password))
        get_files_thread.daemon = True
        get_files_thread.start()
        
    def perform_get_files(self, url, password):
        """执行实际的获取文件操作"""
        try:
            # 创建下载器实例
            self.downloader = LanzouDownloader(headless=self.headless_var.get())
            self.downloader.setup_driver()
            
            # 获取文件列表
            self.downloader.login_and_get_files(url, password)
            self.file_list = self.downloader.files
            
            # 在主线程中更新UI
            self.root.after(0, self.update_file_list_ui)
            
        except Exception as e:
            error_msg = f"获取文件列表失败: {str(e)}"
            self.log_message(error_msg)
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
        finally:
            # 恢复按钮状态
            self.root.after(0, lambda: self.get_files_btn.config(state='normal'))
            self.root.after(0, lambda: self.status_label.config(text="文件列表获取完成"))
            
    def update_file_list_ui(self):
        """更新文件列表UI"""
        # 清空当前列表
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 添加新文件到列表
        for file_info in self.file_list:
            self.tree.insert('', tk.END, values=(
                file_info['index'],
                file_info['name'],
                file_info['size'],
                file_info['time']
            ))
        
        self.log_message(f"成功获取 {len(self.file_list)} 个文件")
        
    def download_selected(self):
        """下载选中的文件"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请选择要下载的文件！\n\n选择方法：\n• 单击选择单个项目\n• Ctrl+单击选择多个项目\n• Shift+单击选择范围")
            return
            
        # 获取选中的文件索引
        selected_indices = []
        for item in selected_items:
            item_values = self.tree.item(item, 'values')
            index = int(item_values[0])  # 序号
            # 将1基索引转换为0基索引
            selected_indices.append(index - 1)
            
        # 过滤有效的索引
        valid_indices = [idx for idx in selected_indices if 0 <= idx < len(self.file_list)]
        
        if not valid_indices:
            messagebox.showwarning("警告", "没有有效的文件被选中！")
            return
            
        self.log_message(f"开始下载选中的 {len(valid_indices)} 个文件")
        
        # 在新线程中执行下载
        download_thread = threading.Thread(
            target=self.perform_download_multiple, 
            args=(valid_indices, self.download_dir_var.get(), self.retry_var.get())
        )
        download_thread.daemon = True
        download_thread.start()
        
    def download_all(self):
        """下载所有文件"""
        if not self.file_list:
            messagebox.showwarning("警告", "没有可下载的文件！")
            return
            
        # 获取所有索引
        all_indices = list(range(len(self.file_list)))
        
        self.log_message(f"开始下载全部 {len(self.file_list)} 个文件")
        
        # 在新线程中执行下载
        download_thread = threading.Thread(
            target=self.perform_download_multiple, 
            args=(all_indices, self.download_dir_var.get(), self.retry_var.get())
        )
        download_thread.daemon = True
        download_thread.start()
        
    def perform_download_multiple(self, indices, download_dir, max_retries):
        """批量下载文件"""
        total_files = len(indices)
        downloaded_count = 0
        
        # 确保下载目录存在
        os.makedirs(download_dir, exist_ok=True)
        
        # 重置进度条
        self.root.after(0, lambda: self.progress_var.set(0))
        
        for idx in indices:
            if idx >= len(self.file_list):
                continue
                
            # 更新整体进度
            overall_progress = (downloaded_count / total_files) * 100
            self.root.after(0, lambda op=overall_progress: self.progress_var.set(op))
            self.root.after(0, lambda: self.status_label.config(
                text=f"正在下载第 {downloaded_count+1}/{total_files} 个文件: {self.file_list[idx]['name'][:30]}..."
            ))
            
            # 下载单个文件
            success = self.perform_download_single(idx, download_dir, max_retries)
            if success:
                downloaded_count += 1
            
            # 更新整体进度
            overall_progress = (downloaded_count / total_files) * 100
            self.root.after(0, lambda op=overall_progress: self.progress_var.set(op))
        
        # 下载完成后更新状态
        self.root.after(0, lambda: self.download_complete(total_files, downloaded_count))
        
    def perform_download_single(self, index, download_dir, max_retries):
        """下载单个文件"""
        if index >= len(self.file_list):
            return False
            
        try:
            file_info = self.file_list[index]
            file_name = file_info['name']
            
            self.log_message(f"开始下载: {file_name}")
            
            # 使用下载器下载文件
            success = self.downloader.download_single_file(
                file_info, 
                download_dir=download_dir, 
                max_retries=max_retries
            )
            
            if success:
                self.log_message(f"✓ {file_name} 下载完成")
                return True
            else:
                self.log_message(f"✗ {file_name} 下载失败")
                return False
                
        except Exception as e:
            self.log_message(f"下载 {self.file_list[index]['name']} 时出错: {str(e)}")
            return False
        
    def download_complete(self, total_files, downloaded_count):
        """下载完成后的回调函数"""
        self.status_label.config(text=f"全部下载完成！成功: {downloaded_count}/{total_files}")
        self.log_message(f"所有 {total_files} 个文件处理完成，成功下载 {downloaded_count} 个文件")
        messagebox.showinfo("下载完成", f"全部 {total_files} 个文件处理完成\n成功下载 {downloaded_count} 个文件\n文件保存在: {self.download_dir_var.get()}")


def main():
    root = tk.Tk()
    app = LanzouDownloaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()