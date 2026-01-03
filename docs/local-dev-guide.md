# 本地开发环境配置指南

本指南介绍如何配置本地 FoundryVTT 环境以测试和预览翻译效果。

## 目录

- [环境要求](#环境要求)
- [FoundryVTT 安装配置](#foundryvtt-安装配置)
- [模块安装](#模块安装)
- [开发模式配置](#开发模式配置)
- [热重载设置](#热重载设置)
- [调试技巧](#调试技巧)
- [常见问题排查](#常见问题排查)

---

## 环境要求

### 软件要求

| 软件 | 版本要求 | 用途 |
|------|---------|------|
| FoundryVTT | v11+ (推荐 v13) | 游戏平台 |
| Node.js | v18+ | 运行 FoundryVTT |
| Python | 3.9+ | 运行自动化工具 |
| Git | 最新版 | 版本控制 |

### 硬件建议

- **内存**: 8GB+ RAM
- **存储**: 10GB+ 可用空间
- **网络**: 稳定的网络连接（首次下载模块）

---

## FoundryVTT 安装配置

### 步骤 1：安装 FoundryVTT

1. 从 [FoundryVTT 官网](https://foundryvtt.com/) 下载安装包
2. 按照官方指南完成安装
3. 首次启动并完成许可证激活

### 步骤 2：配置数据目录

FoundryVTT 数据目录结构：

```
FoundryVTT/
├── Config/
├── Data/
│   ├── modules/          # 模块安装目录
│   ├── systems/          # 系统安装目录
│   └── worlds/           # 世界数据目录
└── Logs/
```

**Windows 默认路径**：
```
%LOCALAPPDATA%\FoundryVTT\Data\
```

**macOS 默认路径**：
```
~/Library/Application Support/FoundryVTT/Data/
```

**Linux 默认路径**：
```
~/.local/share/FoundryVTT/Data/
```

### 步骤 3：安装 SWADE 系统

1. 启动 FoundryVTT
2. 进入 **Game Systems** 标签
3. 搜索 `Savage Worlds Adventure Edition`
4. 点击安装

---

## 模块安装

### 必需模块

#### 1. Babele（翻译框架）

```
模块 ID: babele
Manifest: https://gitlab.com/riccisi/foundryvtt-babele/raw/master/module/module.json
```

#### 2. SWADE Core Rules（核心规则内容）

```
模块 ID: swade-core-rules
```

#### 3. 翻译模块（开发版本）

**方法一：符号链接（推荐）**

将项目目录链接到 FoundryVTT 模块目录：

**Windows (PowerShell 管理员模式)**：
```powershell
# 创建符号链接
New-Item -ItemType SymbolicLink `
  -Path "$env:LOCALAPPDATA\FoundryVTT\Data\modules\swade_compendium_chn" `
  -Target "D:\Github\swade_compendium_chn"
```

**macOS/Linux**：
```bash
# 创建符号链接
ln -s /path/to/swade_compendium_chn \
  ~/.local/share/FoundryVTT/Data/modules/swade_compendium_chn
```

**方法二：直接复制**

将项目文件复制到模块目录（不推荐，需要每次手动同步）。

---

## 开发模式配置

### 启用开发者模式

1. 启动 FoundryVTT
2. 进入 **设置 → 核心设置**
3. 启用 **Developer Mode**（如可用）

### 配置 VS Code 工作区

创建 `.vscode/settings.json`：

```json
{
  "files.associations": {
    "*.json": "json"
  },
  "json.schemas": [
    {
      "fileMatch": ["zh_Hans/*.json", "en-US/*.json"],
      "url": "./schemas/babele-translation.schema.json"
    }
  ],
  "editor.formatOnSave": true,
  "python.defaultInterpreterPath": ".venv/bin/python"
}
```

### Python 开发环境

```bash
# 进入项目目录
cd swade_compendium_chn

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 安装开发依赖
pip install -e ".[dev]"
```

---

## 热重载设置

FoundryVTT 支持热重载，可以在不重启的情况下更新翻译文件。

### 配置热重载

在 `module.json` 中添加热重载配置（已配置）：

```json
{
  "flags": {
    "hotReload": {
      "extensions": ["css", "json"],
      "paths": ["lang/", "zh_Hans/", "styles/"]
    }
  }
}
```

### 使用热重载

1. **修改翻译文件**：编辑 `zh_Hans/` 目录下的 JSON 文件
2. **保存文件**：FoundryVTT 会自动检测变更
3. **刷新 Compendium**：
   - 关闭并重新打开 Compendium 窗口
   - 或使用 `F5` 刷新页面（会重新加载所有内容）

### 手动刷新翻译

如果热重载不生效，可以在浏览器控制台执行：

```javascript
// 重新加载 Babele 翻译
game.babele.refresh();

// 或重新初始化特定 pack
const pack = game.packs.get("swade-core-rules.swade-edges");
await pack.getIndex({ fields: ["name", "type"] });
```

---

## 调试技巧

### 浏览器开发者工具

1. 按 `F12` 打开开发者工具
2. 切换到 **Console** 标签
3. 查看翻译相关日志（以 `SWADE Translation:` 开头）

### 常用调试命令

```javascript
// 查看 Babele 状态
console.log(game.babele);

// 查看已注册的翻译包
game.babele.packs.forEach(p => console.log(p.name, p.translated));

// 查看特定条目的翻译
const pack = game.babele.packs.find(p => p.name === "swade-edges");
console.log(pack.translations["Alertness"]);

// 检查转换器是否注册
console.log(game.babele.converters);

// 测试翻译查找
const item = await game.packs.get("swade-core-rules.swade-edges").getDocument("item-id");
console.log(item.name, item.system.description);
```

### 日志级别

在 `babele.js` 中调整日志级别：

```javascript
// 启用详细日志
const DEBUG = true;

if (DEBUG) {
  console.log('SWADE Translation: Debug info...', data);
}
```

---

## 常见问题排查

### 问题 1：翻译不显示

**症状**：Compendium 内容仍显示英文

**排查步骤**：

1. **检查模块是否启用**
   ```javascript
   game.modules.get("swade_compendium_chn")?.active
   // 应返回 true
   ```

2. **检查 Babele 是否加载翻译**
   ```javascript
   game.babele.packs.find(p => p.name.includes("swade"))
   // 应返回翻译包对象
   ```

3. **检查语言设置**
   - 进入 **设置 → 核心设置 → 语言**
   - 确保选择 **中文**

4. **检查翻译文件路径**
   - 确认 `zh_Hans/` 目录下有对应的 JSON 文件
   - 文件名必须与 Compendium ID 匹配

### 问题 2：热重载不工作

**症状**：修改文件后翻译不更新

**解决方案**：

1. 确认 `module.json` 中的 `hotReload` 配置正确
2. 检查文件是否在监控路径内
3. 尝试手动刷新：
   ```javascript
   game.babele.refresh();
   ```
4. 如仍不生效，使用 `F5` 完全刷新页面

### 问题 3：JSON 解析错误

**症状**：控制台显示 JSON 解析错误

**排查步骤**：

1. **验证 JSON 语法**
   ```bash
   python -m json.tool zh_Hans/problematic-file.json
   ```

2. **检查常见错误**
   - 缺少逗号或多余逗号
   - 未转义的引号
   - 非法字符（如 BOM）

3. **使用自动化验证**
   ```bash
   python -m automation.json_validator.validator zh_Hans/
   ```

### 问题 4：嵌入物品未翻译

**症状**：Actor 的嵌入物品显示英文

**排查步骤**：

1. **检查物品 Compendium 是否已翻译**
   - 嵌入物品翻译依赖于对应 Compendium 的翻译

2. **检查转换器是否注册**
   ```javascript
   console.log(game.babele.converters.embeddedItems);
   // 应返回函数
   ```

3. **检查映射配置**
   - 确认 `mappings/actor.json` 中配置了 `embeddedItems` 转换器

### 问题 5：中文字体显示异常

**症状**：中文显示为方块或乱码

**解决方案**：

1. **检查字体文件**
   - 确认 `style/cnHeading.TTF` 和 `style/cnP.ttf` 存在

2. **检查 CSS 加载**
   ```javascript
   // 在控制台检查样式是否加载
   document.querySelector('link[href*="swade-core.css"]')
   ```

3. **手动加载样式**
   ```javascript
   const link = document.createElement('link');
   link.rel = 'stylesheet';
   link.href = 'modules/swade_compendium_chn/swade-core.css';
   document.head.appendChild(link);
   ```

---

## 性能优化

### 减少加载时间

1. **只启用必要模块**
2. **使用 SSD 存储 FoundryVTT 数据**
3. **定期清理浏览器缓存**

### 翻译缓存

翻译模块使用内存缓存来加速重复查找：

```javascript
// 缓存会在以下情况清除：
// 1. 关闭世界
// 2. 重新加载页面
// 3. 手动调用 game.babele.refresh()
```

---

## 下一步

- [翻译工作流文档](./translation-workflow.md) - 完整翻译流程
- [Translation Generator 使用指南](./translation-generator-guide.md) - 导出翻译模板
