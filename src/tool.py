from dataclasses import dataclass
from pathlib import Path
from typing import Union, Optional
from datetime import datetime
import os
import sys
import zipfile


@dataclass
class Colors:
    """控制台输出颜色"""
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    ENDC = '\033[0m'


def print_color(text: str, color: str) -> None:
    print(f"{color}{text}{Colors.ENDC}")


def get_resource_path(relative_path: str) -> Path:
    """获取资源的绝对路径，兼容开发环境和PyInstaller打包环境"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # 如果在 PyInstaller 打包环境中运行
        # 资源文件（如 Mods.zip, SMAPI*.zip）应该位于可执行文件旁边
        # 使用 sys.executable 获取可执行文件的路径，其父目录即为基准路径
        base_path = Path(sys.executable).parent
    else:
        # 不在打包环境中（即直接运行 .py 脚本）
        # 假设 tool.py 在 src 目录下，项目根目录是其上级目录
        base_path = Path(__file__).parent.parent.resolve()

    # 返回相对于基准路径的绝对路径
    return (base_path / relative_path).resolve()


def expand_zip_file(zip_path: Union[str, Path], destination_name: str) -> Path:
    zip_path = Path(zip_path)
    # 使用 resolve() 获取绝对路径，并确保目标路径也是绝对路径
    extract_path = zip_path.parent.resolve() / destination_name

    if extract_path.exists():
        print_color(f"文件夹已存在，跳过解压: {extract_path}", Colors.YELLOW)
        return extract_path
    try:
        # 为长路径创建目录
        os.makedirs(rf"\\?\{extract_path}", exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for info in zip_ref.infolist():
                # 尝试修复中文乱码
                try:
                    filename = info.filename.encode(
                        'cp437').decode('gbk')  # 优先尝试 gbk
                except UnicodeDecodeError:
                    try:
                        filename = info.filename.encode(
                            'cp437').decode('utf-8')
                    except UnicodeDecodeError:
                        # 如果还是失败，保留原始文件名，但可能仍有问题
                        filename = info.filename
                        print_color(
                            f"警告: 文件名解码失败，可能导致问题: {filename}", Colors.YELLOW)

                # 构造目标路径，并添加长路径前缀
                target_path_str = str(extract_path / filename)
                target_prefixed = rf"\\?\{target_path_str}"

                # 安全检查：防止 ZIP Slip 漏洞 (基于原始路径检查)
                target_path_obj = Path(target_path_str).resolve()  # 用于安全检查
                if not target_path_obj.is_relative_to(extract_path.resolve()):
                    raise ValueError(f"非法路径尝试: {filename}")

                # 创建父目录 (使用长路径前缀)
                target_parent_prefixed = rf"\\?\{os.path.dirname(target_path_str)}"
                if not os.path.exists(target_parent_prefixed):
                    os.makedirs(target_parent_prefixed, exist_ok=True)

                # 如果是目录则创建 (使用长路径前缀)
                if info.is_dir():
                    if not os.path.exists(target_prefixed):
                        os.makedirs(target_prefixed, exist_ok=True)
                else:
                    # 写入文件内容 (使用长路径前缀打开文件)
                    with zip_ref.open(info) as source, open(target_prefixed, 'wb') as dest:
                        dest.write(source.read())

        return extract_path

    except Exception as e:
        # 打印更详细的错误信息，包括出错的文件名
        error_file = filename if 'filename' in locals() else "未知文件"
        print_color(f"解压文件 '{error_file}' 时失败: {str(e)}", Colors.RED)
        # 同时打印原始异常，方便调试
        import traceback
        traceback.print_exc()
        raise


def find_zip_file(keyword: str, resource_dir: Path) -> Path:
    zip_files = list(resource_dir.glob(f"*{keyword}*.zip"))
    if not zip_files:
        raise Exception(f"未找到包含 '{keyword}' 的zip文件")
    return zip_files[0]


def get_project_version(args_version: Optional[str], script_dir: Path, release_dir: Path) -> Optional[str]:
    """确定项目版本号，优先读取 VERSION 文件，其次是命令行参数，最后尝试推断"""
    version_file = script_dir / "VERSION"  # 使用参数 script_dir
    if version_file.exists():
        with open(version_file, 'r', encoding='utf-8') as f:
            version = f.read().strip()
            print_color(f"从 VERSION 文件读取版本号: {version}", Colors.BLUE)
            return version

    if args_version:
        print_color(f"使用命令行指定的版本号: {args_version}", Colors.BLUE)
        return args_version

    # 尝试从 release 目录推断
    if not release_dir.exists():  # 使用参数 release_dir
        print_color("警告: Release 目录不存在，无法从中推断版本号。", Colors.YELLOW)
    else:
        release_dirs = sorted([d for d in release_dir.iterdir() if d.is_dir()  # 使用参数 release_dir
                               and d.name.startswith("SVModsInstall_v")], reverse=True)
        if release_dirs:
            try:
                version = release_dirs[0].name.split("_v")[-1]
                print_color(f"从最新的发布目录推断版本号: {version}", Colors.BLUE)
                return version
            except IndexError:
                pass  # 如果分割失败，则忽略

    print_color("警告: 无法确定版本号。将使用当前日期。", Colors.YELLOW)
    return datetime.now().strftime("%Y%m%d")
