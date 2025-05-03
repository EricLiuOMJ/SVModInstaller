"""
星露谷物语模组安装程序

此程序用于自动化安装和管理星露谷物语的模组，包括：
1. 检测和安装SMAPI
2. 管理MOD的安装和移除
3. 安装Stardrop管理器

版本: 1.0.0
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Union
import os
import sys
import shutil
import time
import zipfile
import win32com.client
from pywinauto.application import Application
from SVPathFinder import get_stardew_game_path


def get_resource_path(relative_path: Union[str, Path]) -> Path:
    """
    获取资源文件的绝对路径

    Args:
        relative_path: 相对于资源目录的路径

    Returns:
        Path: 资源文件的绝对路径
    """
    try:
        # 如果是打包后的exe
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            # 如果是开发环境
            base_path = Path(__file__).parent.parent

        return base_path / relative_path
    except Exception:
        return Path(relative_path)


# 设置工作目录和资源目录
WORK_DIR = get_resource_path("")
RESOURCE_DIR = WORK_DIR
print(f"工作目录: {WORK_DIR}")
os.chdir(WORK_DIR)


@dataclass
class Colors:
    """控制台颜色类"""
    GREEN = '\033[92m'  # 成功信息
    YELLOW = '\033[93m'  # 警告信息
    RED = '\033[91m'  # 错误信息
    BLUE = '\033[94m'  # 提示信息
    ENDC = '\033[0m'  # 重置颜色


def print_color(text: str, color: str) -> None:
    """
    打印带颜色的文本

    Args:
        text: 要打印的文本
        color: 颜色代码
    """
    print(f"{color}{text}{Colors.ENDC}")


def expand_zip_file(zip_path: Union[str, Path], destination_name: str) -> Path:
    """
    解压zip文件到指定目录，支持中文文件名和长路径。

    Args:
        zip_path: zip文件路径
        destination_name: 目标文件夹名称

    Returns:
        Path: 解压后的目标文件夹路径

    Raises:
        Exception: 解压失败或未找到目标文件夹
    """
    zip_path = Path(zip_path)
    extract_path = zip_path.parent / destination_name

    if extract_path.exists():
        print_color(f"文件夹已存在，跳过解压: {extract_path}", Colors.YELLOW)
        return extract_path

    try:
        extract_path.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for info in zip_ref.infolist():
                # 尝试修复中文乱码
                try:
                    filename = info.filename.encode('cp437').decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        filename = info.filename.encode('cp437').decode('gbk')
                    except UnicodeDecodeError:
                        filename = info.filename

                # 构造目标路径
                target = (extract_path / filename).resolve()

                # 安全检查：防止 ZIP Slip 漏洞
                if not target.is_relative_to(extract_path):
                    raise ValueError(f"非法路径尝试: {filename}")

                # 创建父目录
                if not target.parent.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)

                # 如果是目录则创建
                if info.is_dir():
                    target.mkdir(exist_ok=True)
                else:
                    # 写入文件内容
                    with zip_ref.open(info) as source, open(target,
                                                            'wb') as dest:
                        dest.write(source.read())

        return extract_path

    except Exception as e:
        print_color(f"解压失败: {str(e)}", Colors.RED)
        raise


def find_zip_file(keyword: str) -> Path:
    """
    查找包含关键字的zip文件

    Args:
        keyword: 要搜索的关键字

    Returns:
        Path: 找到的zip文件路径

    Raises:
        Exception: 未找到匹配的zip文件
    """
    zip_files = list(RESOURCE_DIR.glob(f"*{keyword}*.zip"))
    if not zip_files:
        raise Exception(f"未找到包含 '{keyword}' 的zip文件")
    return zip_files[0]


def manage_mod(source_folder: Union[str, Path], mod_name: str, operation: str,
               mods_path: Union[str, Path]) -> None:
    """
    管理MOD的复制或删除操作

    Args:
        source_folder: 源文件夹路径
        mod_name: MOD名称
        operation: 操作类型（"copy"或"remove"）
        mods_path: 目标文件夹路径
    """
    source_path = Path(source_folder)
    mods_path = Path(mods_path)

    if not source_path.exists():
        print_color(f"{mod_name} 文件夹不存在", Colors.RED)
        return

    try:
        for mod_dir in source_path.iterdir():
            if not mod_dir.is_dir():
                continue

            target_path = mods_path / mod_dir.name
            if operation == "copy":
                if target_path.exists():
                    shutil.rmtree(target_path)
                    print_color(f"已移除旧的 {mod_dir.name}", Colors.GREEN)
                shutil.copytree(mod_dir, target_path)
                print_color(f"已将 {mod_dir.name} 拷贝到 - {mods_path}",
                            Colors.GREEN)
            elif target_path.exists():
                shutil.rmtree(target_path)
                print_color(f"已移除 {mod_dir.name}", Colors.GREEN)
    except Exception as e:
        print_color(f"{operation}过程中出错: {str(e)}", Colors.RED)


def show_mod_menu(operation: str, mods_path: Union[str, Path]) -> None:
    """
    显示MOD管理菜单并处理用户选择

    Args:
        operation: 操作类型（"copy"或"remove"）
        mods_path: MOD目标路径
    """
    mods_dir = RESOURCE_DIR / "Mods"
    mod_folders = [
        f for f in mods_dir.iterdir()
        if f.is_dir() and not f.name.startswith('.')
    ]

    if not mod_folders:
        print_color("Mods文件夹下没有找到任何MOD文件夹", Colors.RED)
        return

    mods = [{
        "index": i + 1,
        "name": f.name,
        "source": str(f)
    } for i, f in enumerate(mod_folders)]

    print_color(f"\n请选择要{operation}的MOD：", Colors.YELLOW)
    for mod in mods:
        print_color(f"{mod['index']}. {mod['name']}", Colors.YELLOW)
    print_color(f"{len(mods) + 1}. 全部{operation}", Colors.YELLOW)
    print_color(f"请输入选项（1-{len(mods) + 1}）：", Colors.YELLOW)

    try:
        choice = int(input())
        if choice == len(mods) + 1:
            for mod in mods:
                manage_mod(mod["source"], mod["name"], operation, mods_path)
        elif 1 <= choice <= len(mods):
            selected_mod = next(m for m in mods if m["index"] == choice)
            manage_mod(selected_mod["source"], selected_mod["name"], operation,
                       mods_path)
        else:
            print_color("无效的选项", Colors.RED)
    except ValueError:
        print_color("请输入有效的数字", Colors.RED)


def install_smapi(sv_path: Union[str, Path]) -> bool:
    """
    安装SMAPI

    Args:
        sv_path: 游戏安装路径

    Returns:
        bool: 是否成功安装SMAPI
    """
    smapi_exe = Path(sv_path) / "StardewModdingAPI.exe"

    # 检查SMAPI是否已安装
    if smapi_exe.exists():
        print_color("SMAPI已安装，跳过安装步骤", Colors.GREEN)
        return False

    print_color("SMAPI未安装，开始安装...", Colors.YELLOW)

    # 解压SMAPI安装包
    smapi_zip = find_zip_file("SMAPI")
    smapi_path = expand_zip_file(smapi_zip, "SMAPI_Installer")

    # 检查安装程序文件
    installer_path = smapi_path / \
        "SMAPI 4.2.1 installer/internal/windows/SMAPI.Installer.exe"
    dll_path = smapi_path / "SMAPI 4.2.1 installer/internal/windows/SMAPI.Installer.dll"

    if not installer_path.exists() or not dll_path.exists():
        raise Exception("SMAPI安装程序文件不存在，请确保文件完整性")

    print_color("正在启动SMAPI安装程序...", Colors.YELLOW)

    try:
        # 使用Shell.Application启动安装程序

        shell = win32com.client.Dispatch("Shell.Application")
        shell.ShellExecute(str(installer_path), "", str(installer_path.parent),
                           "open", 1)

        # 等待程序启动
        time.sleep(1)

        app = Application(backend="win32").connect(path=str(installer_path))

        app.top_window().type_keys("1{ENTER}")
        time.sleep(0.5)

        app.top_window().type_keys("1{ENTER}")
        time.sleep(0.5)

        app.top_window().type_keys("{ENTER}")

        app.top_window().wait_not('visible', timeout=30)

        print_color("SMAPI安装完成", Colors.GREEN)
        return True

    except Exception as e:
        print_color(f"安装过程中出错: {str(e)}", Colors.RED)
        raise


def install_stardrop(sv_path: Union[str, Path]) -> None:
    """
    安装Stardrop管理器

    Args:
        sv_path: 游戏安装路径
    """
    sv_parent_path = Path(sv_path).parent.parent
    stardrop_path = sv_parent_path / "Stardrop"
    stardrop_shortcut = Path(os.path.expanduser("~/Desktop")) / "Stardrop.lnk"

    print_color("正在安装Stardrop...", Colors.YELLOW)
    try:
        if stardrop_path.exists():
            print_color("Stardrop已安装，跳过安装步骤", Colors.GREEN)
        else:
            stardrop_zip = find_zip_file("Stardrop")
            stardrop_extract_path = expand_zip_file(stardrop_zip, "Stardrop")

            if not stardrop_extract_path.exists():
                raise Exception("Stardrop 解压失败")

            shutil.copytree(stardrop_extract_path, stardrop_path)
            print_color("Stardrop安装完成", Colors.GREEN)

        if not stardrop_shortcut.exists():
            print_color("正在创建桌面快捷方式...", Colors.YELLOW)
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(stardrop_shortcut))
            shortcut.TargetPath = str(stardrop_path / "Stardrop.exe")
            shortcut.save()
            print_color("桌面快捷方式创建完成", Colors.GREEN)
    except Exception as e:
        print_color(f"Stardrop 安装失败: {str(e)}", Colors.RED)
        raise


def main() -> None:
    """主函数"""
    LINE = "══════════════════════════════════════════════════════════════════════════════"

    print_color(LINE, Colors.GREEN)
    print_color("                    星露谷物语模组安装程序", Colors.GREEN)
    print_color("                    1. 检测是否安装SMAPI", Colors.GREEN)
    print_color("                    2. MODS安装管理", Colors.GREEN)
    print_color("                    3. 安装Stardrop", Colors.GREEN)
    print_color(LINE, Colors.GREEN)

    try:
        # 获取游戏路径
        SV_PATH = get_stardew_game_path()
        if not SV_PATH or not os.path.exists(SV_PATH):
            raise Exception("无法获取游戏路径或路径不存在")

        MODS_PATH = Path(SV_PATH) / "Mods"
        if not MODS_PATH.exists():
            MODS_PATH.mkdir()

        print_color(f"\n  星露谷物语安装路径: {SV_PATH}", Colors.BLUE)
        print_color(f"  Mods文件夹路径: {MODS_PATH}", Colors.BLUE)

        # 1. 检测SMAPI安装状态
        print_color("\n=== 步骤1：检测SMAPI安装状态 ===", Colors.YELLOW)
        installed_smapi = install_smapi(SV_PATH)

        # 2. MODS安装管理
        print_color("\n=== 步骤2：MODS安装管理 ===", Colors.YELLOW)
        mods_zip = find_zip_file("Mods")
        mods_extract_path = expand_zip_file(mods_zip, "Mods")

        while True:
            print_color("\n请选择操作：", Colors.YELLOW)
            print_color("1. 安装MOD", Colors.YELLOW)
            print_color("2. 移除MOD", Colors.YELLOW)
            print_color("3. 继续下一步", Colors.YELLOW)
            print_color("请输入选项（1-3）：", Colors.YELLOW)

            choice = input()
            if choice == "1":
                print_color("\n正在移动Mods文件...", Colors.YELLOW)
                show_mod_menu("copy", MODS_PATH)
                print_color("Mods文件移动完成", Colors.GREEN)
            elif choice == "2":
                show_mod_menu("remove", MODS_PATH)
            elif choice == "3":
                break
            else:
                print_color("无效的选项", Colors.RED)

            if choice != "3":
                print_color("\n是否继续管理MOD？(Y/N) [默认N]", Colors.YELLOW)
                continue_choice = input().lower()
                if not continue_choice or continue_choice != 'y':
                    break

        # 3. 安装Stardrop
        print_color("\n=== 步骤3：安装Stardrop ===", Colors.YELLOW)
        install_stardrop(SV_PATH)

        print_color(LINE, Colors.GREEN)
        print_color("                    安装完成！", Colors.GREEN)
        print_color(LINE, Colors.GREEN)

        if installed_smapi:
            print_color("请将如下内容复制粘贴到Steam属性中", Colors.BLUE)
            print_color(
                f'        "{SV_PATH}\\StardewModdingAPI.exe" %command%',
                Colors.BLUE)

    except Exception as e:
        print_color(f"错误: {str(e)}", Colors.RED)
        input("按回车键退出")
        sys.exit(1)


if __name__ == "__main__":
    main()
