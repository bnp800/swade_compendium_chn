# Design Document: SWADE 中文翻译自动化工作流

## Overview

本设计文档描述了 SWADE 中文翻译项目的自动化工作流架构。该系统整合了 foundryvtt-swade-babele-translation-files-generator、Babele 模块和 Weblate 翻译平台，提供端到端的翻译工作流支持。

### 核心设计原则

1. **增量优先**: 只处理变更的内容，避免重复工作
2. **格式分离**: 翻译者处理纯文本，系统处理 HTML 结构
3. **术语一致**: 通过 Glossary 确保专业术语统一
4. **复用最大化**: 利用 Babele Converter 减少重复翻译

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Translation Workflow                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   FoundryVTT │    │  Translation │    │   Weblate    │                   │
│  │    + SWADE   │───▶│  Generator   │───▶│   Platform   │                   │
│  │   + Babele   │    │   Module     │    │              │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
│         │                   │                   │                            │
│         │                   ▼                   ▼                            │
│         │           ┌──────────────┐    ┌──────────────┐                    │
│         │           │   en-US/     │    │  Translated  │                    │
│         │           │  (Source)    │    │    Text      │                    │
│         │           └──────────────┘    └──────────────┘                    │
│         │                   │                   │                            │
│         │                   ▼                   ▼                            │
│         │           ┌─────────────────────────────────┐                     │
│         │           │      Automation Pipeline        │                     │
│         │           │  ┌───────────┐ ┌───────────┐   │                     │
│         │           │  │  Change   │ │  Format   │   │                     │
│         │           │  │ Detector  │ │ Converter │   │                     │
│         │           │  └───────────┘ └───────────┘   │                     │
│         │           │  ┌───────────┐ ┌───────────┐   │                     │
│         │           │  │ Glossary  │ │  Quality  │   │                     │
│         │           │  │  Manager  │ │  Checker  │   │                     │
│         │           │  └───────────┘ └───────────┘   │                     │
│         │           └─────────────────────────────────┘                     │
│         │                         │                                          │
│         │                         ▼                                          │
│         │                 ┌──────────────┐                                  │
│         │                 │   zh_Hans/   │                                  │
│         │                 │  (Target)    │                                  │
│         │                 └──────────────┘                                  │
│         │                         │                                          │
│         ▼                         ▼                                          │
│  ┌─────────────────────────────────────────────┐                            │
│  │              Babele Runtime                  │                            │
│  │  ┌─────────────┐  ┌─────────────────────┐   │                            │
│  │  │ Converters  │  │ Translation Lookup  │   │                            │
│  │  │ (Reuse)     │  │                     │   │                            │
│  │  └─────────────┘  └─────────────────────┘   │                            │
│  └─────────────────────────────────────────────┘                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Change Detector (变更检测器)

负责检测源文件变更，生成变更报告。

```python
class ChangeDetector:
    """检测 en-US 目录中的文件变更"""
    
    def compare_files(self, old_file: str, new_file: str) -> ChangeReport:
        """比较两个 JSON 文件，返回变更报告"""
        pass
    
    def detect_changes(self, source_dir: str) -> List[ChangeReport]:
        """检测目录中所有文件的变更"""
        pass
    
    def generate_changelog(self, changes: List[ChangeReport]) -> str:
        """生成人类可读的变更日志"""
        pass

@dataclass
class ChangeReport:
    file_name: str
    added_entries: List[str]      # 新增条目的 key
    modified_entries: List[str]   # 修改条目的 key
    deleted_entries: List[str]    # 删除条目的 key
    unchanged_entries: List[str]  # 未变更条目的 key
```

### 2. Format Converter (格式转换器)

处理 Babele JSON 与 Weblate 友好格式之间的转换。

```python
class FormatConverter:
    """在 Babele JSON 和 Weblate 格式之间转换"""
    
    def extract_for_weblate(self, babele_json: str, output_format: str = 'po') -> str:
        """从 Babele JSON 提取纯文本，生成 Weblate 兼容格式"""
        pass
    
    def inject_translations(self, source_json: str, translations: str) -> str:
        """将翻译注入回 Babele JSON 格式"""
        pass
    
    def preserve_html_structure(self, source_html: str, translated_text: str) -> str:
        """保持 HTML 结构，只替换文本内容"""
        pass
```

### 3. Glossary Manager (术语管理器)

管理术语表，确保翻译一致性。

```python
class GlossaryManager:
    """管理翻译术语表"""
    
    def __init__(self, glossary_path: str):
        self.glossary = self._load_glossary(glossary_path)
    
    def apply_glossary(self, text: str) -> str:
        """应用术语表到文本"""
        pass
    
    def find_missing_terms(self, text: str) -> List[str]:
        """查找文本中未在术语表中的术语"""
        pass
    
    def suggest_translations(self, term: str) -> List[str]:
        """为术语建议翻译"""
        pass
    
    def update_glossary(self, term: str, translation: str) -> None:
        """更新术语表"""
        pass
```

### 4. Quality Checker (质量检查器)

验证翻译质量，检测常见问题。

