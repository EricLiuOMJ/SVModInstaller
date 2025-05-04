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
from pathlib import Path
from typing import Union, Dict, List, Optional, Any
from src.tool import Colors, print_color, get_project_version

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
    dir_path.mkdir(exist_ok=True)

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


def get_cache_file_path(repo_name: str) -> Path:
    return CACHE_DIR / f"{repo_name}_release_info.json"


def is_cache_valid(repo_name: str) -> bool:
    cache_file = get_cache_file_path(repo_name)
    if cache_file.exists():
        file_time = cache_file.stat().st_mtime
        if time.time() - file_time < 3600:  # 1小时
            return True
    return False


def load_cache(repo_name: str) -> Dict[str, Any]:
    cache_file = get_cache_file_path(repo_name)
    with open(cache_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_cache(repo_name: str, data: Dict[str, Any]) -> None:
    cache_file = get_cache_file_path(repo_name)
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_latest_zip_info(repo_name: str, api_url: str, headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    if is_cache_valid(repo_name):
        print_color(f"[{repo_name}] 使用缓存数据...", Colors.BLUE)
        data = load_cache(repo_name)
    else:
        print_color(f"[{repo_name}] 请求 GitHub API 获取最新版本...", Colors.YELLOW)
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            save_cache(repo_name, data)
        else:
            print_color(f"请求失败，状态码：{response.status_code}", Colors.RED)
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

    print_color(f"[{repo_name}] 最新版本: {version}", Colors.GREEN)
    if zip_url:
        print_color(
            f"[{repo_name}] 匹配到指定 ZIP 文件: {target_zip_name}", Colors.GREEN)
        print_color(f"[{repo_name}] 下载地址: {zip_url}", Colors.BLUE)
    else:
        print_color(
            f"[{repo_name}] 未找到指定的 ZIP 文件: {target_zip_name}", Colors.RED)

    return {
        "version": version,
        "zip_url": zip_url,
        "target_zip_name": target_zip_name
    }


def download_zip(repo_name: str, zip_url: Optional[str], target_zip_name: Optional[str]) -> None:
    if not zip_url or not target_zip_name:
        print_color(f"[{repo_name}] 无效的下载信息，跳过下载。", Colors.RED)
        return

    zip_path = RESOURCE_DIR / target_zip_name
    print_color(f"[{repo_name}] 正在下载 ZIP 到: {zip_path}", Colors.YELLOW)

    try:
        response = requests.get(zip_url, stream=True)
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        print_color(f"[{repo_name}] ZIP 下载完成: {target_zip_name}", Colors.GREEN)
    except Exception as e:
        print_color(f"[{repo_name}] 下载失败: {str(e)}", Colors.RED)

# ====== Build 相关函数 ======


def clean_build_dirs() -> None:
    """清理构建目录"""
    for dir_name in [BUILD_DIR, DIST_DIR]:
        if dir_name.exists():
            shutil.rmtree(dir_name)
            print_color(f"已清理目录: {dir_name}", Colors.YELLOW)

    for spec_file in SCRIPT_DIR.glob("*.spec"):
        try:
            spec_file.unlink()
            print_color(f"已删除: {spec_file}", Colors.YELLOW)
        except Exception as e:
            print_color(f"无法删除 {spec_file}: {e}", Colors.RED)


def build_exe(py_file: str, exe_name: str) -> bool:
    print_color(f"正在构建 {exe_name}...", Colors.YELLOW)

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

    try:
        # 使用 check=True 会在返回码非零时自动抛出 CalledProcessError
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
        # 打印 PyInstaller 的部分输出（如果需要调试）
        # print_color(f"PyInstaller 输出:\n{result.stdout}", Colors.BLUE)
    except subprocess.CalledProcessError as e:
        print_color(f"构建 {exe_name} 失败! 返回码: {e.returncode}", Colors.RED)
        # 打印更详细的错误信息
        print_color(f"错误输出:\n{e.stderr}", Colors.RED)
        return False
    except Exception as e:
        print_color(f"构建 {exe_name} 时发生未知错误: {e}", Colors.RED)
        return False

    print_color(f"{exe_name} 构建完成", Colors.GREEN)
    return True


def run_build_all() -> bool:
    print_color("开始执行 build --all...", Colors.YELLOW)
    if not SRC_DIR.exists() or not RESOURCE_DIR.exists():
        print_color("错误: src或resource目录不存在", Colors.RED)
        return False

    build_targets = [item[0] for item in BUILD_ITEMS]
    print_color("构建所有目标", Colors.BLUE)

    clean_build_dirs()
    success = all(
        build_exe(py_file, exe_name)
        for py_file, exe_name in BUILD_ITEMS
    )

    if success:
        for spec_file in SCRIPT_DIR.glob("*.spec"):
            try:
                spec_file.unlink()
            except Exception as e:
                print_color(f"无法删除 {spec_file}: {e}", Colors.RED)
        print_color("所有文件构建完成", Colors.GREEN)
        return True
    else:
        print_color("部分文件构建失败", Colors.RED)
        return False

# ====== Release 相关函数 ======


def build_release_package(release_name: str, zip_name: str, files_to_copy: List[Path]) -> Path:
    release_dir = RELEASE_DIR / release_name
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir(parents=True)

    # 直接复制文件并创建压缩包
    for src in files_to_copy:
        if src.exists():
            shutil.copy2(src, release_dir)
            print_color(f"已复制: {src} -> {release_dir}", Colors.BLUE)
        else:
            print_color(f"文件不存在，跳过: {src}", Colors.RED)

    release_zip = RELEASE_DIR / f"{zip_name}.zip"
    with zipfile.ZipFile(release_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in release_dir.rglob("*"):
            if file.is_file():
                zipf.write(file, file.relative_to(release_dir))

    shutil.rmtree(release_dir)
    print_color(f"发布包已创建: {release_zip}", Colors.GREEN)
    return release_zip


def create_release_zip(version: str) -> Path:
    release_name = f"SVModsInstall_v{version}"
    zip_name = release_name
    exe_path = DIST_DIR / "SVModInstaller.exe"
    readme_path = SCRIPT_DIR / "INSTALL.md"
    zip_files = list(RESOURCE_DIR.glob("*.zip"))
    files_to_copy = [exe_path, readme_path] + zip_files
    return build_release_package(release_name, zip_name, files_to_copy)


def create_sv_path_finder_zip(version: str) -> Path:
    release_name = f"SVPathFinder_v{version}"
    zip_name = release_name
    exe_path = DIST_DIR / "SVPathFinder.exe"
    readme_path = SCRIPT_DIR / "INTRODUCTION.md"
    files_to_copy = [exe_path, readme_path]
    return build_release_package(release_name, zip_name, files_to_copy)


# ====== 主函数 ======

def main():
    parser = argparse.ArgumentParser(description="星露谷模组安装器项目工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # update 命令
    subparsers.add_parser('update', help='更新模组文件')

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

    # replace 命令
    replace_parser = subparsers.add_parser('replace', help='替换更新过的exe')

    args = parser.parse_args()

    if args.command == 'update':
        print_color("开始更新模组文件...", Colors.YELLOW)
        for repo_name, api_url in REPO_API_URLS.items():
            result = get_latest_zip_info(repo_name, api_url)
            if result:
                download_zip(repo_name, result.get('zip_url'),
                             result.get('target_zip_name'))
        print_color("更新完成", Colors.GREEN)

    elif args.command == 'build':
        if args.all:
            run_build_all()
        else:
            if not SRC_DIR.exists() or not RESOURCE_DIR.exists():
                print_color("错误: src或resource目录不存在", Colors.RED)
                return

            build_targets = []
            if args.sv_mod_installer:
                build_targets.append("SVModInstaller.py")
            if args.sv_path_finder:
                build_targets.append("SVPathFinder.py")
            if not build_targets:
                build_targets = ["SVModInstaller.py"]  # 默认只构建SVModInstaller
            print_color(f"构建目标: {', '.join(build_targets)}", Colors.BLUE)

            clean_build_dirs()
            success = all(
                build_exe(py_file, exe_name)
                for py_file, exe_name in BUILD_ITEMS
                if py_file in build_targets
            )

            if success:
                for spec_file in SCRIPT_DIR.glob("*.spec"):
                    try:
                        spec_file.unlink()
                    except Exception as e:
                        print_color(f"无法删除 {spec_file}: {e}", Colors.RED)
                print_color("指定文件构建完成", Colors.GREEN)  # 修改提示信息
            else:
                print_color("部分文件构建失败", Colors.RED)

    elif args.command == 'release':
        if not DIST_DIR.exists():
            print_color("错误: 请先运行 build 命令生成 exe 文件", Colors.RED)
            return

        RELEASE_DIR.mkdir(exist_ok=True)

        # 调用 get_project_version 并传递 SCRIPT_DIR 和 RELEASE_DIR
        version = get_project_version(args.version, SCRIPT_DIR, RELEASE_DIR)
        if not version:
            print_color("错误: 无法确定版本号，无法创建发布包。", Colors.RED)
            return

        create_release_zip(version)
        create_sv_path_finder_zip(version)
        print_color("发布包创建完成", Colors.GREEN)

    elif args.command == 'replace':
        print_color("首先执行 build --all...", Colors.CYAN)
        build_success = run_build_all()
        if not build_success:
            print_color("构建失败，无法继续执行替换操作。", Colors.RED)
            return

        print_color("\n开始替换发布包中的 SVModInstaller.exe...", Colors.YELLOW)

        version = get_project_version(None, SCRIPT_DIR, RELEASE_DIR)
        if not version:
            print_color("错误: 无法确定版本号，无法执行替换。", Colors.RED)
            return

        source_exe = DIST_DIR / "SVModInstaller.exe"
        release_name = f"SVModsInstall_v{version}"
        destination_dir = RELEASE_DIR / release_name
        destination_exe = destination_dir / "SVModInstaller.exe"

        if not source_exe.exists():
            print_color(f"错误: 源文件不存在: {source_exe}", Colors.RED)
            return

        if not destination_dir.exists():
            print_color(f"错误: 目标发布目录不存在: {destination_dir}", Colors.RED)
            print_color("请先运行 release 命令创建发布包", Colors.YELLOW)
            return

        try:
            shutil.copy2(source_exe, destination_exe)
            print_color(
                f"已将 {source_exe.name} 复制到 {destination_dir}", Colors.GREEN)
            print_color("替换完成", Colors.GREEN)
        except PermissionError as e:
            print_color(f"替换文件时权限错误: {e}", Colors.RED)
            print_color("请确保目标文件没有正在运行，并尝试以管理员身份运行此脚本。", Colors.YELLOW)
        except Exception as e:
            print_color(f"替换文件时发生其他错误: {e}", Colors.RED)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
