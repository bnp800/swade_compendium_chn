# Implementation Plan: SWADE 中文翻译自动化工作流

## Overview

本实现计划将设计文档中的组件分解为可执行的编码任务。实现采用 Python 作为主要语言，使用 pytest 和 hypothesis 进行测试。任务按照依赖关系排序，确保增量开发和持续验证。

## Tasks

- [x] 1. 项目结构和基础设施搭建
  - [x] 1.1 创建 Python 项目结构和配置文件
    - 创建 `automation/` 目录结构
    - 配置 `pyproject.toml` 或 `setup.py`
    - 配置 pytest 和 hypothesis
    - _Requirements: 6.1, 6.2_
  - [x] 1.2 设置测试框架和 CI 配置
    - 创建 `.github/workflows/test.yml`
    - 配置测试覆盖率报告
    - _Requirements: 6.1, 6.2_

- [x] 2. Change Detector 组件实现
  - [x] 2.1 实现 JSON 文件比较核心逻辑
    - 实现 `ChangeDetector.compare_files()` 方法
    - 实现条目级别的差异检测
    - 支持内容哈希比较
    - _Requirements: 1.2, 8.1_
  - [x] 2.2 编写 Change Detector 属性测试
    - **Property 1: Change Detection Accuracy**
    - **Validates: Requirements 1.2, 8.1**
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
  - 确保所有测试通过，如有问题请询问用户

- [x] 4. Format Converter 组件实现
  - [x] 4.1 实现 HTML 文本提取器
    - 增强现有 `extract_text.py` 功能
    - 支持 UUID 链接占位符处理
    - 支持 Weblate PO 格式输出
    - _Requirements: 2.1, 2.2_
  - [x] 4.2 实现翻译注入器
    - 增强现有 `html_injector.py` 功能
    - 确保 HTML 结构完整保留
    - _Requirements: 2.3, 2.4_
  - [x] 4.3 编写格式转换往返属性测试
    - **Property 2: Format Conversion Round-Trip**
    - **Validates: Requirements 2.2, 2.3, 2.4**
  - [x] 4.4 编写 UUID 链接保留属性测试
    - **Property 3: UUID Link Preservation**
    - **Validates: Requirements 2.4, 7.3**
  - [x] 4.5 实现多格式支持 (CSV, JSON, PO)
    - 支持 CSV 格式（现有）
    - 支持 JSON 格式（现有）
    - 添加 PO 格式支持（Weblate 原生格式）
    - _Requirements: 2.5_

- [ ] 5. Checkpoint - 确保所有测试通过
  - 确保所有测试通过，如有问题请询问用户

- [x] 6. Glossary Manager 组件实现
  - [x] 6.1 实现术语表加载和应用
    - 加载 `glossary/swade-glossary.json`
    - 实现术语替换逻辑
    - _Requirements: 3.1_
  - [x] 6.2 编写术语应用一致性属性测试
    - **Property 4: Glossary Application Consistency**
    - **Validates: Requirements 3.1, 3.4, 7.5**
  - [x] 6.3 实现未知术语检测
    - 检测文本中未在术语表中的专业术语
    - 生成建议添加的术语列表
    - _Requirements: 3.2_
  - [x] 6.4 实现术语表更新功能
    - 支持添加新术语
    - 支持批量更新引用该术语的翻译
    - _Requirements: 3.3_

- [ ] 7. Quality Checker 组件实现
  - [ ] 7.1 实现占位符检测
    - 检测 `{0}`, `{{variable}}` 等占位符
    - 验证翻译中占位符完整性
    - _Requirements: 7.1_
  - [ ] 7.2 编写占位符检测属性测试
    - **Property 10: Placeholder Detection**
    - **Validates: Requirements 7.1**
  - [ ] 7.3 实现 HTML 标签验证
    - 验证标签配对完整性
    - 检测未闭合标签
    - _Requirements: 7.2_
  - [ ] 7.4 编写 HTML 标签平衡属性测试
    - **Property 9: HTML Tag Balance**
    - **Validates: Requirements 7.2**
  - [ ] 7.5 实现 UUID 链接验证
    - 验证 UUID 链接在翻译前后保持一致
    - _Requirements: 7.3_
  - [ ] 7.6 实现质量报告生成
    - 生成详细的问题报告
    - 支持 Markdown 和 JSON 格式
    - _Requirements: 7.4_

- [ ] 8. Checkpoint - 确保所有测试通过
  - 确保所有测试通过，如有问题请询问用户

