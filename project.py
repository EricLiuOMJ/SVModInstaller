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
import logging
from pathlib import Path
from typing import Union, Dict, List, Optional, Any
from src.tool import (
    print_info, print_warning, print_error, print_success, print_step, print_white,
    get_project_version
)

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
LOGS_DIR = SCRIPT_DIR / "logs"

# 确保必要目录存在
for dir_path in [CACHE_DIR, RESOURCE_DIR, LOGS_DIR]:
    dir_path.mkdir(exist_ok=True)

log_file_project = LOGS_DIR / "project_tool.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=log_file_project,
    filemode='a',
    encoding='utf-8'
)

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
        print_info(f"[{repo_name}] 使用缓存数据...")
        data = load_cache(repo_name)
    else:
        print_warning(f"[{repo_name}] 请求 GitHub API 获取最新版本...")
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            save_cache(repo_name, data)
        else:
            print_error(f"请求失败，状态码：{response.status_code}")
            logging.error(
                f"[{repo_name}] GitHub API 请求失败，URL: {api_url}, 状态码: {response.status_code}, 响应: {response.text}")
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

    print_success(f"[{repo_name}] 最新版本: {version}")
    if zip_url:
        print_success(
            f"[{repo_name}] 匹配到指定 ZIP 文件: {target_zip_name}")
        print_info(f"[{repo_name}] 下载地址: {zip_url}")
    else:
        zip_name_str = target_zip_name if target_zip_name else "未指定模板"
        print_error(
            f"[{repo_name}] 未找到指定的 ZIP 文件: {zip_name_str}")

    return {
        "version": version,
        "zip_url": zip_url,
        "target_zip_name": target_zip_name
    }


def download_zip(repo_name: str, zip_url: Optional[str], target_zip_name: Optional[str]) -> None:
    if not zip_url or not target_zip_name:
        print_error(f"[{repo_name}] 无效的下载信息，跳过下载。")
        return

    zip_path = RESOURCE_DIR / target_zip_name
    print_warning(f"[{repo_name}] 正在下载 ZIP 到: {zip_path}")

    try:
        response = requests.get(zip_url, stream=True, timeout=60)
        response.raise_for_status()
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print_success(f"[{repo_name}] ZIP 下载完成: {target_zip_name}")
    except requests.exceptions.RequestException as e:
        print_error(f"[{repo_name}] 下载时发生网络错误: {str(e)}")
        logging.exception(f"[{repo_name}] 下载 ZIP ({target_zip_name}) 时发生网络错误:")
    except Exception as e:
        print_error(f"[{repo_name}] 下载或写入文件时失败: {str(e)}")
        logging.exception(f"[{repo_name}] 下载或写入 ZIP ({target_zip_name}) 时失败:")
        # 尝试删除不完整的文件
        if zip_path.exists():
            try:
                zip_path.unlink()
                print_warning(f"[{repo_name}] 已删除不完整的下载文件: {zip_path.name}")
            except Exception as del_e:
                print_error(f"[{repo_name}] 删除不完整文件失败: {del_e}")

# ====== Build 相关函数 ======


def clean_build_dirs() -> None:
    """清理构建目录"""
    for dir_name in [BUILD_DIR, DIST_DIR]:
        if dir_name.exists():
            try:
                shutil.rmtree(dir_name)
                print_warning(f"已清理目录: {dir_name}")
            except Exception as e:
                print_error(f"清理目录 {dir_name} 时出错: {e}")
                logging.exception(f"清理目录 {dir_name} 时出错:")

    for spec_file in SCRIPT_DIR.glob("*.spec"):
        try:
            spec_file.unlink()
            print_warning(f"已删除: {spec_file}")
        except Exception as e:
            print_error(f"无法删除 {spec_file}: {e}")
            logging.exception(f"删除 spec 文件 {spec_file} 时出错:")


def build_exe(py_file: str, exe_name: str) -> bool:
    print_warning(f"正在构建 {exe_name}...")

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
        # print_info(f"PyInstaller 输出:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        print_error(f"构建 {exe_name} 失败! 返回码: {e.returncode}")
        # 打印更详细的错误信息
        print_error(f"错误输出:\n{e.stderr}")
        logging.error(
            f"构建 {exe_name} 失败! 返回码: {e.returncode}\n标准输出:\n{e.stdout}\n错误输出:\n{e.stderr}")
        return False
    except Exception as e:
        print_error(f"构建 {exe_name} 时发生未知错误: {e}")
        logging.exception(f"构建 {exe_name} 时发生未知错误:")
        return False

    print_success(f"{exe_name} 构建完成")
    return True


def run_build_all() -> bool:
    print_warning("开始执行 build --all...")
    if not SRC_DIR.exists() or not RESOURCE_DIR.exists():
        print_error("错误: src 或 resource 目录不存在")
        return False

    build_targets = [item[0] for item in BUILD_ITEMS]
    print_info(f"构建所有目标: {', '.join(build_targets)}")

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
                print_error(f"无法删除 {spec_file}: {e}")
                logging.exception(f"删除 spec 文件 {spec_file} 时出错:")
        print_success("所有文件构建完成")
        return True
    else:
        print_error("部分文件构建失败")
        return False

# ====== Release 相关函数 ======


