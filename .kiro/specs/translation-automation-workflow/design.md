# Design Document: SWADE 中文翻译自动化工作流

## Overview

本设计文档描述了 SWADE 中文翻译项目的自动化工作流架构。该系统整合了 foundryvtt-swade-babele-translation-files-generator、Babele 模块和 Weblate 翻译平台，提供端到端的翻译工作流支持。

### 核心设计原则

1. **增量优先**: 只处理变更的内容，避免重复工作
2. **格式分离**: 翻译者处理纯文本，系统处理 HTML 结构
3. **术语一致**: 通过 Glossary 确保专业术语统一
4. **复用最大化**: 利用 Babele Converter 减少重复翻译
5. **链接后处理**: 超链接在翻译完成后统一替换，翻译者无需关心链接语法
6. **CSV 优先**: 输出给翻译者的格式以 CSV 为主，便于手动编辑和批量处理

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           Translation Workflow                                │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                    │
│  │   FoundryVTT │    │  Translation │    │   Weblate /  │                    │
│  │    + SWADE   │───▶│  Generator   │───▶│  手动编辑CSV │                    │
│  │   + Babele   │    │   Module     │    │              │                    │
│  └──────────────┘    └──────────────┘    └──────────────┘                    │
│         │                   │                   │                             │
│         │                   ▼                   ▼                             │
│         │           ┌──────────────┐    ┌──────────────┐                     │
│         │           │   en-US/     │    │  Translated  │                     │
│         │           │  (Source)    │    │  CSV (纯文本) │                     │
│         │           └──────────────┘    └──────────────┘                     │
│         │                   │                   │                             │
│         │                   ▼                   ▼                             │
│         │           ┌──────────────────────────────────────────┐             │
│         │           │         Automation Pipeline              │             │
│         │           │  ┌───────────┐ ┌────────────────────┐   │             │
│         │           │  │  Change   │ │  Format Converter  │   │             │
│         │           │  │ Detector  │ │  (剥离链接→纯文本) │   │             │
│         │           │  └───────────┘ └────────────────────┘   │             │
│         │           │  ┌───────────┐ ┌────────────────────┐   │             │
│         │           │  │ Glossary  │ │ Link Post-Processor│   │             │
│         │           │  │  Manager  │ │ (链接统一后处理)   │   │             │
│         │           │  └───────────┘ └────────────────────┘   │             │
│         │           │  ┌───────────┐                          │             │
│         │           │  │  Quality  │                          │             │
│         │           │  │  Checker  │                          │             │
│         │           │  └───────────┘                          │             │
│         │           └──────────────────────────────────────────┘             │
│         │                         │                                          │
│         │                         ▼                                          │
│         │                 ┌──────────────┐                                   │
│         │                 │   zh_Hans/   │                                   │
│         │                 │  (Target)    │                                   │
│         │                 └──────────────┘                                   │
│         │                         │                                          │
│         ▼                         ▼                                          │
│  ┌─────────────────────────────────────────────┐                             │
│  │              Babele Runtime                  │                             │
│  │  ┌─────────────┐  ┌─────────────────────┐   │                             │
│  │  │ Converters  │  │ Translation Lookup  │   │                             │
│  │  │ (Reuse)     │  │                     │   │                             │
│  │  └─────────────┘  └─────────────────────┘   │                             │
│  └─────────────────────────────────────────────┘                             │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 核心数据流

