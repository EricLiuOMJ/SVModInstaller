# 🌟 星露谷物语模组安装程序使用说明

## 📦 功能概述

本程序是一个自动化工具，用于帮助玩家轻松安装和管理《星露谷物语（Stardew Valley）》的模组（MOD），主要功能包括：

1. **检测并安装 SMAPI（Stardew Valley Modding API）**
2. **管理和安装 MOD 文件**
3. **安装 Stardrop 模组管理器**

---

## ⚙️ 使用步骤

### 1. 准备工作

- 确保你已购买并安装了《星露谷物语》游戏。
- 游戏需通过 Steam 或 Epic 平台安装。
- 推荐在 Windows 系统上运行本程序。

---

### 2. 启动安装程序

双击运行 `SVModInstaller.exe`，进入主菜单界面。

---

### 3. 自动检测与安装 SMAPI

- 程序会自动检测是否已安装 **SMAPI**。
- 如果未安装，程序将：
  - 解压 SMAPI 安装包
  - 自动运行安装程序并完成安装
  - 提示你选择安装路径（通常为游戏根目录）

> ✅ 注意：请勿关闭安装窗口，直到提示“SMAPI 安装完成”。

---

### 4. 安装 MOD

- 程序会解压预置的 `Mods.zip` 文件。
- 进入 MOD 管理界面后，你可以选择：
  - **安装 MOD**：从预设列表中选择要安装的 MOD
  - **移除 MOD**：从游戏中删除已安装的 MOD
  - **全部安装/移除**

> 📁 所有 MOD 将被复制到游戏目录下的 `Mods/` 文件夹中。

---

### 5. 安装 Stardrop 管理器（推荐）

- 程序会解压并安装 [Stardrop](https://github.com/brandonkelly/Stardrop)。
- 自动创建桌面快捷方式。
- Stardrop 可以帮助你更方便地管理 MOD 配置、更新模组等。

---

## 📁 文件结构说明

```text
根目录/
│
├── SVModInstaller.exe          # 主程序
├── Mods.zip                    # 包含所有可用MOD的压缩包
├── SMAPI*.zip                  # SMAPI 安装包
├── Stardrop*.zip               # Stardrop 安装包
└── INSTALL.md                  # 安装说明
```

---

## ❗ 常见问题

### Q: 安装过程中提示“无法找到游戏路径”怎么办？

A: 确保你已正确安装游戏，并且可以通过 `SVPathFinder.exe` 正确识别游戏路径。如果失败，请手动输入游戏安装目录。

---

### Q: 安装完成后如何启动游戏？

A: 有两种方式：

1. 通过 Steam/Epic 启动游戏前，右键点击游戏 → 属性 → 启动选项，添加如下命令：

   ```text
   "${X:\Path\To}\Stardew Valley\StardewModdingAPI.exe" %command%
   ```

2. 直接使用 Stardrop 启动游戏。

---

### Q: 如何卸载 MOD？

A: 再次运行本程序，选择【移除 MOD】即可删除指定或全部 MOD。

---

如遇任何问题，请检查日志输出或联系开发者获取支持。祝你在星露谷中愉快种田！🌾
