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
import traceback
import win32com.client
from pywinauto.application import Application
from SVPathFinder import get_stardew_game_path
from tool import Colors, print_color, get_resource_path, expand_zip_file, find_zip_file

WORK_DIR = get_resource_path("")
RESOURCE_DIR = WORK_DIR
print_color(f"工作目录: {WORK_DIR}", Colors.BLUE)
os.chdir(WORK_DIR)


# ====== 长路径处理函数 ======

def _longpath(path: Path) -> str:
    """将路径转换为长路径格式 (使用长路径前缀)"""
    abs_path = path.resolve()
    return rf"\\?\{str(abs_path)}"


def remove_path(path: Path):
    """统一处理文件或目录的删除（支持长路径，依赖 shutil/os）"""
    if not path.exists():
        print_color(f"目标不存在，无需删除: {path}", Colors.YELLOW)
        return True  # 不存在视为成功

    path_prefixed = _longpath(path)
    path_str = str(path)  # 用于日志

    try:
        if path.is_dir():
            # 主要依赖 shutil.rmtree
            shutil.rmtree(path_prefixed, ignore_errors=False)  # 让错误抛出
            print_color(f"已移除目录: {path_str}", Colors.GREEN)
        elif path.is_file():
            os.remove(path_prefixed)
            print_color(f"已移除文件: {path_str}", Colors.GREEN)
        else:
            print_color(f"无法识别的路径类型，跳过删除: {path_str}", Colors.YELLOW)
            # 不认为是失败，因为无法处理
        return True
    except Exception as e:
        print_color(f"删除 {path_str} 时出错: {e}", Colors.RED)
        # traceback.print_exc() # 可选：打印详细堆栈
        return False  # 删除失败


def copytree_longpath(src: Path, dst: Path, symlinks: bool = False, ignore=None):
    """使用长路径前缀复制目录树（依赖 shutil.copytree）"""
    src_prefixed = _longpath(src)
    dst_prefixed = _longpath(dst)
    src_str = str(src)  # 用于日志
    dst_str = str(dst)  # 用于日志

    if not os.path.isdir(src_prefixed):
        raise FileNotFoundError(f"源目录不存在或不是目录: {src_str}")

    try:
        # 主要依赖 shutil.copytree，dirs_exist_ok=True 允许目标存在
        shutil.copytree(src_prefixed, dst_prefixed,
                        symlinks=symlinks, ignore=ignore, dirs_exist_ok=True)
        # 成功信息由调用者 (manage_mod) 打印
    except Exception as e:
        print_color(f"复制目录 {src_str} 到 {dst_str} 时出错: {e}", Colors.RED)
        # traceback.print_exc() # 可选：打印详细堆栈
        raise  # 将错误重新抛出给调用者


