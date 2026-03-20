# Requirements Document

## Introduction

本文档定义了 SWADE 中文翻译项目 (swade_compendium_chn) 的自动化工作流需求。该工作流以 Weblate 为核心翻译管理平台，构建从源文件导出到最终翻译同步的完整流水线。

完整工作流链路：
1. **源文件导出**: 使用 Translation Generator 从 FoundryVTT 导出 Weblate 兼容的 JSON 源文件
2. **文本提取**: 从 JSON 提取纯文本到 CSV，剥离链接和 HTML，便于翻译
3. **翻译**: 翻译者在 CSV 中完成翻译（可通过 Weblate 或本地编辑）
4. **链接后处理**: 翻译完成后，基于术语表批量替换超链接显示文本
5. **Weblate 集成**: 导入翻译到 Weblate，由 Weblate 管理 JSON 源文件和翻译文件的更新
6. **仓库同步**: Weblate 自动同步翻译结果到本仓库

核心设计原则：
- 翻译者只接触纯文本 CSV，无需处理链接和 HTML
- 超链接在翻译完成后由系统统一替换
- Weblate 作为翻译管理中枢，负责源文件/翻译文件的版本管理和同步
- 术语表驱动链接翻译和术语一致性

## Glossary

- **Babele**: FoundryVTT 的翻译框架模块，支持运行时翻译 compendium 内容
- **Compendium**: FoundryVTT 中的内容包，包含 Items、Actors、JournalEntries 等
- **Converter**: Babele 提供的转换器机制，用于动态翻译嵌套内容
- **Translation_Generator**: foundryvtt-swade-babele-translation-files-generator 模块，用于从 SWADE compendium 导出翻译模板
- **Weblate**: 协作翻译平台，用于管理翻译工作流和版本同步
- **Glossary**: 术语表，存储英文到中文的标准翻译映射
- **Source_JSON**: en-US 目录下的英文源文件（Translation Generator 导出）
- **Target_JSON**: zh_Hans 目录下的中文翻译文件
- **Mapping**: Babele 字段映射配置，定义哪些字段需要翻译
- **Link Post-Processor**: 链接后处理器，在翻译完成后基于术语表统一替换链接显示文本

## Requirements

### Requirement 1: 源文件导出与变更检测

**User Story:** As a 翻译协调者, I want 使用 Translation Generator 导出最新英文源文件并自动检测变更, so that 翻译团队能清楚知道哪些内容需要翻译或更新。

#### Acceptance Criteria

1. WHEN 翻译协调者使用 Translation_Generator 在 FoundryVTT 中导出新的源文件 THEN Source_Update_System SHALL 接受导出的 JSON 文件到 en-US 目录
2. WHEN 新的源文件提交到仓库 THEN Source_Update_System SHALL 自动对比新旧文件，识别新增、修改和删除的条目
3. WHEN 检测到变更 THEN Source_Update_System SHALL 生成变更报告（changelog），列出具体的条目变化
4. WHEN 源文件更新 THEN Source_Update_System SHALL 自动在 zh_Hans 目录创建对应的占位翻译文件（如不存在）
5. WHEN 条目被删除 THEN Source_Update_System SHALL 标记对应的翻译条目为废弃而非直接删除

### Requirement 2: 文本提取与 CSV 格式转换

**User Story:** As a 翻译者, I want 从 JSON 源文件中提取纯文本到 CSV 格式, so that 我可以在 Excel/WPS 或 Weblate 中方便地翻译，无需处理 HTML 和链接语法。

#### Acceptance Criteria

1. WHEN 英文源 JSON 文件更新 THEN Format_Converter SHALL 提取纯文本内容，完全剥离所有 @UUID 和 @Compendium 链接语法
2. WHEN 提取文本 THEN Format_Converter SHALL 剥离所有 HTML 标签，只输出纯文本
3. WHEN 提取文本 THEN Format_Converter SHALL 保留 HTML 结构信息和链接位置元数据，以便后续注入
4. WHEN 生成 CSV THEN Format_Converter SHALL 输出包含 key, field, source_text, translated_text, context 列的 CSV 文件
5. WHEN 生成 CSV THEN Format_Converter SHALL 在 context 列中包含链接相关术语提示，帮助翻译者理解上下文
6. WHEN 输出 CSV THEN Format_Converter SHALL 使用 UTF-8 BOM 编码，确保 Excel/WPS 兼容
7. WHEN 转换格式 THEN Format_Converter SHALL 以 CSV 为主要输出格式，同时支持 JSON 格式作为辅助

