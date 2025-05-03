import argparse
import io
import json
import os
import requests
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

# 设置标准输出编码为 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 基础路径配置
SCRIPT_DIR = Path(__file__).parent.absolute()
DIST_DIR = SCRIPT_DIR / "dist"
RELEASE_DIR = SCRIPT_DIR / "release"
RESOURCE_DIR = SCRIPT_DIR / "resource"
SRC_DIR = SCRIPT_DIR / "src"
BUILD_DIR = SCRIPT_DIR / "build"
CACHE_DIR = SCRIPT_DIR / "cache"

# 确保必要目录存在
for dir_path in [CACHE_DIR, RESOURCE_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# GitHub API 配置
REPO_API_URLS = {
    "SMAPI": "https://api.github.com/repos/Pathoschild/SMAPI/releases/latest",
    "Stardrop": "https://api.github.com/repos/Floogen/Stardrop/releases/latest"
}

ZIP_FILENAME_TEMPLATES = {
    "SMAPI": "SMAPI-{version}-installer.zip",
    "Stardrop": "Stardrop-win-x64.zip"
}

# 构建配置
BUILD_ITEMS = [
    ("SVModInstaller.py", "SVModInstaller"),
    ("SVPathFinder.py", "SVPathFinder")
]

# ====== Update 相关函数 ======


def get_cache_file_path(repo_name):
    return os.path.join(CACHE_DIR, f"{repo_name}_release_info.json")


def is_cache_valid(repo_name):
    cache_file = get_cache_file_path(repo_name)
    if os.path.exists(cache_file):
        file_time = os.path.getmtime(cache_file)
        if time.time() - file_time < 3600:  # 1小时
            return True
    return False


def load_cache(repo_name):
    cache_file = get_cache_file_path(repo_name)
    with open(cache_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_cache(repo_name, data):
    cache_file = get_cache_file_path(repo_name)
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_latest_zip_info(repo_name, api_url, headers=None):
    if is_cache_valid(repo_name):
        print(f"[{repo_name}] 使用缓存数据...")
        data = load_cache(repo_name)
    else:
        print(f"[{repo_name}] 请求 GitHub API 获取最新版本...")
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            save_cache(repo_name, data)
        else:
            print(f"请求失败，状态码：{response.status_code}")
            return None

    version = data['tag_name']
    zip_template = ZIP_FILENAME_TEMPLATES.get(repo_name)
    zip_url = None

    if zip_template:
        target_zip_name = zip_template.format(version=version)
        for asset in data['assets']:
            if asset['name'] == target_zip_name:
                zip_url = asset['browser_download_url']
                break
    else:
        target_zip_name = None

    print(f"[{repo_name}] 最新版本: {version}")
    if zip_url:
        print(f"[{repo_name}] 匹配到指定 ZIP 文件: {target_zip_name}")
        print(f"[{repo_name}] 下载地址: {zip_url}\n")
    else:
        print(f"[{repo_name}] 未找到指定的 ZIP 文件: {target_zip_name}\n")

    return {
        "version": version,
        "zip_url": zip_url,
        "target_zip_name": target_zip_name
    }


def download_zip(repo_name, zip_url, target_zip_name):
    if not zip_url or not target_zip_name:
        print(f"[{repo_name}] 无效的下载信息，跳过下载。")
        return

    zip_path = os.path.join(RESOURCE_DIR, target_zip_name)
    print(f"[{repo_name}] 正在下载 ZIP 到: {zip_path}")

    try:
        response = requests.get(zip_url, stream=True)
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        print(f"[{repo_name}] ZIP 下载完成: {target_zip_name}")
    except Exception as e:
        print(f"[{repo_name}] 下载失败: {str(e)}")

# ====== Build 相关函数 ======


def clean_build_dirs():
    """清理构建目录"""
    for dir_name in [BUILD_DIR, DIST_DIR]:
        if dir_name.exists():
            shutil.rmtree(dir_name)

    for spec_file in SCRIPT_DIR.glob("*.spec"):
        try:
            spec_file.unlink()
        except Exception as e:
            print(f"无法删除 {spec_file}: {e}")


def build_exe(py_file: str, exe_name: str):
    print(f"正在构建 {exe_name}...")

    cmd = [
        'pyinstaller', '--noconfirm', '--onefile', '--clean',
        '--distpath', str(DIST_DIR),
        '--workpath', str(BUILD_DIR),
        '--name', exe_name,
        '--hidden-import', 'win32com.client',
        '--hidden-import', 'pywinauto.application',
        '--hidden-import', 'vdf',
        str(SRC_DIR / py_file)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"构建失败: {result.stderr}")
        return False

    print(f"{exe_name} 构建完成")
    return True

# ====== Release 相关函数 ======


def create_release_dir(release_name: str) -> Path:
    release_dir = RELEASE_DIR / release_name
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir(parents=True)
    return release_dir


def copy_files(src_paths, dest_dir: Path):
    for src in src_paths:
        if src.exists():
            shutil.copy2(src, dest_dir)


def package_zip(release_dir: Path, zip_name: str):
    release_zip = RELEASE_DIR / f"{zip_name}.zip"
    with zipfile.ZipFile(release_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in release_dir.rglob("*"):
            if file.is_file():
                zipf.write(file, file.relative_to(release_dir))
    return release_zip


def build_release_package(release_name: str, zip_name: str, files_to_copy):
    release_dir = create_release_dir(release_name)
    copy_files(files_to_copy, release_dir)
    release_zip = package_zip(release_dir, zip_name)
    shutil.rmtree(release_dir)
    print(f"发布包已创建: {release_zip}")
    return release_zip


def create_release_zip(version: str):
    release_name = f"SVModsInstall_v{version}"
    zip_name = release_name
    exe_path = DIST_DIR / "SVModInstaller.exe"
    readme_path = SCRIPT_DIR / "INSTALL.md"
    zip_files = list(RESOURCE_DIR.glob("*.zip"))
    files_to_copy = [exe_path, readme_path] + zip_files
    build_release_package(release_name, zip_name, files_to_copy)


def create_sv_path_finder_zip(version: str):
    release_name = f"SVPathFinder_v{version}"
    zip_name = release_name
    exe_path = DIST_DIR / "SVPathFinder.exe"
    readme_path = SCRIPT_DIR / "INTRODUCTION.md"
    files_to_copy = [exe_path, readme_path]
    build_release_package(release_name, zip_name, files_to_copy)

# ====== 主函数 ======


def main():
    parser = argparse.ArgumentParser(description="星露谷模组安装器项目工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # update 命令
    update_parser = subparsers.add_parser('update', help='更新模组文件')

    # build 命令
    build_parser = subparsers.add_parser('build', help='构建可执行文件')
    build_parser.add_argument(
        "--sv-mod-installer", "-i", action="store_true", help="构建SVModInstaller.exe")
    build_parser.add_argument("--sv-path-finder", "-p",
                              action="store_true", help="构建SVPathFinder.exe")
    build_parser.add_argument(
        "--all", "-a", action="store_true", help="构建所有文件")

    # release 命令
    release_parser = subparsers.add_parser('release', help='创建发布包')
    release_parser.add_argument("--version", "-v", help="指定版本号，默认使用当前日期")

    args = parser.parse_args()

    if args.command == 'update':
        for repo_name, api_url in REPO_API_URLS.items():
            result = get_latest_zip_info(repo_name, api_url)
            if result:
                download_zip(repo_name, result.get('zip_url'),
                             result.get('target_zip_name'))

    elif args.command == 'build':
        if not SRC_DIR.exists() or not RESOURCE_DIR.exists():
            print("错误: src或resource目录不存在")
            return

        build_targets = []
        if args.sv_mod_installer:
            build_targets.append("SVModInstaller.py")
        if args.sv_path_finder:
            build_targets.append("SVPathFinder.py")
        if args.all:
            build_targets = [item[0] for item in BUILD_ITEMS]
        if not build_targets:
            build_targets = ["SVModInstaller.py"]  # 默认只构建SVModInstaller

        clean_build_dirs()
        success = True
        for py_file, exe_name in BUILD_ITEMS:
            if py_file in build_targets:
                if not build_exe(py_file, exe_name):
                    success = False
                    break

        if success:
            for spec_file in SCRIPT_DIR.glob("*.spec"):
                try:
                    spec_file.unlink()
                except Exception as e:
                    print(f"无法删除 {spec_file}: {e}")
            print("所有文件构建完成")
        else:
            print("部分文件构建失败")

    elif args.command == 'release':
        if not DIST_DIR.exists():
            print("错误: 请先运行 build 命令生成 exe 文件")
            return

        RELEASE_DIR.mkdir(exist_ok=True)
        version = args.version or datetime.now().strftime("%Y%m%d")
        create_release_zip(version)
        create_sv_path_finder_zip(version)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