def manage_mod(source_folder: Union[str, Path], mod_name: str, operation: str,
               mods_path: Union[str, Path]) -> Tuple[int, int]:
    """
    管理MOD内容的复制或删除操作 (使用简化后的长路径支持)
    返回: (成功处理的项目数, 失败的项目数)    

    Args:
        source_folder: 源文件夹路径 (单个 Mod 的源目录，例如 resource/Mods/ModA)
        mod_name: MOD名称 (例如 ModA) - 主要用于日志记录
        operation: 操作类型（"copy"或"remove"）
        mods_path: 目标文件夹路径 (游戏目录下的 Mods 文件夹)
    """
    source_path = Path(source_folder)
    mods_path = Path(mods_path)
    items_processed = 0
    items_failed = 0

    if not source_path.is_dir():
        print_color(f"源 Mod 文件夹无效: {source_path}", Colors.RED)
        return 0, 1

    print_color(f"处理 Mod '{mod_name}' ({operation})...", Colors.BLUE)

    for item in source_path.iterdir():
        target_item_path = mods_path / item.name
        item_name = item.name

        success = True  # 假设成功
        try:
            if operation == "copy":
                # 1. 如果目标存在，先移除
                if target_item_path.exists():
                    print_color(
                        f"  发现旧版本 '{item_name}'，正在移除...", Colors.YELLOW)
                    if not remove_path(target_item_path):
                        print_color(
                            f"  移除旧版本 '{item_name}' 失败，跳过复制。", Colors.RED)
                        success = False  # 标记失败

                # 2. 如果移除成功或无需移除，执行复制
                if success:
                    if item.is_dir():
                        copytree_longpath(item, target_item_path)
                        print_color(f"  已拷贝目录 '{item_name}'", Colors.GREEN)
                    elif item.is_file():

                        shutil.copy2(_longpath(item),
                                     _longpath(target_item_path))
                        print_color(f"  已拷贝文件 '{item_name}'", Colors.GREEN)
                    else:
                        print_color(
                            f"  跳过不支持的项目类型: '{item_name}'", Colors.YELLOW)
                        success = False

            elif operation == "remove":
                if target_item_path.exists():
                    if not remove_path(target_item_path):
                        success = False
                else:
                    print_color(f"  目标 '{item_name}' 不存在，无需移除", Colors.YELLOW)
                    success = None

        except Exception as e:
            print_color(
                f"  处理 '{item_name}' ({operation}) 时出错: {e}", Colors.RED)
            success = False

        # 更新计数器
        if success is True:
            items_processed += 1
        elif success is False:
            items_failed += 1

    return items_processed, items_failed


def show_mod_menu(operation: str, mods_path: Union[str, Path]) -> None:
    """显示MOD管理菜单并处理用户选择"""
    mods_dir = None
    try:
        mods_zip = find_zip_file("Mods", RESOURCE_DIR)
        temp_extract_dir = RESOURCE_DIR / f"Mods_extracted_{int(time.time())}"
        mods_dir = expand_zip_file(
            mods_zip, temp_extract_dir.name)  # 使用带时间戳的目录名
    except Exception as e:
        print_color(f"错误：无法找到或解压 Mods.zip: {e}", Colors.RED)
        return

    if not mods_dir or not mods_dir.is_dir():
        print_color(f"错误：解压后的 Mods 目录无效: {mods_dir}", Colors.RED)
        return

    mod_folders = sorted([
        f for f in mods_dir.iterdir()
        if f.is_dir() and not f.name.startswith('.')
    ], key=lambda p: p.name)

    if not mod_folders:
        print_color(f"在解压目录 {mods_dir.name} 下没有找到任何MOD文件夹", Colors.YELLOW)
        return

    mods = [{"index": i + 1, "name": f.name, "source": f}
            for i, f in enumerate(mod_folders)]

    print_color(f"\n可用 Mods (来源: {mods_dir.name}):", Colors.CYAN)
    for mod in mods:
        print_color(f"{mod['index']:>2}. {mod['name']}", Colors.YELLOW)
    print_color(f"{len(mods) + 1:>2}. {'全部' + operation}", Colors.YELLOW)
    print_color(f" 0. 取消", Colors.YELLOW)

    while True:
        try:
            choice_str = input(
                f"请选择要 {operation} 的 Mod (输入数字 0-{len(mods) + 1}): ").strip()
            if not choice_str:
                continue
            choice = int(choice_str)

            total_processed = 0
            total_failed = 0
            mods_to_process = []

            if choice == 0:
                print_color("操作已取消。", Colors.BLUE)
                return
            elif choice == len(mods) + 1:
                print_color(
                    f"准备 {operation} 全部 {len(mods)} 个 Mods...", Colors.BLUE)
                mods_to_process = mods
            elif 1 <= choice <= len(mods):
                mods_to_process = [mods[choice - 1]]
            else:
                print_color(f"无效的选项 '{choice_str}'。", Colors.RED)
                continue

            # 执行处理
            for mod_info in mods_to_process:
                processed, failed = manage_mod(
                    mod_info["source"], mod_info["name"], operation, mods_path)
                total_processed += processed
                total_failed += failed

            # 打印总结
            if len(mods_to_process) > 0:
                summary_color = Colors.RED if total_failed > 0 else Colors.GREEN
                print_color(
                    f"\n操作总结：{total_processed} 个项目成功，{total_failed} 个项目失败。", summary_color)
            break

        except ValueError:
            print_color(f"输入无效 '{choice_str}'，请输入数字。", Colors.RED)
        except Exception as e:  # 捕获 manage_mod 可能抛出的其他错误
            print_color(f"处理选择时发生意外错误: {e}", Colors.RED)
            traceback.print_exc()
            break  # 出错则退出循环