```python
class QualityChecker:
    """翻译质量检查"""
    
    def check_placeholders(self, source: str, translation: str) -> List[Issue]:
        """检查占位符是否保持一致"""
        pass
    
    def check_html_tags(self, source: str, translation: str) -> List[Issue]:
        """检查 HTML 标签是否配对"""
        pass
    
    def check_uuid_links(self, source: str, translation: str) -> List[Issue]:
        """检查 UUID 链接是否保持不变"""
        pass
    
    def check_glossary_consistency(self, translation: str, glossary: dict) -> List[Issue]:
        """检查术语使用是否一致"""
        pass
    
    def generate_report(self, issues: List[Issue]) -> QualityReport:
        """生成质量报告"""
        pass

@dataclass
class Issue:
    severity: str  # 'error', 'warning', 'info'
    type: str      # 'placeholder', 'html', 'uuid', 'glossary'
    message: str
    location: str  # entry key + field
```

### 5. Progress Tracker (进度追踪器)

追踪翻译进度，生成统计报告。

```python
class ProgressTracker:
    """翻译进度追踪"""
    
    def calculate_progress(self, source_dir: str, target_dir: str) -> ProgressReport:
        """计算翻译进度"""
        pass
    
    def get_untranslated_entries(self, compendium: str) -> List[str]:
        """获取未翻译的条目列表"""
        pass
    
    def get_outdated_entries(self, compendium: str) -> List[str]:
        """获取需要更新的条目列表"""
        pass
    
    def generate_dashboard(self) -> str:
        """生成进度仪表板 (Markdown 格式)"""
        pass

@dataclass
class ProgressReport:
    total_entries: int
    translated_entries: int
    untranslated_entries: int
    outdated_entries: int
    completion_percentage: float
    by_compendium: Dict[str, CompendiumProgress]
```

### 6. Babele Converter Optimizer (Converter 优化器)

优化 Babele converter 配置，减少重复翻译。

```javascript
// babele.js 中的 converter 配置
const SWADE_CONVERTERS = {
    // 嵌入 Items 的翻译复用
    embeddedItems: (items, translations, data, tc) => {
        return items.map(item => {
            // 首先检查是否有直接翻译
            if (translations && translations[item.name]) {
                return mergeObject(item, translations[item.name]);
            }
            // 否则从已翻译的 compendium 中查找
            const pack = game.babele.packs.find(
                p => p.translated && p.translations[item.name]
            );
            if (pack) {
                return pack.translate(item, pack.translations[item.name]);
            }
            return item;
        });
    },
    
    // 共享 Abilities 的翻译复用
    sharedAbilities: (abilities, translations, data, tc) => {
        // 类似逻辑，从 abilities compendium 复用翻译
    }
};
```

## Data Models

### Translation Entry (翻译条目)

```json
{
    "entries": {
        "Entry Name": {
            "name": "条目名称",
            "description": "<article class=\"swade-core\">...</article>",
            "category": "类别",
            "_meta": {
                "source_hash": "abc123",
                "translated_at": "2024-01-15T10:30:00Z",
                "translator": "translator_id",
                "status": "translated"
            }
        }
    }
}
```

### Change Report (变更报告)

```json
{
    "file": "swade-core-rules.swade-edges.json",
    "timestamp": "2024-01-15T10:30:00Z",
    "summary": {
        "added": 5,
        "modified": 3,
        "deleted": 1,
        "unchanged": 120
    },
    "details": {
        "added": ["New Edge 1", "New Edge 2"],
        "modified": ["Modified Edge 1"],
        "deleted": ["Removed Edge 1"]
    }
}
```

### Progress Report (进度报告)

