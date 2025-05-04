"""
星露谷物语模组安装程序

此程序用于自动化安装和管理星露谷物语的模组，包括：
1. 检测和安装SMAPI
2. 管理MOD的安装和移除
3. 安装Stardrop管理器

版本: 1.1.0
"""

from pathlib import Path
from typing import Union, List, Tuple
import os
import sys
import shutil
import time
import win32com.client
from pywinauto.application import Application
from SVPathFinder import get_stardew_game_path
from tool import Colors, print_color, get_resource_path, expand_zip_file, find_zip_file


WORK_DIR = get_resource_path("")
RESOURCE_DIR = WORK_DIR
print_color(f"工作目录: {WORK_DIR}", Colors.BLUE)
os.chdir(WORK_DIR)


# ====== 长路径处理函数 ======

def remove_longpath_file(file_path: Path):
    """自定义 remove 函数，用于处理 Windows 长路径下的单个文件。"""
    file_path_str = str(file_path.resolve())
    file_path_prefixed = rf"\\?\{file_path_str}"
    if not os.path.exists(file_path_prefixed):
        print_color(f"尝试删除的文件不存在: {file_path_str}", Colors.YELLOW)
        return
    try:
        os.remove(file_path_prefixed)
        print_color(f"已移除文件 (long path): {file_path_str}", Colors.GREEN)
    except OSError as e:
        print_color(f"无法删除文件 {file_path_str}: {e}", Colors.RED)
    except Exception as e:
        print_color(f"删除文件 {file_path_str} 时出错: {e}", Colors.RED)


def rmtree_longpath(path: Path):
    """自定义 rmtree 函数，用于处理 Windows 长路径。"""
    path_str = str(path.resolve())
    path_prefixed = rf"\\?\{path_str}"
    if not os.path.exists(path_prefixed):
        print_color(f"尝试删除的目录不存在: {path_str}", Colors.YELLOW)
        return

    try:
        # 使用 os.walk 自底向上删除
        for root, dirs, files in os.walk(path_prefixed, topdown=False):
            for name in files:
                file_path = os.path.join(root, name)
                try:
                    os.remove(file_path)
                except OSError as e:
                    print_color(f"无法删除文件 {file_path}: {e}", Colors.RED)
            for name in dirs:
                dir_path = os.path.join(root, name)
                try:
                    os.rmdir(dir_path)
                except OSError as e:
                    print_color(f"无法删除目录 {dir_path}: {e}", Colors.RED)
        # 最后删除根目录
        os.rmdir(path_prefixed)
        print_color(f"已移除旧目录 (long path): {path_str}", Colors.GREEN)
    except Exception as e:
        print_color(f"删除目录 {path_str} 时出错: {e}", Colors.RED)
        # 可以选择重新抛出异常或仅记录错误
        # raise


