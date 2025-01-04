import socket
import os
import json
from threading import Thread

class FileServer:
    def __init__(self, host='localhost', port=9999):
        self.host = host
        self.port = port
        self.server_dir = 'server_files'
        
        if not os.path.exists(self.server_dir):
            os.makedirs(self.server_dir)
            
    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"服务器启动在 {self.host}:{self.port}")
        
        while True:
            client, addr = self.sock.accept()
            print(f"客户端连接: {addr}")
            Thread(target=self.handle_client, args=(client,)).start()
    
    def get_directory_structure(self, path):
        """获取目录结构"""
        items = []
        for item in os.listdir(path):
            full_path = os.path.join(path, item)
            relative_path = os.path.relpath(full_path, self.server_dir)
            items.append({
                'name': item,
                'path': relative_path,
                'is_dir': os.path.isdir(full_path)
            })
        return items

    def handle_client(self, client):
        while True:
            try:
                cmd = json.loads(client.recv(1024).decode())
                print(f"收到命令: {cmd}")
                
                if cmd['type'] == 'list':
                    # 获取指定目录的内容
                    target_dir = os.path.join(self.server_dir, cmd.get('path', ''))
                    if not os.path.exists(target_dir):
                        client.send(json.dumps({'error': '目录不存在'}).encode())
                        continue
                        
                    items = self.get_directory_structure(target_dir)
                    client.send(json.dumps(items).encode())
                    
                elif cmd['type'] == 'get':
                    filepath = os.path.join(self.server_dir, cmd['path'])
                    if os.path.exists(filepath) and os.path.isfile(filepath):
                        # 先发送文件大小
                        file_size = os.path.getsize(filepath)
                        client.send(str(file_size).encode())
                        client.recv(1024)  # 等待客户端确认
                        
                        with open(filepath, 'rb') as f:
                            while True:
                                data = f.read(1024)
                                if not data:
                                    break
                                client.send(data)
                        print(f"文件 {cmd['path']} 发送完成")
                    
                elif cmd['type'] == 'put':
                    filepath = os.path.join(self.server_dir, cmd['path'])
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    
                    file_size = int(cmd['size'])
                    client.send(b'ready')
                    
                    received_size = 0
                    with open(filepath, 'wb') as f:
                        while received_size < file_size:
                            data = client.recv(min(1024, file_size - received_size))
                            received_size += len(data)
                            f.write(data)
                    print(f"文件 {cmd['path']} 接收完成")
                
                elif cmd['type'] == 'mkdir':
                    # 创建目录
                    dirpath = os.path.join(self.server_dir, cmd['path'])
                    os.makedirs(dirpath, exist_ok=True)
                    client.send(b'ok')
                    print(f"创建目录: {cmd['path']}")
                    
            except Exception as e:
                print(f"错误: {e}")
                break
        client.close()
        print("客户端连接断开")

if __name__ == '__main__':
    server = FileServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n服务器关闭")
    except Exception as e:
        print(f"服务器错误: {e}")