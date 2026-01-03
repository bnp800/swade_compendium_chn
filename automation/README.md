# SWADE 翻译自动化工具

本目录包含 SWADE 中文翻译项目的自动化工作流工具。

## 模块结构

```
automation/
├── __init__.py              # 包初始化
├── change_detector/         # 变更检测模块
│   ├── __init__.py
│   ├── detector.py          # 变更检测器实现
│   └── models.py            # 数据模型
├── format_converter/        # 格式转换模块
│   ├── __init__.py
│   └── converter.py         # 格式转换器实现
├── glossary_manager/        # 术语管理模块
│   ├── __init__.py
│   └── manager.py           # 术语管理器实现
├── progress_tracker/        # 进度追踪模块
│   ├── __init__.py
│   ├── tracker.py           # 进度追踪器实现
│   └── models.py            # 数据模型
├── quality_checker/         # 质量检查模块
│   ├── __init__.py
│   ├── checker.py           # 质量检查器实现
│   └── models.py            # 数据模型
└── tests/                   # 测试目录
    ├── __init__.py
    ├── conftest.py          # pytest 配置和 fixtures
    └── test_models.py       # 数据模型测试
```

## 安装

```bash
# 安装开发依赖
pip install -e ".[dev]"
```

## 运行测试

```bash
# 运行所有测试
pytest automation/tests/ -v

# 运行测试并生成覆盖率报告
pytest automation/tests/ -v --cov=automation --cov-report=html

# 只运行属性测试
pytest automation/tests/ -v -m property
```

## 模块说明

### Change Detector (变更检测器)
检测 en-US 目录中的文件变更，生成变更报告。

### Format Converter (格式转换器)
处理 Babele JSON 与 Weblate 友好格式之间的转换。

### Glossary Manager (术语管理器)
管理术语表，确保翻译一致性。

### Quality Checker (质量检查器)
验证翻译质量，检测常见问题（占位符、HTML 标签、UUID 链接等）。

### Progress Tracker (进度追踪器)
追踪翻译进度，生成统计报告和仪表板。

## 测试策略

本项目使用两种测试方法：

1. **单元测试**: 验证具体示例和边界情况
2. **属性测试**: 使用 Hypothesis 验证通用属性

属性测试配置为每个属性至少运行 100 次迭代。
