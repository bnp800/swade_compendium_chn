# Translation Generator 使用指南

本指南介绍如何使用 `foundryvtt-swade-babele-translation-files-generator` 模块从 FoundryVTT 导出 SWADE 内容的翻译模板文件。

## 目录

- [前置要求](#前置要求)
- [安装 Translation Generator](#安装-translation-generator)
- [导出流程](#导出流程)
- [映射配置说明](#映射配置说明)
- [导出文件格式](#导出文件格式)
- [验证导出文件](#验证导出文件)
- [不同 Compendium 类型处理](#不同-compendium-类型处理)

---

## 前置要求

在开始导出之前，请确保：

1. **FoundryVTT v13+** 已安装并运行
2. **SWADE 系统 v5.0.0+** 已安装
3. **Babele 模块** 已安装（用于翻译注入）
4. **目标内容模块** 已安装（如 swade-core-rules、swpf-core-rules 等）

---

## 安装 Translation Generator

### 方法一：模块管理器搜索（推荐）

1. 打开 FoundryVTT
2. 进入 **设置 → 模块管理**
3. 搜索 `SWADE - Translation files generator for Babele`
4. 点击安装

### 方法二：使用 Manifest URL

1. 打开 FoundryVTT
2. 进入 **设置 → 模块管理 → 安装模块**
3. 粘贴以下 Manifest URL：
   ```
   https://github.com/bnp800/foundryvtt-swade-babele-translation-files-generator/releases/latest/download/module.json
   ```
4. 点击安装

---

## 导出流程

### 步骤 1：启用模块

1. 创建或打开一个 SWADE 世界
2. 进入 **设置 → 管理模块**
3. 启用以下模块：
   - `SWADE - Translation files generator for Babele`
   - 目标内容模块（如 `SWADE Core Rules`）
4. 保存并重新加载世界

### 步骤 2：打开导出器

1. 点击侧边栏的 **Compendium Packs** 标签
2. 在顶部找到 **导出翻译文件** 按钮（仅 GM 可见）
3. 点击打开导出器界面

### 步骤 3：选择导出选项

导出器界面分为两个部分：

#### 单个 Compendium 导出

1. 从下拉列表选择要导出的 Compendium
2. （可选）上传现有翻译文件以合并已有翻译
3. 配置映射选项（见下文）
4. 点击 **导出** 按钮

#### 批量导出

1. 勾选要导出的多个 Compendium
2. 点击 **批量导出** 按钮
3. 系统将生成包含所有文件的 ZIP 压缩包

### 步骤 4：保存导出文件

导出的文件将自动下载到浏览器默认下载目录。

**文件命名规范**：
```
{module-id}.{compendium-id}.json
```

**示例**：
- `swade-core-rules.swade-edges.json`
- `swpf-core-rules.swpf-abilities.json`

---

## 映射配置说明

映射（Mapping）定义了 Babele 如何从 FoundryVTT 文档中提取和翻译字段。

### 映射文件位置

映射配置文件位于 `mappings/` 目录：

```
mappings/
├── abilities.json    # 能力映射
├── actor.json        # 角色映射
├── edges.json        # 专长映射
├── equipment.json    # 装备映射
├── hindrances.json   # 障碍映射
├── journal.json      # 日志映射
├── powers.json       # 异能映射
├── races.json        # 种族映射
├── skills.json       # 技能映射
├── tables.json       # 表格映射
└── vehicles.json     # 载具映射
```

### 映射格式

```json
{
    "mapping": {
        "字段名": "系统路径",
        "嵌套字段": {
            "path": "系统路径",
            "converter": "转换器名称"
        }
    }
}
```

### 常用映射示例

#### Edges（专长）映射
```json
{
    "mapping": {
        "description": "system.description",
        "requirements": "system.requirements.value",
        "category": "system.category",
        "actions": {
            "path": "system.actions",
            "converter": "actions"
        }
    }
}
```

#### Actor（角色）映射
```json
{
    "mapping": {
        "biography": "system.details.biography.value",
        "appearance": "system.details.appearance",
        "notes": "system.details.notes.value",
        "goals": "system.details.goals.value",
        "items": {
            "path": "items",
            "converter": "embeddedItems"
        },
        "effects": {
            "path": "effects",
            "converter": "nestedContent"
        }
    }
}
```

### 可用转换器

| 转换器名称 | 用途 |
|-----------|------|
| `embeddedItems` | 翻译嵌入的物品（自动复用已翻译内容） |
| `nestedContent` | 递归翻译嵌套内容 |
| `pages` | 翻译日志条目的多个页面 |
| `actions` | 翻译动作和技能名称 |

---

## 导出文件格式

导出的 JSON 文件遵循 Babele 翻译格式：

```json
{
    "label": "Compendium 显示名称",
    "entries": {
        "Entry Name": {
            "name": "条目名称（待翻译）",
            "description": "<article>HTML 内容（待翻译）</article>",
            "其他字段": "..."
        }
    },
    "mapping": {
        "字段映射配置": "..."
    }
}
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `label` | Compendium 在 UI 中显示的名称 |
| `entries` | 所有条目的翻译内容，以英文名称为键 |
| `mapping` | Babele 字段映射配置 |

---

## 验证导出文件

### 方法一：JSON 语法验证

```bash
# 使用 Python 验证
python -m json.tool path/to/exported-file.json

# 使用 jq 验证（如已安装）
jq . path/to/exported-file.json
```

### 方法二：使用自动化工具

```bash
cd swade_compendium_chn
python -m automation.json_validator.validator path/to/exported-file.json
```

### 方法三：检查条目数量

```bash
# 统计条目数量
python -c "import json; f=open('file.json'); d=json.load(f); print(f'条目数: {len(d.get(\"entries\", {}))}')"
```

### 验证清单

- [ ] JSON 语法正确
- [ ] `entries` 字段存在且非空
- [ ] 所有条目都有 `name` 字段
- [ ] HTML 内容格式正确
- [ ] 映射配置与目标 Compendium 类型匹配

---

## 不同 Compendium 类型处理

### Items（物品类）

包括：Edges、Hindrances、Powers、Skills、Weapons、Armor、Gear 等

**导出字段**：
- `name` - 物品名称
- `description` - 物品描述（HTML）
- `category` - 分类（如适用）
- `requirements` - 需求（专长）
- `trapping` - 修饰（异能）

**示例**：
```json
{
    "entries": {
        "Alertness": {
            "name": "Alertness",
            "description": "<article class=\"swade-core\">...</article>",
            "category": "Background"
        }
    }
}
```

### Actors（角色类）

包括：Characters、NPCs、Vehicles、Groups

**导出字段**：
- `name` - 角色名称
- `biography` - 传记
- `appearance` - 外貌
- `notes` - 备注
- `goals` - 目标
- `items` - 嵌入物品（使用 `embeddedItems` 转换器）

**注意**：嵌入物品会自动从已翻译的 Compendium 复用翻译。

### JournalEntries（日志条目）

**导出字段**：
- `name` - 日志名称
- `pages` - 页面数组（使用 `pages` 转换器）

**页面结构**：
```json
{
    "pages": {
        "page-id-or-name": {
            "name": "页面标题",
            "text": "页面内容（HTML）",
            "caption": "图片说明（如适用）"
        }
    }
}
```

### RollTables（随机表）

**导出字段**：
- `name` - 表格名称
- `description` - 表格描述
- `results` - 结果条目

---

## 常见问题

### Q: 导出按钮不显示？

A: 确保：
1. 你是 GM 角色
2. Translation Generator 模块已启用
3. 刷新页面后重试

### Q: 导出文件为空？

A: 检查：
1. 目标 Compendium 是否有内容
2. 映射配置是否正确
3. 浏览器控制台是否有错误信息

### Q: 如何合并现有翻译？

A: 在导出时：
1. 点击"选择现有翻译文件"
2. 上传之前的翻译 JSON 文件
3. 导出器会自动合并已有翻译

### Q: 批量导出失败？

A: 尝试：
1. 减少同时导出的 Compendium 数量
2. 检查浏览器内存使用
3. 分批次导出

---

## 下一步

导出完成后，请参考：
- [翻译工作流文档](./translation-workflow.md) - 完整翻译流程
- [本地开发环境配置](./local-dev-guide.md) - 测试翻译效果
