import sys
import time
import json
import threading
import webview

def poll_cookies(window):
    """
    后台轮询抓取 Cookie，并在凑齐特定关键字段时自动返回结果并销毁视窗
    """
    time.sleep(2)
    # sid_guard 不是绝对必须立刻获得的，但能拿到最好，我们主要检测这 4 个必备
    REQUIRED_KEYS = {"msToken", "ttwid", "odin_tt", "passport_csrf_token"}
    results = {}
    
    while True:
        try:
            cookies = window.get_cookies()
            if not cookies:
                time.sleep(1)
                continue
                
            for c in cookies:
                # 兼容 pywebview 的不同版本（字典、Morsel 或 Cookie 对象）
                if isinstance(c, dict):
                    name = c.get('name', c.get('key'))
                    value = c.get('value')
                else:
                    name = getattr(c, 'name', getattr(c, 'key', None))
                    value = getattr(c, 'value', None)
                    
                if name and value:
                    if name in REQUIRED_KEYS or name == "sid_guard":
                        results[name] = value

            # 如果收集进度达到了标准（必须字段全部都有）
            if len(set(results.keys()) & REQUIRED_KEYS) == len(REQUIRED_KEYS):
                # 以 JSON 形式仅将数据打印到 stdout，后端通过捕获 stdout 获得
                print(json.dumps(results, ensure_ascii=False))
                
                # 给界面一点成功感提示，并自动关闭
                window.evaluate_js("document.body.innerHTML = '<h1 style=\"display:flex;justify-content:center;align-items:center;height:100vh;color:green;font-family:sans-serif;\">授权成功，请回到主界面继续！(窗口自动关闭中...)</h1>';")
                time.sleep(1.5)
                window.destroy()
                return

        except Exception:
            pass
        
        time.sleep(1)

def on_closed():
    # 如果用户未扫码主动关闭了窗口，并且程序没退出，则什么也不打印
    pass

def main():
    window = webview.create_window(
        "安全网页授权 - 抖音 (请扫码登录，登录成功自动关闭)", 
        "https://www.douyin.com/",
        width=1100,
        height=700,
    )
    window.events.closed += on_closed
    
    t = threading.Thread(target=poll_cookies, args=(window,))
    t.daemon = True
    t.start()
    
    try:
        webview.start(private_mode=False)
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    main()
