import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import time
import win32gui
import win32con
import win32api
from datetime import datetime
import threading
import sys
import ctypes
import os

# 检查管理员权限
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
    sys.exit()

# 虚拟键码映射（根据游戏实际需要调整）
VK_CODE = {
    "1": 0x41,  # A
    "2": 0x53,  # S
    "3": 0x44,  # D
    "4": 0x46,  # F
    "5": 0x47,  # G
    "6": 0x48,  # H
    "7": 0x4A,  # J
    "h1": 0x51,  # Q
    "h2": 0x57,  # W
    "h3": 0x45,  # E
    "h4": 0x52,  # R
    "h5": 0x54,  # T
    "h6": 0x59,  # Y
    "h7": 0x55   # U
}

class NotePlayer:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("无限暖暖音符播放器 v2.0")
        self.window.geometry("680x550")
        
        # 样式配置
        self.bg_color = "#F0F0F0"
        self.btn_color = "#E1E1E1"
        self.window.configure(bg=self.bg_color)
        
        # 创建控件
        self.create_widgets()
        
        # 运行状态
        self.is_playing = False
        self.current_notes = []
        self.game_hwnd = None
        
        # 自动查找游戏窗口
        self.find_game_window()
        
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        # 顶部控制面板
        control_frame = tk.Frame(self.window, bg=self.bg_color, padx=10, pady=10)
        control_frame.pack(fill=tk.X)
        
        # 文件选择
        file_frame = tk.Frame(control_frame, bg=self.bg_color)
        file_frame.pack(side=tk.LEFT, padx=5)
        tk.Button(file_frame, text="选择音符文件", command=self.select_file, 
                 bg=self.btn_color, relief=tk.GROOVE).pack(side=tk.LEFT)
        self.file_label = tk.Label(file_frame, text="未选择文件", bg=self.bg_color)
        self.file_label.pack(side=tk.LEFT, padx=5)
        
        # 操作按钮
        btn_frame = tk.Frame(control_frame, bg=self.bg_color)
        btn_frame.pack(side=tk.RIGHT)
        self.play_btn = tk.Button(btn_frame, text="开始播放", command=self.toggle_play, 
                                 bg="#C3E8C3", relief=tk.GROOVE)
        self.play_btn.pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="重新检测窗口", command=self.find_game_window, 
                 bg=self.btn_color, relief=tk.GROOVE).pack(side=tk.LEFT)
        
        # 日志区域
        log_frame = tk.Frame(self.window)
        log_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, 
                                                 font=("Consolas", 9))
        self.log_area.pack(fill=tk.BOTH, expand=True)
        
        # 状态栏
        self.status_bar = tk.Label(self.window, text="就绪", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def log_message(self, message, status=False):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_text = f"[{timestamp}] {message}\n"
        self.log_area.insert(tk.END, log_text)
        self.log_area.see(tk.END)
        if status:
            self.status_bar.config(text=message)

    def find_game_window(self):
        """查找游戏窗口句柄"""
        self.game_hwnd = None
        # 尝试多种窗口匹配方式
        titles = ["无限暖暖", "X6Game-Win64-Shipping"]
        classes = ["UnrealWindow"]
        
        for class_name in classes:
            self.game_hwnd = win32gui.FindWindow(class_name, None)
            if self.game_hwnd:
                break
                
        if self.game_hwnd:
            self.log_message(f"找到游戏窗口 句柄: 0x{self.game_hwnd:X}")
            self.status_bar.config(text="游戏窗口已就绪", fg="green")
        else:
            self.log_message("未找到游戏窗口！")
            self.status_bar.config(text="游戏窗口未找到", fg="red")

    def select_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            self.file_label.config(text=os.path.basename(file_path))
            with open(file_path, "r", encoding="utf-8") as f:
                self.current_notes = self.parse_notes(f.read())
            self.log_message(f"已加载文件：{file_path}")

    def parse_notes(self, content):
        """解析音符格式 '音符,持续时间' """
        notes = []
        lines = content.strip().split('\n')
        for line in lines:
            if line.strip():  # 忽略空行
                note, duration = line.strip().split(',')
                notes.append((note, int(duration)))
        return notes

    def toggle_play(self):
        if not self.is_playing:
            if not self.game_hwnd:
                messagebox.showerror("错误", "未找到游戏窗口！")
                return
            if not self.current_notes:
                messagebox.showerror("错误", "请先选择音符文件！")
                return
            self.is_playing = True
            self.play_btn.config(text="停止播放", bg="#FFC1C1")
            threading.Thread(target=self.play_notes, daemon=True).start()
        else:
            self.is_playing = False
            self.play_btn.config(text="开始播放", bg="#C3E8C3")

    def send_note(self, note, duration):
        """向游戏窗口发送按键消息"""
        if note not in VK_CODE:
            self.log_message(f"无效音符: {note}")
            return False
            
        vk = VK_CODE[note]
        try:
            # 发送按下消息
            win32api.PostMessage(self.game_hwnd, win32con.WM_KEYDOWN, vk, 0)
            time.sleep(duration / 1000.0)  # 按照指定的持续时间保持按键
            # 发送释放消息
            win32api.PostMessage(self.game_hwnd, win32con.WM_KEYUP, vk, 0)
            return True
        except Exception as e:
            self.log_message(f"发送失败: {str(e)}")
            return False

    def play_notes(self):
        self.log_message("开始播放...")
        
        for note, duration in self.current_notes:
            if not self.is_playing:
                break
                
            if self.send_note(note, duration):
                self.log_area.insert(tk.END, f"{note}({duration}ms) ")
                self.log_area.see(tk.END)
                self.window.update()
            else:
                self.log_message("遇到错误，停止播放")
                break
                
        self.is_playing = False
        self.play_btn.config(text="开始播放", bg="#C3E8C3")
        self.log_message("播放结束")

    def on_close(self):
        if self.is_playing:
            self.is_playing = False
            time.sleep(0.5)
        self.window.destroy()

if __name__ == "__main__":
    player = NotePlayer()
    player.window.mainloop()