def install_smapi(sv_path: Union[str, Path]) -> bool:
    """安装SMAPI"""
    sv_path = Path(sv_path)
    smapi_exe_path = sv_path / "StardewModdingAPI.exe"

    if smapi_exe_path.exists():
        print_color("SMAPI 已安装，跳过。", Colors.GREEN)
        return False

    print_color("SMAPI 未安装，开始安装...", Colors.YELLOW)

    smapi_installer_temp_dir = RESOURCE_DIR / "SMAPI_Installer"
    if smapi_installer_temp_dir.exists():
        print_color(
            f"发现旧的临时 SMAPI 目录，尝试清理: {smapi_installer_temp_dir.name}", Colors.YELLOW)
        remove_path(smapi_installer_temp_dir)  # 直接调用

    smapi_extract_path = None
    try:
        smapi_zip = find_zip_file("SMAPI", RESOURCE_DIR)
        smapi_extract_path = expand_zip_file(
            smapi_zip, smapi_installer_temp_dir.name)

        if not smapi_extract_path or not smapi_extract_path.is_dir():
            raise Exception("SMAPI 解压失败或路径无效")

        # 动态查找 SMAPI.Installer.exe
        installer_path = next(smapi_extract_path.rglob(
            "SMAPI.Installer.exe"), None)

        if not installer_path or not installer_path.is_file():
            raise Exception(f"在 {smapi_extract_path} 中找不到 SMAPI.Installer.exe")

        print_color(f"找到 SMAPI 安装程序: {installer_path}", Colors.BLUE)
        print_color("正在启动 SMAPI 安装程序...", Colors.YELLOW)

        shell = win32com.client.Dispatch("Shell.Application")
        shell.ShellExecute(str(installer_path), "", str(
            installer_path.parent), "open", 1)

        time.sleep(1)

        app = Application(backend="win32").connect(
            path=str(installer_path), timeout=15)

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
        traceback.print_exc()
        return False


