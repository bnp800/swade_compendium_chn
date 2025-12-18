# 翻译工作流 - HTML 注入工具

## 背景问题

当你进行 SWADE 项目翻译时，JSON 文件中嵌套的 HTML 结构（如 `\n`, `<article>`, `<span class="fontstyle0">`, UUID 链接等）会对翻译工作造成干扰。

这些工具让你能够：**专注于翻译纯文本，而无需手动维护复杂的 HTML 结构**

---

## 工作流概览

```
英文 JSON (带HTML)
    ↓
┌─────────────────────────────┐
│ 步骤1: 提取纯文本            │
│ tools/extract_text.py       │
└─────────────────────────────┘
    ↓
CSV 翻译模板 (纯文本, 无HTML)
    ↓ (交给译者或使用现有翻译)
填写中文翻译
    ↓
CSV 文件 (含中文翻译)
    ↓
┌─────────────────────────────┐
│ 步骤2: 注入HTML结构          │
│ utility/html_injector.py    │
└─────────────────────────────┘
    ↓
中文 JSON (保留完整HTML结构)
```

---

## 步骤1: 提取纯文本

**用途**: 从英文 JSON 中提取干净的纯文本，生成翻译模板

**命令**:
```bash
# 进入 utility 目录
cd utility

# 从英文 JSON 提取文本（生成CSV模板）
python extract_text.py ../en-US/swade-core-rules.swade-hindrances.json

# 或提取所有JSON文件
for file in ../en-US/*.json; do
    python extract_text.py "$file"
done
```

**输出**: `swade-core-rules.swade-hindrances_extract.csv`

**CSV 格式**:
```csv
key,field,source_text,translated_text
Enemy,description,Someone out there hates the character and wants him ruined...,
Small,name,Small,
```

> **注意**: 翻译时只需在 `translated_text` 列填写中文，无需关心 HTML 标签

---

## 步骤2: 翻译内容

**选项A**: 使用现有的纯文本翻译

如果你的翻译已经是纯文本格式，需要转换为 CSV:
```python
# 示例：将字典转换为CSV
import csv

translations = {
    'Enemy': {
        'name': '宿敌',
        'description': '有某些家伙憎恨该角色，希望其被毁灭、监禁或死亡。'
    },
    'Small': {
        'name': '矮小',
        'description': '此冒险者非常瘦小、非常矮，或是两者兼备。'
    }
}

with open('my_translations.csv', 'w', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['key', 'field', 'source_text', 'translated_text'])
    for key, fields in translations.items():
        for field, text in fields.items():
            writer.writerow([key, field, '', text])
```

**选项B**: 使用专业工具翻译
- 将 CSV 导入 Excel/Google Sheets
- 使用 CAT 工具（如 OmegaT、Trados）
- 在翻译平台协作

---

## 步骤3: 注入HTML结构

**用途**: 将纯文本翻译嵌入到英文 JSON 的 HTML 结构中，保持所有格式不变

**命令**:
```bash
# 基本用法
python html_injector.py \
    ../en-US/swade-core-rules.swade-hindrances.json \
    swade-core-rules.swade-hindrances_extract.csv \
    -o ../zh_Hans/swade-core-rules.swade-hindrances.json

# 处理所有文件
for csv_file in *_extract.csv; do
    base_name=$(echo "$csv_file" | sed 's/_extract.csv//')
    python html_injector.py \
        "../en-US/${base_name}.json" \
        "$csv_file" \
        -o "../zh_Hans/${base_name}.json"
done
```

**特点**:
- ✅ 保持所有 HTML 标签（`<article>`, `<p>`, `<span>` 等）
- ✅ 保持所有 CSS 类名（`class="fontstyle0"`）
- ✅ 保持所有 UUID 链接（`@UUID[...]{text}`）
- ✅ 保持 HTML 实体（`&rsquo;`, `&ldquo;` 等）
- ✅ 保持换行和格式
- ✅ 智能段落对齐

**示例转换**:

英文原始:
```html
<article class="swade-core">
<p><span class="fontstyle0">Someone out there hates the character...</span></p>
<p><span class="fontstyle0">If the enemy is one day defeated...</span></p>
</article>
```

