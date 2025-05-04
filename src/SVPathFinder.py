import argparse
import winreg
from pathlib import Path
from typing import Optional
import sys

import vdf
from tool import Colors, print_color


def get_stardew_game_path() -> Optional[Path]:
    """
    获取Stardew Valley游戏安装路径
    Returns:
        Optional[Path]: 游戏安装路径，如果未找到则返回None
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam")
        steam_path_str, _ = winreg.QueryValueEx(key, "SteamPath")
        winreg.CloseKey(key)
        steam_path = Path(steam_path_str)
        vdf_file = steam_path / "steamapps" / "libraryfolders.vdf"
        if not vdf_file.is_file():
            print_color(f"未找到 Steam 库配置文件: {vdf_file}", Colors.YELLOW)
            return None
        with open(vdf_file, 'r', encoding='utf-8') as f:
            libraryfolders = vdf.loads(f.read()).get('libraryfolders', {})
        # 遍历库文件夹查找游戏 (AppID 413150)
        for folder_info in libraryfolders.values():
            if isinstance(folder_info, dict) and 'path' in folder_info and 'apps' in folder_info:
                apps = folder_info.get('apps')
                if isinstance(apps, dict) and '413150' in apps:
                    library_path = Path(folder_info['path'])
                    game_path = library_path / 'steamapps' / 'common' / 'Stardew Valley'
                    if game_path.is_dir():
                        return game_path

    except winreg.error as e:
        print_color(f"读取注册表时出错 (Steam 未安装或配置错误?): {e}", Colors.RED)
    except FileNotFoundError:
        print_color(f"无法找到 Steam 库配置文件: {vdf_file}", Colors.RED)
    except vdf.VDFMalformedError as e:
        print_color(f"解析 VDF 文件时出错: {e}", Colors.RED)
    except Exception as e:
        print_color(f"查找游戏路径时发生未知错误: {e}", Colors.RED)
    return None


def get_mods_folder_path() -> Optional[Path]:
    """
    获取Stardew Valley Mods文件夹路径
    Returns:
        Optional[Path]: Mods文件夹路径，如果未找到游戏路径或Mods文件夹不存在则返回None
    """
    game_path = get_stardew_game_path()
    if game_path:
        mods_folder = game_path / 'Mods'
        return mods_folder
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='获取Stardew Valley的路径信息')
    parser.add_argument('-g', '--game', action='store_true', help='输出游戏安装路径')
    parser.add_argument('-m', '--mods', action='store_true',
                        help='输出Mods文件夹路径')
    parser.add_argument('-c', '--console',
                        action='store_true', help='输出游戏安装路径（中文格式）')
    args = parser.parse_args()

    game_path = get_stardew_game_path()
    if not game_path:
        print_color("错误：未找到Stardew Valley的安装路径。", Colors.RED)
    else:
        mod_path = game_path / 'Mods'
        con_path_str = f"游戏安装路径为：{game_path}"

        print_game = args.game
        print_mods = args.mods
        print_console = args.console

        if not (print_game or print_mods or print_console):
            print_console = True
        if print_game:
            print(str(game_path))
        if print_mods:
            print(str(mod_path))
        if print_console:
            print_color(con_path_str, Colors.GREEN)

    # 仅在交互式模式下暂停
    if sys.stdout.isatty():
        input("\n按回车键退出...")
