"""术语管理器实现"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field


@dataclass
class GlossaryUpdateResult:
    """术语表更新结果"""
    updated_files: List[str] = field(default_factory=list)
    updated_entries: int = 0
    errors: List[str] = field(default_factory=list)


class GlossaryManager:
    """管理翻译术语表
    
    负责加载术语表、应用术语替换、检测未知术语和更新术语表。
    """
    
    def __init__(self, glossary_path: str):
        """初始化术语管理器
        
        Args:
            glossary_path: 术语表文件路径
        """
        self.glossary_path = Path(glossary_path)
        self.glossary: Dict[str, str] = {}
        self._sorted_terms: List[str] = []  # 按长度降序排列的术语列表
        self._load_glossary()
    
    def _load_glossary(self) -> None:
        """加载术语表
        
        从 JSON 文件加载术语映射。如果文件不存在，初始化为空字典。
        """
        if not self.glossary_path.exists():
            self.glossary = {}
            self._sorted_terms = []
            return
        
        try:
            with open(self.glossary_path, 'r', encoding='utf-8') as f:
                self.glossary = json.load(f)
            # 按术语长度降序排列，确保长术语优先匹配
            self._sorted_terms = sorted(
                self.glossary.keys(), 
                key=len, 
                reverse=True
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in glossary file: {e}")
    
    def reload(self) -> None:
        """重新加载术语表"""
        self._load_glossary()
    
    def get_translation(self, term: str) -> Optional[str]:
        """获取术语的翻译
        
        Args:
            term: 英文术语
            
        Returns:
            Optional[str]: 中文翻译，如果不存在则返回 None
        """
        return self.glossary.get(term)
    
    def apply_glossary(self, text: str) -> str:
        """应用术语表到文本
        
        将文本中的英文术语替换为对应的中文翻译。
        使用单词边界匹配，避免部分匹配。
        长术语优先匹配，避免短术语错误替换长术语的一部分。
        
        Args:
            text: 待处理的文本
            
        Returns:
            str: 应用术语后的文本
        """
        if not text or not self.glossary:
            return text
        
        result = text
        
        # 按长度降序处理术语，确保长术语优先匹配
        for term in self._sorted_terms:
            translation = self.glossary[term]
            # 使用单词边界匹配，支持大小写不敏感
            # 注意：对于包含特殊字符的术语（如 "/"），需要转义
            escaped_term = re.escape(term)
            # 使用单词边界，但对于非字母数字字符的边界需要特殊处理
            pattern = rf'\b{escaped_term}\b'
            result = re.sub(pattern, translation, result, flags=re.IGNORECASE)
        
        return result
    
    def apply_glossary_with_tracking(self, text: str) -> Tuple[str, Dict[str, int]]:
        """应用术语表并追踪替换情况
        
        Args:
            text: 待处理的文本
            
        Returns:
            Tuple[str, Dict[str, int]]: (处理后的文本, 术语替换计数)
        """
        if not text or not self.glossary:
            return text, {}
        
        result = text
        replacements: Dict[str, int] = {}
        
        for term in self._sorted_terms:
            translation = self.glossary[term]
            escaped_term = re.escape(term)
            pattern = rf'\b{escaped_term}\b'
            
            # 计算匹配次数
            matches = re.findall(pattern, result, flags=re.IGNORECASE)
            if matches:
                replacements[term] = len(matches)
                result = re.sub(pattern, translation, result, flags=re.IGNORECASE)
        
        return result, replacements

    # 常见英文单词，不应被识别为专业术语
    COMMON_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'if', 'then', 'else', 'when',
        'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into',
        'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from',
        'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again',
        'further', 'once', 'here', 'there', 'where', 'why', 'how', 'all',
        'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
        'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'can',
        'will', 'just', 'should', 'now', 'also', 'any', 'both', 'every',
        'this', 'that', 'these', 'those', 'what', 'which', 'who', 'whom',
        'its', 'his', 'her', 'their', 'our', 'your', 'my', 'has', 'have',
        'had', 'do', 'does', 'did', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'may', 'might', 'must', 'shall', 'would', 'could', 'of',
        'as', 'it', 'he', 'she', 'they', 'we', 'you', 'i', 'me', 'him',
        'them', 'us', 'one', 'two', 'three', 'four', 'five', 'six', 'seven',
        'eight', 'nine', 'ten', 'first', 'second', 'third', 'new', 'old',
        'high', 'low', 'good', 'bad', 'great', 'small', 'large', 'long',
        'short', 'right', 'left', 'next', 'last', 'many', 'much', 'little',
        'see', 'get', 'make', 'take', 'use', 'find', 'give', 'tell', 'say',
        'know', 'think', 'come', 'go', 'want', 'look', 'put', 'need', 'try',
        'ask', 'work', 'seem', 'feel', 'leave', 'call', 'keep', 'let', 'begin',
        'show', 'hear', 'play', 'run', 'move', 'live', 'believe', 'hold',
        'bring', 'happen', 'write', 'provide', 'sit', 'stand', 'lose', 'pay',
        'meet', 'include', 'continue', 'set', 'learn', 'change', 'lead',
        'understand', 'watch', 'follow', 'stop', 'create', 'speak', 'read',
        'allow', 'add', 'spend', 'grow', 'open', 'walk', 'win', 'offer',
        'remember', 'love', 'consider', 'appear', 'buy', 'wait', 'serve',
        'die', 'send', 'expect', 'build', 'stay', 'fall', 'cut', 'reach',
        'kill', 'remain', 'using', 'uses', 'used'
    }
    
    def find_missing_terms(self, text: str) -> List[str]:
        """查找文本中未在术语表中的专业术语
        
        检测文本中可能是专业术语但未在术语表中的词汇。
        使用启发式方法识别可能的术语：
        - 首字母大写的单词（专有名词）
        - 全大写的缩写词
        - 驼峰命名的词汇
        - 带连字符的复合词
        
        过滤掉常见英文单词，只保留可能的专业术语。
        
        Args:
            text: 待检查的文本
            
        Returns:
            List[str]: 未知术语列表（去重，按字母排序）
        """
        if not text:
            return []
        
        # 移除 HTML 标签
        clean_text = re.sub(r'<[^>]+>', ' ', text)
        
        # 查找可能的术语模式
        potential_terms: Set[str] = set()
        
        # 1. 首字母大写的单词（排除句首）
        # 匹配不在句首的大写开头单词
        capitalized = re.findall(r'(?<=[.!?]\s)[A-Z][a-z]+|(?<=\s)[A-Z][a-z]+', clean_text)
        potential_terms.update(capitalized)
        
        # 2. 全大写的缩写词（2-5个字母）
        acronyms = re.findall(r'\b[A-Z]{2,5}\b', clean_text)
        potential_terms.update(acronyms)
        
        # 3. 驼峰命名的词汇
        camel_case = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', clean_text)
        potential_terms.update(camel_case)
        
        # 4. 带连字符的复合词
        hyphenated = re.findall(r'\b[A-Za-z]+-[A-Za-z]+(?:-[A-Za-z]+)*\b', clean_text)
        potential_terms.update(hyphenated)
        
        # 过滤掉已在术语表中的术语和常见英文单词
        missing = []
        for term in potential_terms:
            term_lower = term.lower()
            # 跳过常见英文单词
            if term_lower in self.COMMON_WORDS:
                continue
            # 检查术语是否已存在（大小写不敏感）
            if not any(k.lower() == term_lower for k in self.glossary.keys()):
                missing.append(term)
        
        return sorted(missing)
    
    def suggest_translations(self, term: str) -> List[str]:
        """为术语建议翻译
        
        基于已有术语表中的相似术语提供翻译建议。
        
        Args:
            term: 待翻译的术语
            
        Returns:
            List[str]: 建议的翻译列表
        """
        suggestions = []
        term_lower = term.lower()
        
        # 1. 精确匹配（大小写不敏感）
        for key, value in self.glossary.items():
            if key.lower() == term_lower:
                suggestions.append(value)
                break
        
        # 2. 部分匹配 - 查找包含该术语的已有翻译
        for key, value in self.glossary.items():
            if term_lower in key.lower() and value not in suggestions:
                suggestions.append(f"{value} (from: {key})")
            elif key.lower() in term_lower and value not in suggestions:
                suggestions.append(f"{value} (from: {key})")
        
        return suggestions[:5]  # 最多返回5个建议
    
    def update_glossary(self, term: str, translation: str) -> None:
        """更新术语表
        
        添加或更新术语映射，并保存到文件。
        
        Args:
            term: 英文术语
            translation: 中文翻译
        """
        if not term or not translation:
            raise ValueError("Term and translation cannot be empty")
        
        self.glossary[term] = translation
        self._save_glossary()
        # 重新排序术语列表
        self._sorted_terms = sorted(
            self.glossary.keys(), 
            key=len, 
            reverse=True
        )
    
    def batch_update_glossary(self, updates: Dict[str, str]) -> int:
        """批量更新术语表
        
        Args:
            updates: 术语到翻译的映射字典
            
        Returns:
            int: 更新的术语数量
        """
        if not updates:
            return 0
        
        count = 0
        for term, translation in updates.items():
            if term and translation:
                self.glossary[term] = translation
                count += 1
        
        if count > 0:
            self._save_glossary()
            self._sorted_terms = sorted(
                self.glossary.keys(), 
                key=len, 
                reverse=True
            )
        
        return count
    
    def _save_glossary(self) -> None:
        """保存术语表到文件"""
        # 按字母顺序排序后保存
        sorted_glossary = dict(sorted(self.glossary.items()))
        
        # 确保目录存在
        self.glossary_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.glossary_path, 'w', encoding='utf-8') as f:
            json.dump(sorted_glossary, f, ensure_ascii=False, indent=4)
    
    def remove_term(self, term: str) -> bool:
        """从术语表中移除术语
        
        Args:
            term: 要移除的术语
            
        Returns:
            bool: 是否成功移除
        """
        if term in self.glossary:
            del self.glossary[term]
            self._save_glossary()
            self._sorted_terms = sorted(
                self.glossary.keys(), 
                key=len, 
                reverse=True
            )
            return True
        return False
    
    def get_all_terms(self) -> Dict[str, str]:
        """获取所有术语
        
        Returns:
            Dict[str, str]: 术语表的副本
        """
        return dict(self.glossary)
    
    def __len__(self) -> int:
        """返回术语表中的术语数量"""
        return len(self.glossary)
    
    def __contains__(self, term: str) -> bool:
        """检查术语是否在术语表中"""
        return term in self.glossary

    def update_translations_for_term(
        self, 
        term: str, 
        old_translation: str, 
        new_translation: str,
        translation_dir: str
    ) -> GlossaryUpdateResult:
        """更新所有翻译文件中引用该术语的翻译
        
        当术语表中的翻译发生变化时，批量更新所有翻译文件中的对应翻译。
        
        Args:
            term: 英文术语
            old_translation: 旧的中文翻译
            new_translation: 新的中文翻译
            translation_dir: 翻译文件目录路径
            
        Returns:
            GlossaryUpdateResult: 更新结果，包含更新的文件列表和条目数
        """
        result = GlossaryUpdateResult()
        translation_path = Path(translation_dir)
        
        if not translation_path.exists():
            result.errors.append(f"Translation directory not found: {translation_dir}")
            return result
        
        # 遍历所有 JSON 文件
        for json_file in translation_path.glob("**/*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 检查文件是否包含旧翻译
                if old_translation not in content:
                    continue
                
                # 替换旧翻译为新翻译
                new_content = content.replace(old_translation, new_translation)
                
                if new_content != content:
                    with open(json_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    result.updated_files.append(str(json_file))
                    # 计算替换次数
                    result.updated_entries += content.count(old_translation)
                    
            except Exception as e:
                result.errors.append(f"Error processing {json_file}: {e}")
        
        return result
    
    def update_term_and_translations(
        self,
        term: str,
        new_translation: str,
        translation_dir: Optional[str] = None
    ) -> GlossaryUpdateResult:
        """更新术语表并同步更新所有翻译文件
        
        这是一个便捷方法，同时更新术语表和所有引用该术语的翻译文件。
        
        Args:
            term: 英文术语
            new_translation: 新的中文翻译
            translation_dir: 翻译文件目录路径（可选）
            
        Returns:
            GlossaryUpdateResult: 更新结果
        """
        result = GlossaryUpdateResult()
        
        # 获取旧翻译
        old_translation = self.glossary.get(term)
        
        # 更新术语表
        self.update_glossary(term, new_translation)
        
        # 如果有旧翻译且提供了翻译目录，则更新翻译文件
        if old_translation and translation_dir and old_translation != new_translation:
            file_result = self.update_translations_for_term(
                term, old_translation, new_translation, translation_dir
            )
            result.updated_files = file_result.updated_files
            result.updated_entries = file_result.updated_entries
            result.errors = file_result.errors
        
        return result
    
    def generate_missing_terms_report(self, text: str) -> str:
        """生成未知术语报告
        
        分析文本中的未知术语，生成 Markdown 格式的报告。
        
        Args:
            text: 待分析的文本
            
        Returns:
            str: Markdown 格式的报告
        """
        missing = self.find_missing_terms(text)
        
        if not missing:
            return "# 未知术语报告\n\n未发现新的未知术语。"
        
        lines = [
            "# 未知术语报告",
            "",
            f"发现 {len(missing)} 个可能的未知术语：",
            "",
            "| 术语 | 建议翻译 |",
            "|------|----------|"
        ]
        
        for term in missing:
            suggestions = self.suggest_translations(term)
            suggestion_text = suggestions[0] if suggestions else "无建议"
            lines.append(f"| {term} | {suggestion_text} |")
        
        return "\n".join(lines)
    
    def export_glossary(self, output_path: str, format: str = "json") -> None:
        """导出术语表
        
        Args:
            output_path: 输出文件路径
            format: 输出格式 ('json', 'csv', 'md')
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            sorted_glossary = dict(sorted(self.glossary.items()))
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(sorted_glossary, f, ensure_ascii=False, indent=4)
        
        elif format == "csv":
            import csv
            with open(output, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["English", "Chinese"])
                for term, translation in sorted(self.glossary.items()):
                    writer.writerow([term, translation])
        
        elif format == "md":
            lines = [
                "# SWADE 术语表",
                "",
                "| English | 中文 |",
                "|---------|------|"
            ]
            for term, translation in sorted(self.glossary.items()):
                lines.append(f"| {term} | {translation} |")
            
            with open(output, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def import_glossary(self, input_path: str, merge: bool = True) -> int:
        """导入术语表
        
        Args:
            input_path: 输入文件路径
            merge: 是否合并到现有术语表（True）或替换（False）
            
        Returns:
            int: 导入的术语数量
        """
        input_file = Path(input_path)
        
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        suffix = input_file.suffix.lower()
        imported: Dict[str, str] = {}
        
        if suffix == ".json":
            with open(input_file, 'r', encoding='utf-8') as f:
                imported = json.load(f)
        
        elif suffix == ".csv":
            import csv
            with open(input_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                next(reader, None)  # Skip header
                for row in reader:
                    if len(row) >= 2:
                        imported[row[0]] = row[1]
        
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
        
        if not merge:
            self.glossary = {}
        
        count = self.batch_update_glossary(imported)
        return count
