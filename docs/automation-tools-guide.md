# 自动化工具使用指南

本指南详细介绍如何使用 `automation/` 目录下的各种自动化工具。

## 目录

- [环境准备](#环境准备)
- [工具概览](#工具概览)
- [Change Detector (变更检测器)](#change-detector-变更检测器)
- [Format Converter (格式转换器)](#format-converter-格式转换器)
- [Glossary Manager (术语管理器)](#glossary-manager-术语管理器)
- [Quality Checker (质量检查器)](#quality-checker-质量检查器)
- [Progress Tracker (进度追踪器)](#progress-tracker-进度追踪器)
- [JSON Validator (JSON 验证器)](#json-validator-json-验证器)
- [Multi Module Support (多模块支持)](#multi-module-support-多模块支持)
- [Incremental Update (增量更新)](#incremental-update-增量更新)
- [Babele Converter (Babele 转换器)](#babele-converter-babele-转换器)
- [CLI 工具](#cli-工具)
- [批处理脚本](#批处理脚本)

---

## 环境准备

### 安装依赖

```bash
cd swade_compendium_chn

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 安装依赖
pip install -e ".[dev]"
```

### 验证安装

```bash
# 运行测试确保环境正确
pytest automation/tests/ -v

# 检查工具是否可用
python -m automation.change_detector.detector --help
```

---

## 工具概览

| 工具 | 模块路径 | 主要功能 |
|------|----------|----------|
| Change Detector | `automation.change_detector` | 检测源文件变更 |
| Format Converter | `automation.format_converter` | 格式转换 |
| Glossary Manager | `automation.glossary_manager` | 术语表管理 |
| Quality Checker | `automation.quality_checker` | 质量检查 |
| Progress Tracker | `automation.progress_tracker` | 进度追踪 |
| JSON Validator | `automation.json_validator` | JSON 验证 |
| Multi Module | `automation.multi_module` | 多模块支持 |
| Incremental Update | `automation.incremental_update` | 增量更新 |
| Babele Converter | `automation.babele_converter` | Babele 转换 |

---

## Change Detector (变更检测器)

检测 `en-US/` 目录中的文件变更，生成变更报告。

### 基本用法

```bash
# 检测目录中所有文件变更
python -m automation.change_detector \
    en-US/ \
    --target zh_Hans/ \
    --output changelog.md \
    --sync-placeholders
```

### 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `source` | 源文件或目录 | `en-US/` |
| `--compare-with` | 比较的文件 | `backup.json` |
| `--backup-dir` | 备份目录 | `en-US.backup/` |
| `--output` | 输出报告文件 | `changelog.md` |
| `--create-placeholders` | 创建占位文件 | - |
| `--target-dir` | 目标目录 | `zh_Hans/` |
| `--format` | 输出格式 | `markdown`, `json` |

### 输出示例

```markdown
# 变更报告 - 2024-01-15

## swade-core-rules.swade-edges.json

### 新增条目 (3)
- Alertness
- Combat Reflexes
- Quick

### 修改条目 (2)
- Arcane Background (Magic)
- Beast Bond

### 删除条目 (1)
- Old Edge

### 统计
- 总条目: 120
- 新增: 3 (2.5%)
- 修改: 2 (1.7%)
- 删除: 1 (0.8%)
- 未变更: 114 (95%)
```

### 高级用法

```bash
# 生成详细的变更报告
python -m automation.change_detector.detector en-US/ \
    --backup-dir en-US.backup/ \
    --output detailed-changelog.json \
    --format json \
    --include-content-diff

# 只检测特定类型的文件
python -m automation.change_detector.detector en-US/ \
    --pattern "*.swade-edges.json" \
    --output edges-changelog.md

# 设置变更阈值
python -m automation.change_detector.detector en-US/ \
    --min-change-ratio 0.1 \
    --output significant-changes.md
```

---

## Format Converter (格式转换器)

在 Babele JSON 和 Weblate 友好格式之间转换。

### 基本用法

```bash
# 从 JSON 提取纯文本（用于 Weblate）
python -m automation.format_converter extract \
    en-US/swade-core-rules.swade-edges.json \
    --output weblate/edges.po \
    --format po

# 将翻译注入回 JSON
python -m automation.format_converter inject \
    en-US/swade-core-rules.swade-edges.json \
    weblate/edges.po \
    --output zh_Hans/swade-core-rules.swade-edges.json
```

### 支持的格式

| 格式 | 扩展名 | 用途 |
|------|--------|------|
| PO | `.po` | Weblate 原生格式 |
| CSV | `.csv` | Excel/表格编辑 |
| JSON | `.json` | 程序处理 |
| XLIFF | `.xlf` | CAT 工具 |

### 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `extract` | 提取文本到翻译格式 | - |
| `inject` | 注入翻译回 JSON | - |
| `INPUT_FILE` | 输入 JSON 文件 (位置参数) | `source.json` |
| `TRANSLATIONS_FILE` | 翻译文件 (位置参数) | `translations.po` |
| `--output` | 输出文件 | `target.po` |
| `--format` | 输出格式 | `po`, `csv`, `json` |
| `--track` | 显示替换统计 | - |

### 高级功能

```bash
# 提取时显示统计信息
python -m automation.format_converter extract \
    en-US/swade-core-rules.swade-edges.json \
    --output edges.csv \
    --format csv

# 注入翻译并验证结果
python -m automation.format_converter inject \
    en-US/swade-core-rules.swade-edges.json \
    edges-translated.csv \
    --output zh_Hans/swade-core-rules.swade-edges.json
```

---

## Glossary Manager (术语管理器)

管理翻译术语表，确保术语一致性。

### 基本用法

```bash
# 应用术语表到文本
python -m automation.glossary_manager apply \
    glossary/swade-glossary.json \
    input.txt \
    --output translated.txt \
    --track

# 查找未知术语
python -m automation.glossary_manager find-missing \
    glossary/swade-glossary.json \
    input.txt \
    --format markdown \
    --output missing-terms.md

# 更新术语表
python -m automation.glossary_manager update \
    glossary/swade-glossary.json \
    "Combat Reflexes" \
    "战斗反射"

# 导出术语表
python -m automation.glossary_manager export \
    glossary/swade-glossary.json \
    output.csv \
    --format csv

# 导入术语表
python -m automation.glossary_manager import \
    glossary/swade-glossary.json \
    new-terms.csv \
    --merge
```

### 术语表格式

```json
{
    "terms": {
        "Edge": "专长",
        "Hindrance": "障碍",
        "Power": "异能",
        "Wild Card": "主角",
        "Combat Reflexes": "战斗反射"
    },
    "metadata": {
        "version": "1.0",
        "last_updated": "2024-01-15T10:30:00Z"
    }
}
```

### 高级功能

```bash
# 批量应用术语表
python -m automation.glossary_manager.manager batch-apply \
    --glossary glossary/swade-glossary.json \
    --input-dir zh_Hans/ \
    --pattern "*.json" \
    --backup

# 生成术语使用报告
python -m automation.glossary_manager.manager analyze \
    --glossary glossary/swade-glossary.json \
    --input-dir zh_Hans/ \
    --output term-usage-report.html

# 从现有翻译中提取术语
python -m automation.glossary_manager.manager extract-terms \
    --source-dir en-US/ \
    --target-dir zh_Hans/ \
    --output candidate-terms.json \
    --min-frequency 3

# 验证术语一致性
python -m automation.glossary_manager.manager validate \
    --glossary glossary/swade-glossary.json \
    --input-dir zh_Hans/ \
    --output inconsistency-report.json
```

---

## Quality Checker (质量检查器)

验证翻译质量，检测常见问题。

### 基本用法

```bash
# 检查单个文件
python -m automation.quality_checker check \
    en-US/swade-core-rules.swade-edges.json \
    zh_Hans/swade-core-rules.swade-edges.json \
    --format text

# 批量检查
python -m automation.quality_checker batch \
    en-US/ \
    zh_Hans/ \
    --format markdown \
    --output quality-report.md

# 使用术语表检查
python -m automation.quality_checker check \
    en-US/swade-core-rules.swade-edges.json \
    zh_Hans/swade-core-rules.swade-edges.json \
    --glossary glossary/swade-glossary.json
```

### 检查类型

| 检查类型 | 说明 | 示例问题 |
|----------|------|----------|
| `placeholder` | 占位符检查 | 缺少 `{0}` 占位符 |
| `html` | HTML 标签检查 | 标签不匹配 `<p>` vs `</div>` |
| `uuid` | UUID 链接检查 | 链接被修改或删除 |
| `glossary` | 术语一致性 | Edge 翻译不一致 |
| `length` | 长度检查 | 翻译过长或过短 |
| `encoding` | 编码检查 | 特殊字符问题 |

### 报告格式

```json
{
    "file": "swade-core-rules.swade-edges.json",
    "timestamp": "2024-01-15T10:30:00Z",
    "summary": {
        "total_entries": 100,
        "checked_entries": 95,
        "issues_found": 8,
        "error_count": 2,
        "warning_count": 6
    },
    "issues": [
        {
            "entry": "Alertness",
            "field": "description",
            "type": "placeholder",
            "severity": "error",
            "message": "Missing placeholder {0} in translation",
            "source": "Gain {0} to Notice rolls",
            "target": "获得察觉检定加值"
        }
    ]
}
```

### 高级功能

```bash
# 自定义检查规则
python -m automation.quality_checker.checker \
    --source en-US/swade-core-rules.swade-edges.json \
    --target zh_Hans/swade-core-rules.swade-edges.json \
    --config custom-rules.json \
    --output detailed-report.json

# 生成修复建议
python -m automation.quality_checker.checker \
    --source en-US/swade-core-rules.swade-edges.json \
    --target zh_Hans/swade-core-rules.swade-edges.json \
    --suggest-fixes \
    --output report-with-fixes.json

# 与 Weblate 集成
python -m automation.quality_checker.checker weblate-export \
    --project-url http://150.109.5.239/projects/swade/ \
    --component swade-edges \
    --output weblate-issues.json
```

---

## Progress Tracker (进度追踪器)

追踪翻译进度，生成统计报告。

### 基本用法

```bash
# 生成进度报告
python -m automation.progress_tracker.tracker \
    --source-dir en-US/ \
    --target-dir zh_Hans/ \
    --output progress-report.md

# 生成 HTML 仪表板
python -m automation.progress_tracker.tracker dashboard \
    --source-dir en-US/ \
    --target-dir zh_Hans/ \
    --output dashboard.html \
    --include-charts

# 获取特定 Compendium 进度
python -m automation.progress_tracker.tracker single \
    --source en-US/swade-core-rules.swade-edges.json \
    --target zh_Hans/swade-core-rules.swade-edges.json \
    --output edges-progress.json
```

### 进度计算

```python
# 进度计算逻辑
completion_rate = translated_entries / total_entries * 100

# 条目状态分类
- translated: 有非空翻译内容
- untranslated: 无翻译或翻译为空
- outdated: 源文件更新后需要审核
- needs_review: 标记为需要审核
```

### 报告示例

```markdown
# SWADE 翻译进度报告
生成时间: 2024-01-15 10:30:00

## 总体进度
- 总条目: 1,250
- 已翻译: 1,125 (90.0%)
- 未翻译: 125 (10.0%)
- 需要审核: 50 (4.0%)

## 各 Compendium 详情

### swade-core-rules.swade-edges
- 进度: 95/100 (95.0%)
- 状态: 接近完成
- 最后更新: 2024-01-14

### swade-core-rules.swade-hindrances  
- 进度: 48/50 (96.0%)
- 状态: 接近完成
- 最后更新: 2024-01-13

### swade-core-rules.swade-powers
- 进度: 70/80 (87.5%)
- 状态: 进行中
- 最后更新: 2024-01-15
```

### 高级功能

```bash
# 生成趋势分析
python -m automation.progress_tracker.tracker trend \
    --source-dir en-US/ \
    --target-dir zh_Hans/ \
    --history-days 30 \
    --output trend-analysis.html

# 贡献者统计
python -m automation.progress_tracker.tracker contributors \
    --target-dir zh_Hans/ \
    --git-log \
    --output contributors.json

# 预估完成时间
python -m automation.progress_tracker.tracker estimate \
    --source-dir en-US/ \
    --target-dir zh_Hans/ \
    --history-days 14 \
    --output completion-estimate.json
```

---

## JSON Validator (JSON 验证器)

验证 JSON 文件语法和结构。

### 基本用法

```bash
# 验证单个文件
python -m automation.json_validator \
    zh_Hans/swade-core-rules.swade-edges.json

# 验证目录中所有文件
python -m automation.json_validator \
    zh_Hans/ \
    --format json \
    --output validation-report.json

# 验证时过滤文件
python -m automation.json_validator \
    zh_Hans/ \
    --pattern "*.json" \
    --no-recursive
```

### 验证规则

| 规则 | 说明 | 示例错误 |
|------|------|----------|
| 语法检查 | JSON 语法正确性 | 缺少逗号、引号不匹配 |
| 结构检查 | Babele 格式要求 | 缺少 `entries` 字段 |
| 编码检查 | UTF-8 编码 | BOM 字符、非法字符 |
| 字段检查 | 必需字段存在 | 条目缺少 `name` 字段 |

### 输出示例

```json
{
    "validation_results": {
        "total_files": 25,
        "valid_files": 23,
        "invalid_files": 2,
        "errors": [
            {
                "file": "swade-core-rules.swade-edges.json",
                "line": 45,
                "column": 12,
                "error": "Expecting ',' delimiter",
                "severity": "error"
            }
        ],
        "warnings": [
            {
                "file": "swade-core-rules.swade-powers.json",
                "entry": "Bolt",
                "field": "description",
                "warning": "Empty translation field",
                "severity": "warning"
            }
        ]
    }
}
```

---

## Multi Module Support (多模块支持)

支持多个 SWADE 扩展模块的翻译。

### 基本用法

```bash
# 初始化新模块支持
python -m automation.multi_module.manager init \
    --module-id swpf-apg \
    --module-name "SWPF Advanced Player's Guide" \
    --create-structure

# 检测跨模块共享内容
python -m automation.multi_module.manager detect-shared \
    --modules swade-core-rules,swpf-core-rules \
    --output shared-content.json

# 复用翻译到新模块
python -m automation.multi_module.manager reuse-translations \
    --source-module swade-core-rules \
    --target-module swpf-core-rules \
    --content-type abilities
```

### 支持的模块

| 模块 ID | 模块名称 | 状态 |
|---------|----------|------|
| `swade-core-rules` | SWADE 核心规则 | ✅ 完整支持 |
| `swpf-core-rules` | SWPF 核心规则 | ✅ 完整支持 |
| `swpf-bestiary` | SWPF 怪物图鉴 | ✅ 完整支持 |
| `swpf-apg` | SWPF 高级玩家指南 | 🚧 开发中 |

### 高级功能

```bash
# 生成模块依赖图
python -m automation.multi_module.manager dependency-graph \
    --modules-dir modules/ \
    --output dependency-graph.svg

# 同步共享翻译
python -m automation.multi_module.manager sync-shared \
    --config multi-module-config.json \
    --dry-run

# 验证模块完整性
python -m automation.multi_module.manager validate \
    --module swpf-core-rules \
    --check-dependencies \
    --output validation-report.json
```

---

## Incremental Update (增量更新)

处理源文件更新时的增量翻译。

### 基本用法

```bash
# 更新单个翻译文件
python -m automation.incremental_update update \
    en-US/swade-core-rules.swade-edges.json \
    zh_Hans/swade-core-rules.swade-edges.json \
    --output updated.json \
    --backup

# 批量更新所有文件
python -m automation.incremental_update batch \
    en-US/ \
    zh_Hans/ \
    --pattern "*.json" \
    --backup \
    --report update-report.md
```

### 更新策略

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| `preserve` | 保留现有翻译 | 小幅更新 |
| `overwrite` | 覆盖现有翻译 | 大幅重构 |
| `smart` | 智能合并 | 常规更新 |
| `interactive` | 交互式选择 | 复杂冲突 |

### 冲突处理

```bash
# 交互式解决冲突
python -m automation.incremental_update.updater resolve-conflicts \
    --conflicts conflicts.json \
    --interactive

# 自动解决简单冲突
python -m automation.incremental_update.updater resolve-conflicts \
    --conflicts conflicts.json \
    --auto-resolve \
    --prefer-newer
```

---

## Babele Converter (Babele 转换器)

测试和验证 Babele 转换器功能。

### 基本用法

```bash
# 验证翻译完整性
python -m automation.babele_converter validate \
    en-US/swade-core-rules.swade-edges.json \
    zh_Hans/swade-core-rules.swade-edges.json \
    --format text

# 测试嵌入项目重用
python -m automation.babele_converter test-reuse \
    zh_Hans/ \
    --verbose

# 列出可翻译字段
python -m automation.babele_converter fields \
    en-US/swade-core-rules.swade-edges.json
```

### 转换器类型

| 转换器 | 用途 | 示例 |
|--------|------|------|
| `embeddedItems` | 嵌入物品翻译 | Actor 中的装备 |
| `nestedContent` | 嵌套内容翻译 | 复杂数据结构 |
| `pages` | 多页面翻译 | JournalEntry 页面 |
| `actions` | 动作翻译 | 技能和动作 |

---

## CLI 工具

统一的命令行接口。

### 安装 CLI

```bash
# 安装 CLI 工具
pip install -e ".[cli]"

# 验证安装
swade-translation --version
```

### 基本命令

```bash
# 检测变更
swade-translation detect-changes en-US/ --backup en-US.backup/

# 提取翻译模板
swade-translation extract en-US/ --output weblate/ --format po

# 注入翻译
swade-translation inject en-US/ weblate/ --output zh_Hans/

# 质量检查
swade-translation check zh_Hans/ --source en-US/

# 生成进度报告
swade-translation progress zh_Hans/ --source en-US/
```

### 配置文件

创建 `swade-translation.toml`：

```toml
[paths]
source_dir = "en-US"
target_dir = "zh_Hans"
backup_dir = "en-US.backup"
glossary = "glossary/swade-glossary.json"

[quality]
checks = ["placeholder", "html", "uuid", "glossary"]
severity_threshold = "warning"

[progress]
include_charts = true
output_format = "html"

[automation]
auto_backup = true
auto_validate = true
```

---

## 批处理脚本

常用的批处理操作。

### Windows 批处理

创建 `scripts/update-translations.bat`：

```batch
@echo off
echo 开始翻译更新流程...

echo 1. 检测变更
python -m automation.change_detector en-US/ --target zh_Hans/ --output changelog.md --sync-placeholders

echo 2. 应用术语表
python -m automation.glossary_manager apply glossary/swade-glossary.json zh_Hans/ --track

echo 3. 质量检查
python -m automation.quality_checker batch en-US/ zh_Hans/ --format markdown --output quality-report.md

echo 4. JSON 验证
python -m automation.json_validator zh_Hans/ --format json --output validation-report.json

echo 翻译更新完成！
pause
```

### Linux/macOS 脚本

创建 `scripts/update-translations.sh`：

```bash
#!/bin/bash
set -e

echo "开始翻译更新流程..."

echo "1. 检测变更"
python -m automation.change_detector en-US/ \
    --target zh_Hans/ \
    --output changelog.md \
    --sync-placeholders

echo "2. 应用术语表"
python -m automation.glossary_manager apply \
    glossary/swade-glossary.json \
    zh_Hans/ \
    --track

echo "3. 质量检查"
python -m automation.quality_checker batch \
    en-US/ \
    zh_Hans/ \
    --format markdown \
    --output quality-report.md

echo "4. JSON 验证"
python -m automation.json_validator zh_Hans/ \
    --format json \
    --output validation-report.json

echo "翻译更新完成！"
```

### Python 脚本

创建 `scripts/full-workflow.py`：

```python
#!/usr/bin/env python3
"""完整翻译工作流脚本"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """运行命令并处理错误"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"✅ {description}完成")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description}失败: {e}")
        print(f"错误输出: {e.stderr}")
        return None

def main():
    """主工作流"""
    print("🚀 开始 SWADE 翻译自动化工作流")
    
    # 1. 检测变更
    run_command(
        "python -m automation.change_detector en-US/ "
        "--target zh_Hans/ --output changelog.md --sync-placeholders",
        "检测源文件变更"
    )
    
    # 2. 格式转换（如需要）
    run_command(
        "python -m automation.format_converter extract "
        "en-US/swade-core-rules.swade-edges.json --output weblate/edges.po --format po",
        "提取翻译模板"
    )
    
    # 3. 应用术语表
    run_command(
        "python -m automation.glossary_manager apply "
        "glossary/swade-glossary.json zh_Hans/ --track",
        "应用术语表"
    )
    
    # 4. 质量检查
    run_command(
        "python -m automation.quality_checker batch "
        "en-US/ zh_Hans/ --format markdown --output quality-report.md",
        "执行质量检查"
    )
    
    # 5. JSON 验证
    run_command(
        "python -m automation.json_validator zh_Hans/ "
        "--format json --output validation-report.json",
        "验证 JSON 文件"
    )
    
    print("\n🎉 翻译工作流完成！")
    print("📊 查看报告:")
    print("  - 变更日志: changelog.md")
    print("  - 质量报告: quality-report.md") 
    print("  - 验证报告: validation-report.json")

if __name__ == "__main__":
    main()
```

---

## 故障排除

### 常见错误

#### 1. 模块导入错误

```bash
# 错误: ModuleNotFoundError: No module named 'automation'
# 解决: 确保在项目根目录运行，并安装了依赖
cd swade_compendium_chn
pip install -e ".[dev]"
```

#### 2. 文件路径错误

```bash
# 错误: FileNotFoundError: [Errno 2] No such file or directory
# 解决: 检查文件路径是否正确
ls -la en-US/  # 确认文件存在
```

#### 3. 权限错误

```bash
# 错误: PermissionError: [Errno 13] Permission denied
# 解决: 检查文件权限
chmod +w zh_Hans/  # 给予写权限
```

#### 4. JSON 解析错误

```bash
# 错误: json.JSONDecodeError: Expecting ',' delimiter
# 解决: 使用 JSON 验证器检查语法
python -m automation.json_validator.validator problematic-file.json
```

### 调试技巧

```bash
# 启用详细日志
export SWADE_TRANSLATION_DEBUG=1
python -m automation.change_detector.detector en-US/

# 使用 pdb 调试
python -m pdb -m automation.change_detector.detector en-US/

# 检查工具版本
python -c "import automation; print(automation.__version__)"
```

---

## 相关文档

- [翻译工作流文档](./translation-workflow.md)
- [Weblate 使用指南](./weblate-guide.md)
- [本地开发环境配置](./local-dev-guide.md)
- [自动化工具 API 文档](../automation/README.md)