```
提取阶段 (Extract):
  en-US/*.json ──→ 剥离HTML标签 ──→ 剥离所有链接 ──→ 纯文本 CSV
                                                        │
翻译阶段 (Translate):                                    │
  翻译者在 Weblate 或 Excel 中编辑 CSV ◄────────────────┘
                                          │
注入阶段 (Inject):                        ▼
  翻译后的 CSV ──→ 注入回 HTML 结构 ──→ 半成品 JSON (含英文链接)
                                          │
后处理阶段 (Post-Process):                ▼
  半成品 JSON ──→ Link Post-Processor ──→ 最终 zh_Hans/*.json
                  (用 Glossary 替换链接显示文本)
                  (用 Glossary 替换 @Compendium ref 路径中的名称)
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

处理 Babele JSON 与翻译者友好格式之间的转换。采用 CSV 作为主要输出格式，提取时完全剥离链接和 HTML 标签，翻译者只需处理纯文本。

**设计要点：**
- 提取阶段完全剥离 `@UUID[...]{text}` 和 `@Compendium[...]{text}` 链接，只保留显示文本作为上下文
- 剥离所有 HTML 标签，只输出纯文本
- CSV 格式便于在 Excel/WPS 中直接编辑，也兼容 Weblate 导入
- 注入阶段将纯文本翻译回填到源 HTML 结构中，链接暂保留英文原样
- 链接的翻译由 Link Post-Processor 在后处理阶段统一完成

```python
class FormatConverter:
    """在 Babele JSON 和翻译者友好格式之间转换
    
    核心流程：
    1. extract: Babele JSON → 剥离链接和HTML → 纯文本 CSV
    2. inject:  翻译后的 CSV + 源 HTML 结构 → 半成品 JSON (链接待后处理)
    """
    
    def extract_for_translation(self, babele_json: str, output_format: str = 'csv') -> str:
        """从 Babele JSON 提取纯文本，生成翻译者友好格式
        
        处理步骤：
        1. 遍历所有 entries 的可翻译字段
        2. 对 HTML 内容：剥离所有链接（记录链接信息到元数据），剥离 HTML 标签
        3. 输出纯文本 CSV（默认）或 JSON
        
        CSV 列：key, field, source_text, translated_text, context
        - source_text: 纯文本，无链接无HTML
        - context: 包含链接位置提示，帮助翻译者理解上下文
        """
        pass
    
    def inject_translations(self, source_json: str, translations_csv: str) -> str:
        """将翻译注入回 Babele JSON 格式
        
        处理步骤：
        1. 读取源 JSON 获取 HTML 结构
        2. 读取翻译 CSV 获取翻译文本
        3. 将翻译文本注入 HTML 结构（保留原始链接不变）
        4. 输出半成品 JSON，链接仍为英文，待 Link Post-Processor 处理
        """
        pass
    
    def strip_links(self, html_content: str) -> Tuple[str, List[LinkInfo]]:
        """从 HTML 内容中剥离所有链接，返回纯文本和链接元数据
        
        @UUID[Compendium.xxx.yyy]{Display Text} → "Display Text"
        @Compendium[xxx.yyy]{Display Text} → "Display Text"
        @Compendium[xxx.yyy] → ""（纯引用，无显示文本）
        
        Returns:
            (剥离链接后的文本, 链接信息列表)
        """
        pass
    
    def preserve_html_structure(self, source_html: str, translated_text: str) -> str:
        """保持 HTML 结构，只替换文本内容，保留原始链接"""
        pass

@dataclass
class LinkInfo:
    """链接元数据，用于后处理阶段"""
    type: str           # 'uuid' 或 'compendium'
    ref: str            # 链接引用路径
    display_text: str   # 原始显示文本（英文）
    position: int       # 在文本中的大致位置
```

**CSV 输出格式示例：**

```csv
key,field,source_text,translated_text,context
"Ace",name,"Ace","","swade-edges"
"Ace",description,"Aces are specially trained drivers... using Bennies to Soak damage for any vehicle...","","Contains links: Boating, Driving, Piloting, Vigor, Soak"
"Ace",category,"Professional","","edge category"
```

翻译者看到的是干净的纯文本，无需关心 `@UUID[...]` 或 `@Compendium[...]` 语法。`context` 列提供链接相关术语作为参考。

### 3. Glossary Manager (术语管理器)

管理术语表，确保翻译一致性。同时为 Link Post-Processor 提供链接显示文本的翻译映射。

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
    
    def get_link_display_translation(self, english_display: str) -> Optional[str]:
        """获取链接显示文本的中文翻译
        
        用于 Link Post-Processor 替换链接中的显示文本。
        查找顺序：精确匹配 → 忽略大小写匹配 → 返回 None
        
        示例：
            "Smarts" → "聪慧"
            "Fighting" → "格斗"
            "attributes" → "属性"（忽略大小写匹配）
        """
        pass
    
    def get_compendium_name_translation(self, english_name: str) -> Optional[str]:
        """获取 Compendium 条目名称的中文翻译
        
        用于 Link Post-Processor 替换 @Compendium ref 路径中的名称。
        
        示例：
            "Shooting" → "射击"（用于 @Compendium[swade-core-rules.swade-skills.射击]）
            "Strong Willed" → "意志坚定"
        """
        pass
```

### 4. Link Post-Processor (链接后处理器)