def build_release_package(release_name: str, zip_name: str, files_to_copy: List[Path]) -> Optional[Path]:
    release_dir = RELEASE_DIR / release_name
    try:
        if release_dir.exists():
            shutil.rmtree(release_dir)
        release_dir.mkdir(parents=True)

        # 直接复制文件并创建压缩包
        all_files_exist = True
        for src in files_to_copy:
            if src.exists():
                shutil.copy2(src, release_dir)
                print_info(f"已复制: {src.name} -> {release_dir.name}")
            else:
                print_error(f"文件不存在，无法创建发布包: {src}")
                all_files_exist = False

        if not all_files_exist:
            # 如果有文件缺失，不创建 zip 包
            print_error(f"因文件缺失，未创建发布包 {zip_name}.zip")
            if release_dir.exists():  # 清理已复制的文件
                shutil.rmtree(release_dir)
            return None

        release_zip = RELEASE_DIR / f"{zip_name}.zip"
        with zipfile.ZipFile(release_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in release_dir.rglob("*"):
                if file.is_file():
                    zipf.write(file, file.relative_to(release_dir))

        shutil.rmtree(release_dir)
        print_success(f"发布包已创建: {release_zip}")
        return release_zip
    except Exception as e:
        print_error(f"创建发布包 {zip_name} 时出错: {e}")
        logging.exception(f"创建发布包 {zip_name} 时出错:")
        # 清理可能残留的目录
        if release_dir.exists():
            try:
                shutil.rmtree(release_dir)
            except Exception as clean_e:
                print_warning(f"清理发布目录 {release_dir} 失败: {clean_e}")
        return None


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
        print_warning("开始更新模组文件...")
        update_success_count = 0
        for repo_name, api_url in REPO_API_URLS.items():
            result = get_latest_zip_info(repo_name, api_url)
            if result and result.get('zip_url') and result.get('target_zip_name'):
                download_zip(repo_name, result.get('zip_url'),
                             result.get('target_zip_name'))
                update_success_count += 1
            else:
                print_error(f"[{repo_name}] 获取信息或下载失败，跳过。")
        if update_success_count == len(REPO_API_URLS):
            print_success("所有模组文件更新完成")
        else:
            print_warning(
                f"部分模组文件更新失败 ({update_success_count}/{len(REPO_API_URLS)} 成功)")

    elif args.command == 'build':
        if args.all:
            run_build_all()
        else:
            if not SRC_DIR.exists() or not RESOURCE_DIR.exists():
                print_error("错误: src 或 resource 目录不存在")
                return

            build_targets = []
            if args.sv_mod_installer:
                build_targets.append("SVModInstaller.py")
            if args.sv_path_finder:
                build_targets.append("SVPathFinder.py")
            if not build_targets:
                build_targets = ["SVModInstaller.py"]  # 默认只构建SVModInstaller
            print_info(f"构建目标: {', '.join(build_targets)}")

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
                        print_error(f"无法删除 {spec_file}: {e}")
                        logging.exception(f"删除 spec 文件 {spec_file} 时出错:")
                print_success("指定文件构建完成")
            else:
                print_error("部分文件构建失败")

    elif args.command == 'release':
        if not DIST_DIR.exists() or not list(DIST_DIR.glob("*.exe")):
            print_error("错误: dist 目录不存在或未包含 exe 文件。请先运行 build 命令。")
            return

        RELEASE_DIR.mkdir(exist_ok=True)

        # 调用 get_project_version 并传递 SCRIPT_DIR 和 RELEASE_DIR
        version = get_project_version(args.version, SCRIPT_DIR, RELEASE_DIR)
        if not version:
            print_error("错误: 无法确定版本号，无法创建发布包。")
            return

        print_warning(f"开始创建版本 {version} 的发布包...")
        release_zip_path = create_release_zip(version)
        path_finder_zip_path = create_sv_path_finder_zip(version)

        if release_zip_path and path_finder_zip_path:
            print_success("所有发布包创建完成")
        else:
            print_error("部分或全部发布包创建失败。请检查上面的错误信息。")

    elif args.command == 'replace':
        build_success = run_build_all()
        if not build_success:
            print_error("构建失败，无法继续执行替换操作。")
            return

        print_warning("\n开始替换发布包中的 SVModInstaller.exe...")

        version = get_project_version(None, SCRIPT_DIR, RELEASE_DIR)
        if not version:
            print_error("错误: 无法确定版本号，无法执行替换。")
            return

        source_exe = DIST_DIR / "SVModInstaller.exe"
        release_name = f"SVModsInstall_v{version}"
        destination_dir = RELEASE_DIR / release_name
        destination_exe = destination_dir / "SVModInstaller.exe"
        # 注意：这里假设 release 包是一个目录，而不是 zip 文件。
        # 如果 release 包是 zip 文件，需要先解压，替换，再压缩。

        if not source_exe.exists():
            print_error(f"错误: 源文件不存在: {source_exe}")
            return
        if not destination_dir.exists():
            print_error(f"错误: 目标目录不存在: {destination_dir}")
            return

        print_info(f"正在重新创建版本 {version} 的主发布包以包含更新后的 EXE...")

        try:
            shutil.copy2(source_exe, destination_exe)
            print_success(f"替换更新后的 {destination_exe} 完成...")
        except PermissionError as e:
            print_error(f"替换文件时权限错误: {e}")
        except Exception as e:
            print_error(f"替换文件时发生其他错误: {e}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