def install_stardrop(sv_path: Union[str, Path]) -> None:
    """安装Stardrop管理器 (使用长路径支持)"""
    sv_path = Path(sv_path)
    install_base_path = sv_path.parent.parent
    stardrop_target_path = install_base_path / "Stardrop"
    stardrop_shortcut_path = Path(
        os.path.expanduser("~/Desktop")) / "Stardrop.lnk"

    print_color(f"检查 Stardrop 安装状态于: {stardrop_target_path}", Colors.BLUE)

    stardrop_extract_path = None
    try:
        if stardrop_target_path.exists() and (stardrop_target_path / "Stardrop.exe").exists():
            print_color("Stardrop 已安装，跳过安装。", Colors.GREEN)
        else:
            print_color("Stardrop 未安装或不完整，开始安装...", Colors.YELLOW)
            stardrop_zip = find_zip_file("Stardrop", RESOURCE_DIR)
            stardrop_extract_temp_dir = RESOURCE_DIR / "Stardrop_extracted"

            # 清理旧的临时目录（如果存在）
            # remove_path 会处理不存在的情况，无需 try-except
            if stardrop_extract_temp_dir.exists():
                print_color(
                    f"发现旧的临时目录，尝试清理: {stardrop_extract_temp_dir.name}", Colors.YELLOW)
                # 直接调用，remove_path 会处理错误
                remove_path(stardrop_extract_temp_dir)

            stardrop_extract_path = expand_zip_file(
                stardrop_zip, stardrop_extract_temp_dir.name)

            if not stardrop_extract_path or not stardrop_extract_path.is_dir():
                raise Exception("Stardrop 解压失败或解压路径无效")

            print_color(
                f"将 Stardrop 从 {stardrop_extract_path} 复制到 {stardrop_target_path}...", Colors.BLUE)

            stardrop_target_path.parent.mkdir(parents=True, exist_ok=True)
            copytree_longpath(stardrop_extract_path, stardrop_target_path)
            print_color("Stardrop 文件复制完成。", Colors.GREEN)

        # 创建桌面快捷方式
        if not stardrop_shortcut_path.exists():
            print_color("正在创建 Stardrop 桌面快捷方式...", Colors.YELLOW)
            try:
                stardrop_exe_path = stardrop_target_path / "Stardrop.exe"
                if not stardrop_exe_path.exists():
                    print_color(
                        f"错误：找不到 Stardrop.exe 用于创建快捷方式: {stardrop_exe_path}", Colors.RED)
                else:
                    shell = win32com.client.Dispatch("WScript.Shell")
                    shortcut = shell.CreateShortCut(
                        str(stardrop_shortcut_path))
                    shortcut.TargetPath = str(stardrop_exe_path)
                    shortcut.WorkingDirectory = str(stardrop_target_path)

                    shortcut.save()
                    print_color("桌面快捷方式创建完成。", Colors.GREEN)
            except Exception as short_e:
                print_color(f"创建 Stardrop 快捷方式时出错: {short_e}", Colors.RED)
        else:
            print_color("Stardrop 桌面快捷方式已存在。", Colors.GREEN)

    except Exception as e:
        print_color(f"Stardrop 安装过程中失败: {str(e)}", Colors.RED)
        traceback.print_exc()


def show_mod_menu_wrapper(mods_path: Path):
    """包装 show_mod_menu 以适应 run_step (处理用户交互循环)"""
    while True:
        print_color("\n请选择 Mod 操作：", Colors.YELLOW)
        print_color("1. 安装/更新 Mod (会覆盖现有同名文件/文件夹)", Colors.YELLOW)
        print_color("2. 移除 Mod", Colors.YELLOW)
        print_color("3. 跳过 Mod 管理", Colors.YELLOW)
        print_color("请输入选项（1-3）：", Colors.YELLOW)

        choice = input().strip()
        if choice == "1":
            show_mod_menu("copy", mods_path)
            break  # 完成操作后退出循环
        elif choice == "2":
            show_mod_menu("remove", mods_path)
            break  # 完成操作后退出循环
        elif choice == "3":
            print_color("跳过 MOD 管理。", Colors.BLUE)
            break
        else:
            print_color("无效的选项，请重新输入。", Colors.RED)


def run_step(step_num: int, description: str, func, *args, **kwargs) -> bool:
    """运行一个步骤并处理异常"""
    print_color(f"\n=== 步骤 {step_num}：{description} ===", Colors.YELLOW)
    try:
        result = func(*args, **kwargs)
        # print_color(f"步骤 {step_num} 完成。", Colors.GREEN) # 可以在具体函数内部打印成功信息
        return True  # 表示步骤启动且无异常（不一定代表逻辑成功）
    except Exception as e:
        print_color(f"步骤 {step_num} ({description}) 执行失败:", Colors.RED)
        traceback.print_exc()
        return False  # 表示步骤执行失败


