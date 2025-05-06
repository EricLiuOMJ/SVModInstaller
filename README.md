# 🌟 星露谷物语模组安装程序使用说明

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org)

[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **作者**：Eric Liu
>
> **开发工具**：VS Code
>
> **GitHub 仓库**：[https://github.com/EricLiuOMJ/SVModInstaller](https://github.com/EricLiuOMJ/SVModInstaller)

这是一个用于自动化安装《星露谷物语（Stardew Valley）》模组的 Python 程序。它可以帮助你轻松安装 SMAPI、管理 MOD，并安装 Stardrop 模组管理器。本程序特别适合电脑新手，提供一键式操作体验。
文档内容和程序由 AI 生成，仅供参考。

---

## ✨ 功能概述

本程序是一个自动化工具，用于帮助玩家轻松安装和管理《星露谷物语》的模组（MOD），主要功能包括：

- **🔍 自动检测并安装 SMAPI**：脚本会自动检测是否已安装 SMAPI，如果未安装，将自动完成安装。
- **📦 提供 MOD 的安装和移除功能**：支持单个或批量操作，自动处理文件冲突。
- **🎮 自动安装 Stardrop 模组管理器**：包括创建桌面快捷方式。
- **🔗 创建桌面快捷方式**：方便快速启动 Stardrop。
- **⚙️ 提供 Steam 启动参数配置**：确保游戏能够正确启动 SMAPI。

---

## ⚙️ 使用步骤

### 1. 准备工作

- 确保你已购买并安装了《星露谷物语》（Stardew Valley）游戏。
- 游戏需通过 Steam 平台安装。
- 推荐在 Windows 系统上运行本程序。

---

### 2. 启动安装程序

解压 `SVModsInstall_v${VERSION}.zip`，进入 `SVModInstaller` 目录，双击运行 `SVModInstaller.exe`，进入主菜单界面。

---

### 3. 按照提示操作

- 脚本会自动检测游戏路径。如果无法识别，请手动输入正确的路径。
- 根据菜单提示选择需要执行的操作：安装 SMAPI、MOD 或 Stardrop。
- 安装过程中请耐心等待，不要关闭 PowerShell 窗口。

---

## 📁 文件结构说明

| 文件/目录               | 说明             |
| ----------------------- | ---------------- |
| `src/`                  | 源代码目录       |
| `src/SVModInstaller.py` | 主安装程序       |
| `src/SVPathFinder.py`   | 游戏路径查找工具 |
| `src/ColorLogger.py`    | 彩色日志输出工具 |
| `src/project.py`        | 项目管理工具     |
| `src/tool.py`           | 工具函数         |
| `resource/`             | 资源文件目录     |
| `resource/Mods/`        | MOD 文件存放目录 |
| `build/`                | 构建临时文件目录 |
| `cache/`                | 缓存目录         |
| `dist/`                 | 构建输出目录     |
| `release/`              | 发布包输出目录   |
| `requirements.txt`      | Python 依赖文件  |
| `CHANGELOG.md`          | 版本更新日志     |
| `LICENSE`               | 许可证文件       |
| `INTRODUCTION.md`       | 项目介绍文档     |

---

## 🛠️ 开发环境与构建说明

### 环境要求

- Python 3.8 或更高版本
- 安装所需依赖

  ```pwsh
  git clone https://github.com/EricLiuOMJ/SVModInstaller.git
  git lfs pull
  cd SVModInstaller
  python -m venv venv
  .\venv\Scripts\activate
  pip install -r requirements.txt
  ```

### 构建步骤

1. 更新资源文件（可选）
   将 Stardrop 和 SMAPI 安装包放入 `resource/` 目录。

   ```bash
   python src/project.py update
   ```

2. 构建可执行文件

   ```bash
   python src/project.py build --all  # 构建所有可执行文件
   # 或
   python src/project.py build -i     # 仅构建 SVModInstaller
   python src/project.py build -p     # 仅构建 SVPathFinder
   ```

3. 构建文件将在 [dist](./dist/) 目录中生成。

### 发布步骤

1. 运行发布命令

   ```bash
   python src/project.py release -v <版本号>  # 指定版本号
   # 或
   python src/project.py release              # 使用当前日期作为版本号
   ```

2. 发布文件将在 [release](./release/) 目录中生成。

---

## 📋 预期效果

### 1. 自动检测与安装 SMAPI

- 程序会自动检测是否已安装 **SMAPI**。
- 如果未安装，程序将：
  - 解压 SMAPI 安装包
  - 自动运行安装程序并完成安装
  - 提示你选择安装路径（通常为游戏根目录）

✅ **注意**：请勿关闭安装窗口，直到提示“SMAPI 安装完成”。

> 当前 SMAPI 版本为：`SMAPI 4.2.1-2400-4-2-1-1742951921`

---

### 2. 安装 MOD

- 程序会解压预置的 `Mods.zip` 文件。
- 进入 MOD 管理界面后，你可以选择：
  - **安装 MOD**：从预设列表中选择要安装的 MOD
  - **移除 MOD**：从游戏中删除已安装的 MOD
  - **全部安装/移除**

📁 所有 MOD 将被复制到游戏目录下的 `Mods/` 文件夹中。

⚠️ 注意：如果游戏已启动，请先关闭游戏，然后再运行安装程序。

#### 当前包含的 MOD 列表

| 名称                        | 版本号                       | 下载链接                                                             |
| --------------------------- | ---------------------------- | -------------------------------------------------------------------- |
| Stardew Valley Expanded     | 1.15.10                      | [Nexus Mod #3753](https://www.nexusmods.com/stardewvalley/mods/3753) |
| CJB Cheats Menu             | 1.38.0                       | [Nexus Mod #4](https://www.nexusmods.com/stardewvalley/mods/4)       |
| Content Patcher             | 2.6.1                        | [Nexus Mod #1915](https://www.nexusmods.com/stardewvalley/mods/1915) |
| Custom Companions           | 5.0.0                        | [Nexus Mod #8626](https://www.nexusmods.com/stardewvalley/mods/8626) |
| Farm Type Manager           | 1.24.0                       | [Nexus Mod #3231](https://www.nexusmods.com/stardewvalley/mods/3231) |
| Ridgeside Village           | 2.5.17                       | [Nexus Mod #7286](https://www.nexusmods.com/stardewvalley/mods/7286) |
| Ridgeside Village - Chinese | 2.5.17 - 2024 年 11 月 24 日 | [Nexus Mod #9247](https://www.nexusmods.com/stardewvalley/mods/9247) |
| SpaceCore                   | 1.27.0                       | [Nexus Mod #1348](https://www.nexusmods.com/stardewvalley/mods/1348) |
| Tractor Mod                 | 4.22.2                       | [Nexus Mod #1401](https://www.nexusmods.com/stardewvalley/mods/1401) |

---

### 3. 安装 Stardrop 管理器

**[Stardrop](https://github.com/brandonkelly/Stardrop) 是一个用于管理 MOD 的工具**，详情可点击查询。

> 当前使用的 Stardrop 版本为：[Stardrop 1.2.1](https://www.nexusmods.com/stardewvalley/mods/10455)

- 程序会解压并安装 `Stardrop-win-x64.zip` 。
- 自动创建桌面快捷方式。
- Stardrop 可以帮助你更方便地管理 MOD 配置、更新模组等。

---

## ❗ 常见问题

### Q: 安装过程中提示“无法找到游戏路径”怎么办？

A: 确保你已正确安装游戏，并且可以通过 `SVPathFinder.exe` 正确识别游戏路径。如果失败，请手动输入游戏安装目录。

---

### Q: 安装完成后如何启动游戏？

A: 有两种方式：

1. 通过 Steam 启动游戏前，右键点击游戏 → 属性 → 启动选项，添加如下命令：

   ```bash
   "${"X:\Path\To"}\Stardew Valley\StardewModdingAPI.exe" %command%
   ```

2. 直接使用 Stardrop 启动游戏。

---

### Q: 如何卸载 MOD？

A: 再次运行本程序，选择【移除 MOD】即可删除指定或全部 MOD。

---

### Q: 安装 Mods 时候报错？

A: 可能是该文件路径过深，引起的解压错误，从而报错找不到对应的文件。建议将 `SVModsInstall_v${VERSION}.zip` 移动至浅层路径下再解压运行。

---

## 📝 版本信息

当前版本：`v1.2.2`
请查看 [CHANGELOG.md](./CHANGELOG.md) 获取详细的版本更新信息。

---

## 💬 贡献与反馈

欢迎提交 PR 或在 GitHub 上提出 Issue：
[GitHub Issues](https://github.com/EricLiuOMJ/SVModInstaller/issues)

---

## 📄 许可证

本项目采用 MIT License，详情请参阅 [LICENSE](LICENSE) 文件。

---

如遇任何问题，请检查日志输出或联系开发者获取支持。祝你在星露谷中愉快种田！🌾