在翻译注入完成后，统一处理所有超链接的翻译。这是本设计的核心创新点：将链接翻译从翻译者的工作中完全解耦，由系统基于 Glossary 自动完成。

**设计动机：**
- 翻译者不需要理解 `@UUID[...]{}` 和 `@Compendium[...]{}` 语法
- 链接显示文本几乎都是术语表中的标准术语（Edge 名、Skill 名、规则术语等）
- `@Compendium` 短链接的 ref 路径中包含条目名称，翻译后需要同步更新
- 统一后处理确保所有链接翻译的一致性

**处理的链接类型：**

| 链接类型 | 英文示例 | 中文结果 | 处理方式 |
|---------|---------|---------|---------|
| UUID + 显示文本 | `@UUID[...xxx]{Smarts}` | `@UUID[...xxx]{聪慧}` | 替换 `{}` 内的显示文本 |
| Compendium + 显示文本 | `@Compendium[swade-core-rules.swade-skills.Shooting]{Shooting}` | `@Compendium[swade-core-rules.swade-skills.射击]{射击}` | 替换 ref 路径中的名称 + 显示文本 |
| Compendium 纯引用 | `@Compendium[swade-core-rules.swade-skills.Shooting]` | `@Compendium[swade-core-rules.swade-skills.射击]` | 仅替换 ref 路径中的名称 |
| UUID 纯引用 | `@UUID[...xxx]` | `@UUID[...xxx]`（不变） | UUID ref 路径不含可翻译名称，保持不变 |

```python
class LinkPostProcessor:
    """链接后处理器：在翻译注入后统一替换链接中的文本"""
    
    def __init__(self, glossary_manager: GlossaryManager):
        self.glossary = glossary_manager
    
    def process_file(self, translated_json_path: str) -> ProcessResult:
        """处理整个翻译文件中的所有链接
        
        Args:
            translated_json_path: 半成品翻译 JSON 文件路径
            
        Returns:
            处理结果，包含替换统计和未匹配的术语列表
        """
        pass
    
    def process_content(self, html_content: str) -> Tuple[str, List[LinkReplacement]]:
        """处理单个 HTML 内容中的所有链接
        
        处理步骤：
        1. 扫描所有 @UUID[ref]{text} 链接，用 Glossary 替换 {text}
        2. 扫描所有 @Compendium[module.pack.Name]{text} 链接：
           a. 用 Glossary 替换 ref 路径最后一段的 Name
           b. 用 Glossary 替换 {text}
        3. 扫描所有 @Compendium[module.pack.Name] 纯引用：
           a. 用 Glossary 替换 ref 路径最后一段的 Name
        4. 记录所有未匹配的术语
        
        Returns:
            (处理后的内容, 替换记录列表)
        """
        pass
    
    def replace_uuid_display_text(self, content: str) -> str:
        """替换 @UUID[...]{text} 中的显示文本
        
        @UUID[Compendium.swade-core-rules.swade-rules.xxx]{Smarts}
        → @UUID[Compendium.swade-core-rules.swade-rules.xxx]{聪慧}
        """
        pass
    
    def replace_compendium_links(self, content: str) -> str:
        """替换 @Compendium 链接中的名称和显示文本
        
        @Compendium[swade-core-rules.swade-skills.Shooting]{Shooting}
        → @Compendium[swade-core-rules.swade-skills.射击]{射击}
        
        @Compendium[swade-core-rules.swade-skills.Shooting]
        → @Compendium[swade-core-rules.swade-skills.射击]
        """
        pass
    
    def get_unmatched_terms(self) -> List[str]:
        """获取在 Glossary 中未找到翻译的链接显示文本列表
        
        用于提示翻译协调者补充术语表
        """
        pass

@dataclass
class LinkReplacement:
    """链接替换记录"""
    link_type: str          # 'uuid_display', 'compendium_ref', 'compendium_display'
    original: str           # 原始链接文本
    replaced: str           # 替换后的链接文本
    english_term: str       # 被替换的英文术语
    chinese_term: str       # 替换为的中文术语
    matched: bool           # 是否在 Glossary 中找到匹配

@dataclass
class ProcessResult:
    """文件处理结果"""
    file_path: str
    total_links: int        # 总链接数
    replaced_links: int     # 成功替换的链接数
    unmatched_links: int    # 未匹配的链接数
    replacements: List[LinkReplacement]
    unmatched_terms: List[str]
```

### 5. Quality Checker (质量检查器)

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

