import os
import shutil
import subprocess
from pathlib import Path

def print_step(msg):
    print(f"\n{'='*50}\n>> {msg}\n{'='*50}")

def run_cmd(cmd, cwd=None):
    subprocess.run(cmd, shell=True, check=True, cwd=cwd)

def main():
    base_dir = Path(__file__).parent.absolute()
    web_dir = base_dir / "web"
    dist_dir = base_dir / "dist"
    build_dir = base_dir / "build"
    
    # 1. 构建前端
    print_step("Step 1: 构建 React 前端静态资源 ( npm run build )")
    run_cmd("npm install", cwd=str(web_dir))
    run_cmd("npm run build", cwd=str(web_dir))
    
    # 2. 清理旧构建
    print_step("Step 2: 清理旧的构建产物")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
        
    try:
        # 3. 执行 PyInstaller 打包 (对明文代码进行依赖追踪)
        print_step("Step 3: 执行 PyInstaller 封装主程序与追踪全部依赖库")
        import sys
        scripts_dir = Path(sys.executable).parent
        pyarmor_exe = scripts_dir / "pyarmor.exe" if (scripts_dir / "pyarmor.exe").exists() else "pyarmor"
        pyinstaller_exe = scripts_dir / "pyinstaller.exe" if (scripts_dir / "pyinstaller.exe").exists() else "pyinstaller"

        hidden_imports = (
            "--collect-all fastapi --collect-all uvicorn --collect-all starlette --collect-all pydantic --collect-all webview "
            "--collect-all aiosqlite --collect-all aiohttp --collect-all aiofiles --collect-all rich --collect-all yaml --collect-all auth "
            "--collect-all gmssl "
            "--hidden-import=fastapi.middleware.cors --hidden-import=fastapi.staticfiles --hidden-import=fastapi.responses "
            "--hidden-import=uvicorn.logging --hidden-import=uvicorn.loops --hidden-import=uvicorn.loops.auto "
            "--hidden-import=uvicorn.protocols --hidden-import=uvicorn.protocols.http --hidden-import=uvicorn.protocols.http.auto "
            "--hidden-import=uvicorn.protocols.websockets --hidden-import=uvicorn.protocols.websockets.auto "
            "--hidden-import=uvicorn.lifespan.on --hidden-import=uvicorn.lifespan.off"
        )
        
        frontend_data = f'"{web_dir / "dist"}{os.pathsep}web/dist"'
        icon_path = base_dir / 'app_icon.ico'
        icon_arg = f'--icon "{icon_path}"' if icon_path.exists() else ''
        pyinstaller_cmd = (
            f'"{pyinstaller_exe}" --noconfirm --windowed --name DouyinDownloader '
            f'{hidden_imports} --add-data {frontend_data} {icon_arg} '
            f'desktop_app.py'  # 用明文代码生成以避免丢失 webview 以及任何第三方库
        )
        print(f"执行明文分析与打包: {pyinstaller_cmd}")
        run_cmd(pyinstaller_cmd, cwd=str(base_dir))

        # 4. 执行 PyArmor 混合加密并覆盖替换
        print_step("Step 4: 加密核心源码并无损替换进发行包")
        pyarmor_cmd = f'"{pyarmor_exe}" gen -O dist_obf -r api auth cli config control core storage utils'
        print(f"安全产出加密字节码: {pyarmor_cmd}")
        run_cmd(pyarmor_cmd, cwd=str(base_dir))
        
        # 将打包产生的加密文件夹热替换进 _internal 中
        internal_dir = base_dir / 'dist' / 'DouyinDownloader' / '_internal'
        dist_obf = base_dir / 'dist_obf'
        
        print("注入混合加密模块与底层运行时库...")
        for item in dist_obf.iterdir():
            target = internal_dir / item.name
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)
                
        # 清理多余临时文件
        shutil.rmtree(dist_obf)

        # 5. 还原不可混淆的签名模块（PyArmor 会破坏其加密运算逻辑）
        print("还原签名算法模块（xbogus/abogus 不可混淆）...")
        sign_files = ["xbogus.py", "abogus.py"]
        for fname in sign_files:
            src = base_dir / "utils" / fname
            dst = internal_dir / "utils" / fname
            if src.exists():
                shutil.copy2(src, dst)
                print(f"  ✓ 还原 utils/{fname}")
        
        # 6. 补充环境文件（不复制项目 config.yml，仅在无配置时放模板）
        print("写入外置环境配置...")
        target_dir = base_dir / 'dist' / 'DouyinDownloader'
        target_config = target_dir / 'config.yml'
        if not target_config.exists():
            if (base_dir / 'config.example.yml').exists():
                shutil.copy2(base_dir / 'config.example.yml', target_config)
                print("  ✓ 已从 config.example.yml 生成初始配置")
            else:
                print("  ⚠ 未找到 config.example.yml，请手动添加 config.yml")
        else:
            print("  ✓ 保留已有 config.yml（未覆盖）")

        print_step("编译防护注入完毕！✅")
        print(f"请双击运行并验证: {target_dir / 'DouyinDownloader.exe'}")

    except subprocess.CalledProcessError as e:
        print_step("❌ 打包过程出现错误，请检查日志。")
        print(str(e))

if __name__ == "__main__":
    main()
