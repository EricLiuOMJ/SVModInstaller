# 🧭 SVPathFinder 使用说明

[SVPathFinder.exe](.\SVPathFinder.exe) 是一个用于自动检测《星露谷物语（Stardew Valley）》游戏安装路径的小工具。它主要用于帮助主程序快速定位游戏目录，从而顺利安装模组。

## 📦 用途

- 自动查找 Steam 平台上的 Stardew Valley 游戏安装路径
- 输出路径或以中文提示形式展示结果
- 支持输出 `Mods` 文件夹路径，便于模组管理

---

## ⚙️ 使用方式

### 执行方式

在命令行中运行：

```bash
SVPathFinder.exe [参数]
```

如果你是直接双击运行，不带参数时会默认以中文格式显示游戏安装路径，并暂停等待按键退出。

---

## 📥 可选参数

| 参数 | 含义                                                        |
| ---- | ----------------------------------------------------------- |
| `-g` | 显示 **游戏安装路径**（英文格式，无提示）                   |
| `-m` | 显示 **Mods 文件夹路径**（英文格式）                        |
| `-c` | 显示 **游戏安装路径**（中文格式，带“游戏安装路径为：”前缀） |

### 示例

1. 显示游戏安装路径（英文）：

   ```bash
   SVPathFinder.exe -g
   ```

2. 显示 Mods 文件夹路径：

   ```bash
   SVPathFinder.exe -m
   ```

3. 显示中文格式的游戏路径：

   ```bash
   SVPathFinder.exe -c
   ```

4. 不带参数运行（默认行为）：

   ```bash
   SVPathFinder.exe
   ```

   将等效于 `-c`，并等待用户按回车键退出。

---

## ✅ 成功输出示例

如果成功找到路径，将输出如下内容之一：

- `-g`:

  ```text
  D:\Steam\steamapps\common\Stardew Valley
  ```

- `-m`:

  ```text
  D:\Steam\steamapps\common\Stardew Valley\Mods
  ```

- `-c`:

  ```text
  游戏安装路径为：D:\Steam\steamapps\common\Stardew Valley
  ```

---

## ❌ 错误处理

如果找不到游戏路径或发生错误，程序将返回错误信息字符串，例如：

```Text
错误：找不到Stardew Valley的安装路径。
```

---

## 📁 应用场景

该工具主要被主程序调用，用于自动化获取路径。也可单独运行用于调试、手动查找路径或供其他脚本调用。

---

## 📝 注意事项

- 确保 Steam 和 Stardew Valley 已正确安装。
- 如果游戏安装在非标准路径，请确保其路径未被移动或损坏。
- 如果路径过深或含有特殊字符，可能导致读取失败，请尝试将游戏重新安装到浅层路径下。