def copytree_longpath(src: Path, dst: Path, symlinks: bool = False, ignore=None):
    """
    自定义 copytree 函数，用于处理 Windows 长路径。
    src 和 dst 应该是 Path 对象。
    """
    src_str = str(src.resolve())
    dst_str = str(dst.resolve())
    src_prefixed = rf"\\?\{src_str}"
    dst_prefixed = rf"\\?\{dst_str}"

    if not os.path.exists(src_prefixed):
        raise FileNotFoundError(f"源目录不存在: {src_str}")

    try:
        names = os.listdir(src_prefixed)
    except OSError as e:
        raise OSError(f"无法列出源目录 {src_str}: {e}") from e

    if ignore is not None:
        ignored_names = ignore(src_str, names)
    else:
        ignored_names = set()

    os.makedirs(dst_prefixed, exist_ok=True)
    errors: List[Tuple[str, str, str]] = []

    for name in names:
        if name in ignored_names:
            continue

        srcname = src / name
        dstname = dst / name
        srcname_str = str(srcname.resolve())
        dstname_str = str(dstname.resolve())
        srcname_prefixed = rf"\\?\{srcname_str}"
        dstname_prefixed = rf"\\?\{dstname_str}"

        try:
            if symlinks and os.path.islink(srcname_prefixed):
                linkto = os.readlink(srcname_prefixed)
                os.symlink(linkto, dstname_prefixed)
            elif os.path.isdir(srcname_prefixed):
                copytree_longpath(srcname, dstname, symlinks, ignore)
            else:
                shutil.copy2(srcname_prefixed, dstname_prefixed)
        except OSError as why:
            errors.append((srcname_str, dstname_str, str(why)))
        except Exception as err:
            # 假设递归调用抛出的错误是列表形式
            if isinstance(err.args[0], list):
                errors.extend(err.args[0])
            else:
                # 如果不是预期的错误格式，记录下来
                errors.append((srcname_str, dstname_str, f"未知递归错误: {err}"))

    try:
        shutil.copystat(src_prefixed, dst_prefixed)
    except OSError as why:
        if why.winerror is None:  # type: ignore
            errors.append((src_str, dst_str, str(why)))

    if errors:
        # 抛出包含所有错误的异常
        raise Exception(errors)


def manage_mod(source_folder: Union[str, Path], mod_name: str, operation: str,
               mods_path: Union[str, Path]) -> None:
    """
    管理MOD内容的复制或删除操作 (使用长路径支持, 操作第二层内容)

    Args:
        source_folder: 源文件夹路径 (单个 Mod 的源目录，例如 resource/Mods/ModA)
        mod_name: MOD名称 (例如 ModA) - 主要用于日志记录
        operation: 操作类型（"copy"或"remove"）
        mods_path: 目标文件夹路径 (游戏目录下的 Mods 文件夹)
    """
    source_path = Path(source_folder)
    mods_path = Path(mods_path)

    if not source_path.is_dir():
        print_color(
            f"源 Mod 文件夹 '{source_path.name}' 不是一个有效的目录: {source_path}", Colors.RED)
        return

    print_color(f"正在处理 Mod '{mod_name}' 的 {operation} 操作...", Colors.BLUE)

    items_processed = 0
    items_failed = 0

    def _remove_target_item(target_path: Path) -> bool:
        """内部辅助函数，用于移除目标项"""
        if not target_path.exists():
            return True  # 不存在视为成功移除
        print_color(
            f"  目标 '{target_path.name}' 已存在，正在尝试移除旧版本...", Colors.YELLOW)
        try:
            if target_path.is_dir():
                rmtree_longpath(target_path)
            elif target_path.is_file():
                remove_longpath_file(target_path)
            else:
                print_color(f"  无法识别的目标类型: {target_path}", Colors.RED)
                return False  # 移除失败
            return True  # 移除成功
        except Exception as rem_e:
            print_color(f"  移除 '{target_path.name}' 时出错: {rem_e}", Colors.RED)
            return False  # 移除失败

    for item in source_path.iterdir():
        target_item_path = mods_path / item.name
        item_str = str(item.resolve())
        item_prefixed = rf"\\?\{item_str}"
        target_item_path_str = str(target_item_path.resolve())
        target_item_path_prefixed = rf"\\?\{target_item_path_str}"

        try:
            if operation == "copy":
                # 移除旧版本
                if not _remove_target_item(target_item_path):
                    items_failed += 1
                    continue  # 移除失败，跳过此项

                # 执行复制
                if item.is_dir():
                    copytree_longpath(item, target_item_path)
                    print_color(
                        f"  已将目录 '{item.name}' 拷贝到 {mods_path}", Colors.GREEN)
                elif item.is_file():
                    shutil.copy2(item_prefixed, target_item_path_prefixed)
                    print_color(
                        f"  已将文件 '{item.name}' 拷贝到 {mods_path}", Colors.GREEN)
                items_processed += 1

            elif operation == "remove":
                if target_item_path.exists():
                    if _remove_target_item(target_item_path):
                        # 移除成功，打印消息已在 _remove_target_item 或其调用的函数中完成
                        items_processed += 1
                    else:
                        items_failed += 1  # 记录移除失败
                else:
                    print_color(
                        f"  目标 '{item.name}' 在 {mods_path} 中不存在，无需移除", Colors.YELLOW)

        except Exception as e:
            items_failed += 1
            print_color(
                f"  处理 '{item.name}' 时出错: {e}", Colors.RED)
            # 打印详细错误列表（如果 copytree_longpath 抛出的是列表）
            if isinstance(e, Exception) and len(e.args) > 0 and isinstance(e.args[0], list):
                for src_err, dst_err, err_msg in e.args[0]:
                    print_color(
                        f"    - 无法处理 {Path(src_err).name}: {err_msg}", Colors.RED)
            # else: # 避免重复打印普通错误
            #     print_color(f"    错误详情: {str(e)}", Colors.RED)

    if items_failed > 0:
        print_color(
            f"Mod '{mod_name}' 的 {operation} 操作完成，但有 {items_failed} 个项目处理失败。", Colors.RED)
    elif items_processed > 0:
        print_color(f"Mod '{mod_name}' 的 {operation} 操作成功完成。", Colors.GREEN)
    else:
        print_color(
            f"Mod '{mod_name}' 的 {operation} 操作未执行任何更改。", Colors.YELLOW)


