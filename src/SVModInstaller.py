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
import logging
import win32com.client
from pywinauto.application import Application
from SVPathFinder import get_stardew_game_path, get_mods_folder_path
from ColorLogger import logger
from tool import get_resource_path, expand_zip_file, find_zip_file


WORK_DIR = get_resource_path("")
RESOURCE_DIR = WORK_DIR
logger.info(f"工作目录: {WORK_DIR}")
os.chdir(WORK_DIR)


# ====== 长路径处理函数 ======

def _longpath(path: Path) -> str:
    """将路径转换为长路径格式 (使用长路径前缀)"""
    abs_path = path.resolve()
    return rf"\\?\{str(abs_path)}"


def remove_path(path: Path):
    """统一处理文件或目录的删除（支持长路径，依赖 shutil/os）"""
    if not path.exists():
        logger.warning(f"目标不存在，无需删除: {path}")
        return True  # 不存在视为成功

    path_prefixed = _longpath(path)
    path_str = str(path)  # 用于日志

    try:
        if path.is_dir():
            # 主要依赖 shutil.rmtree
            shutil.rmtree(path_prefixed, ignore_errors=False)
            logger.success(f"已移除目录: {path_str}")
        elif path.is_file():
            os.remove(path_prefixed)
            logger.success(f"已移除文件: {path_str}")
        else:
            logger.warning(f"无法识别的路径类型，跳过删除: {path_str}")
            # 不认为是失败，因为无法处理
        return True
    except Exception as e:
        logger.error(f"删除 {path_str} 时出错: {e}")
        logging.exception(f"删除路径 {path_str} 时发生错误:")
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
        logger.error(f"复制目录 {src_str} 到 {dst_str} 时出错: {e}")
        logging.exception(f"复制目录 {src_str} 到 {dst_str} 时发生错误:")
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
        logger.error(f"源 Mod 文件夹无效: {source_path}")
        return 0, 1

    logger.info(f"处理 Mod '{mod_name}' ({operation})...")

    for item in source_path.iterdir():
        target_item_path = mods_path / item.name
        item_name = item.name

        success = True  # 假设成功
        try:
            if operation == "copy":
                # 1. 如果目标存在，先移除
                if target_item_path.exists():
                    logger.warning(f"  发现旧版本 '{item_name}'，正在移除...")
                    if not remove_path(target_item_path):
                        logger.error(f"  移除旧版本 '{item_name}' 失败，跳过复制。")
                        success = False  # 标记失败

                # 2. 如果移除成功或无需移除，执行复制
                if success:
                    if item.is_dir():
                        copytree_longpath(item, target_item_path)
                        logger.success(f"  已拷贝目录 '{item_name}'")
                    elif item.is_file():
                        shutil.copy2(_longpath(item),
                                     _longpath(target_item_path))
                        logger.success(f"  已拷贝文件 '{item_name}'")
                    else:
                        logger.warning(f"  跳过不支持的项目类型: '{item_name}'")
                        success = False

            elif operation == "remove":
                if target_item_path.exists():
                    if not remove_path(target_item_path):
                        success = False
                else:
                    logger.warning(f"  目标 '{item_name}' 不存在，无需移除")
                    success = None

        except Exception as e:
            logger.error(f"  处理 '{item_name}' ({operation}) 时出错: {e}")
            logging.exception(
                f"处理 Mod '{mod_name}' 中的项目 '{item_name}' ({operation}) 时发生错误:")
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
            mods_zip, temp_extract_dir.name)
    except Exception as e:
        logger.error(f"错误：无法找到或解压 Mods.zip: {e}")
        logging.exception("查找或解压 Mods.zip 时出错:")
        return

    if not mods_dir or not mods_dir.is_dir():
        logger.error(f"错误：解压后的 Mods 目录无效: {mods_dir}")
        return

    mod_folders = sorted([
        f for f in mods_dir.iterdir()
        if f.is_dir() and not f.name.startswith('.')
    ], key=lambda p: p.name)

    if not mod_folders:
        logger.warning(f"在解压目录 {mods_dir.name} 下没有找到任何MOD文件夹")
        return

    mods = [{"index": i + 1, "name": f.name, "source": f}
            for i, f in enumerate(mod_folders)]

    logger.step(f"可用 Mods (来源: {mods_dir.name}):")
    for mod in mods:
        logger.debug(f"{mod['index']:>2}. {mod['name']}")
    logger.debug(f"{len(mods) + 1:>2}. {'全部' + operation}")
    logger.debug(f" 0. 取消")

    while True:
        try:
            logger.step(f"请选择要 {operation} 的 Mod (输入数字 0-{len(mods) + 1}): ")
            choice_str = input().strip()
            if not choice_str:
                continue
            choice = int(choice_str)

            total_processed, total_failed = 0, 0
            mods_to_process = []

            if choice == 0:
                logger.info("操作已取消。")
                return
            elif choice == len(mods) + 1:
                logger.info(f"准备 {operation} 全部 {len(mods)} 个 Mods...")
                mods_to_process = mods
            elif 1 <= choice <= len(mods):
                mods_to_process = [mods[choice - 1]]
            else:
                logger.error(f"无效的选项 '{choice_str}'。")
                continue

            # 执行处理
            for mod_info in mods_to_process:
                processed, failed = manage_mod(
                    mod_info["source"], mod_info["name"], operation, mods_path)
                total_processed += processed
                total_failed += failed

            # 打印总结
            if len(mods_to_process) > 0:
                if total_failed > 0:
                    logger.error(
                        f"操作总结：{total_processed} 个项目成功，{total_failed} 个项目失败。")
                else:
                    logger.success(
                        f"操作总结：{total_processed} 个项目成功，{total_failed} 个项目失败。")
            break

        except ValueError:
            logger.error(f"输入无效 '{choice_str}'，请输入数字。")
        except Exception as e:  # 捕获 manage_mod 可能抛出的其他错误
            logger.error(f"处理选择时发生意外错误: {e}")
            logging.exception("处理 Mod 菜单选择时发生错误:")
            break


