import argparse
import os
import winreg

import vdf


def get_stardew_game_path():
    try:
        # 获取Steam路径
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             "SOFTWARE\\Valve\\Steam")
        steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
        winreg.CloseKey(key)

        if not os.path.exists(steam_path):
            raise FileNotFoundError("错误：Steam路径不存在或无法访问。")

        # 获取VDF文件路径
        vdf_file_path = os.path.join(steam_path, "steamapps",
                                     "libraryfolders.vdf")
        if not os.path.exists(vdf_file_path):
            raise FileNotFoundError("错误：找不到libraryfolders.vdf文件。")

        # 读取并解析VDF文件
        with open(vdf_file_path, 'r') as file:
            data = file.read()
        parsed = vdf.loads(data)
        libraryfolders = parsed.get('libraryfolders', {})

        # 查找游戏路径
        app_path = None
        for folder in libraryfolders.values():
            if isinstance(
                    folder,
                    dict) and 'apps' in folder and '413150' in folder['apps']:
                app_path = folder.get('path')
                if app_path and os.path.exists(app_path):
                    break

        if app_path is None:
            raise FileNotFoundError("错误：找不到Stardew Valley的安装路径。")

        # 构建Mods路径
        game_path = os.path.join(app_path, 'steamapps', 'common',
                                 'Stardew Valley')
        if not os.path.exists(game_path):
            raise FileNotFoundError("错误：游戏路径不存在。请检查游戏是否正确安装。")

        return game_path

    except Exception as e:
        return str(e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='获取Stardew Valley的路径信息')
    parser.add_argument('-g', action='store_true', help='输出游戏安装路径')
    parser.add_argument('-m', action='store_true', help='输出Mods文件夹路径')
    parser.add_argument('-c', action='store_true', help='输出游戏安装路径（中文格式）')

    args = parser.parse_args()

    game_path = get_stardew_game_path()
    mod_path = os.path.join(game_path, 'Mods')
    con_path = f"游戏安装路径为：{game_path}"

    # 如果没有提供任何参数，默认使用-c
    if not any([args.g, args.m, args.c]):
        print(con_path)
        input("\n按回车键退出...")
    else:
        if args.g:
            print(game_path)
        if args.m:
            print(mod_path)
        if args.c:
            print(con_path)
            input("\n按回车键退出...")
