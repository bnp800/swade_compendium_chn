"""变更检测器实现"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import ChangeReport


class ChangeDetector:
    """检测 en-US 目录中的文件变更"""
    
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
    
    def compare_entries(
        self, 
        old_entries: Dict[str, Any], 
        new_entries: Dict[str, Any]
    ) -> ChangeReport:
        """比较两个条目字典，返回变更报告
        
        Args:
            old_entries: 旧条目字典
            new_entries: 新条目字典
            
        Returns:
            ChangeReport: 变更报告
        """
        added = []
        modified = []
        deleted = []
        unchanged = []
        
        old_keys = set(old_entries.keys())
        new_keys = set(new_entries.keys())
        
        # 新增的条目
        for key in new_keys - old_keys:
            added.append(key)
        
        # 删除的条目
        for key in old_keys - new_keys:
            deleted.append(key)
        
        # 检查修改和未变更的条目
        for key in old_keys & new_keys:
            old_hash = self._compute_content_hash(old_entries[key])
            new_hash = self._compute_content_hash(new_entries[key])
            if old_hash != new_hash:
                modified.append(key)
            else:
                unchanged.append(key)
        
        return ChangeReport(
            file_name="",  # Will be set by caller
            added_entries=sorted(added),
            modified_entries=sorted(modified),
            deleted_entries=sorted(deleted),
            unchanged_entries=sorted(unchanged)
        )
    
    def compare_files(self, old_file: str, new_file: str) -> ChangeReport:
        """比较两个 JSON 文件，返回变更报告
        
        Args:
            old_file: 旧文件路径
            new_file: 新文件路径
            
        Returns:
            ChangeReport: 变更报告
        """
        old_data = self._load_json_file(old_file)
        new_data = self._load_json_file(new_file)
        
        # 提取文件名
        file_name = Path(new_file).name if new_file else Path(old_file).name
        
        # 处理文件不存在的情况
        if old_data is None and new_data is None:
            return ChangeReport(file_name=file_name)
        
        old_entries = old_data.get("entries", {}) if old_data else {}
        new_entries = new_data.get("entries", {}) if new_data else {}
        
        report = self.compare_entries(old_entries, new_entries)
        report.file_name = file_name
        
        return report
    
    def detect_changes(self, source_dir: str, target_dir: Optional[str] = None) -> List[ChangeReport]:
        """检测目录中所有文件的变更
        
        比较 source_dir 中的文件与 target_dir 中的对应文件。
        如果 target_dir 未指定，则假设所有条目都是新增的。
        
        Args:
            source_dir: 源目录路径 (新文件)
            target_dir: 目标目录路径 (旧文件)，可选
            
        Returns:
            List[ChangeReport]: 变更报告列表
        """
        source_path = Path(source_dir)
        reports = []
        
        if not source_path.exists():
            return reports
        
        for json_file in sorted(source_path.glob("*.json")):
            if target_dir:
                old_file = Path(target_dir) / json_file.name
                report = self.compare_files(
                    str(old_file) if old_file.exists() else "",
                    str(json_file)
                )
            else:
                # 没有旧文件，所有条目都是新增的
                new_data = self._load_json_file(str(json_file))
                entries = new_data.get("entries", {}) if new_data else {}
                report = ChangeReport(
                    file_name=json_file.name,
                    added_entries=sorted(entries.keys())
                )
            
            reports.append(report)
        
        return reports
    
    def generate_changelog(self, changes: List[ChangeReport]) -> str:
        """生成人类可读的变更日志
        
        Args:
            changes: 变更报告列表
            
        Returns:
            str: Markdown 格式的变更日志
        """
        from datetime import datetime
        
        lines = []
        lines.append("# 变更日志 (Changelog)")
        lines.append("")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 计算总体统计
        total_added = sum(len(c.added_entries) for c in changes)
        total_modified = sum(len(c.modified_entries) for c in changes)
        total_deleted = sum(len(c.deleted_entries) for c in changes)
        total_unchanged = sum(len(c.unchanged_entries) for c in changes)
        
        lines.append("## 总体统计")
        lines.append("")
        lines.append(f"- 新增条目: {total_added}")
        lines.append(f"- 修改条目: {total_modified}")
        lines.append(f"- 删除条目: {total_deleted}")
        lines.append(f"- 未变更条目: {total_unchanged}")
        lines.append("")
        
        # 只显示有变更的文件
        files_with_changes = [c for c in changes if c.has_changes]
        
        if not files_with_changes:
            lines.append("## 详细变更")
            lines.append("")
            lines.append("无变更。")
            return "\n".join(lines)
        
        lines.append("## 详细变更")
        lines.append("")
        
        for report in files_with_changes:
            lines.append(f"### {report.file_name}")
            lines.append("")
            
            if report.added_entries:
                lines.append(f"**新增 ({len(report.added_entries)}):**")
                for entry in report.added_entries:
                    lines.append(f"- {entry}")
                lines.append("")
            
            if report.modified_entries:
                lines.append(f"**修改 ({len(report.modified_entries)}):**")
                for entry in report.modified_entries:
                    lines.append(f"- {entry}")
                lines.append("")
            
            if report.deleted_entries:
                lines.append(f"**删除 ({len(report.deleted_entries)}):**")
                for entry in report.deleted_entries:
                    lines.append(f"- {entry}")
                lines.append("")
        
        return "\n".join(lines)

    def create_placeholder_file(self, source_file: str, target_dir: str) -> Optional[Path]:
        """为源文件在目标目录创建占位翻译文件
        
        如果目标目录中不存在对应的翻译文件，则创建一个空的占位文件。
        
        Args:
            source_file: 源文件路径 (en-US 目录中的文件)
            target_dir: 目标目录路径 (zh_Hans 目录)
            
        Returns:
            Optional[Path]: 创建的文件路径，如果文件已存在则返回 None
        """
        source_path = Path(source_file)
        target_path = Path(target_dir) / source_path.name
        
        # 如果目标文件已存在，不创建
        if target_path.exists():
            return None
        
        # 确保目标目录存在
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建空的占位文件结构
        placeholder_content = {
            "entries": {}
        }
        
        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(placeholder_content, f, ensure_ascii=False, indent=4)
        
        return target_path
    
    def sync_placeholder_files(self, source_dir: str, target_dir: str) -> List[Path]:
        """同步源目录和目标目录，为缺失的文件创建占位文件
        
        Args:
            source_dir: 源目录路径 (en-US 目录)
            target_dir: 目标目录路径 (zh_Hans 目录)
            
        Returns:
            List[Path]: 创建的占位文件路径列表
        """
        source_path = Path(source_dir)
        created_files = []
        
        if not source_path.exists():
            return created_files
        
        for json_file in sorted(source_path.glob("*.json")):
            result = self.create_placeholder_file(str(json_file), target_dir)
            if result:
                created_files.append(result)
        
        return created_files

    def mark_deleted_entries(
        self, 
        translation_file: str, 
        deleted_entries: List[str]
    ) -> Dict[str, Any]:
        """标记翻译文件中的删除条目为 deprecated
        
        不直接删除条目，而是添加 _deprecated 标记，保留翻译以备将来使用。
        
        Args:
            translation_file: 翻译文件路径 (zh_Hans 目录中的文件)
            deleted_entries: 要标记为删除的条目名称列表
            
        Returns:
            Dict[str, Any]: 更新后的翻译数据
        """
        from datetime import datetime
        
        data = self._load_json_file(translation_file)
        if data is None:
            return {"entries": {}}
        
        entries = data.get("entries", {})
        
        for entry_name in deleted_entries:
            if entry_name in entries:
                entry = entries[entry_name]
                # 添加 _meta 字段标记为 deprecated
                if "_meta" not in entry:
                    entry["_meta"] = {}
                entry["_meta"]["deprecated"] = True
                entry["_meta"]["deprecated_at"] = datetime.now().isoformat()
        
        return data
    
    def save_json_file(self, file_path: str, data: Dict[str, Any]) -> None:
        """保存 JSON 数据到文件
        
        Args:
            file_path: 文件路径
            data: 要保存的数据
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def apply_deleted_entry_marking(
        self, 
        source_file: str, 
        translation_file: str
    ) -> ChangeReport:
        """检测删除的条目并在翻译文件中标记为 deprecated
        
        比较源文件和翻译文件，找出在源文件中已删除但在翻译文件中存在的条目，
        并将这些条目标记为 deprecated。
        
        Args:
            source_file: 源文件路径 (en-US 目录中的文件)
            translation_file: 翻译文件路径 (zh_Hans 目录中的文件)
            
        Returns:
            ChangeReport: 变更报告，包含标记为删除的条目
        """
        source_data = self._load_json_file(source_file)
        translation_data = self._load_json_file(translation_file)
        
        if source_data is None or translation_data is None:
            return ChangeReport(file_name=Path(translation_file).name)
        
        source_entries = source_data.get("entries", {})
        translation_entries = translation_data.get("entries", {})
        
        # 找出在翻译文件中存在但在源文件中不存在的条目
        # 这些是需要标记为 deprecated 的条目
        deleted_entries = []
        for key in translation_entries.keys():
            if key not in source_entries:
                # 检查是否已经标记为 deprecated
                entry = translation_entries[key]
                meta = entry.get("_meta", {})
                if not meta.get("deprecated", False):
                    deleted_entries.append(key)
        
        if deleted_entries:
            updated_data = self.mark_deleted_entries(translation_file, deleted_entries)
            self.save_json_file(translation_file, updated_data)
        
        return ChangeReport(
            file_name=Path(translation_file).name,
            deleted_entries=sorted(deleted_entries)
        )
    
    def is_entry_deprecated(self, entry: Dict[str, Any]) -> bool:
        """检查条目是否被标记为 deprecated
        
        Args:
            entry: 条目数据
            
        Returns:
            bool: 是否被标记为 deprecated
        """
        meta = entry.get("_meta", {})
        return meta.get("deprecated", False)
    
    def get_deprecated_entries(self, translation_file: str) -> List[str]:
        """获取翻译文件中所有被标记为 deprecated 的条目
        
        Args:
            translation_file: 翻译文件路径
            
        Returns:
            List[str]: deprecated 条目名称列表
        """
        data = self._load_json_file(translation_file)
        if data is None:
            return []
        
        entries = data.get("entries", {})
        deprecated = []
        
        for name, entry in entries.items():
            if self.is_entry_deprecated(entry):
                deprecated.append(name)
        
        return sorted(deprecated)