你的翻译（纯文本）:
```
有某些家伙憎恨该角色，希望其被毁灭、监禁或死亡。
如果该敌人某天被击败，GM 应该...
```

输出结果:
```html
<article class="swade-core">
<p><span class="fontstyle0">有某些家伙憎恨该角色，希望其被毁灭、监禁或死亡。</span></p>
<p><span class="fontstyle0">如果该敌人某天被击败，GM 应该...</span></p>
</article>
```

---

## 高级用法

### 处理复杂的 UUID 链接

如果英文中包含链接:
```html
<p>See @UUID[Compendium.rules]{Rules} for details.</p>
```

你的翻译应该是:
```
详见规则了解更多信息。
```

脚本会自动保持链接位置:
```html
<p><span>详见@UUID[Compendium.rules]{Rules}了解更多信息。</span></p>
```

### 处理多个字段

如果你的 JSON 包含多个文本字段（name, description, biography等），CSV 应该有对应的行：

```csv
key,field,source_text,translated_text
Warrior,name,Warrior,战士
Warrior,description,A brave fighter.,勇敢的战士。
Warrior,biography,Born in the north...,出生于北方...
```

---

## 常见问题

### Q: 如何验证翻译是否正确嵌入？

A: 使用 JSON 格式化工具检查输出，或使用浏览器预览:

```bash
# 检查特定条目
python -m json.tool zh_Hans/swade-hindrances.json | grep -A 10 '"Enemy"'
```

### Q: 如何更新部分翻译？

A: 只需更新 CSV 文件中的对应行，然后重新运行 `html_injector.py`

### Q: 保留 HTML 结构会不会导致重复的类名或空标签？

A: 脚本会智能处理这个问题，保持原有结构的同时注入翻译文本

---

## 完整示例

全流程演示（以 hindrances 为例）:

```bash
cd utility

# 步骤1: 提取文本
python extract_text.py ../en-US/swade-core-rules.swade-hindrances.json

# 输出: swade-core-rules.swade-hindrances_extract.csv

# 步骤2: 在CSV中填写翻译（或使用你的现有翻译）
# - 在 translated_text 列填写中文
# - 保存为 my_translations.csv

# 步骤3: 注入HTML结构
python html_injector.py \
    ../en-US/swade-core-rules.swade-hindrances.json \
    my_translations.csv \
    -o ../zh_Hans/swade-core-rules.swade-hindrances.json

# 完成！检查输出
cat ../zh_Hans/swade-core-rules.swade-hindrances.json
```

---

## 脚本说明

### `extract_text.py`
- **输入**: 英文 JSON 文件（含 HTML）
- **输出**: CSV 或 JSON 格式的纯文本
- **用途**: 生成翻译模板

### `html_injector.py`
- **输入**: 英文 JSON + 中文翻译（CSV/JSON）
- **输出**: 中文 JSON（含完整 HTML 结构）
- **用途**: 将翻译注入 HTML 框架

---

## 最佳实践

1. **备份原始文件**: 操作前备份 `en-US/` 和 `zh_Hans/` 目录

2. **分批次处理**: 不要一次性处理所有文件，先测试单个文件

3. **验证关键条目**: 翻译后检查几个复杂的条目（含多个段落、链接的）

4. **使用版本控制**: 用 git 跟踪更改，便于回滚
   ```bash
   git add zh_Hans/
   git commit -m "Update translations using html injector"
   ```

5. **自动化**: 为常用操作创建 shell 脚本

---

## 技术支持

如果遇到问题：

1. **检查 CSV 格式**: 确保列名正确（key, field, translated_text）
2. **验证 JSON 语法**: `python -m json.tool file.json`
3. **查看详细日志**: 脚本会输出未找到翻译的条目
4. **手动调整**: 对于复杂条目，可手动编辑输出 JSON

---

## 性能

- 处理单个文件: < 1秒
- 处理全部 SWADE 文件: ~10-20秒
- 内存使用: < 100MB

---

**祝你翻译顺利！**