def install_smapi(smapi_exe_path: Union[str, Path]) -> bool:
    """安装SMAPI"""
    if Path(smapi_exe_path).exists():
        logger.success("SMAPI 已安装，跳过。")
        return False

    logger.warning("SMAPI 未安装，开始安装...")

    smapi_installer_temp_dir = RESOURCE_DIR / "SMAPI_Installer"
    if smapi_installer_temp_dir.exists():
        logger.warning(
            f"发现旧的临时 SMAPI 目录，尝试清理: {smapi_installer_temp_dir.name}")
        remove_path(smapi_installer_temp_dir)

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
            logger.error(f"在 {smapi_extract_path} 中找不到 SMAPI.Installer.exe")
            raise FileNotFoundError(
                f"在 {smapi_extract_path} 中找不到 SMAPI.Installer.exe")

        logger.info(f"找到 SMAPI 安装程序: {installer_path}")
        logger.warning("正在启动 SMAPI 安装程序...")

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

        logger.success("SMAPI安装完成")
        return True

    except Exception as e:
        logger.error(f"SMAPI 安装过程中出错: {str(e)}")
        logging.exception("SMAPI 安装过程中出错:")
        return False


def install_stardrop(sv_path: Union[str, Path]) -> None:
    """安装Stardrop管理器 (使用长路径支持)"""
    stardrop_target_path = Path(sv_path).parent.parent / "Stardrop"
    stardrop_shortcut_path = Path(
        os.path.expanduser("~/Desktop")) / "Stardrop.lnk"

    logger.info(f"检查 Stardrop 安装状态于: {stardrop_target_path}")

    stardrop_extract_path = None
    try:
        if stardrop_target_path.exists() and (stardrop_target_path / "Stardrop.exe").exists():
            logger.success("Stardrop 已安装，跳过安装。")
        else:
            logger.warning("Stardrop 未安装或不完整，开始安装...")
            stardrop_zip = find_zip_file("Stardrop", RESOURCE_DIR)
            stardrop_extract_temp_dir = RESOURCE_DIR / "Stardrop_extracted"

            # 清理旧的临时目录（如果存在）
            if stardrop_extract_temp_dir.exists():
                logger.warning(
                    f"发现旧的临时目录，尝试清理: {stardrop_extract_temp_dir.name}")
                remove_path(stardrop_extract_temp_dir)

            stardrop_extract_path = expand_zip_file(
                stardrop_zip, stardrop_extract_temp_dir.name)

            if not stardrop_extract_path or not stardrop_extract_path.is_dir():
                raise Exception("Stardrop 解压失败或解压路径无效")

            logger.info(
                f"将 Stardrop 从 {stardrop_extract_path} 复制到 {stardrop_target_path}...")

            stardrop_target_path.parent.mkdir(parents=True, exist_ok=True)
            copytree_longpath(stardrop_extract_path, stardrop_target_path)
            logger.success("Stardrop 文件复制完成。")

        # 创建桌面快捷方式
        if not stardrop_shortcut_path.exists():
            logger.warning("正在创建 Stardrop 桌面快捷方式...")
            try:
                stardrop_exe_path = stardrop_target_path / "Stardrop.exe"
                if not stardrop_exe_path.exists():
                    logger.error(
                        f"错误：找不到 Stardrop.exe 用于创建快捷方式: {stardrop_exe_path}")
                else:
                    shell = win32com.client.Dispatch("WScript.Shell")
                    shortcut = shell.CreateShortCut(
                        str(stardrop_shortcut_path))
                    shortcut.TargetPath = str(stardrop_exe_path)
                    shortcut.WorkingDirectory = str(stardrop_target_path)

                    shortcut.save()
                    print_color("桌面快捷方式创建完成。", Colors.GREEN)
            except Exception as short_e:
                logger.error(f"创建 Stardrop 快捷方式时出错: {short_e}")
                logging.exception("创建 Stardrop 快捷方式时出错:")  # 记录堆栈
        else:
            logger.success("Stardrop 桌面快捷方式已存在。")

    except Exception as e:
        logger.error(f"Stardrop 安装过程中失败: {str(e)}")
        logging.exception("Stardrop 安装过程中失败:")


