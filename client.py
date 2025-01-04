import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import socket
import json
import os

class FileClient:
    def __init__(self, root):
        self.root = root
        self.root.title("文件传输客户端")
        self.current_path = ''  # 当前路径
        
        # 设置窗口大小和位置
        self.root.geometry("600x400")
        self.root.minsize(500, 300)
        
        self.setup_ui()
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(('localhost', 9999))
            self.refresh_files()
        except Exception as e:
            messagebox.showerror("错误", f"无法连接到服务器: {e}")
            root.destroy()
        
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 路径框架
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(path_frame, text="当前路径: ").pack(side=tk.LEFT)
        self.path_label = ttk.Label(path_frame, text="/")
        self.path_label.pack(side=tk.LEFT)
        
        # 文件列表框架
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Treeview和滚动条
        self.tree = ttk.Treeview(list_frame, columns=('type', 'name'), show='headings')
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # 设置列
        self.tree.heading('type', text='类型')
        self.tree.heading('name', text='名称')
        self.tree.column('type', width=100)
        self.tree.column('name', width=400)
        
        # 布局
        self.tree.grid(column=0, row=0, sticky='nsew')
        vsb.grid(column=1, row=0, sticky='ns')
        hsb.grid(column=0, row=1, sticky='ew')
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        
        # 双击处理
        self.tree.bind('<Double-1>', self.on_double_click)
        
        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="返回上级", command=self.go_up).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="刷新", command=self.refresh_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="下载", command=self.download_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="上传文件", command=self.upload_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="新建文件夹", command=self.create_directory).pack(side=tk.LEFT, padx=5)
    
    def on_double_click(self, event):
        selection = self.tree.selection()
        if not selection:
            return
            
        item = self.tree.selection()[0]
        item_type = self.tree.item(item)['values'][0]
        item_name = self.tree.item(item)['values'][1]
        
        if item_type == '文件夹':
            self.current_path = os.path.join(self.current_path, item_name)
            self.refresh_files()
    
    def go_up(self):
        if self.current_path:
            self.current_path = os.path.dirname(self.current_path)
            self.refresh_files()
    
    def refresh_files(self):
        self.tree.delete(*self.tree.get_children())
        self.path_label.config(text='/' + self.current_path)
        
        try:
            self.sock.send(json.dumps({
                "type": "list",
                "path": self.current_path
            }).encode())
            
            response = json.loads(self.sock.recv(1024).decode())
            
            if isinstance(response, list):
                # 先添加文件夹
                for item in sorted([i for i in response if i['is_dir']], key=lambda x: x['name']):
                    self.tree.insert('', 'end', values=('文件夹', item['name']))
                # 再添加文件
                for item in sorted([i for i in response if not i['is_dir']], key=lambda x: x['name']):
                    self.tree.insert('', 'end', values=('文件', item['name']))
        except Exception as e:
            messagebox.showerror("错误", f"刷新失败: {e}")
    
    def create_directory(self):
        dirname = simpledialog.askstring("新建文件夹", "请输入文件夹名称：")
        if dirname:
            if '/' in dirname or '\\' in dirname:
                messagebox.showerror("错误", "文件夹名称不能包含'/'或'\\'")
                return
                
            new_path = os.path.join(self.current_path, dirname)
            try:
                self.sock.send(json.dumps({
                    "type": "mkdir",
                    "path": new_path
                }).encode())
                self.sock.recv(1024)  # 等待确认
                self.refresh_files()
            except Exception as e:
                messagebox.showerror("错误", f"创建文件夹失败: {e}")
    
    def download_file(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请选择要下载的文件")
            return
            
        item = self.tree.item(selected[0])
        if item['values'][0] == '文件夹':
            messagebox.showwarning("警告", "不能直接下载文件夹")
            return
            
        filename = item['values'][1]
        file_path = os.path.join(self.current_path, filename)
        
        save_path = filedialog.asksaveasfilename(
            defaultextension=".*",
            initialfile=filename
        )
        
        if save_path:
            try:
                self.sock.send(json.dumps({
                    "type": "get",
                    "path": file_path
                }).encode())
                
                file_size = int(self.sock.recv(1024).decode())
                self.sock.send(b'ready')
                
                received_size = 0
                with open(save_path, 'wb') as f:
                    while received_size < file_size:
                        data = self.sock.recv(min(1024, file_size - received_size))
                        received_size += len(data)
                        f.write(data)
                        
                messagebox.showinfo("成功", "文件下载完成！")
            except Exception as e:
                messagebox.showerror("错误", f"下载失败: {e}")
    
    def upload_file(self):
        filename = filedialog.askopenfilename()
        if filename:
            try:
                dest_path = os.path.join(self.current_path, os.path.basename(filename))
                file_size = os.path.getsize(filename)
                
                self.sock.send(json.dumps({
                    "type": "put",
                    "path": dest_path,
                    "size": file_size
                }).encode())
                
                self.sock.recv(1024)  # 等待服务器ready信号
                
                with open(filename, 'rb') as f:
                    while True:
                        data = f.read(1024)
                        if not data:
                            break
                        self.sock.send(data)
                        
                messagebox.showinfo("成功", "文件上传完成！")
                self.refresh_files()
            except Exception as e:
                messagebox.showerror("错误", f"上传失败: {e}")
    
    def __del__(self):
        try:
            self.sock.close()
        except:
            pass

if __name__ == '__main__':
    root = tk.Tk()
    client = FileClient(root)
    root.mainloop()