def show_mod_menu(operation: str, mods_path: Union[str, Path]) -> None:
    """
    显示MOD管理菜单并处理用户选择

    Args:
        operation: 操作类型（"copy"或"remove"）
        mods_path: MOD目标路径
    """
    mods_zip = find_zip_file("Mods", RESOURCE_DIR)
    # 解压 Mods.zip 到同级目录下的 Mods 文件夹
    mods_dir = expand_zip_file(mods_zip, "Mods")

    if not mods_dir or not mods_dir.exists():
        print_color(f"错误：无法找到或解压源 Mods 目录: {mods_dir}", Colors.RED)
        return

    mod_folders = [
        f for f in mods_dir.iterdir()
        if f.is_dir() and not f.name.startswith('.')
    ]

    if not mod_folders:
        print_color(f"在 {mods_dir} 下没有找到任何MOD文件夹", Colors.RED)
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
                # 调用修改后的 manage_mod
                manage_mod(mod["source"], mod["name"], operation, mods_path)
        elif 1 <= choice <= len(mods):
            selected_mod = next(m for m in mods if m["index"] == choice)
            # 调用修改后的 manage_mod
            manage_mod(selected_mod["source"], selected_mod["name"], operation,
                       mods_path)
        else:
            print_color("无效的选项", Colors.RED)
    except ValueError:
        print_color("请输入有效的数字", Colors.RED)
    except StopIteration:
        print_color("内部错误：无法找到选择的 Mod", Colors.RED)  # 理论上不应发生


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
    smapi_zip = find_zip_file("SMAPI", RESOURCE_DIR)
    smapi_path = expand_zip_file(
        smapi_zip, "SMAPI_Installer")  # 解压到 SMAPI_Installer 目录

    if not smapi_path or not smapi_path.exists():
        raise Exception("SMAPI 解压失败或解压路径无效")

    # 动态查找 SMAPI.Installer.exe
    installer_path = None
    for exe_file in smapi_path.rglob("SMAPI.Installer.exe"):
        # 确保找到的是在 windows 子目录下的那个（如果有多个）
        # 或者简单地取第一个找到的，假设结构是固定的
        installer_path = exe_file
        break  # 找到第一个就停止

    if not installer_path or not installer_path.exists():
        raise Exception(f"在 {smapi_path} 及其子目录中找不到 SMAPI.Installer.exe")

    # 检查对应的 DLL 是否存在（通常在同一目录）
    dll_path = installer_path.parent / "SMAPI.Installer.dll"
    if not dll_path.exists():
        print_color(
            f"警告：未找到对应的 SMAPI.Installer.dll 在 {installer_path.parent}", Colors.YELLOW)
        # 可以选择是否继续，这里假设继续
        # raise Exception(f"找不到 SMAPI.Installer.dll 在 {installer_path.parent}")

    print_color("正在启动SMAPI安装程序...", Colors.YELLOW)
    print_color(f"  安装程序路径: {installer_path}", Colors.BLUE)  # 打印找到的路径

    try:
        # 使用Shell.Application启动安装程序
        shell = win32com.client.Dispatch("Shell.Application")
        shell.ShellExecute(str(installer_path), "", str(
            installer_path.parent), "open", 1)

        # 等待程序启动
        time.sleep(1)

        # 连接到找到的 installer_path
        app = Application(backend="win32").connect(
            path=str(installer_path), timeout=15)  # 增加超时

        app.top_window().type_keys("1{ENTER}")
        time.sleep(0.5)

        app.top_window().type_keys("1{ENTER}")
        time.sleep(0.5)

        app.top_window().type_keys("{ENTER}")

        app.top_window().wait_not('visible', timeout=30)

        print_color("SMAPI安装完成", Colors.GREEN)
        return True

    except Exception as e:
        print_color(f"SMAPI 安装过程中出错: {str(e)}", Colors.RED)
        import traceback
        print_color(traceback.format_exc(), Colors.RED)
        raise  # 重新抛出，让 main 函数捕获


