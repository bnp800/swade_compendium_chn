# Requirements Document

## Introduction

本文档定义了 SWADE 中文翻译项目 (swade_compendium_chn) 的自动化工作流需求。该工作流旨在优化翻译流程，实现与 foundryvtt-swade-babele-translation-files-generator、Babele 模块以及 SWADE 系统的高效联动，提供在 Weblate 上友好的翻译体验以及在 FoundryVTT 中良好的游玩使用体验。

核心目标：
1. 自动化翻译文件的生成和同步
2. 利用 Babele converter 减少重复翻译
3. 提供 Weblate 友好的翻译格式
4. 确保翻译质量和一致性

## Glossary

- **Babele**: FoundryVTT 的翻译框架模块，支持运行时翻译 compendium 内容
- **Compendium**: FoundryVTT 中的内容包，包含 Items、Actors、JournalEntries 等
- **Converter**: Babele 提供的转换器机制，用于动态翻译嵌套内容
- **Translation_Generator**: foundryvtt-swade-babele-translation-files-generator 模块，用于从 SWADE compendium 导出翻译模板
- **Weblate**: 协作翻译平台，用于管理翻译工作流
- **Glossary**: 术语表，存储英文到中文的标准翻译映射
- **Source_JSON**: en-US 目录下的英文源文件
- **Target_JSON**: zh_Hans 目录下的中文翻译文件
- **Mapping**: Babele 字段映射配置，定义哪些字段需要翻译

## Requirements

### Requirement 1: 源文件更新与变更检测

**User Story:** As a 翻译协调者, I want 在手动导出新的英文源文件后自动检测变更, so that 翻译团队能清楚知道哪些内容需要翻译或更新。

#### Acceptance Criteria

1. WHEN 翻译协调者使用 Translation_Generator 在 FoundryVTT 中导出新的源文件 THEN Source_Update_System SHALL 接受手动上传的 JSON 文件到 en-US 目录
2. WHEN 新的源文件提交到仓库 THEN Source_Update_System SHALL 自动对比新旧文件，识别新增、修改和删除的条目
3. WHEN 检测到变更 THEN Source_Update_System SHALL 生成变更报告（changelog），列出具体的条目变化
4. WHEN 源文件更新 THEN Source_Update_System SHALL 自动在 zh_Hans 目录创建对应的占位翻译文件（如不存在）
5. WHEN 条目被删除 THEN Source_Update_System SHALL 标记对应的翻译条目为废弃而非直接删除

### Requirement 2: Weblate 格式转换

**User Story:** As a 翻译者, I want 翻译文件以 Weblate 友好的格式呈现, so that 我可以专注于翻译纯文本而无需处理 HTML 结构。

#### Acceptance Criteria

1. WHEN 英文源文件更新 THEN Format_Converter SHALL 提取纯文本内容生成 Weblate 兼容的翻译模板
2. WHEN 提取文本 THEN Format_Converter SHALL 保留 HTML 结构信息以便后续注入
3. WHEN 翻译者在 Weblate 完成翻译 THEN Format_Converter SHALL 将纯文本翻译注入回原始 HTML 结构
4. WHEN 注入翻译 THEN Format_Converter SHALL 保持所有 UUID 链接、CSS 类名和 HTML 实体不变
5. WHEN 转换格式 THEN Format_Converter SHALL 支持 CSV 和 JSON 两种中间格式

### Requirement 3: 术语一致性管理

**User Story:** As a 翻译协调者, I want 自动应用术语表确保翻译一致性, so that 所有翻译使用统一的专业术语。

#### Acceptance Criteria

1. WHEN 翻译文件生成 THEN Glossary_System SHALL 自动应用 swade-glossary.json 中的术语映射
2. WHEN 发现未翻译的术语 THEN Glossary_System SHALL 标记该术语并建议添加到术语表
3. WHEN 术语表更新 THEN Glossary_System SHALL 自动更新所有引用该术语的翻译
4. WHEN 检测到术语不一致 THEN Glossary_System SHALL 生成警告报告

### Requirement 4: Babele Converter 优化

**User Story:** As a 开发者, I want 利用 Babele converter 机制减少重复翻译, so that 相同内容只需翻译一次。

#### Acceptance Criteria

1. WHEN Actor 包含嵌入的 Items THEN Converter_System SHALL 自动从已翻译的 Item compendium 获取翻译
2. WHEN 多个条目引用相同的 Ability 或 Edge THEN Converter_System SHALL 复用已有翻译而非重复翻译
3. WHEN 注册 converter THEN Converter_System SHALL 支持自定义字段映射配置
4. WHEN 翻译嵌套内容 THEN Converter_System SHALL 递归处理所有层级的可翻译字段
5. WHEN 翻译 JournalEntry pages THEN Converter_System SHALL 正确处理多页面结构

### Requirement 5: 翻译进度追踪

