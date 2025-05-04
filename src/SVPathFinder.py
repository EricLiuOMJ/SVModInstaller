import argparse
import winreg
from pathlib import Path
from typing import Optional

import vdf

from tool import Colors, print_color


def get_stardew_game_path() -> Optional[Path]:
    """
    获取Stardew Valley游戏安装路径

    Returns:
        Optional[Path]: 游戏安装路径，如果未找到则返回None
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             "SOFTWARE\\Valve\\Steam")
        steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
        winreg.CloseKey(key)

        steam_path = Path(steam_path)
        vdf_file = steam_path / "steamapps" / "libraryfolders.vdf"

        with open(vdf_file, 'r') as f:
            libraryfolders = vdf.loads(f.read()).get('libraryfolders', {})

        for folder in libraryfolders.values():
            if isinstance(folder, dict) and 'apps' in folder and '413150' in folder['apps']:
                app_path = folder.get('path')
                if app_path:
                    game_path = Path(app_path) / 'steamapps' / \
                        'common' / 'Stardew Valley'
                    if game_path.exists():
                        return game_path
    except Exception as e:
        print_color(f"查找游戏路径时出错: {str(e)}", Colors.RED)

    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='获取Stardew Valley的路径信息')
    parser.add_argument('-g', action='store_true', help='输出游戏安装路径')
    parser.add_argument('-m', action='store_true', help='输出Mods文件夹路径')
    parser.add_argument('-c', action='store_true', help='输出游戏安装路径（中文格式）')
    args = parser.parse_args()

    game_path = get_stardew_game_path()
    if not game_path:
        print_color("未找到Stardew Valley的安装路径。", Colors.RED)
        input("\n按回车键退出...")
    else:
        mod_path = game_path / 'Mods'
        con_path = f"游戏安装路径为：{game_path}"

        if not any([args.g, args.m, args.c]):
            print_color(con_path, Colors.GREEN)
        else:
            if args.g:
                print_color(str(game_path), Colors.BLUE)
            if args.m:
                print_color(str(mod_path), Colors.BLUE)
            if args.c:
                print_color(con_path, Colors.GREEN)

        input("\n按回车键退出...")