- [ ] 9. Progress Tracker 组件实现
  - [ ] 9.1 实现进度计算逻辑
    - 计算每个 compendium 的翻译完成率
    - 区分已翻译、未翻译、需更新条目
    - _Requirements: 5.1, 5.2_
  - [ ] 9.2 编写进度计算准确性属性测试
    - **Property 7: Progress Calculation Accuracy**
    - **Validates: Requirements 5.1, 5.2**
  - [ ] 9.3 实现变更标记功能
    - 标记源文件变更后需要审核的条目
    - _Requirements: 5.3, 8.3_
  - [ ] 9.4 编写变更标记准确性属性测试
    - **Property 6: Change Marking Accuracy**
    - **Validates: Requirements 5.3, 8.3**
  - [ ] 9.5 实现进度仪表板生成
    - 生成 Markdown 格式的进度报告
    - 包含总体进度和各 compendium 详情
    - _Requirements: 5.4_

- [ ] 10. Incremental Update 组件实现
  - [ ] 10.1 实现增量更新逻辑
    - 保留未变更条目的现有翻译
    - 只处理新增和修改的条目
    - _Requirements: 8.2, 8.4_
  - [ ] 10.2 编写增量更新保留属性测试
    - **Property 5: Incremental Update Preservation**
    - **Validates: Requirements 8.2**
  - [ ] 10.3 实现智能合并功能
    - 合并新旧翻译内容
    - 处理冲突情况
    - _Requirements: 8.5_

- [ ] 11. Checkpoint - 确保所有测试通过
  - 确保所有测试通过，如有问题请询问用户

- [ ] 12. Babele Converter 优化
  - [ ] 12.1 优化嵌入 Items 翻译复用
    - 更新 `babele.js` 中的 converter 逻辑
    - 实现从已翻译 compendium 自动获取翻译
    - _Requirements: 4.1, 4.2_
  - [ ] 12.2 实现嵌套内容递归翻译
    - 处理多层嵌套的可翻译字段
    - _Requirements: 4.4_
  - [ ] 12.3 编写嵌套内容翻译属性测试
    - **Property 11: Nested Content Translation**
    - **Validates: Requirements 4.4**
  - [ ] 12.4 实现 JournalEntry 多页面处理
    - 正确处理多页面结构
    - _Requirements: 4.5_
  - [ ] 12.5 编写多页面日志翻译属性测试
    - **Property 12: Multi-Page Journal Translation**
    - **Validates: Requirements 4.5**
  - [ ] 12.6 更新字段映射配置
    - 更新 `mappings/` 目录下的配置文件
    - _Requirements: 4.3_

- [ ] 13. 多模块支持实现
  - [ ] 13.1 实现模块结构自动创建
    - 为新模块自动创建翻译文件结构
    - _Requirements: 9.4_
  - [ ] 13.2 实现跨模块翻译复用
    - 检测共享内容
    - 复用已有翻译
    - _Requirements: 9.5_
  - [ ] 13.3 编写跨模块翻译复用属性测试
    - **Property 13: Translation Reuse Across Modules**
    - **Validates: Requirements 9.5**

- [ ] 14. CI/CD 流程完善
  - [ ] 14.1 实现 JSON 语法验证
    - 验证所有 JSON 文件语法正确性
    - 报告错误位置
    - _Requirements: 6.1, 6.5_
  - [ ] 14.2 编写 JSON 验证完整性属性测试
    - **Property 8: JSON Validation Completeness**
    - **Validates: Requirements 6.1, 6.5**
  - [ ] 14.3 更新 GitHub Actions 工作流
    - 添加翻译验证步骤
    - 添加质量检查步骤
    - _Requirements: 6.2_
  - [ ] 14.4 实现发布流程自动化
    - 自动打包和发布
    - _Requirements: 6.3_

- [ ] 15. 文档和指南
  - [ ] 15.1 编写 Translation Generator 使用指南
    - 导出流程步骤
    - 映射配置说明
    - _Requirements: 10.1, 10.2, 10.3_
  - [ ] 15.2 编写本地开发环境配置指南
    - FoundryVTT 环境配置
    - 热重载设置
    - _Requirements: 11.1, 11.2, 11.3_
  - [ ] 15.3 编写翻译工作流文档
    - 完整工作流说明
    - 常见问题解答
    - _Requirements: 10.4, 10.5, 11.4_

- [ ] 16. Final Checkpoint - 确保所有测试通过
  - 确保所有测试通过，如有问题请询问用户

## Notes

- 所有测试任务都是必需的，确保全面的测试覆盖
- 每个属性测试都引用了设计文档中的具体属性
- Checkpoint 任务用于确保增量验证
- Python 代码放在 `automation/` 目录
- JavaScript 代码更新现有的 `babele.js`