def install_stardrop(sv_path: Union[str, Path]) -> None:
    """
    安装Stardrop管理器 (使用长路径支持)

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
            stardrop_zip = find_zip_file("Stardrop", RESOURCE_DIR)
            stardrop_extract_path = expand_zip_file(stardrop_zip, "Stardrop")

            if not stardrop_extract_path or not stardrop_extract_path.exists():
                raise Exception("Stardrop 解压失败或解压路径无效")

            # 使用自定义 copytree 处理长路径 (虽然 Stardrop 可能不需要，但保持一致性)
            copytree_longpath(stardrop_extract_path, stardrop_path)
            print_color("Stardrop安装完成", Colors.GREEN)

            # 安装后可以考虑删除解压的临时目录
            try:
                rmtree_longpath(stardrop_extract_path)
                print_color(f"已清理临时解压目录: {stardrop_extract_path}", Colors.BLUE)
            except Exception as clean_e:
                print_color(f"清理临时目录时出错: {clean_e}", Colors.YELLOW)

        if not stardrop_shortcut.exists():
            print_color("正在创建桌面快捷方式...", Colors.YELLOW)
            try:
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(str(stardrop_shortcut))
                shortcut.TargetPath = str(stardrop_path / "Stardrop.exe")
                # 可以添加其他属性
                # shortcut.WorkingDirectory = str(stardrop_path)
                # shortcut.IconLocation = str(stardrop_path / "Stardrop.exe, 0")
                shortcut.save()
                print_color("桌面快捷方式创建完成", Colors.GREEN)
            except Exception as short_e:
                print_color(f"创建快捷方式时出错: {short_e}", Colors.RED)

    except Exception as e:
        print_color(f"Stardrop 安装失败: {str(e)}", Colors.RED)


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
        if not SV_PATH or not Path(SV_PATH).exists():
            raise Exception("无法获取游戏路径或路径不存在")

        SV_PATH = Path(SV_PATH)
        MODS_PATH = SV_PATH / "Mods"
        MODS_PATH.mkdir(exist_ok=True)

        print_color(f"\n  星露谷物语安装路径: {SV_PATH}", Colors.BLUE)
        print_color(f"  Mods文件夹路径: {MODS_PATH}", Colors.BLUE)

        # 1. 检测SMAPI安装状态
        print_color("\n=== 步骤1：检测SMAPI安装状态 ===", Colors.YELLOW)
        installed_smapi = False
        try:
            installed_smapi = install_smapi(SV_PATH)
        except Exception as smapi_e:
            print_color(f"SMAPI 安装过程中发生错误:", Colors.RED)
            import traceback
            traceback.print_exc()  # 打印完整堆栈
            print_color("请尝试手动安装 SMAPI。", Colors.YELLOW)

        # 2. MODS安装管理
        print_color("\n=== 步骤2：MODS安装管理 ===", Colors.YELLOW)

        while True:
            print_color("\n请选择 Mod 操作：", Colors.YELLOW)
            print_color("1. 安装/更新 Mod (会覆盖现有同名文件/文件夹)", Colors.YELLOW)
            print_color("2. 移除 Mod", Colors.YELLOW)
            print_color("3. 跳过 Mod 管理", Colors.YELLOW)
            print_color("请输入选项（1-3）：", Colors.YELLOW)

            choice = input().strip()
            if choice == "1":
                # 调用 show_mod_menu 进行安装/更新
                show_mod_menu("copy", MODS_PATH)
                # 安装/更新后通常不需要再选其他操作，直接跳到下一步
                break
            elif choice == "2":
                # 调用 show_mod_menu 进行移除
                show_mod_menu("remove", MODS_PATH)
                # 移除后通常不需要再选其他操作，直接跳到下一步
                break
            elif choice == "3":
                print_color("跳过MOD管理。", Colors.BLUE)
                break
            else:
                print_color("无效的选项，请重新输入。", Colors.RED)
            # 移除 break，允许用户在输入无效后重新选择
            # break # <--- 移除这一行

        # 3. 安装Stardrop
        print_color("\n=== 步骤3：安装Stardrop ===", Colors.YELLOW)
        try:
            install_stardrop(SV_PATH)
        except Exception as drop_e:
            print_color(f"Stardrop 安装过程中发生错误:", Colors.RED)
            import traceback
            traceback.print_exc()  # 打印完整堆栈

        print_color(LINE, Colors.GREEN)
        print_color("                    安装程序执行完毕！", Colors.GREEN)
        print_color(LINE, Colors.GREEN)

        if installed_smapi:
            print_color("提示：如果通过 Steam 启动游戏，请将以下内容复制粘贴到游戏启动选项中：",
                        Colors.CYAN)  # 使用 CYAN
            print_color(
                f'"{SV_PATH}\\StardewModdingAPI.exe" %command%', Colors.CYAN)  # 使用 CYAN

    except Exception as e:
        print_color(f"\n发生严重错误:", Colors.RED)
        import traceback
        traceback.print_exc()  # 确保顶层也打印堆栈
    finally:
        temp_smapi_dir = RESOURCE_DIR / "SMAPI_Installer"
        temp_mods_dir = RESOURCE_DIR / "Mods"
        temp_stardrop_dir = RESOURCE_DIR / "Stardrop"
        print_color("\n正在尝试清理临时文件...", Colors.BLUE)
        if temp_smapi_dir.exists():
            try:
                rmtree_longpath(temp_smapi_dir)
            except Exception as clean_e:
                print_color(f"清理 SMAPI 临时目录失败: {clean_e}", Colors.YELLOW)
        if temp_mods_dir.exists():
            try:
                rmtree_longpath(temp_mods_dir)
            except Exception as clean_e:
                print_color(f"清理 Mods 临时目录失败: {clean_e}", Colors.YELLOW)
        if temp_stardrop_dir.exists():
            try:
                rmtree_longpath(temp_stardrop_dir)
            except Exception as clean_e:
                print_color(f"清理 Stardrop 临时目录失败: {clean_e}", Colors.YELLOW)

        print_color("\n按回车键退出...", Colors.WHITE)
        input()
        sys.exit(0)  # 正常退出


if __name__ == "__main__":
    main()
