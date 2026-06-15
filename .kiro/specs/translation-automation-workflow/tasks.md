# Implementation Plan: SWADE 中文翻译自动化工作流

## Overview

本实现计划将设计文档中的组件分解为可执行的编码任务。实现采用 Python 作为主要语言，使用 pytest 和 hypothesis 进行测试。任务按照依赖关系排序，确保增量开发和持续验证。

## Tasks

- [x] 1. 项目结构和基础设施搭建
  - [x] 1.1 创建 Python 项目结构和配置文件
    - 创建 `automation/` 目录结构
    - 配置 `pyproject.toml` 或 `setup.py`
    - 配置 pytest 和 hypothesis
    - _Requirements: 11.1, 11.2_
  - [x] 1.2 设置测试框架和 CI 配置
    - 创建 `.github/workflows/test.yml`
    - 配置测试覆盖率报告
    - _Requirements: 11.1, 11.2_

- [x] 2. Change Detector 组件实现
  - [x] 2.1 实现 JSON 文件比较核心逻辑
    - 实现 `ChangeDetector.compare_files()` 方法
    - 实现条目级别的差异检测
    - 支持内容哈希比较
    - _Requirements: 1.2, 9.1_
  - [x] 2.2 编写 Change Detector 属性测试
    - **Property 1: Change Detection Accuracy**
    - **Validates: Requirements 1.2, 9.1**
  - [x] 2.3 实现变更报告生成
    - 实现 `ChangeDetector.generate_changelog()` 方法
    - 生成 Markdown 格式的变更日志
    - _Requirements: 1.3_
  - [x] 2.4 实现占位文件创建
    - 当 zh_Hans 目录缺少对应文件时自动创建
    - _Requirements: 1.4_
  - [x] 2.5 编写占位文件创建属性测试
    - **Property 14: Placeholder File Creation**
    - **Validates: Requirements 1.4**
  - [x] 2.6 实现删除条目标记
    - 标记删除的条目为 "deprecated" 而非直接删除
    - _Requirements: 1.5_
  - [x] 2.7 编写删除条目处理属性测试
    - **Property 15: Deleted Entry Handling**
    - **Validates: Requirements 1.5**

- [x] 3. Checkpoint - 确保所有测试通过

- [x] 4. Format Converter 组件重构（CSV 优先 + 链接剥离）
  - [x] 4.1 重构 HTML 文本提取器（链接剥离模式）
    - 重构 `FormatConverter` 提取逻辑：完全剥离 @UUID 和 @Compendium 链接
    - 链接显示文本保留为上下文信息，不作为翻译内容
    - 剥离 HTML 标签，输出纯文本
    - _Requirements: 2.1, 2.2, 2.3_
  - [x] 4.2 重构翻译注入器（保留原始链接）
    - 注入翻译文本到 HTML 结构时保留原始英文链接不变
    - 输出半成品 JSON，链接待 Link Post-Processor 后处理
    - _Requirements: 3.1_
  - [x] 4.3 重构格式转换往返属性测试
    - **Property 2: Format Conversion Round-Trip**（验证链接在注入后保留在原始位置）
    - **Validates: Requirements 2.3, 3.1**
  - [x] 4.4 重构 CSV 输出格式
    - CSV 列：key, field, source_text, translated_text, context
    - context 列包含链接相关术语提示
    - 确保 Excel/WPS 兼容（UTF-8 BOM）
    - _Requirements: 2.4, 2.5, 2.6_
  - [x] 4.5 移除 PO 格式支持，简化为 CSV + JSON
    - CSV 为主要格式（手动编辑和 Weblate 导入）
    - JSON 为辅助格式
    - _Requirements: 2.7_

- [ ] 5. Checkpoint - 确保所有测试通过

