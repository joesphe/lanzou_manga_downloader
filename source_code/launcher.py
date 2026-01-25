import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os


class LanzouDownloaderLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("蓝奏云下载器启动器")
        self.root.geometry("400x200")
        self.root.resizable(False, False)
        
        # 居中窗口
        self.center_window()
        
        self.create_widgets()
        
    def center_window(self):
        """居中窗口"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="蓝奏云漫画下载器", font=("微软雅黑", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 选择版本
        ttk.Label(main_frame, text="请选择要使用的版本:", font=("微软雅黑", 10)).pack(pady=(0, 10))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 高级版按钮
        advanced_btn = ttk.Button(
            button_frame, 
            text="高级版", 
            command=self.launch_advanced,
            width=15
        )
        advanced_btn.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        
        # 专用版按钮
        simple_btn = ttk.Button(
            button_frame, 
            text="专用版", 
            command=self.launch_simple,
            width=15
        )
        simple_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 说明标签
        info_label = ttk.Label(
            main_frame, 
            text="高级版: 可自定义链接和密码\n专用版: 专用于预设链接",
            foreground="gray"
        )
        info_label.pack(pady=(10, 0))
        
    def launch_advanced(self):
        """启动高级版"""
        try:
            self.root.destroy()
            subprocess.run([sys.executable, "lanzou_gui.py"], check=True)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("错误", f"启动高级版失败: {e}")
        except FileNotFoundError:
            messagebox.showerror("错误", "未找到 lanzou_gui.py 文件")
    
    def launch_simple(self):
        """启动专用版"""
        try:
            self.root.destroy()
            subprocess.run([sys.executable, "lanzou_simple_gui.py"], check=True)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("错误", f"启动专用版失败: {e}")
        except FileNotFoundError:
            messagebox.showerror("错误", "未找到 lanzou_simple_gui.py 文件")


def main():
    root = tk.Tk()
    app = LanzouDownloaderLauncher(root)
    root.mainloop()


if __name__ == "__main__":
    main()