### Requirement 3: 翻译注入与链接后处理

**User Story:** As a 翻译协调者, I want 将翻译后的纯文本注入回 HTML 结构并自动替换所有链接显示文本, so that 最终的翻译文件包含完整的 HTML 格式和中文链接。

#### Acceptance Criteria

1. WHEN 翻译者完成 CSV 翻译 THEN Format_Converter SHALL 将纯文本翻译注入回原始 HTML 结构，保留原始链接不变
2. WHEN 注入翻译完成 THEN Link_Post_Processor SHALL 基于术语表自动替换所有 @UUID 链接中的显示文本为中文
3. WHEN 处理 @Compendium 链接 THEN Link_Post_Processor SHALL 同时替换 ref 路径中的条目名称和显示文本
4. WHEN 处理 @Compendium 纯引用（无显示文本） THEN Link_Post_Processor SHALL 仅替换 ref 路径中的条目名称
5. WHEN 链接显示文本在术语表中未找到 THEN Link_Post_Processor SHALL 保留原文并报告未匹配术语
6. WHEN 处理完成 THEN Link_Post_Processor SHALL 确保链接总数在处理前后保持一致
7. WHEN 处理完成 THEN Link_Post_Processor SHALL 输出处理结果统计（总链接数、成功替换数、未匹配数）

### Requirement 4: Weblate 集成与仓库同步

**User Story:** As a 翻译协调者, I want Weblate 作为翻译管理中枢管理源文件和翻译文件的更新, so that 翻译工作流有统一的版本管理和协作平台。

#### Acceptance Criteria

1. WHEN 翻译 CSV/JSON 文件准备就绪 THEN Weblate_Integration SHALL 支持将文件导入到 Weblate 翻译平台
2. WHEN 源 JSON 文件更新 THEN Weblate SHALL 自动检测源文件变更并更新翻译任务
3. WHEN 翻译者在 Weblate 上完成翻译 THEN Weblate SHALL 管理翻译文件的版本和状态
4. WHEN Weblate 中的翻译更新 THEN Weblate_Sync SHALL 自动同步翻译结果到本仓库的 zh_Hans 目录
5. WHEN 同步翻译 THEN Weblate_Sync SHALL 保持 Babele JSON 格式的正确性
6. THE Weblate_Integration SHALL 提供 Weblate 项目配置指南和组件设置说明

### Requirement 5: 术语一致性管理

**User Story:** As a 翻译协调者, I want 自动应用术语表确保翻译一致性, so that 所有翻译使用统一的专业术语，包括链接中的显示文本。

#### Acceptance Criteria

1. WHEN 翻译文件生成 THEN Glossary_System SHALL 自动应用 swade-glossary.json 中的术语映射
2. WHEN 发现未翻译的术语 THEN Glossary_System SHALL 标记该术语并建议添加到术语表
3. WHEN 术语表更新 THEN Glossary_System SHALL 自动更新所有引用该术语的翻译
4. WHEN 检测到术语不一致 THEN Glossary_System SHALL 生成警告报告
5. WHEN Link_Post_Processor 查找链接显示文本翻译 THEN Glossary_System SHALL 支持精确匹配和忽略大小写匹配
6. WHEN Link_Post_Processor 查找 Compendium 条目名称翻译 THEN Glossary_System SHALL 提供名称到中文的映射

### Requirement 6: Babele Converter 优化

**User Story:** As a 开发者, I want 利用 Babele converter 机制减少重复翻译, so that 相同内容只需翻译一次。

#### Acceptance Criteria

1. WHEN Actor 包含嵌入的 Items THEN Converter_System SHALL 自动从已翻译的 Item compendium 获取翻译
2. WHEN 多个条目引用相同的 Ability 或 Edge THEN Converter_System SHALL 复用已有翻译而非重复翻译
3. WHEN 注册 converter THEN Converter_System SHALL 支持自定义字段映射配置
4. WHEN 翻译嵌套内容 THEN Converter_System SHALL 递归处理所有层级的可翻译字段
5. WHEN 翻译 JournalEntry pages THEN Converter_System SHALL 正确处理多页面结构

### Requirement 7: 翻译质量检查

**User Story:** As a 翻译协调者, I want 自动检查翻译质量, so that 发布的翻译符合质量标准。

#### Acceptance Criteria

