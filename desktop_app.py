import sys
from pathlib import Path
import threading
import time
import uvicorn
import webview
import socket
from api.server import app

def get_free_port():
    """动态获取一个未被占用的端口"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

class ServerThread(threading.Thread):
    def __init__(self, port):
        super().__init__(daemon=True) # 设为守护线程，主进程退出时自动结束
        self.port = port
        self.server = None

    def run(self):
        # 取消 reload，生产环境不需要热重载
        config = uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="warning")
        self.server = uvicorn.Server(config)
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True

def main():
    # 捕获特殊启动参数，以实现在免 Python 环境下生成原生扫码提取窗口
    if len(sys.argv) > 1:
        if sys.argv[1] == "--fetch-cookie":
            from utils import ui_cookie_fetcher
            ui_cookie_fetcher.main()
            return
        elif sys.argv[1] == "--run-download":
            import os
            try:
                sys.stdout = os.fdopen(1, 'w', encoding='utf-8')
                sys.stderr = os.fdopen(2, 'w', encoding='utf-8')
            except Exception:
                pass
            # 确保工作目录与 run.py 行为一致：指向 exe 所在目录
            if getattr(sys, 'frozen', False):
                os.chdir(str(Path(sys.executable).parent))
            sys.argv.pop(1) # 移除注入指令，防止被内置的 argparse 捕捉报错
            from cli.main import main as download_main
            download_main()
            return
        elif sys.argv[1] == "--run-whisper":
            import os
            try:
                sys.stdout = os.fdopen(1, 'w', encoding='utf-8')
                sys.stderr = os.fdopen(2, 'w', encoding='utf-8')
            except Exception:
                pass
            sys.argv.pop(1) # 移除注入指令
            from cli.whisper_transcribe import main as whisper_main
            whisper_main()
            return

    port = get_free_port()
    
    # 启动后台 FastAPI 服务
    server_thread = ServerThread(port)
    server_thread.start()

    # 稍微等待后端服务初始化
    time.sleep(1.5)

    # 创建并在主线程中启动系统原生窗口
    webview.create_window(
        '抖音批量下载器 (Douyin Downloader)',
        f'http://127.0.0.1:{port}',
        width=1200,
        height=800,
        min_size=(900, 600),
        background_color='#0f172a' # 匹配前端深色主题背景
    )
    
    # 阻塞运行，直到用户关闭窗口
    # 正式生产环境：关闭 debug 以隐去控制台开发面板
    webview.start(debug=False)
    
    # 窗口关闭后，安全退出后端服务
    server_thread.stop()
    server_thread.join(timeout=2)

if __name__ == '__main__':
    main()