**User Story:** As a 翻译协调者, I want 追踪翻译进度和覆盖率, so that 我可以了解项目状态并分配工作。

#### Acceptance Criteria

1. WHEN 翻译文件更新 THEN Progress_Tracker SHALL 计算每个 compendium 的翻译完成百分比
2. WHEN 生成进度报告 THEN Progress_Tracker SHALL 区分已翻译、未翻译和需要更新的条目
3. WHEN 源文件变更 THEN Progress_Tracker SHALL 标记需要审核的已翻译条目
4. THE Progress_Tracker SHALL 生成可视化的进度仪表板

### Requirement 6: 自动化 CI/CD 流程

**User Story:** As a 开发者, I want 自动化构建和发布流程, so that 翻译更新能快速部署到用户。

#### Acceptance Criteria

1. WHEN 翻译文件合并到主分支 THEN CI_System SHALL 自动验证 JSON 语法正确性
2. WHEN 验证通过 THEN CI_System SHALL 运行翻译完整性检查
3. WHEN 创建 release THEN CI_System SHALL 自动打包并发布到 FoundryVTT 官方仓库
4. WHEN 发布完成 THEN CI_System SHALL 通知翻译团队发布状态
5. IF JSON 语法错误 THEN CI_System SHALL 阻止合并并报告错误位置

### Requirement 7: 翻译质量检查

**User Story:** As a 翻译协调者, I want 自动检查翻译质量, so that 发布的翻译符合质量标准。

#### Acceptance Criteria

1. WHEN 翻译提交 THEN Quality_Checker SHALL 检查是否存在未翻译的占位符
2. WHEN 翻译提交 THEN Quality_Checker SHALL 验证 HTML 标签配对完整
3. WHEN 翻译提交 THEN Quality_Checker SHALL 检查 UUID 链接是否保持不变
4. WHEN 检测到质量问题 THEN Quality_Checker SHALL 生成详细的问题报告
5. WHEN 翻译包含术语 THEN Quality_Checker SHALL 验证术语使用是否与术语表一致

### Requirement 8: 增量更新支持

**User Story:** As a 翻译者, I want 只处理变更的内容, so that 我不需要重复翻译已完成的内容。

#### Acceptance Criteria

1. WHEN 源文件更新 THEN Incremental_Update_System SHALL 识别新增、修改和删除的条目
2. WHEN 条目内容未变更 THEN Incremental_Update_System SHALL 保留现有翻译
3. WHEN 条目内容变更 THEN Incremental_Update_System SHALL 标记该条目需要审核
4. WHEN 生成翻译任务 THEN Incremental_Update_System SHALL 只包含需要翻译的条目
5. WHEN 合并翻译 THEN Incremental_Update_System SHALL 智能合并新旧翻译内容

### Requirement 9: 多模块支持

**User Story:** As a 翻译协调者, I want 支持多个 SWADE 扩展模块的翻译, so that 用户可以获得完整的中文游戏体验。

#### Acceptance Criteria

1. THE Multi_Module_System SHALL 支持 swade-core-rules 核心规则翻译
2. THE Multi_Module_System SHALL 支持 swpf-core-rules (Pathfinder for Savage Worlds) 翻译
3. THE Multi_Module_System SHALL 支持 swpf-bestiary 怪物图鉴翻译
4. WHEN 添加新模块 THEN Multi_Module_System SHALL 自动创建对应的翻译文件结构
5. WHEN 模块间存在共享内容 THEN Multi_Module_System SHALL 复用已有翻译


### Requirement 10: Translation Generator 集成指南

**User Story:** As a 翻译协调者, I want 有清晰的源文件导出流程文档, so that 我可以高效地从 FoundryVTT 导出最新的英文内容。

#### Acceptance Criteria

1. THE Documentation_System SHALL 提供使用 Translation_Generator 模块导出源文件的步骤指南
2. THE Documentation_System SHALL 说明导出时应选择的选项和映射配置
3. THE Documentation_System SHALL 提供导出文件的命名规范和目录结构说明
4. WHEN 导出完成 THEN Documentation_System SHALL 提供验证导出文件完整性的方法
5. THE Documentation_System SHALL 说明如何处理不同类型的 compendium（Items、Actors、JournalEntries 等）

### Requirement 11: 本地开发环境支持

**User Story:** As a 开发者, I want 在本地环境中测试翻译效果, so that 我可以在发布前验证翻译质量。

#### Acceptance Criteria

1. THE Local_Dev_System SHALL 提供本地 FoundryVTT 环境配置指南
2. THE Local_Dev_System SHALL 支持热重载翻译文件以便快速预览
3. WHEN 翻译文件修改 THEN Local_Dev_System SHALL 无需重启 FoundryVTT 即可看到更新
4. THE Local_Dev_System SHALL 提供常见问题排查指南