- [x] 6. Glossary Manager 组件实现
  - [x] 6.1 实现术语表加载和应用
    - 加载 `glossary/swade-glossary.json`
    - 实现术语替换逻辑
    - _Requirements: 5.1_
  - [x] 6.2 编写术语应用一致性属性测试
    - **Property 4: Glossary Application Consistency**
    - **Validates: Requirements 5.1, 5.4**
  - [x] 6.3 实现未知术语检测
    - 检测文本中未在术语表中的专业术语
    - 生成建议添加的术语列表
    - _Requirements: 5.2_
  - [x] 6.4 实现术语表更新功能
    - 支持添加新术语
    - 支持批量更新引用该术语的翻译
    - _Requirements: 5.3_
  - [x] 6.5 实现链接显示文本翻译查找
    - 实现 `get_link_display_translation()` 方法
    - 支持精确匹配和忽略大小写匹配
    - _Requirements: 5.5, 3.2_
  - [x] 6.6 实现 Compendium 名称翻译查找
    - 实现 `get_compendium_name_translation()` 方法
    - 用于替换 @Compendium ref 路径中的条目名称
    - _Requirements: 5.6, 3.3_

- [ ] 7. Link Post-Processor 组件实现
  - [ ] 7.1 实现 @UUID 显示文本替换
    - 扫描 @UUID[ref]{text} 链接，用 Glossary 替换 {text}
    - _Requirements: 3.2_
  - [ ] 7.2 实现 @Compendium 链接替换
    - 替换 ref 路径最后一段的名称
    - 替换 {text} 显示文本
    - 处理纯引用（无显示文本）的情况
    - _Requirements: 3.3, 3.4_
  - [ ] 7.3 实现未匹配术语报告
    - 收集所有在 Glossary 中未找到翻译的链接显示文本
    - 生成报告供翻译协调者补充术语表
    - _Requirements: 3.5, 5.2_
  - [ ] 7.4 编写链接后处理完整性属性测试
    - **Property 3: Link Post-Processing Completeness**
    - **Validates: Requirements 3.2, 3.3, 3.5, 5.1**
  - [ ] 7.5 编写链接数量保持属性测试
    - **Property 3b: Link Count Preservation**
    - **Validates: Requirements 3.6**
  - [ ] 7.6 实现整文件批量处理
    - 实现 `process_file()` 方法，处理整个翻译 JSON 文件
    - 输出处理结果统计
    - _Requirements: 3.6, 3.7_

- [ ] 8. Checkpoint - 确保所有测试通过

- [x] 9. Quality Checker 组件实现
  - [x] 9.1 实现占位符检测
    - 检测 `{0}`, `{{variable}}` 等占位符
    - 验证翻译中占位符完整性
    - _Requirements: 7.1_
  - [x] 9.2 编写占位符检测属性测试
    - **Property 10: Placeholder Detection**
    - **Validates: Requirements 7.1**
  - [x] 9.3 实现 HTML 标签验证
    - 验证标签配对完整性
    - 检测未闭合标签
    - _Requirements: 7.2_
  - [x] 9.4 编写 HTML 标签平衡属性测试
    - **Property 9: HTML Tag Balance**
    - **Validates: Requirements 7.2**
  - [x] 9.5 实现 UUID 链接验证
    - 验证 UUID 链接在翻译前后保持一致
    - _Requirements: 7.3_
  - [x] 9.6 实现质量报告生成
    - 生成详细的问题报告
    - 支持 Markdown 和 JSON 格式
    - _Requirements: 7.4_

- [ ] 10. Checkpoint - 确保所有测试通过

- [x] 11. Progress Tracker 组件实现
  - [x] 11.1 实现进度计算逻辑
    - 计算每个 compendium 的翻译完成率
    - 区分已翻译、未翻译、需更新条目
    - _Requirements: 8.1, 8.2_
  - [x] 11.2 编写进度计算准确性属性测试
    - **Property 7: Progress Calculation Accuracy**
    - **Validates: Requirements 8.1, 8.2**
  - [x] 11.3 实现变更标记功能
    - 标记源文件变更后需要审核的条目
    - _Requirements: 8.3, 9.3_
  - [x] 11.4 编写变更标记准确性属性测试
    - **Property 6: Change Marking Accuracy**
    - **Validates: Requirements 8.3, 9.3**
  - [x] 11.5 实现进度仪表板生成
    - 生成 Markdown 格式的进度报告
    - 包含总体进度和各 compendium 详情
    - _Requirements: 8.4_

- [x] 12. Incremental Update 组件实现
  - [x] 12.1 实现增量更新逻辑
    - 保留未变更条目的现有翻译
    - 只处理新增和修改的条目
    - _Requirements: 9.2, 9.4_
  - [x] 12.2 编写增量更新保留属性测试
    - **Property 5: Incremental Update Preservation**
    - **Validates: Requirements 9.2**
  - [x] 12.3 实现智能合并功能
    - 合并新旧翻译内容
    - 处理冲突情况
    - _Requirements: 9.5_

