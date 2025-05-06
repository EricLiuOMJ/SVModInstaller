from pathlib import Path
from typing import Union, Optional
import os
import sys
import zipfile
import logging
import shutil
from datetime import datetime

from ColorLogger import logger


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
    logger.info(f"准备解压 '{zip_path.name}' 到 '{extract_path}'")

    if extract_path.exists():

        logger.warning(f"文件夹已存在，跳过解压: {extract_path}")
        return extract_path
    try:
        # 为长路径创建目录
        logger.info(f"开始创建目标文件夹: {extract_path}")
        os.makedirs(rf"\\?\{extract_path}", exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            logger.info(f"成功打开 ZIP 文件: {zip_path}")
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

                        logger.warning(f"警告: 文件名解码失败，可能导致问题: {filename}")

                # 构造目标路径，并添加长路径前缀
                target_path_str = str(extract_path / filename)
                target_prefixed = rf"\\?\{target_path_str}"

                # 安全检查：防止 ZIP Slip 漏洞 (基于原始路径检查)
                target_path_obj = Path(target_path_str).resolve()  # 用于安全检查
                if not target_path_obj.is_relative_to(extract_path.resolve()):
                    # 记录错误日志并抛出异常
                    logger.error(
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
            logger.info(
                f"成功解压 '{zip_path.name}' 到 '{extract_path}'")
        return extract_path

    except Exception as e:
        error_file = filename if 'filename' in locals() else "未知文件"

        logger.error(f"解压文件 '{error_file}' 时失败: {str(e)}")
        logging.exception(f"解压文件 '{error_file}' (来自 {zip_path.name}) 时发生严重错误:")
        raise


def find_zip_file(keyword: str, resource_dir: Path) -> Path:
    logger.info(f"在 '{resource_dir}' 中查找包含 '{keyword}' 的 ZIP 文件...")
    zip_files = list(resource_dir.glob(f"*{keyword}*.zip"))
    if not zip_files:
        error_msg = f"在 '{resource_dir}' 中未找到包含 '{keyword}' 的 ZIP 文件"
        logger.error(error_msg)  # 直接记录错误
        raise FileNotFoundError(error_msg)
    elif len(zip_files) > 1:
        logger.warning(
            f"警告: 找到多个包含 '{keyword}' 的 ZIP 文件，将使用第一个: {zip_files[0].name}")

    logger.info(f"找到 ZIP 文件: {zip_files[0]}")
    return zip_files[0]


def get_project_version(args_version: Optional[str], script_dir: Path, release_dir: Path) -> Optional[str]:
    """确定项目版本号，优先读取 VERSION 文件，其次是命令行参数，最后尝试推断"""
    logger.info("开始确定项目版本号...")
    version_file = script_dir / "VERSION"
    if version_file.exists():
        try:
            with open(version_file, 'r', encoding='utf-8') as f:
                version = f.read().strip()
                if version:
                    logger.info(f"从 VERSION 文件读取版本号: {version}")
                    return version
                else:
                    logger.warning(
                        f"VERSION 文件 '{version_file}' 为空。")  # 直接记录警告
        except Exception as e:
            logger.error(f"读取 VERSION 文件 '{version_file}' 时出错: {e}")  # 直接记录错误

    if args_version:
        logger.info(f"使用命令行指定的版本号: {args_version}")
        return args_version

    logger.info("尝试从 release 目录推断版本号...")
    if not release_dir.exists():
        logger.warning("警告: Release 目录不存在，无法从中推断版本号。")
    else:
        try:
            release_dirs = sorted([d for d in release_dir.iterdir() if d.is_dir()
                                   and d.name.startswith("SVModsInstall_v")], reverse=True)
            if release_dirs:
                try:
                    version = release_dirs[0].name.split("_v")[-1]
                    logger.info(f"从最新的发布目录推断版本号: {version}")
                    return version
                except IndexError:
                    logger.warning(
                        f"无法从目录名 '{release_dirs[0].name}' 解析版本号。")  # 直接记录警告
            else:
                logger.info(f"在 '{release_dir}' 中未找到符合条件的发布目录。")
        except Exception as e:
            logger.error(
                f"在 Release 目录 '{release_dir}' 中查找版本时出错: {e}")  # 直接记录错误

    final_version = datetime.now().strftime("%Y%m%d")
    logger.warning(f"警告: 无法确定版本号。将使用当前日期: {final_version}")
    return final_version
