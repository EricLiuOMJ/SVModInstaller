from dataclasses import dataclass
from pathlib import Path
from typing import Union, Optional
from datetime import datetime
import os
import sys
import zipfile
import logging
import traceback
from datetime import datetime
import sys


# --- 日志配置 ---
# 判断运行环境以确定日志目录的基础路径
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    base_path = Path(sys.executable).parent
else:
    base_path = Path(__file__).parent.parent.resolve()

log_dir = base_path / "logs"
log_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"installer_{timestamp}.log"

# 配置日志记录器
logging.basicConfig(
    level=logging.INFO,  # 设置记录的最低级别
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    filename=log_file,  # 日志文件路径
    filemode='a',  # 追加模式 ('w' 为覆盖模式)
    encoding='utf-8'  # 指定编码
)
# --- 日志配置结束 ---


@dataclass
class Colors:
    """控制台输出颜色"""
    RESET = '\033[0m'
    RED = '\033[91m'      # 通常用于错误
    GREEN = '\033[92m'    # 通常用于成功
    YELLOW = '\033[93m'   # 通常用于警告或步骤
    BLUE = '\033[94m'     # 通常用于一般信息
    MAGENTA = '\033[95m'  # 通常用于调试或特殊信息
    CYAN = '\033[96m'     # 通常用于提示或次要信息
    WHITE = '\033[97m'    # 通常用于默认文本
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ENDC = '\033[0m'


def print_color(text: str, color: str) -> None:
    """
    打印带颜色的文本到控制台，并根据颜色将纯文本记录到日志文件。

    Args:
        text (str): 要打印和记录的文本。
        color (str): 用于控制台输出的颜色代码 (来自 Colors 类)。
    """
    # 1. 打印带颜色的文本到控制台
    print(f"{color}{text}{Colors.ENDC}")

    # 2. 根据颜色确定日志级别并记录
    log_level = logging.INFO  # 默认为 INFO
    if color == Colors.YELLOW:
        log_level = logging.WARNING
    elif color == Colors.RED:
        log_level = logging.ERROR
    elif color == Colors.MAGENTA:
        log_level = logging.DEBUG
    # 其他颜色 (GREEN, BLUE, CYAN, MAGENTA, WHITE) 默认映射到 INFO
    # 如果需要 DEBUG 级别，可以添加更多映射，并调整 basicConfig 的 level

    logging.log(log_level, text)

# --- 封装常用打印函数 ---


def print_info(text: str) -> None:
    """打印蓝色信息文本 (INFO 级别日志)"""
    print_color(text, Colors.BLUE)


def print_success(text: str) -> None:
    """打印绿色成功文本 (INFO 级别日志)"""
    print_color(text, Colors.GREEN)


def print_warning(text: str) -> None:
    """打印黄色警告文本 (WARNING 级别日志)"""
    print_color(text, Colors.YELLOW)


def print_error(text: str) -> None:
    """打印红色错误文本 (ERROR 级别日志)"""
    print_color(text, Colors.RED)


def print_step(text: str) -> None:
    """打印青色步骤文本 (INFO 级别日志)"""
    print_color(text, Colors.CYAN)


def print_debug(text: str) -> None:
    """打印品红色调试文本 (INFO 级别日志，可调整)"""
    print_color(text, Colors.MAGENTA)


def print_white(text: str) -> None:
    """打印白色普通文本 (INFO 级别日志)"""
    print_color(text, Colors.WHITE)


