import sys
from pathlib import Path

def get_data_dir() -> Path:
    """获取用户数据(文件/数据库)存放的根目录"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的环境：存放在 exe 所在目录
        return Path(sys.executable).parent
    # 开发环境：存放在项目根目录
    return Path(__file__).parent.parent
