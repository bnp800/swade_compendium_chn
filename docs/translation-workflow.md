# SWADE 中文翻译工作流文档

本文档描述 SWADE 中文翻译项目的完整工作流程，从源文件导出到最终发布。

## 目录

- [工作流概览](#工作流概览)
- [阶段一：源文件准备](#阶段一源文件准备)
- [阶段二：翻译工作](#阶段二翻译工作)
- [阶段三：质量检查](#阶段三质量检查)
- [阶段四：集成测试](#阶段四集成测试)
- [阶段五：发布](#阶段五发布)
- [自动化工具](#自动化工具)
- [常见问题解答](#常见问题解答)

---

## 工作流概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           翻译工作流                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   FoundryVTT │    │  Translation │    │   en-US/     │                   │
│  │    + SWADE   │───▶│  Generator   │───▶│  源文件      │                   │
│  │   模块       │    │   模块       │    │              │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
│                                                 │                            │
│                                                 ▼                            │
│                                          ┌──────────────┐                   │
│                                          │  变更检测    │                   │
│                                          │  生成报告    │                   │
│                                          └──────────────┘                   │
│                                                 │                            │
│         ┌───────────────────────────────────────┼───────────────────┐       │
│         ▼                                       ▼                   ▼       │
│  ┌──────────────┐                        ┌──────────────┐    ┌──────────┐  │
│  │   Weblate    │                        │  本地翻译    │    │  术语表  │  │
│  │   协作翻译   │                        │  (CSV/JSON)  │    │  更新    │  │
│  └──────────────┘                        └──────────────┘    └──────────┘  │
│         │                                       │                   │       │
│         └───────────────────────────────────────┼───────────────────┘       │
│                                                 ▼                            │
│                                          ┌──────────────┐                   │
│                                          │  格式转换    │                   │
│                                          │  HTML 注入   │                   │
│                                          └──────────────┘                   │
│                                                 │                            │
│                                                 ▼                            │
│                                          ┌──────────────┐                   │
│                                          │  质量检查    │                   │
│                                          │  验证        │                   │
│                                          └──────────────┘                   │
│                                                 │                            │
│                                                 ▼                            │
│                                          ┌──────────────┐                   │
│                                          │   zh_Hans/   │                   │
│                                          │  翻译文件    │                   │
│                                          └──────────────┘                   │
│                                                 │                            │
│                                                 ▼                            │
│                                          ┌──────────────┐                   │
│                                          │  本地测试    │                   │
│                                          │  FoundryVTT  │                   │
│                                          └──────────────┘                   │
│                                                 │                            │
│                                                 ▼                            │
│                                          ┌──────────────┐                   │
│                                          │  发布        │                   │
│                                          │  GitHub      │                   │
│                                          └──────────────┘                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 阶段一：源文件准备

### 1.1 导出英文源文件

当 SWADE 系统或内容模块更新时，需要重新导出源文件。

**步骤**：

1. 在 FoundryVTT 中启用 Translation Generator 模块
2. 打开 Compendium 导出器
3. 选择需要更新的 Compendium
4. 导出 JSON 文件到 `en-US/` 目录

详细操作请参考 [Translation Generator 使用指南](./translation-generator-guide.md)。

### 1.2 检测变更

使用自动化工具检测源文件变更：

```bash
cd swade_compendium_chn

# 检测所有文件变更并生成报告
python -m automation.change_detector en-US/ --output changelog.md --sync-placeholders

# 如果有目标目录，可以同时创建占位文件
python -m automation.change_detector en-US/ --target zh_Hans/ --output changelog.md --sync-placeholders
```

**变更报告示例**：

```markdown
# 变更报告 - 2024-01-15

## swade-core-rules.swade-edges.json

### 新增条目 (3)
- New Edge 1
- New Edge 2
- New Edge 3

### 修改条目 (2)
- Modified Edge 1
- Modified Edge 2

### 删除条目 (1)
- Removed Edge 1
```

### 1.3 创建占位文件

如果 `zh_Hans/` 目录缺少对应文件，自动创建：

```bash
python -m automation.change_detector en-US/ --target zh_Hans/ --sync-placeholders
```

---

## 阶段二：翻译工作

### 2.1 使用 Weblate 协作翻译（推荐）

Weblate 是本项目的主要翻译平台。

**访问地址**：http://150.109.5.239/engage/swade/

**详细操作指南**：请参考 [Weblate 使用指南](./weblate-guide.md)

**工作流程**：

1. 注册/登录 Weblate 账号
2. 选择要翻译的组件
3. 在界面上进行翻译
4. 提交翻译（自动同步到 Git）

**优点**：
- 无需了解 Git 操作
- 支持翻译记忆和术语表
- 多人协作，避免冲突
- 自动质量检查

### 2.2 本地翻译工作流

如果需要本地翻译，可以使用以下流程：

#### 步骤 1：提取纯文本

```bash
# 提取单个文件到 PO 格式（推荐用于 Weblate）
python -m automation.format_converter extract \
    en-US/swade-core-rules.swade-edges.json \
    --output weblate/edges.po \
    --format po

# 提取到 CSV 格式（用于本地翻译）
python -m automation.format_converter extract \
    en-US/swade-core-rules.swade-edges.json \
    --output edges.csv \
    --format csv
```

输出 CSV 文件格式：
```csv
key,field,source_text,translated_text
Alertness,name,Alertness,
Alertness,description,Your hero notices subtle clues...,
```

#### 步骤 2：翻译内容

在 CSV 文件的 `translated_text` 列填写中文翻译。

**翻译建议**：
- 参考术语表 `glossary/swade-glossary.json`
- 保持专业术语一致性
- 注意上下文语境

#### 步骤 3：注入翻译

```bash
# 从 CSV 注入翻译
python -m automation.format_converter inject \
    en-US/swade-core-rules.swade-edges.json \
    edges-translated.csv \
    --output zh_Hans/swade-core-rules.swade-edges.json

# 从 PO 文件注入翻译
python -m automation.format_converter inject \
    en-US/swade-core-rules.swade-edges.json \
    weblate/edges-translated.po \
    --output zh_Hans/swade-core-rules.swade-edges.json
```

### 2.3 术语表管理

#### 查看术语表

```bash
# 查看 SWADE 术语表
cat glossary/swade-glossary.json | python -m json.tool
```

#### 应用术语表

```bash
python -m automation.glossary_manager apply \
    glossary/swade-glossary.json \
    zh_Hans/swade-core-rules.swade-edges.json \
    --output zh_Hans/swade-core-rules.swade-edges.json \
    --track
```

#### 检测未知术语

```bash
python -m automation.glossary_manager find-missing \
    glossary/swade-glossary.json \
    zh_Hans/swade-core-rules.swade-edges.json \
    --format markdown \
    --output missing-terms.md
```

---

## 阶段三：质量检查

### 3.1 JSON 语法验证

```bash
# 验证单个文件
python -m automation.json_validator zh_Hans/swade-core-rules.swade-edges.json

# 验证所有文件
python -m automation.json_validator zh_Hans/ --format json --output validation-report.json
```

### 3.2 翻译质量检查

```bash
python -m automation.quality_checker check \
    en-US/swade-core-rules.swade-edges.json \
    zh_Hans/swade-core-rules.swade-edges.json \
    --format markdown \
    --output quality-report.md

# 使用术语表进行检查
python -m automation.quality_checker check \
    en-US/swade-core-rules.swade-edges.json \
    zh_Hans/swade-core-rules.swade-edges.json \
    --glossary glossary/swade-glossary.json
```

**检查项目**：

| 检查项 | 说明 |
|--------|------|
| 占位符完整性 | 确保 `{0}`, `{{variable}}` 等占位符保留 |
| HTML 标签配对 | 验证所有标签正确闭合 |
| UUID 链接保留 | 确保 `@UUID[...]{}` 链接不变 |
| 术语一致性 | 检查术语使用是否与术语表一致 |

### 3.3 进度追踪

```bash
# 生成进度报告
python -m automation.progress_tracker.tracker \
    --source en-US/ \
    --target zh_Hans/ \
    --output progress-report.md
```

**报告示例**：

```markdown
# 翻译进度报告

## 总体进度
- 总条目: 500
- 已翻译: 450 (90%)
- 未翻译: 50 (10%)

## 各 Compendium 进度

| Compendium | 总数 | 已翻译 | 进度 |
|------------|------|--------|------|
| swade-edges | 100 | 95 | 95% |
| swade-hindrances | 50 | 48 | 96% |
| swade-powers | 80 | 70 | 87.5% |
```

---

## 阶段四：集成测试

### 4.1 本地 FoundryVTT 测试

1. 配置本地开发环境（参考 [本地开发环境配置指南](./local-dev-guide.md)）
2. 启动 FoundryVTT
3. 创建测试世界
4. 启用翻译模块
5. 验证翻译效果

### 4.2 测试清单

- [ ] 所有 Compendium 正确加载
- [ ] 条目名称显示中文
- [ ] 描述内容显示中文
- [ ] HTML 格式正确渲染
- [ ] UUID 链接可正常点击
- [ ] 嵌入物品正确翻译
- [ ] 中文字体正确显示

### 4.3 自动化测试

```bash
# 运行所有测试
pytest automation/tests/ -v

# 运行属性测试
pytest automation/tests/ -v -m property

# 生成覆盖率报告
pytest automation/tests/ -v --cov=automation --cov-report=html
```

---

## 阶段五：发布

### 5.1 提交变更

```bash
# 添加翻译文件
git add zh_Hans/
git add glossary/

# 提交
git commit -m "feat: 更新 SWADE 核心规则翻译"

# 推送
git push origin main
```

### 5.2 创建 Release

1. 在 GitHub 上创建新 Release
2. 填写版本号（遵循语义化版本）
3. 填写更新日志
4. 发布

### 5.3 CI/CD 自动化

GitHub Actions 会自动：
- 验证 JSON 语法
- 运行质量检查
- 打包发布文件
- 更新 FoundryVTT 模块仓库

---

## 自动化工具

### 工具列表

| 工具 | 位置 | 用途 |
|------|------|------|
| Change Detector | `automation/change_detector/` | 检测源文件变更 |
| Format Converter | `automation/format_converter/` | 格式转换 |
| Glossary Manager | `automation/glossary_manager/` | 术语表管理 |
| Quality Checker | `automation/quality_checker/` | 质量检查 |
| Progress Tracker | `automation/progress_tracker/` | 进度追踪 |
| JSON Validator | `automation/json_validator/` | JSON 验证 |

**详细使用说明**：请参考 [自动化工具使用指南](./automation-tools-guide.md)

### CLI 命令参考

```bash
# 变更检测
python -m automation.change_detector <source_dir> [--target <target_dir>] [--output <file>]

# 格式转换
python -m automation.format_converter extract <input_file> [--output <file>] [--format <format>]
python -m automation.format_converter inject <source_file> <translations_file> [--output <file>]

# 术语管理
python -m automation.glossary_manager <command> <glossary_file> [args...]

# 质量检查
python -m automation.quality_checker check <source_file> <target_file> [options]
python -m automation.quality_checker batch <source_dir> <target_dir> [options]

# JSON 验证
python -m automation.json_validator <path> [options]

# 增量更新
python -m automation.incremental_update update <source_file> <translation_file> [options]
python -m automation.incremental_update batch <source_dir> <translation_dir> [options]

# Babele 转换器测试
python -m automation.babele_converter validate <source_file> <translated_file> [options]
```

---

## 常见问题解答

### Q1: 如何处理新增的 Compendium？

**A**: 
1. 使用 Translation Generator 导出新 Compendium
2. 将文件保存到 `en-US/` 目录
3. 运行变更检测创建占位文件
4. 开始翻译工作

### Q2: 翻译冲突如何解决？

**A**: 
- 使用 Weblate 时，平台会自动处理冲突
- 本地翻译时，使用 Git 合并工具解决冲突
- 优先保留最新的翻译

### Q3: 如何回滚错误的翻译？

**A**:
```bash
# 查看历史版本
git log --oneline zh_Hans/problematic-file.json

# 回滚到特定版本
git checkout <commit-hash> -- zh_Hans/problematic-file.json
```

### Q4: 术语表更新后如何批量更新翻译？

**A**:
```bash
# 批量应用术语表到所有文件
python -m automation.glossary_manager apply \
    glossary/swade-glossary.json \
    zh_Hans/ \
    --track

# 或者逐个文件处理
for file in zh_Hans/*.json; do
    python -m automation.glossary_manager apply \
        glossary/swade-glossary.json \
        "$file" \
        --output "$file" \
        --track
done
```

### Q5: 如何处理 HTML 中的特殊字符？

**A**:
- HTML 实体（如 `&rsquo;`）会自动保留
- 中文标点应使用全角字符
- 避免在翻译中添加额外的 HTML 标签

### Q6: 嵌入物品为什么没有翻译？

**A**:
1. 确保对应的物品 Compendium 已翻译
2. 检查 `babele.js` 中的 `embeddedItems` 转换器是否正确注册
3. 验证映射配置是否正确

### Q7: 如何贡献翻译？

**A**:
1. **推荐方式**：通过 Weblate 平台贡献
2. **开发者方式**：Fork 仓库，提交 PR

### Q8: 翻译进度如何查看？

**A**:
- Weblate 平台：查看项目统计页面
- 本地：运行质量检查和验证工具查看完成度

### Q9: 如何报告翻译错误？

**A**:
1. 在 GitHub Issues 中报告
2. 在 Weblate 中标记问题
3. 在 QQ 频道或 Discord 反馈

### Q10: 支持哪些 SWADE 模块？

**A**:
- swade-core-rules（核心规则）
- swpf-core-rules（Pathfinder for Savage Worlds）
- swpf-bestiary（SWPF 怪物图鉴）
- 更多模块持续添加中

---

## 联系方式

- **QQ 频道**: https://qun.qq.com/qqweb/qunpro/share?_wv=3&_wwv=128&appChannel=share&inviteCode=3cheK
- **Discord**: https://discord.gg/7UrkEg634m
- **GitHub Issues**: https://github.com/fvtt-cn/swade_compendium_chn/issues
- **Weblate**: http://150.109.5.239/engage/swade/

---

## 相关文档

- [Weblate 使用指南](./weblate-guide.md)
- [自动化工具使用指南](./automation-tools-guide.md)
- [Translation Generator 使用指南](./translation-generator-guide.md)
- [本地开发环境配置指南](./local-dev-guide.md)
- [自动化工具 README](../automation/README.md)
- [工具脚本 README](../utility/README.md)