1. WHEN 翻译提交 THEN Quality_Checker SHALL 检查是否存在未翻译的占位符
2. WHEN 翻译提交 THEN Quality_Checker SHALL 验证 HTML 标签配对完整
3. WHEN 翻译提交 THEN Quality_Checker SHALL 检查 UUID 链接是否保持不变
4. WHEN 检测到质量问题 THEN Quality_Checker SHALL 生成详细的问题报告
5. WHEN 翻译包含术语 THEN Quality_Checker SHALL 验证术语使用是否与术语表一致

### Requirement 8: 翻译进度追踪

**User Story:** As a 翻译协调者, I want 追踪翻译进度和覆盖率, so that 我可以了解项目状态并分配工作。

#### Acceptance Criteria

1. WHEN 翻译文件更新 THEN Progress_Tracker SHALL 计算每个 compendium 的翻译完成百分比
2. WHEN 生成进度报告 THEN Progress_Tracker SHALL 区分已翻译、未翻译和需要更新的条目
3. WHEN 源文件变更 THEN Progress_Tracker SHALL 标记需要审核的已翻译条目
4. THE Progress_Tracker SHALL 生成可视化的进度仪表板

### Requirement 9: 增量更新支持

**User Story:** As a 翻译者, I want 只处理变更的内容, so that 我不需要重复翻译已完成的内容。

#### Acceptance Criteria

1. WHEN 源文件更新 THEN Incremental_Update_System SHALL 识别新增、修改和删除的条目
2. WHEN 条目内容未变更 THEN Incremental_Update_System SHALL 保留现有翻译
3. WHEN 条目内容变更 THEN Incremental_Update_System SHALL 标记该条目需要审核
4. WHEN 生成翻译任务 THEN Incremental_Update_System SHALL 只包含需要翻译的条目
5. WHEN 合并翻译 THEN Incremental_Update_System SHALL 智能合并新旧翻译内容

### Requirement 10: 多模块支持

**User Story:** As a 翻译协调者, I want 支持多个 SWADE 扩展模块的翻译, so that 用户可以获得完整的中文游戏体验。

#### Acceptance Criteria

1. THE Multi_Module_System SHALL 支持 swade-core-rules 核心规则翻译
2. THE Multi_Module_System SHALL 支持 swpf-core-rules (Pathfinder for Savage Worlds) 翻译
3. THE Multi_Module_System SHALL 支持 swpf-bestiary 怪物图鉴翻译
4. WHEN 添加新模块 THEN Multi_Module_System SHALL 自动创建对应的翻译文件结构
5. WHEN 模块间存在共享内容 THEN Multi_Module_System SHALL 复用已有翻译

### Requirement 11: 自动化 CI/CD 流程

**User Story:** As a 开发者, I want 自动化构建和发布流程, so that 翻译更新能快速部署到用户。

#### Acceptance Criteria

1. WHEN 翻译文件合并到主分支 THEN CI_System SHALL 自动验证 JSON 语法正确性
2. WHEN 验证通过 THEN CI_System SHALL 运行翻译完整性检查
3. WHEN 创建 release THEN CI_System SHALL 自动打包并发布到 FoundryVTT 官方仓库
4. WHEN 发布完成 THEN CI_System SHALL 通知翻译团队发布状态
5. IF JSON 语法错误 THEN CI_System SHALL 阻止合并并报告错误位置

### Requirement 12: Translation Generator 集成指南

**User Story:** As a 翻译协调者, I want 有清晰的源文件导出流程文档, so that 我可以高效地从 FoundryVTT 导出最新的英文内容。

#### Acceptance Criteria

1. THE Documentation_System SHALL 提供使用 Translation_Generator 模块导出源文件的步骤指南
2. THE Documentation_System SHALL 说明导出时应选择的选项和映射配置
3. THE Documentation_System SHALL 提供导出文件的命名规范和目录结构说明
4. WHEN 导出完成 THEN Documentation_System SHALL 提供验证导出文件完整性的方法
5. THE Documentation_System SHALL 说明如何处理不同类型的 compendium（Items、Actors、JournalEntries 等）

### Requirement 13: 本地开发环境支持

**User Story:** As a 开发者, I want 在本地环境中测试翻译效果, so that 我可以在发布前验证翻译质量。

#### Acceptance Criteria

1. THE Local_Dev_System SHALL 提供本地 FoundryVTT 环境配置指南
2. THE Local_Dev_System SHALL 支持热重载翻译文件以便快速预览
3. WHEN 翻译文件修改 THEN Local_Dev_System SHALL 无需重启 FoundryVTT 即可看到更新
4. THE Local_Dev_System SHALL 提供常见问题排查指南