def _cleanup_temp_dirs():
    """清理所有已知的临时目录"""
    print_color("\n正在尝试清理临时文件...", Colors.BLUE)
    temp_dirs_fixed = [
        RESOURCE_DIR / "SMAPI_Installer",
        RESOURCE_DIR / "Stardrop_extracted",
        RESOURCE_DIR / "Stardrop",  # 清理旧的 Stardrop 临时目录名
    ]

    # 查找并添加 Mods_extracted_* 目录
    temp_dirs_pattern = []
    try:
        for item in RESOURCE_DIR.glob("Mods_extracted_*"):
            if item.is_dir():
                temp_dirs_pattern.append(item)
    except Exception as glob_e:
        print_color(f"查找 Mods 临时目录时出错: {glob_e}", Colors.YELLOW)

    all_temp_dirs = temp_dirs_fixed + temp_dirs_pattern

    if not all_temp_dirs:
        print_color("  未找到需要清理的临时目录。", Colors.BLUE)
        return

    for temp_dir in all_temp_dirs:
        if temp_dir.exists():
            print_color(f"  尝试清理: {temp_dir.name}", Colors.BLUE)
            if not remove_path(temp_dir):  # remove_path 会打印成功或失败信息
                pass  # 失败信息已打印


def main() -> None:
    """程序主入口"""
    LINE = "=" * 60
    print_color(LINE, Colors.GREEN)
    print_color("          星露谷物语 Mod 安装程序 v1.1.0", Colors.GREEN)
    print_color(LINE, Colors.GREEN)

    exit_code = 0  # 默认为成功退出
    sv_path = None
    mods_path = None
    was_smapi_installed_now = False  # 用于判断是否显示 Steam 提示

    try:
        # 步骤 0: 获取路径 (这个不适合用 run_step，因为它决定后续步骤是否执行)
        print_color("\n=== 步骤 0：获取游戏路径 ===", Colors.YELLOW)
        sv_path_str = get_stardew_game_path()
        if not sv_path_str:
            print_color("未能自动找到游戏路径，请手动运行 SMAPI 安装程序。", Colors.RED)
            exit_code = 1
            return
        sv_path = Path(sv_path_str)
        mods_path = sv_path / "Mods"
        mods_path.mkdir(exist_ok=True)

        print_color(f"游戏路径: {sv_path}", Colors.BLUE)
        print_color(f"Mods 路径: {mods_path}", Colors.BLUE)

        # 步骤 1: 安装 SMAPI
        smapi_step_success = run_step(1, "安装 SMAPI", install_smapi, sv_path)
        if smapi_step_success:
            # 检查 SMAPI 是否确实安装成功（或已安装）
            if (sv_path / "StardewModdingAPI.exe").exists():
                pass  # 成功信息已在 install_smapi 内部打印
            else:
                # 虽然 run_step 成功，但 SMAPI 文件不存在，说明逻辑失败
                print_color(
                    "SMAPI 安装步骤完成，但未检测到 StardewModdingAPI.exe。", Colors.YELLOW)
        else:
            # run_step 失败，打印了错误，可以选择是否停止
            print_color("SMAPI 安装步骤失败，后续步骤可能受影响。", Colors.YELLOW)

        # 步骤 2: MODS 安装管理
        mod_step_success = run_step(
            2, "MODS 安装管理", show_mod_menu_wrapper, mods_path)
        if not mod_step_success:
            print_color("MOD 管理步骤执行失败。", Colors.YELLOW)

        # 步骤 3: 安装 Stardrop
        stardrop_step_success = run_step(
            3, "安装 Stardrop", install_stardrop, sv_path)
        if not stardrop_step_success:
            print_color("Stardrop 安装步骤执行失败。", Colors.YELLOW)

        # 结束提示
        print_color(LINE, Colors.GREEN)
        print_color("                    安装程序执行完毕！", Colors.GREEN)
        print_color(LINE, Colors.GREEN)

        # 检查 SMAPI 是否存在来决定是否显示提示 (更可靠的方式)
        if (sv_path / "StardewModdingAPI.exe").exists():
            print_color("提示：如果通过 Steam 启动游戏，请将以下内容复制粘贴到游戏启动选项中：", Colors.CYAN)
            print_color(
                f'"{sv_path / "StardewModdingAPI.exe"}" %command%', Colors.CYAN)

    except Exception as e:
        print_color("\n发生未处理的严重错误:", Colors.RED)
        traceback.print_exc()
        exit_code = 1
    finally:
        _cleanup_temp_dirs()
        print_color("\n按回车键退出...", Colors.WHITE)
        input()
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
