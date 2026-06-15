# DeepSeek v4 AI Translation Guide

使用 DeepSeek v4 自动翻译 SWADE compendium 的完整指南。

## 快速开始

### 1. 环境准备

```bash
cd swade_compendium_chn

# 安装依赖
pip install httpx pyyaml

# 设置 API Key
export DEEPSEEK_API_KEY=sk-your-key-here
# Windows PowerShell:
# $env:DEEPSEEK_API_KEY="sk-your-key-here"
```

### 2. 预检（估算费用）

在实际翻译前，先估算范围和费用：

```bash
python -m automation.ai_translator.translate_compendium estimate
```

输出示例：
```
=== Translation Scope Estimate ===
Files:       30
Entries:     2136
Fields:      6264
Total chars: 4,039,393
Est. tokens: 2,356,312 (in+out)
Est. cost:   $0.518 USD
```

### 3. 翻译单个文件

```bash
python -m automation.ai_translator.translate_compendium file \
    en-US/swade-core-rules.swade-edges.json \
    --output zh_Hans/swade-core-rules.swade-edges.json \
    --glossary data/enhanced_glossary.json \
    --few-shot data/few_shot_examples.json
```

### 4. 翻译整个目录

```bash
python -m automation.ai_translator.translate_compendium dir \
    --dir en-US/ \
    --target zh_Hans/ \
    --glossary data/enhanced_glossary.json \
    --few-shot data/few_shot_examples.json
```

### 5. 链接后处理

翻译完成后，替换所有 @UUID 和 @Compendium 链接中的显示文本：

```bash
# 预览（不写入）
python -m automation.ai_translator.link_processor zh_Hans/ --dry-run

# 执行处理
python -m automation.ai_translator.link_processor zh_Hans/ \
    --glossary data/enhanced_glossary.json
```

## 完整工作流

```
┌─────────────────────────────────────────────────────────────────────┐
│                     完整 AI 翻译工作流                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  方式 A: 从 Translation Generator 导出                                │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────────┐            │
│  │ FoundryVTT│───▶│ Translation  │───▶│ en-US/*.json    │            │
│  │ + SWADE   │    │ Generator    │    │ (源文件)         │            │
│  └──────────┘    └──────────────┘    └────────┬────────┘            │
│                                                │                     │
│  方式 B: 直接从 .db 读取                         │                     │
│  ┌──────────┐    ┌──────────────┐              │                     │
│  │ .db 文件  │───▶│ db_converter │──────────────┘                    │
│  └──────────┘    └──────────────┘                                    │
│                                                │                     │
│                   ┌────────────────────────────┘                     │
│                   ▼                                                  │
│  ┌────────────────────────────────┐                                  │
│  │  DeepSeek v4 AI Translation    │                                  │
│  │  - 术语表注入 (1687 术语)       │                                  │
│  │  - Few-shot 示例参考            │                                  │
│  │  - HTML/链接保留                │                                  │
│  │  - 智能分块 (长文本)             │                                  │
│  └───────────────┬────────────────┘                                  │
│                   ▼                                                  │
│  ┌────────────────────────────────┐                                  │
│  │  Link Post-Processor            │                                  │
│  │  - @UUID 显示文本替换           │                                  │
│  │  - @Compendium 路径+显示替换    │                                  │
│  └───────────────┬────────────────┘                                  │
│                   ▼                                                  │
│  ┌────────────────────────────────┐                                  │
│  │  Quality Validation             │                                  │
│  │  - 链接数量校验                 │                                  │
│  │  - HTML 标签完整性              │                                  │
│  │  - 占位符保留校验               │                                  │
│  └───────────────┬────────────────┘                                  │
│                   ▼                                                  │
│            ┌──────────────┐                                          │
│            │ zh_Hans/*.json│  ← 最终翻译文件                          │
│            └──────────────┘                                          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## 从 .db 文件直接翻译

如果 Translation Generator 不可用，可以直接从 FoundryVTT 的 compendium pack 文件：

```bash
# 1. 将 .db 转换为 Babele JSON
python utility/db_converter.py \
    "/path/to/Data/modules/swade-core-rules/packs/swade-edges.db" \
    --type Item \
    --output en-US/swade-core-rules.swade-edges.json

# 2. AI 翻译
python -m automation.ai_translator.translate_compendium file \
    en-US/swade-core-rules.swade-edges.json \
    -o zh_Hans/swade-core-rules.swade-edges.json

# 3. 链接后处理
python -m automation.ai_translator.link_processor \
    zh_Hans/swade-core-rules.swade-edges.json
```

## 高级用法

### 增量翻译

只翻译新增或修改的条目：

```bash
# 比较 en-US 和 zh_Hans，只翻译差异
python -m automation.change_detector en-US/ --target zh_Hans/

# 对变更的文件运行 AI 翻译
python -m automation.ai_translator.translate_compendium dir --dir en-US/ --target zh_Hans/
```

### 干运行模式

不调用 API，仅预览将翻译的内容：

```bash
python -m automation.ai_translator.translate_compendium estimate --verbose
```

### 自定义术语表

```bash
# 使用自己的术语表
python -m automation.ai_translator.translate_compendium dir \
    --glossary my-glossary.json
```

### 环境变量配置

```bash
export DEEPSEEK_API_KEY=sk-xxx
export DEEPSEEK_BASE_URL=https://api.deepseek.com  # 默认
export DEEPSEEK_MODEL=deepseek-chat                 # 默认
```

## 质量保证

### 翻译验证

AI 翻译器内置验证器，自动检查：
- ✅ @UUID/@Compendium 链接数量一致
- ✅ HTML 标签完整配对
- ✅ `{0}`, `{{variable}}` 占位符保留
- ✅ 骰子表达式 `[[/r 1d4]]` 保留

### 链接后处理

运行链接后处理器确保所有链接的显示文本和路径名都翻译为中文。

### 人工审查

验证失败的条目会在日志中标出，可以：
1. 查看日志中的 `WARNING: Validation issues in ...`
2. 手动编辑对应的 zh_Hans JSON 文件
3. 重新运行链接后处理器

## 目录结构

```
swade_compendium_chn/
├── automation/
│   └── ai_translator/
│       ├── __init__.py              # 模块入口
│       ├── client.py                # DeepSeek API 客户端
│       ├── chunker.py               # HTML 智能分块器
│       ├── prompts.py               # 提示词构建 + 验证器
│       ├── translator.py            # 核心翻译引擎
│       ├── link_processor.py        # 链接后处理器
│       ├── tiddlywiki_parser.py     # TiddlyWiki 解析 (翻译记忆)
│       ├── memory_builder.py        # zh_Hans/ 翻译记忆索引
│       └── translate_compendium.py  # CLI 入口
├── data/
│   ├── enhanced_glossary.json       # 增强术语表 (1687 术语)
│   ├── few_shot_examples.json       # Few-shot 示例
│   └── translation_memory.json      # 翻译记忆索引
└── utility/
    └── db_converter.py              # .db → Babele JSON 转换器
```

## 故障排除

### API Key 错误
```
ValueError: DeepSeek API key not found
```
设置环境变量：`export DEEPSEEK_API_KEY=sk-xxx`

### 速率限制
```
WARNING: Rate limited, waiting 10s...
```
自动重试，等待时间指数递增。可降低并发度修改 `client.py`。

### 验证失败
```
WARNING: Validation issues in EntryName.description: ['Link count mismatch']
```
AI 可能遗漏了链接。手动检查该条目的翻译，或重新翻译该文件。