```json
{
    "generated_at": "2024-01-15T10:30:00Z",
    "overall": {
        "total": 500,
        "translated": 450,
        "percentage": 90.0
    },
    "by_compendium": {
        "swade-core-rules.swade-edges": {
            "total": 100,
            "translated": 95,
            "percentage": 95.0
        }
    }
}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Change Detection Accuracy

*For any* pair of source JSON files (old and new), the Change Detector SHALL correctly identify all added, modified, and deleted entries, such that:
- Every entry present in new but not in old is reported as "added"
- Every entry present in both but with different content is reported as "modified"
- Every entry present in old but not in new is reported as "deleted"
- Every entry present in both with identical content is reported as "unchanged"

**Validates: Requirements 1.2, 8.1**

### Property 2: Format Conversion Round-Trip

*For any* valid Babele JSON file with HTML content, extracting text for Weblate and then injecting translations back SHALL preserve:
- All HTML tags and their attributes
- All UUID links (`@UUID[...]{}`)
- All Compendium links (`@Compendium[...]{}`)
- All CSS class names
- All HTML entities

**Validates: Requirements 2.2, 2.3, 2.4**

### Property 3: UUID Link Preservation

*For any* HTML content containing UUID or Compendium links, after translation injection, the number and content of all links SHALL remain identical to the source.

**Validates: Requirements 2.4, 7.3**

### Property 4: Glossary Application Consistency

*For any* text containing terms from the glossary, applying the glossary SHALL replace all occurrences of each term with its translation, and the result SHALL be consistent (same term always maps to same translation).

**Validates: Requirements 3.1, 3.4, 7.5**

### Property 5: Incremental Update Preservation

*For any* source file update where some entries are unchanged, the existing translations for unchanged entries SHALL be preserved exactly as they were.

**Validates: Requirements 8.2**

### Property 6: Change Marking Accuracy

*For any* source file update where entries are modified, the corresponding translation entries SHALL be marked as "needs review" with the modification timestamp.

**Validates: Requirements 5.3, 8.3**

### Property 7: Progress Calculation Accuracy

*For any* pair of source and target directories, the calculated progress percentage SHALL equal (translated_entries / total_entries * 100), where an entry is considered translated if it has non-empty translated content.

**Validates: Requirements 5.1, 5.2**

### Property 8: JSON Validation Completeness

*For any* JSON file with syntax errors, the validator SHALL detect the error and report the line number and error type.

**Validates: Requirements 6.1, 6.5**

### Property 9: HTML Tag Balance

*For any* translated HTML content, the Quality Checker SHALL verify that all opening tags have corresponding closing tags, and report any mismatches.

**Validates: Requirements 7.2**

### Property 10: Placeholder Detection

*For any* translation where the source contains placeholders (e.g., `{0}`, `{{variable}}`), the Quality Checker SHALL verify that all placeholders are present in the translation.

**Validates: Requirements 7.1**

### Property 11: Nested Content Translation

*For any* JSON structure with nested translatable fields (e.g., Actor with embedded Items), the system SHALL recursively process all levels and translate each translatable field.

**Validates: Requirements 4.4**

### Property 12: Multi-Page Journal Translation

*For any* JournalEntry with multiple pages, each page SHALL be translated independently while maintaining the page structure and order.

**Validates: Requirements 4.5**

### Property 13: Translation Reuse Across Modules

*For any* content that appears in multiple modules (e.g., shared abilities), if the content is translated in one module, it SHALL be available for reuse in other modules.

**Validates: Requirements 9.5**

### Property 14: Placeholder File Creation

*For any* source file in en-US directory, if no corresponding file exists in zh_Hans directory, the system SHALL create an empty placeholder file with the correct structure.

**Validates: Requirements 1.4**

### Property 15: Deleted Entry Handling

*For any* entry that is deleted from the source file, the corresponding translation entry SHALL be marked as "deprecated" rather than deleted, preserving the translation for potential future use.

**Validates: Requirements 1.5**

## Error Handling

### JSON Parsing Errors

```python
class JSONParseError(Exception):
    """JSON 解析错误"""
    def __init__(self, file_path: str, line: int, message: str):
        self.file_path = file_path
        self.line = line
        self.message = message
        super().__init__(f"JSON parse error in {file_path} at line {line}: {message}")
```

### Translation Injection Errors

```python
class InjectionError(Exception):
    """翻译注入错误"""
    def __init__(self, entry_key: str, field: str, message: str):
        self.entry_key = entry_key
        self.field = field
        self.message = message
        super().__init__(f"Injection error for {entry_key}.{field}: {message}")
```

### Glossary Errors

```python
class GlossaryError(Exception):
    """术语表错误"""
    def __init__(self, term: str, message: str):
        self.term = term
        self.message = message
        super().__init__(f"Glossary error for term '{term}': {message}")
```

## Testing Strategy

### Unit Tests

单元测试覆盖各个组件的核心功能：

1. **Change Detector Tests**
   - 测试新增条目检测
   - 测试修改条目检测
   - 测试删除条目检测
   - 测试空文件处理

2. **Format Converter Tests**
   - 测试 HTML 文本提取
   - 测试翻译注入
   - 测试 UUID 链接保留
   - 测试特殊字符处理

3. **Glossary Manager Tests**
   - 测试术语应用
   - 测试未知术语检测
   - 测试术语更新

4. **Quality Checker Tests**
   - 测试占位符检测
   - 测试 HTML 标签验证
   - 测试 UUID 链接验证

### Property-Based Tests

使用 Hypothesis (Python) 进行属性测试：

```python
from hypothesis import given, strategies as st

@given(st.dictionaries(st.text(), st.text()))
def test_change_detection_accuracy(entries):
    """Property 1: 变更检测准确性"""
    # 生成随机的新旧条目
    # 验证检测结果的正确性
    pass

@given(st.text())
def test_format_conversion_round_trip(html_content):
    """Property 2: 格式转换往返"""
    # 提取文本，注入翻译，验证结构保持
    pass
```

### Integration Tests

集成测试验证组件间的协作：

1. **端到端工作流测试**
   - 从源文件更新到翻译文件生成的完整流程

2. **CI/CD 流程测试**
   - 验证 GitHub Actions 工作流

3. **Babele 集成测试**
   - 在 FoundryVTT 环境中验证翻译效果

### Test Configuration

- 属性测试最少运行 100 次迭代
- 使用 pytest 作为测试框架
- 使用 hypothesis 进行属性测试
- 测试覆盖率目标: 80%
