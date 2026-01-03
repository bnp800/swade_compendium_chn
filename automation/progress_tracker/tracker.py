"""进度追踪器实现"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import ProgressReport, CompendiumProgress, EntryStatus


class ProgressTracker:
    """翻译进度追踪
    
    追踪翻译进度，计算完成率，识别需要更新的条目。
    """
    
    def __init__(self):
        self._last_report: Optional[ProgressReport] = None
        self._source_dir: Optional[str] = None
        self._target_dir: Optional[str] = None
    
    def _compute_content_hash(self, content: Any) -> str:
        """计算内容的哈希值用于比较
        
        Args:
            content: 要计算哈希的内容
            
        Returns:
            str: 内容的 MD5 哈希值
        """
        serialized = json.dumps(content, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(serialized.encode('utf-8')).hexdigest()
    
    def _load_json_file(self, file_path: str) -> Optional[Dict]:
        """加载 JSON 文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Optional[Dict]: JSON 内容，文件不存在时返回 None
        """
        path = Path(file_path)
        if not path.exists():
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _is_entry_translated(self, source_entry: Dict, target_entry: Optional[Dict]) -> bool:
        """判断条目是否已翻译
        
        翻译判断标准：
        1. 目标条目存在
        2. 目标条目有非空的 name 字段（且与源不同，或有其他翻译字段）
        3. 目标条目未被标记为 deprecated
        
        Args:
            source_entry: 源条目
            target_entry: 目标条目（可能为 None）
            
        Returns:
            bool: 是否已翻译
        """
        if target_entry is None:
            return False
        
        # 检查是否被标记为 deprecated
        meta = target_entry.get("_meta", {})
        if meta.get("deprecated", False):
            return False
        
        # 检查是否有翻译内容
        # 至少需要有 name 字段，且不为空
        target_name = target_entry.get("name", "")
        if not target_name:
            return False
        
        # 如果 name 与源相同，检查是否有其他翻译字段
        source_name = source_entry.get("name", "")
        if target_name == source_name:
            # 检查 description 是否有翻译
            target_desc = target_entry.get("description", "")
            source_desc = source_entry.get("description", "")
            if target_desc and target_desc != source_desc:
                return True
            # 没有任何翻译内容
            return False
        
        return True
    
    def _is_entry_outdated(
        self, 
        source_entry: Dict, 
        target_entry: Optional[Dict],
        source_hash: str
    ) -> bool:
        """判断条目是否需要更新
        
        需要更新的条件：
        1. 条目已翻译
        2. 源内容的哈希与翻译时记录的源哈希不同
        
        Args:
            source_entry: 源条目
            target_entry: 目标条目
            source_hash: 当前源内容的哈希
            
        Returns:
            bool: 是否需要更新
        """
        if target_entry is None:
            return False
        
        # 检查是否有记录的源哈希
        meta = target_entry.get("_meta", {})
        recorded_hash = meta.get("source_hash")
        
        if recorded_hash is None:
            # 没有记录源哈希，无法判断是否过期
            # 保守起见，不标记为过期
            return False
        
        return recorded_hash != source_hash
    
    def _analyze_entry(
        self, 
        key: str,
        source_entry: Dict, 
        target_entry: Optional[Dict]
    ) -> EntryStatus:
        """分析单个条目的状态
        
        Args:
            key: 条目键名
            source_entry: 源条目
            target_entry: 目标条目
            
        Returns:
            EntryStatus: 条目状态
        """
        source_hash = self._compute_content_hash(source_entry)
        is_translated = self._is_entry_translated(source_entry, target_entry)
        is_outdated = False
        
        if is_translated:
            is_outdated = self._is_entry_outdated(source_entry, target_entry, source_hash)
        
        return EntryStatus(
            key=key,
            is_translated=is_translated,
            is_outdated=is_outdated,
            source_hash=source_hash,
            translation_hash=self._compute_content_hash(target_entry) if target_entry else None
        )
    
    def _calculate_compendium_progress(
        self, 
        source_file: str, 
        target_file: str
    ) -> CompendiumProgress:
        """计算单个 compendium 的进度
        
        Args:
            source_file: 源文件路径
            target_file: 目标文件路径
            
        Returns:
            CompendiumProgress: compendium 进度
        """
        source_data = self._load_json_file(source_file)
        target_data = self._load_json_file(target_file)
        
        file_name = Path(source_file).stem
        
        if source_data is None:
            return CompendiumProgress(name=file_name)
        
        source_entries = source_data.get("entries", {})
        target_entries = target_data.get("entries", {}) if target_data else {}
        
        total = len(source_entries)
        translated = 0
        untranslated = 0
        outdated = 0
        untranslated_list = []
        outdated_list = []
        
        for key, source_entry in source_entries.items():
            target_entry = target_entries.get(key)
            status = self._analyze_entry(key, source_entry, target_entry)
            
            if status.is_translated:
                translated += 1
                if status.is_outdated:
                    outdated += 1
                    outdated_list.append(key)
            else:
                untranslated += 1
                untranslated_list.append(key)
        
        return CompendiumProgress(
            name=file_name,
            total=total,
            translated=translated,
            untranslated=untranslated,
            outdated=outdated,
            untranslated_entries=sorted(untranslated_list),
            outdated_entries=sorted(outdated_list)
        )
    
    def calculate_progress(self, source_dir: str, target_dir: str) -> ProgressReport:
        """计算翻译进度
        
        Args:
            source_dir: 源文件目录 (en-US)
            target_dir: 目标文件目录 (zh_Hans)
            
        Returns:
            ProgressReport: 进度报告
        """
        self._source_dir = source_dir
        self._target_dir = target_dir
        
        source_path = Path(source_dir)
        target_path = Path(target_dir)
        
        report = ProgressReport()
        
        if not source_path.exists():
            self._last_report = report
            return report
        
        # 遍历所有源文件
        for source_file in sorted(source_path.glob("*.json")):
            target_file = target_path / source_file.name
            
            progress = self._calculate_compendium_progress(
                str(source_file), 
                str(target_file)
            )
            
            report.by_compendium[progress.name] = progress
            report.total_entries += progress.total
            report.translated_entries += progress.translated
            report.untranslated_entries += progress.untranslated
            report.outdated_entries += progress.outdated
        
        self._last_report = report
        return report
    
    def get_untranslated_entries(self, compendium: str) -> List[str]:
        """获取未翻译的条目列表
        
        Args:
            compendium: Compendium 名称
            
        Returns:
            List[str]: 未翻译条目的 key 列表
        """
        if self._last_report is None:
            return []
        
        progress = self._last_report.by_compendium.get(compendium)
        if progress is None:
            return []
        
        return progress.untranslated_entries
    
    def get_outdated_entries(self, compendium: str) -> List[str]:
        """获取需要更新的条目列表
        
        Args:
            compendium: Compendium 名称
            
        Returns:
            List[str]: 需要更新条目的 key 列表
        """
        if self._last_report is None:
            return []
        
        progress = self._last_report.by_compendium.get(compendium)
        if progress is None:
            return []
        
        return progress.outdated_entries

    def _save_json_file(self, file_path: str, data: Dict[str, Any]) -> None:
        """保存 JSON 数据到文件
        
        Args:
            file_path: 文件路径
            data: 要保存的数据
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def mark_entry_needs_review(
        self, 
        entry: Dict[str, Any], 
        source_hash: str,
        reason: str = "source_changed"
    ) -> Dict[str, Any]:
        """标记条目需要审核
        
        在条目的 _meta 字段中添加 needs_review 标记和相关信息。
        
        Args:
            entry: 翻译条目
            source_hash: 当前源内容的哈希
            reason: 需要审核的原因
            
        Returns:
            Dict[str, Any]: 更新后的条目
        """
        if "_meta" not in entry:
            entry["_meta"] = {}
        
        entry["_meta"]["needs_review"] = True
        entry["_meta"]["review_reason"] = reason
        entry["_meta"]["marked_at"] = datetime.now().isoformat()
        entry["_meta"]["new_source_hash"] = source_hash
        
        return entry
    
    def update_source_hash(
        self, 
        entry: Dict[str, Any], 
        source_hash: str
    ) -> Dict[str, Any]:
        """更新条目的源哈希
        
        在翻译完成后调用，记录当前源内容的哈希，用于后续变更检测。
        
        Args:
            entry: 翻译条目
            source_hash: 源内容的哈希
            
        Returns:
            Dict[str, Any]: 更新后的条目
        """
        if "_meta" not in entry:
            entry["_meta"] = {}
        
        entry["_meta"]["source_hash"] = source_hash
        entry["_meta"]["translated_at"] = datetime.now().isoformat()
        
        # 清除 needs_review 标记
        if "needs_review" in entry["_meta"]:
            del entry["_meta"]["needs_review"]
        if "review_reason" in entry["_meta"]:
            del entry["_meta"]["review_reason"]
        if "marked_at" in entry["_meta"]:
            del entry["_meta"]["marked_at"]
        if "new_source_hash" in entry["_meta"]:
            del entry["_meta"]["new_source_hash"]
        
        return entry
    
    def mark_changed_entries(
        self, 
        source_file: str, 
        translation_file: str
    ) -> List[str]:
        """标记源文件变更后需要审核的条目
        
        比较源文件和翻译文件，找出源内容已变更但翻译未更新的条目，
        并在翻译文件中标记这些条目需要审核。
        
        Args:
            source_file: 源文件路径 (en-US 目录中的文件)
            translation_file: 翻译文件路径 (zh_Hans 目录中的文件)
            
        Returns:
            List[str]: 被标记为需要审核的条目名称列表
        """
        source_data = self._load_json_file(source_file)
        translation_data = self._load_json_file(translation_file)
        
        if source_data is None:
            return []
        
        if translation_data is None:
            translation_data = {"entries": {}}
        
        source_entries = source_data.get("entries", {})
        translation_entries = translation_data.get("entries", {})
        
        marked_entries = []
        
        for key, source_entry in source_entries.items():
            translation_entry = translation_entries.get(key)
            
            if translation_entry is None:
                continue
            
            # 检查是否已翻译
            if not self._is_entry_translated(source_entry, translation_entry):
                continue
            
            # 计算当前源哈希
            source_hash = self._compute_content_hash(source_entry)
            
            # 检查是否需要标记
            if self._is_entry_outdated(source_entry, translation_entry, source_hash):
                # 检查是否已经标记过
                meta = translation_entry.get("_meta", {})
                if not meta.get("needs_review", False):
                    self.mark_entry_needs_review(translation_entry, source_hash)
                    marked_entries.append(key)
        
        # 保存更新后的翻译文件
        if marked_entries:
            self._save_json_file(translation_file, translation_data)
        
        return sorted(marked_entries)
    
    def mark_all_changed_entries(
        self, 
        source_dir: str, 
        target_dir: str
    ) -> Dict[str, List[str]]:
        """标记所有源文件变更后需要审核的条目
        
        遍历源目录中的所有文件，标记需要审核的条目。
        
        Args:
            source_dir: 源文件目录 (en-US)
            target_dir: 目标文件目录 (zh_Hans)
            
        Returns:
            Dict[str, List[str]]: 每个文件中被标记的条目列表
        """
        source_path = Path(source_dir)
        target_path = Path(target_dir)
        
        result = {}
        
        if not source_path.exists():
            return result
        
        for source_file in sorted(source_path.glob("*.json")):
            target_file = target_path / source_file.name
            
            if not target_file.exists():
                continue
            
            marked = self.mark_changed_entries(str(source_file), str(target_file))
            if marked:
                result[source_file.stem] = marked
        
        return result
    
    def get_entries_needing_review(self, translation_file: str) -> List[str]:
        """获取翻译文件中需要审核的条目列表
        
        Args:
            translation_file: 翻译文件路径
            
        Returns:
            List[str]: 需要审核的条目名称列表
        """
        data = self._load_json_file(translation_file)
        if data is None:
            return []
        
        entries = data.get("entries", {})
        needs_review = []
        
        for name, entry in entries.items():
            meta = entry.get("_meta", {})
            if meta.get("needs_review", False):
                needs_review.append(name)
        
        return sorted(needs_review)
    
    def clear_review_mark(
        self, 
        translation_file: str, 
        entry_key: str,
        update_source_hash: bool = True
    ) -> bool:
        """清除条目的审核标记
        
        在翻译者审核并更新翻译后调用。
        
        Args:
            translation_file: 翻译文件路径
            entry_key: 条目键名
            update_source_hash: 是否更新源哈希
            
        Returns:
            bool: 是否成功清除标记
        """
        data = self._load_json_file(translation_file)
        if data is None:
            return False
        
        entries = data.get("entries", {})
        if entry_key not in entries:
            return False
        
        entry = entries[entry_key]
        meta = entry.get("_meta", {})
        
        if update_source_hash and "new_source_hash" in meta:
            # 使用新的源哈希更新
            new_hash = meta["new_source_hash"]
            self.update_source_hash(entry, new_hash)
        else:
            # 只清除审核标记
            if "needs_review" in meta:
                del meta["needs_review"]
            if "review_reason" in meta:
                del meta["review_reason"]
            if "marked_at" in meta:
                del meta["marked_at"]
            if "new_source_hash" in meta:
                del meta["new_source_hash"]
        
        self._save_json_file(translation_file, data)
        return True

    def generate_dashboard(self, report: Optional[ProgressReport] = None) -> str:
        """生成进度仪表板 (Markdown 格式)
        
        生成包含总体进度和各 compendium 详情的 Markdown 格式进度报告。
        
        Args:
            report: 进度报告，如果为 None 则使用最后一次计算的报告
            
        Returns:
            str: Markdown 格式的进度仪表板
        """
        if report is None:
            report = self._last_report
        
        if report is None:
            return "# 翻译进度仪表板\n\n暂无进度数据。请先运行 `calculate_progress()` 计算进度。"
        
        lines = []
        
        # 标题
        lines.append("# 翻译进度仪表板")
        lines.append("")
        lines.append(f"生成时间: {report.generated_at}")
        lines.append("")
        
        # 总体进度
        lines.append("## 总体进度")
        lines.append("")
        lines.append(self._generate_progress_bar(report.completion_percentage))
        lines.append("")
        lines.append(f"- **总条目数**: {report.total_entries}")
        lines.append(f"- **已翻译**: {report.translated_entries} ({report.completion_percentage:.1f}%)")
        lines.append(f"- **未翻译**: {report.untranslated_entries}")
        lines.append(f"- **需要更新**: {report.outdated_entries}")
        lines.append("")
        
        # 各 Compendium 详情
        lines.append("## 各 Compendium 详情")
        lines.append("")
        
        # 按完成度排序
        sorted_compendiums = sorted(
            report.by_compendium.values(),
            key=lambda x: x.percentage,
            reverse=True
        )
        
        # 表格头
        lines.append("| Compendium | 进度 | 已翻译 | 未翻译 | 需更新 |")
        lines.append("|------------|------|--------|--------|--------|")
        
        for progress in sorted_compendiums:
            progress_bar = self._generate_mini_progress_bar(progress.percentage)
            lines.append(
                f"| {progress.name} | {progress_bar} {progress.percentage:.1f}% | "
                f"{progress.translated} | {progress.untranslated} | {progress.outdated} |"
            )
        
        lines.append("")
        
        # 未翻译条目详情（如果有）
        untranslated_all = report.get_all_untranslated_entries()
        if untranslated_all:
            lines.append("## 未翻译条目")
            lines.append("")
            lines.append("<details>")
            lines.append("<summary>点击展开未翻译条目列表</summary>")
            lines.append("")
            
            for compendium, entries in sorted(untranslated_all.items()):
                lines.append(f"### {compendium}")
                lines.append("")
                for entry in entries[:20]:  # 限制显示数量
                    lines.append(f"- {entry}")
                if len(entries) > 20:
                    lines.append(f"- ... 还有 {len(entries) - 20} 个条目")
                lines.append("")
            
            lines.append("</details>")
            lines.append("")
        
        # 需要更新的条目详情（如果有）
        outdated_all = report.get_all_outdated_entries()
        if outdated_all:
            lines.append("## 需要更新的条目")
            lines.append("")
            lines.append("<details>")
            lines.append("<summary>点击展开需要更新的条目列表</summary>")
            lines.append("")
            
            for compendium, entries in sorted(outdated_all.items()):
                lines.append(f"### {compendium}")
                lines.append("")
                for entry in entries[:20]:
                    lines.append(f"- {entry}")
                if len(entries) > 20:
                    lines.append(f"- ... 还有 {len(entries) - 20} 个条目")
                lines.append("")
            
            lines.append("</details>")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_progress_bar(self, percentage: float, width: int = 30) -> str:
        """生成文本进度条
        
        Args:
            percentage: 完成百分比 (0-100)
            width: 进度条宽度
            
        Returns:
            str: 文本进度条
        """
        filled = int(width * percentage / 100)
        empty = width - filled
        bar = "█" * filled + "░" * empty
        return f"`[{bar}]` **{percentage:.1f}%**"
    
    def _generate_mini_progress_bar(self, percentage: float, width: int = 10) -> str:
        """生成迷你进度条（用于表格）
        
        Args:
            percentage: 完成百分比 (0-100)
            width: 进度条宽度
            
        Returns:
            str: 迷你进度条
        """
        filled = int(width * percentage / 100)
        empty = width - filled
        return "█" * filled + "░" * empty
    
    def generate_json_report(self, report: Optional[ProgressReport] = None) -> str:
        """生成 JSON 格式的进度报告
        
        Args:
            report: 进度报告，如果为 None 则使用最后一次计算的报告
            
        Returns:
            str: JSON 格式的进度报告
        """
        if report is None:
            report = self._last_report
        
        if report is None:
            return json.dumps({"error": "No progress data available"}, ensure_ascii=False, indent=2)
        
        data = {
            "generated_at": report.generated_at,
            "overall": {
                "total": report.total_entries,
                "translated": report.translated_entries,
                "untranslated": report.untranslated_entries,
                "outdated": report.outdated_entries,
                "percentage": round(report.completion_percentage, 2)
            },
            "by_compendium": {}
        }
        
        for name, progress in report.by_compendium.items():
            data["by_compendium"][name] = {
                "total": progress.total,
                "translated": progress.translated,
                "untranslated": progress.untranslated,
                "outdated": progress.outdated,
                "percentage": round(progress.percentage, 2),
                "untranslated_entries": progress.untranslated_entries,
                "outdated_entries": progress.outdated_entries
            }
        
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def save_dashboard(
        self, 
        output_path: str, 
        format: str = "markdown",
        report: Optional[ProgressReport] = None
    ) -> None:
        """保存进度仪表板到文件
        
        Args:
            output_path: 输出文件路径
            format: 输出格式 ("markdown" 或 "json")
            report: 进度报告
        """
        if format == "json":
            content = self.generate_json_report(report)
        else:
            content = self.generate_dashboard(report)
        
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
