import yaml
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from utils.paths import get_data_dir

router = APIRouter()
CONFIG_PATH = get_data_dir() / "config.yml"

@router.get("/")
def get_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="Config file not found")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    config_dict = yaml.safe_load(content) or {}
    
    # 从原始文件中提取被注释掉的链接行 (#- https://...)
    import re
    commented = re.findall(r'^#- *(https?://\S+)', content, re.MULTILINE)
    if commented:
        if not isinstance(config_dict.get('link'), list):
            config_dict['link'] = []
        for url in commented:
            config_dict['link'].append("# " + url)

    return config_dict

@router.post("/")
def save_config(config_data: Dict[str, Any]):
    
    if CONFIG_PATH.exists():
        backup_path = CONFIG_PATH.with_suffix(".yml.bak")
        backup_path.write_text(CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    
    # 分离出被忽略的链接URL（去掉#前缀）
    all_links = config_data.get('link', []) or []
    ignored_urls = set()
    clean_links = []
    for link in all_links:
        if isinstance(link, str) and link.startswith('#'):
            url = link.lstrip('#').strip()
            ignored_urls.add(url)
            clean_links.append(url)  # 先全部当正常链接写入
        else:
            clean_links.append(link)
    
    config_data['link'] = clean_links
    yaml_text = yaml.dump(config_data, allow_unicode=True, sort_keys=False)
    
    # 在输出文本中，对被忽略的链接行首直接加 #
    for url in ignored_urls:
        yaml_text = yaml_text.replace(f"- {url}", f"#- {url}")
    
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(yaml_text)
        
    return {"status": "success", "message": "Configuration saved"}

@router.post("/pick_folder")
def pick_folder():
    import subprocess
    
    ps_script = (
        '[System.Reflection.Assembly]::LoadWithPartialName("System.windows.forms") | Out-Null; '
        '$f = New-Object System.Windows.Forms.FolderBrowserDialog; '
        '$f.Description = "选择下载保存路径"; '
        'if ($f.ShowDialog() -eq "OK") { $f.SelectedPath } else { "" }'
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True, text=True, timeout=120,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    folder_path = result.stdout.strip()
    
    if folder_path:
        return {"path": folder_path}
    else:
        return {"path": None}

@router.get("/fetch_cookie")
def fetch_cookie():
    import sys
    import json
    import subprocess
    from pathlib import Path
    
    # 因为 get_data_dir() 获取的是实际的运行时持久化路径
    # 而 ui_cookie_fetcher.py 是源码文件
    base = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent.parent.parent
    
    target_script = base / "_internal" / "utils" / "ui_cookie_fetcher.py"
    if not target_script.exists():
        target_script = base / "utils" / "ui_cookie_fetcher.py" # 尝试直接从utils下找
        
    if getattr(sys, 'frozen', False) and getattr(sys, '_MEIPASS', None):
         # MEIPASS 为解压目录方案准备
         if not target_script.exists():
              target_script = Path(sys._MEIPASS) / "utils" / "ui_cookie_fetcher.py"

    run_args = [sys.executable, str(target_script)]
    if getattr(sys, 'frozen', False):
         # 独立打包模式下 sys.executable 是主程序的exe，直接追加我们约定的触发参数
         run_args = [sys.executable, "--fetch-cookie"]
    elif not target_script.exists():
         raise HTTPException(status_code=500, detail=f"找不到安全扫码核心组件: {target_script}")

    try:
        # 不使用 startupinfo 隐藏窗口，否则会连带着把扫码浏览器窗口完全隐形
        process = subprocess.Popen(
            run_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        stdout_data, _ = process.communicate(timeout=600) # 给 10 分钟慢慢扫
    except subprocess.TimeoutExpired:
        process.kill()
        raise HTTPException(status_code=408, detail="获取超时，用户未能及时扫码")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部拉起错误: {str(e)}")

    if not stdout_data.strip():
         raise HTTPException(status_code=400, detail="提取失败：扫码未完成即被关闭。")
    
    # 从最后面开始找，防抖
    lines = stdout_data.strip().split('\n')
    for line in reversed(lines):
        if 'msToken' in line or '{' in line:
            try:
                res = json.loads(line)
                if isinstance(res, dict) and "msToken" in res:
                    return {"status": "success", "data": res}
            except:
                continue

    raise HTTPException(status_code=500, detail=f"解析 Cookie 错误: {stdout_data}")