def show_mod_menu_wrapper(mods_path: Path):
    """包装 show_mod_menu 以适应 run_step (处理用户交互循环)"""
    while True:
        logger.step("请选择 Mod 操作：")
        logger.debug("1. 安装/更新 Mod (会覆盖现有同名文件/文件夹)")
        logger.debug("2. 移除 Mod")
        logger.debug("3. 跳过 Mod 管理")
        logger.step("请输入选项（1-3）：")

        choice = input().strip()
        if choice == "1":
            show_mod_menu("copy", mods_path)
            break
        elif choice == "2":
            show_mod_menu("remove", mods_path)
            break
        elif choice == "3":
            logger.info("跳过 MOD 管理。")
            break
        else:
            logger.error("无效的选项，请重新输入。")


def run_step(step_num: int, description: str, func, *args, **kwargs) -> bool:
    """运行一个步骤并处理异常"""
    logger.step(f"=== 步骤 {step_num}：{description} ===")
    try:
        result = func(*args, **kwargs)
        return True
    except Exception as e:
        logger.error(f"步骤 {step_num} ({description}) 执行失败:")
        logging.exception(f"步骤 {step_num} ({description}) 执行时发生错误:")
        return False


def _cleanup_temp_dirs():
    """清理所有已知的临时目录"""
    logger.info("正在尝试清理临时文件...")
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
        logger.warning(f"查找 Mods 临时目录时出错: {glob_e}")

    all_temp_dirs = temp_dirs_fixed + temp_dirs_pattern

    if not all_temp_dirs:
        logger.info("  未找到需要清理的临时目录。")
        return

    for temp_dir in all_temp_dirs:
        if temp_dir.exists():
            logger.info(f"  尝试清理: {temp_dir.name}")
            if not remove_path(temp_dir):  # remove_path 会打印成功或失败信息
                pass


def main() -> None:
    """程序主入口"""
    LINE = "=" * 60
    logger.success(LINE)
    logger.success("          星露谷物语 Mod 安装程序 v1.1.0")
    logger.success(LINE)
    exit_code = 0

    try:
        # 步骤 0: 获取路径
        logger.step("=== 步骤 0：获取游戏路径 ===")
        sv_path = get_stardew_game_path()
        if not sv_path:
            logger.error("未能自动找到游戏路径，请手动运行 SMAPI 安装程序。")
            exit_code = 1
            return
        mods_path = sv_path / "Mods"
        smapi_exe_path = sv_path / "StardewModdingAPI.exe"

        logger.info(f"游戏路径: {sv_path}")
        logger.info(f"Mods 路径: {mods_path}")

        # 步骤 1: 安装 SMAPI
        smapi_step_success = run_step(
            1, "安装 SMAPI", install_smapi, smapi_exe_path)
        if smapi_step_success:
            if not smapi_exe_path.exists():
                logger.warning(
                    "SMAPI 安装步骤报告成功，但未检测到 StardewModdingAPI.exe。")
        else:
            logger.warning("SMAPI 安装步骤失败，后续步骤可能受影响。")
            try:
                mods_path.mkdir(exist_ok=True)
                logger.info(f"已尝试创建 Mods 目录: {mods_path}")
            except Exception as mkdir_e:
                logger.warning(f"尝试创建 Mods 目录失败: {mkdir_e}")

        # 步骤 2: MODS 安装管理
        mod_step_success = run_step(
            2, "MODS 安装管理", show_mod_menu_wrapper, mods_path)
        if not mod_step_success:
            logger.warning("MOD 管理步骤执行失败。")

        # 步骤 3: 安装 Stardrop
        stardrop_step_success = run_step(
            3, "安装 Stardrop", install_stardrop, sv_path)
        if not stardrop_step_success:
            logger.warning("Stardrop 安装步骤执行失败。")

        # 结束提示
        logger.success(LINE)
        logger.success("                    安装程序执行完毕！")
        logger.success(LINE)

        # 检查 SMAPI 是否存在来决定是否显示提示
        if smapi_exe_path.exists():
            logger.info("" + LINE)
            logger.step("提示：如果通过 Steam 启动游戏，请将以下内容复制粘贴到游戏启动选项中：")
            logger.critical(f'  "{smapi_exe_path}" %command%')
            logger.info(LINE)

    except Exception as e:
        logger.error("发生未处理的严重错误:")
        logging.exception("主程序发生未处理的严重错误:")
        exit_code = 1
    finally:
        _cleanup_temp_dirs()
        logger.debug("按回车键退出...")
        input()
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