def get_resource_path(relative_path: str) -> Path:
    """获取资源的绝对路径，兼容开发环境和PyInstaller打包环境"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent.parent.resolve()
    return (base_path / relative_path).resolve()


def expand_zip_file(zip_path: Union[str, Path], destination_name: str) -> Path:
    zip_path = Path(zip_path)
    extract_path = zip_path.parent.resolve() / destination_name
    logging.info(f"准备解压 '{zip_path.name}' 到 '{extract_path}'")  # 保留底层日志

    if extract_path.exists():

        print_warning(f"文件夹已存在，跳过解压: {extract_path}")
        return extract_path
    try:
        # 为长路径创建目录
        logging.info(f"开始创建目标文件夹: {extract_path}")  # 保留底层日志
        os.makedirs(rf"\\?\{extract_path}", exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            logging.info(f"成功打开 ZIP 文件: {zip_path}")  # 保留底层日志
            for info in zip_ref.infolist():
                # 尝试修复中文乱码
                try:
                    filename = info.filename.encode('cp437').decode('gbk')
                except UnicodeDecodeError:
                    try:
                        filename = info.filename.encode(
                            'cp437').decode('utf-8')
                    except UnicodeDecodeError:
                        filename = info.filename

                        print_warning(f"警告: 文件名解码失败，可能导致问题: {filename}")

                # 构造目标路径，并添加长路径前缀
                target_path_str = str(extract_path / filename)
                target_prefixed = rf"\\?\{target_path_str}"

                # 安全检查：防止 ZIP Slip 漏洞 (基于原始路径检查)
                target_path_obj = Path(target_path_str).resolve()  # 用于安全检查
                if not target_path_obj.is_relative_to(extract_path.resolve()):
                    # 记录错误日志并抛出异常
                    logging.error(
                        f"检测到非法路径尝试 (Zip Slip?): {filename} -> {target_path_obj}")
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
            logging.info(
                f"成功解压 '{zip_path.name}' 到 '{extract_path}'")  # 保留底层日志
        return extract_path

    except Exception as e:
        error_file = filename if 'filename' in locals() else "未知文件"

        print_error(f"解压文件 '{error_file}' 时失败: {str(e)}")
        logging.exception(f"解压文件 '{error_file}' (来自 {zip_path.name}) 时发生严重错误:")
        raise


def find_zip_file(keyword: str, resource_dir: Path) -> Path:
    logging.info(f"在 '{resource_dir}' 中查找包含 '{keyword}' 的 ZIP 文件...")  # 保留底层日志
    zip_files = list(resource_dir.glob(f"*{keyword}*.zip"))
    if not zip_files:
        error_msg = f"在 '{resource_dir}' 中未找到包含 '{keyword}' 的 ZIP 文件"
        logging.error(error_msg)  # 直接记录错误
        raise FileNotFoundError(error_msg)
    elif len(zip_files) > 1:
        print_warning(
            f"警告: 找到多个包含 '{keyword}' 的 ZIP 文件，将使用第一个: {zip_files[0].name}")

    logging.info(f"找到 ZIP 文件: {zip_files[0]}")  # 保留底层日志
    return zip_files[0]


def get_project_version(args_version: Optional[str], script_dir: Path, release_dir: Path) -> Optional[str]:
    """确定项目版本号，优先读取 VERSION 文件，其次是命令行参数，最后尝试推断"""
    logging.info("开始确定项目版本号...")  # 保留底层日志
    version_file = script_dir / "VERSION"
    if version_file.exists():
        try:
            with open(version_file, 'r', encoding='utf-8') as f:
                version = f.read().strip()
                if version:
                    print_info(f"从 VERSION 文件读取版本号: {version}")
                    return version
                else:
                    logging.warning(
                        f"VERSION 文件 '{version_file}' 为空。")  # 直接记录警告
        except Exception as e:
            logging.error(f"读取 VERSION 文件 '{version_file}' 时出错: {e}")  # 直接记录错误

    if args_version:
        print_info(f"使用命令行指定的版本号: {args_version}")
        return args_version

    logging.info("尝试从 release 目录推断版本号...")  # 保留底层日志
    if not release_dir.exists():
        print_warning("警告: Release 目录不存在，无法从中推断版本号。")
    else:
        try:
            release_dirs = sorted([d for d in release_dir.iterdir() if d.is_dir()
                                   and d.name.startswith("SVModsInstall_v")], reverse=True)
            if release_dirs:
                try:
                    version = release_dirs[0].name.split("_v")[-1]
                    print_info(f"从最新的发布目录推断版本号: {version}")
                    return version
                except IndexError:
                    logging.warning(
                        f"无法从目录名 '{release_dirs[0].name}' 解析版本号。")  # 直接记录警告
            else:
                logging.info(f"在 '{release_dir}' 中未找到符合条件的发布目录。")  # 保留底层日志
        except Exception as e:
            logging.error(
                f"在 Release 目录 '{release_dir}' 中查找版本时出错: {e}")  # 直接记录错误

    final_version = datetime.now().strftime("%Y%m%d")
    print_warning(f"警告: 无法确定版本号。将使用当前日期: {final_version}")
    return final_version