- [ ] 13. Checkpoint - 确保所有测试通过

- [x] 14. Babele Converter 优化
  - [x] 14.1 优化嵌入 Items 翻译复用
    - 更新 `babele.js` 中的 converter 逻辑
    - 实现从已翻译 compendium 自动获取翻译
    - _Requirements: 6.1, 6.2_
  - [x] 14.2 实现嵌套内容递归翻译
    - 处理多层嵌套的可翻译字段
    - _Requirements: 6.4_
  - [x] 14.3 编写嵌套内容翻译属性测试
    - **Property 11: Nested Content Translation**
    - **Validates: Requirements 6.4**
  - [x] 14.4 实现 JournalEntry 多页面处理
    - 正确处理多页面结构
    - _Requirements: 6.5_
  - [x] 14.5 编写多页面日志翻译属性测试
    - **Property 12: Multi-Page Journal Translation**
    - **Validates: Requirements 6.5**
  - [x] 14.6 更新字段映射配置
    - 更新 `mappings/` 目录下的配置文件
    - _Requirements: 6.3_

- [x] 15. 多模块支持实现
  - [x] 15.1 实现模块结构自动创建
    - 为新模块自动创建翻译文件结构
    - _Requirements: 10.4_
  - [x] 15.2 实现跨模块翻译复用
    - 检测共享内容
    - 复用已有翻译
    - _Requirements: 10.5_
  - [x] 15.3 编写跨模块翻译复用属性测试
    - **Property 13: Translation Reuse Across Modules**
    - **Validates: Requirements 10.5**

- [x] 16. CI/CD 流程完善
  - [x] 16.1 实现 JSON 语法验证
    - 验证所有 JSON 文件语法正确性
    - 报告错误位置
    - _Requirements: 11.1, 11.5_
  - [x] 16.2 编写 JSON 验证完整性属性测试
    - **Property 8: JSON Validation Completeness**
    - **Validates: Requirements 11.1, 11.5**
  - [x] 16.3 更新 GitHub Actions 工作流
    - 添加翻译验证步骤
    - 添加质量检查步骤
    - _Requirements: 11.2_
  - [x] 16.4 实现发布流程自动化
    - 自动打包和发布
    - _Requirements: 11.3_

- [ ] 17. Weblate 集成配置
  - [ ] 17.1 编写 Weblate 项目配置指南
    - Weblate 组件设置（JSON 格式、文件路径映射）
    - 源文件和翻译文件的关联配置
    - _Requirements: 4.1, 4.6_
  - [ ] 17.2 配置 Weblate 与 Git 仓库同步
    - 设置 Weblate 自动拉取源文件更新
    - 设置 Weblate 自动推送翻译到仓库
    - _Requirements: 4.2, 4.4, 4.5_
  - [ ] 17.3 验证 Weblate 端到端工作流
    - 测试源文件更新 → Weblate 检测 → 翻译 → 同步回仓库的完整流程
    - _Requirements: 4.2, 4.3, 4.4_

- [x] 18. 文档和指南
  - [x] 18.1 编写 Translation Generator 使用指南
    - 导出流程步骤
    - 映射配置说明
    - _Requirements: 12.1, 12.2, 12.3_
  - [x] 18.2 编写本地开发环境配置指南
    - FoundryVTT 环境配置
    - 热重载设置
    - _Requirements: 13.1, 13.2, 13.3_
  - [x] 18.3 编写翻译工作流文档
    - 完整工作流说明（导出 → 提取CSV → 翻译 → 链接后处理 → Weblate → 同步）
    - 常见问题解答
    - _Requirements: 12.4, 12.5, 13.4_

- [ ] 19. Final Checkpoint - 确保所有测试通过

## Notes

- 所有测试任务都是必需的，确保全面的测试覆盖
- 每个属性测试都引用了设计文档中的具体属性
- Checkpoint 任务用于确保增量验证
- Python 代码放在 `automation/` 目录
- JavaScript 代码更新现有的 `babele.js`
- 待实现的核心任务：Task 4（Format Converter 重构）、Task 7（Link Post-Processor）、Task 17（Weblate 集成）