### 6. Progress Tracker (进度追踪器)

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

### 7. Babele Converter Optimizer (Converter 优化器)

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

*For any* valid Babele JSON file with HTML content, extracting text for translation (stripping links and HTML) and then injecting translations back SHALL preserve:
- All HTML tags and their attributes
- All CSS class names
- All HTML entities
- All original links in their exact positions (links remain in English at this stage, pending post-processing)

The round-trip is defined as: extract → translate pure text → inject back into HTML structure. Link translation is handled separately by the Link Post-Processor.

**Validates: Requirements 2.2, 2.3, 2.4**

### Property 3: Link Post-Processing Completeness

*For any* HTML content containing UUID or Compendium links, after Link Post-Processor execution:
- The number of links SHALL remain identical to the source
- All link ref paths (`@UUID[ref]`, `@Compendium[ref]`) SHALL remain structurally valid
- For every link whose display text exists in the Glossary, the display text SHALL be replaced with the Chinese translation
- For every `@Compendium[module.pack.Name]` link whose Name exists in the Glossary, the Name in the ref path SHALL be replaced with the Chinese translation
- Links with display text not found in the Glossary SHALL be reported as unmatched but left unchanged

**Validates: Requirements 2.4, 3.1, 7.3**

### Property 3b: Link Count Preservation

*For any* HTML content, the total number of `@UUID` and `@Compendium` links before and after the full pipeline (extraction → injection → post-processing) SHALL be identical.

**Validates: Requirements 2.4, 7.3**

### Property 4: Glossary Application Consistency

*For any* text containing terms from the glossary, applying the glossary SHALL replace all occurrences of each term with its translation, and the result SHALL be consistent (same term always maps to same translation). This applies to both:
- Plain text glossary application (body text)
- Link display text replacement (via Link Post-Processor)
- Compendium ref path name replacement (via Link Post-Processor)

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
   - 测试链接剥离（@UUID 和 @Compendium 链接完全移除，保留显示文本）
   - 测试 HTML 标签剥离，输出纯文本
   - 测试 CSV 格式输出（列结构、编码、转义）
   - 测试翻译注入回 HTML 结构（保留原始链接位置）
   - 测试特殊字符处理

3. **Glossary Manager Tests**
   - 测试术语应用
   - 测试未知术语检测
   - 测试术语更新
   - 测试链接显示文本翻译查找（精确匹配、忽略大小写）
   - 测试 Compendium 名称翻译查找

4. **Link Post-Processor Tests**
   - 测试 @UUID 显示文本替换
   - 测试 @Compendium ref 路径名称替换
   - 测试 @Compendium 显示文本替换
   - 测试未匹配术语的报告
   - 测试链接数量在处理前后保持一致
   - 测试 UUID 纯引用（无显示文本）保持不变

5. **Quality Checker Tests**
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
    # 提取纯文本（剥离链接和HTML），注入翻译，验证HTML结构保持
    # 验证链接在注入后仍保留在原始位置
    pass

@given(st.text(), st.dictionaries(st.text(), st.text()))
def test_link_post_processing_completeness(html_with_links, glossary):
    """Property 3: 链接后处理完整性"""
    # 生成包含链接的HTML内容和术语表
    # 验证后处理后链接数量不变
    # 验证术语表中存在的术语被正确替换
    # 验证未匹配术语被报告
    pass

@given(st.text(), st.dictionaries(st.text(), st.text()))
def test_link_count_preservation(html_with_links, glossary):
    """Property 3b: 链接数量保持"""
    # 验证完整流水线前后链接数量一致
    pass
```

### Integration Tests

集成测试验证组件间的协作：

1. **端到端工作流测试**
   - 从源文件更新到翻译文件生成的完整流程
   - 提取 → CSV 翻译 → 注入 → 链接后处理 → 最终 JSON 的完整流水线

2. **Link Post-Processor 集成测试**
   - 使用真实的 glossary 文件和翻译文件验证链接替换
   - 验证 @Compendium ref 路径中的名称替换与 Babele 运行时兼容

3. **CI/CD 流程测试**
   - 验证 GitHub Actions 工作流

4. **Babele 集成测试**
   - 在 FoundryVTT 环境中验证翻译效果

### Test Configuration

- 属性测试最少运行 100 次迭代
- 使用 pytest 作为测试框架
- 使用 hypothesis 进行属性测试
- 测试覆盖率目标: 80%
