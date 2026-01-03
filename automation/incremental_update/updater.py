"""增量更新器实现

实现增量更新逻辑，保留未变更条目的现有翻译，只处理新增和修改的条目。
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from automation.change_detector import ChangeDetector, ChangeReport


@dataclass
class UpdateResult:
    """增量更新结果"""
    
    file_name: str
    preserved_entries: List[str] = field(default_factory=list)  # 保留的未变更翻译
    added_entries: List[str] = field(default_factory=list)      # 新增的条目
    modified_entries: List[str] = field(default_factory=list)   # 修改的条目（需要审核）
    merged_entries: List[str] = field(default_factory=list)     # 智能合并的条目
    conflicts: List[str] = field(default_factory=list)          # 冲突的条目
    
    @property
    def has_changes(self) -> bool:
        """检查是否有任何变更"""
        return bool(
            self.added_entries or 
            self.modified_entries or 
            self.merged_entries or 
            self.conflicts
        )


@dataclass
class MergeConflict:
    """合并冲突信息"""
    
    entry_key: str
    field: str
    source_value: Any
    existing_translation: Any
    conflict_type: str  # 'structure_change', 'content_change', 'field_removed'


class IncrementalUpdater:
    """增量更新器
    
    实现增量更新逻辑：
    - 保留未变更条目的现有翻译
    - 只处理新增和修改的条目
    - 智能合并新旧翻译内容
    """
    
    def __init__(self):
        self._change_detector = ChangeDetector()
    
    def _compute_content_hash(self, content: Any) -> str:
        """计算内容的哈希值"""
        serialized = json.dumps(content, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(serialized.encode('utf-8')).hexdigest()
    
    def _load_json_file(self, file_path: str) -> Optional[Dict]:
        """加载 JSON 文件"""
        path = Path(file_path)
        if not path.exists():
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_json_file(self, file_path: str, data: Dict[str, Any]) -> None:
        """保存 JSON 数据到文件"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def _is_entry_translated(self, entry: Dict[str, Any]) -> bool:
        """判断条目是否已翻译
        
        Args:
            entry: 翻译条目
            
        Returns:
            bool: 是否已翻译
        """
        # 检查是否被标记为 deprecated
        meta = entry.get("_meta", {})
        if meta.get("deprecated", False):
            return False
        
        # 检查是否有翻译内容（name 字段非空）
        name = entry.get("name", "")
        return bool(name)
    
    def _has_source_hash(self, entry: Dict[str, Any]) -> bool:
        """检查条目是否有源哈希记录"""
        meta = entry.get("_meta", {})
        return "source_hash" in meta
    
    def _get_source_hash(self, entry: Dict[str, Any]) -> Optional[str]:
        """获取条目的源哈希"""
        meta = entry.get("_meta", {})
        return meta.get("source_hash")
    
    def _is_source_unchanged(
        self, 
        source_entry: Dict[str, Any], 
        translation_entry: Dict[str, Any]
    ) -> bool:
        """判断源条目是否未变更
        
        通过比较当前源内容哈希与翻译时记录的源哈希来判断。
        
        Args:
            source_entry: 源条目
            translation_entry: 翻译条目
            
        Returns:
            bool: 源条目是否未变更
        """
        recorded_hash = self._get_source_hash(translation_entry)
        if recorded_hash is None:
            # 没有记录源哈希，无法判断
            return False
        
        current_hash = self._compute_content_hash(source_entry)
        return recorded_hash == current_hash
    
    def preserve_unchanged_translations(
        self,
        source_entries: Dict[str, Dict],
        existing_translations: Dict[str, Dict]
    ) -> Tuple[Dict[str, Dict], List[str]]:
        """保留未变更条目的现有翻译
        
        对于源内容未变更的条目，直接保留现有翻译。
        
        Args:
            source_entries: 源条目字典
            existing_translations: 现有翻译字典
            
        Returns:
            Tuple[Dict, List]: (保留的翻译字典, 保留的条目键列表)
        """
        preserved = {}
        preserved_keys = []
        
        for key, translation in existing_translations.items():
            # 跳过已废弃的条目
            if not self._is_entry_translated(translation):
                continue
            
            # 检查源条目是否存在
            source_entry = source_entries.get(key)
            if source_entry is None:
                # 源条目已删除，不保留（由 ChangeDetector 处理废弃标记）
                continue
            
            # 检查源内容是否未变更
            if self._is_source_unchanged(source_entry, translation):
                preserved[key] = translation
                preserved_keys.append(key)
        
        return preserved, preserved_keys
    
    def identify_entries_to_process(
        self,
        source_entries: Dict[str, Dict],
        existing_translations: Dict[str, Dict],
        preserved_keys: List[str]
    ) -> Tuple[List[str], List[str]]:
        """识别需要处理的条目
        
        Args:
            source_entries: 源条目字典
            existing_translations: 现有翻译字典
            preserved_keys: 已保留的条目键列表
            
        Returns:
            Tuple[List, List]: (新增条目键列表, 修改条目键列表)
        """
        added = []
        modified = []
        
        preserved_set = set(preserved_keys)
        
        for key in source_entries.keys():
            if key in preserved_set:
                # 已保留，跳过
                continue
            
            if key not in existing_translations:
                # 新增条目
                added.append(key)
            else:
                # 修改的条目（源内容已变更）
                modified.append(key)
        
        return sorted(added), sorted(modified)

    def create_placeholder_entry(
        self,
        source_entry: Dict[str, Any],
        entry_key: str
    ) -> Dict[str, Any]:
        """为新增条目创建占位翻译条目
        
        Args:
            source_entry: 源条目
            entry_key: 条目键名
            
        Returns:
            Dict: 占位翻译条目
        """
        # 创建基本结构，保留源内容作为参考
        placeholder = {
            "name": "",  # 空名称表示未翻译
            "_meta": {
                "source_hash": self._compute_content_hash(source_entry),
                "created_at": datetime.now().isoformat(),
                "status": "untranslated"
            }
        }
        
        # 复制其他可翻译字段的结构（但不复制内容）
        for field in ["description", "category"]:
            if field in source_entry:
                placeholder[field] = ""
        
        return placeholder
    
    def mark_entry_for_review(
        self,
        existing_translation: Dict[str, Any],
        source_entry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """标记条目需要审核
        
        当源内容变更时，保留现有翻译但标记需要审核。
        
        Args:
            existing_translation: 现有翻译
            source_entry: 新的源条目
            
        Returns:
            Dict: 标记后的翻译条目
        """
        result = dict(existing_translation)
        
        if "_meta" not in result:
            result["_meta"] = {}
        
        result["_meta"]["needs_review"] = True
        result["_meta"]["review_reason"] = "source_changed"
        result["_meta"]["marked_at"] = datetime.now().isoformat()
        result["_meta"]["new_source_hash"] = self._compute_content_hash(source_entry)
        
        return result
    
    def incremental_update(
        self,
        source_file: str,
        translation_file: str,
        create_placeholders: bool = True
    ) -> UpdateResult:
        """执行增量更新
        
        保留未变更条目的现有翻译，只处理新增和修改的条目。
        
        Args:
            source_file: 源文件路径 (en-US)
            translation_file: 翻译文件路径 (zh_Hans)
            create_placeholders: 是否为新增条目创建占位条目
            
        Returns:
            UpdateResult: 更新结果
        """
        source_data = self._load_json_file(source_file)
        translation_data = self._load_json_file(translation_file)
        
        file_name = Path(source_file).name
        result = UpdateResult(file_name=file_name)
        
        if source_data is None:
            return result
        
        source_entries = source_data.get("entries", {})
        existing_translations = translation_data.get("entries", {}) if translation_data else {}
        
        # 1. 保留未变更条目的现有翻译
        preserved, preserved_keys = self.preserve_unchanged_translations(
            source_entries, existing_translations
        )
        result.preserved_entries = preserved_keys
        
        # 2. 识别需要处理的条目
        added_keys, modified_keys = self.identify_entries_to_process(
            source_entries, existing_translations, preserved_keys
        )
        result.added_entries = added_keys
        result.modified_entries = modified_keys
        
        # 3. 构建更新后的翻译数据
        updated_entries = dict(preserved)
        
        # 处理新增条目
        if create_placeholders:
            for key in added_keys:
                updated_entries[key] = self.create_placeholder_entry(
                    source_entries[key], key
                )
        
        # 处理修改的条目（保留翻译但标记需要审核）
        for key in modified_keys:
            if key in existing_translations:
                updated_entries[key] = self.mark_entry_for_review(
                    existing_translations[key],
                    source_entries[key]
                )
        
        # 4. 保存更新后的翻译文件
        updated_data = {"entries": updated_entries}
        self._save_json_file(translation_file, updated_data)
        
        return result
    
    def incremental_update_directory(
        self,
        source_dir: str,
        target_dir: str,
        create_placeholders: bool = True
    ) -> Dict[str, UpdateResult]:
        """对整个目录执行增量更新
        
        Args:
            source_dir: 源目录路径 (en-US)
            target_dir: 目标目录路径 (zh_Hans)
            create_placeholders: 是否为新增条目创建占位条目
            
        Returns:
            Dict[str, UpdateResult]: 每个文件的更新结果
        """
        source_path = Path(source_dir)
        target_path = Path(target_dir)
        
        results = {}
        
        if not source_path.exists():
            return results
        
        # 确保目标目录存在
        target_path.mkdir(parents=True, exist_ok=True)
        
        for source_file in sorted(source_path.glob("*.json")):
            target_file = target_path / source_file.name
            
            result = self.incremental_update(
                str(source_file),
                str(target_file),
                create_placeholders
            )
            
            results[source_file.stem] = result
        
        return results

    def _detect_field_changes(
        self,
        old_source: Dict[str, Any],
        new_source: Dict[str, Any]
    ) -> Dict[str, str]:
        """检测源条目字段的变更类型
        
        Args:
            old_source: 旧源条目
            new_source: 新源条目
            
        Returns:
            Dict[str, str]: 字段名到变更类型的映射
                - 'added': 新增字段
                - 'removed': 删除字段
                - 'modified': 修改字段
                - 'unchanged': 未变更字段
        """
        changes = {}
        
        old_keys = set(old_source.keys()) - {"_meta"}
        new_keys = set(new_source.keys()) - {"_meta"}
        
        # 新增字段
        for key in new_keys - old_keys:
            changes[key] = "added"
        
        # 删除字段
        for key in old_keys - new_keys:
            changes[key] = "removed"
        
        # 检查共有字段
        for key in old_keys & new_keys:
            if old_source[key] == new_source[key]:
                changes[key] = "unchanged"
            else:
                changes[key] = "modified"
        
        return changes
    
    def _can_auto_merge(
        self,
        field_changes: Dict[str, str],
        translation: Dict[str, Any]
    ) -> bool:
        """判断是否可以自动合并
        
        自动合并条件：
        - 只有新增字段
        - 或者只有未变更字段
        - 翻译中没有与新增字段冲突的内容
        
        Args:
            field_changes: 字段变更映射
            translation: 现有翻译
            
        Returns:
            bool: 是否可以自动合并
        """
        has_modified = any(v == "modified" for v in field_changes.values())
        has_removed = any(v == "removed" for v in field_changes.values())
        
        # 如果有修改或删除的字段，需要人工审核
        if has_modified or has_removed:
            return False
        
        return True
    
    def smart_merge(
        self,
        old_source: Dict[str, Any],
        new_source: Dict[str, Any],
        existing_translation: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[MergeConflict]]:
        """智能合并新旧翻译内容
        
        尝试自动合并翻译，处理以下情况：
        - 新增字段：添加空占位
        - 删除字段：保留翻译但标记
        - 修改字段：保留翻译但标记需要审核
        - 未变更字段：保留现有翻译
        
        Args:
            old_source: 旧源条目（翻译时的源内容）
            new_source: 新源条目
            existing_translation: 现有翻译
            
        Returns:
            Tuple[Dict, List]: (合并后的翻译, 冲突列表)
        """
        conflicts = []
        merged = dict(existing_translation)
        
        # 检测字段变更
        field_changes = self._detect_field_changes(old_source, new_source)
        
        # 处理各种变更
        for field, change_type in field_changes.items():
            if change_type == "added":
                # 新增字段：添加空占位
                if field not in merged:
                    merged[field] = ""
            
            elif change_type == "removed":
                # 删除字段：保留翻译但记录冲突
                if field in merged and merged[field]:
                    conflicts.append(MergeConflict(
                        entry_key="",  # Will be set by caller
                        field=field,
                        source_value=None,
                        existing_translation=merged[field],
                        conflict_type="field_removed"
                    ))
            
            elif change_type == "modified":
                # 修改字段：保留翻译但记录冲突
                if field in merged and merged[field]:
                    conflicts.append(MergeConflict(
                        entry_key="",
                        field=field,
                        source_value=new_source[field],
                        existing_translation=merged[field],
                        conflict_type="content_change"
                    ))
        
        # 更新元数据
        if "_meta" not in merged:
            merged["_meta"] = {}
        
        merged["_meta"]["source_hash"] = self._compute_content_hash(new_source)
        merged["_meta"]["merged_at"] = datetime.now().isoformat()
        
        if conflicts:
            merged["_meta"]["has_conflicts"] = True
            merged["_meta"]["conflict_count"] = len(conflicts)
        
        return merged, conflicts
    
    def smart_merge_entry(
        self,
        entry_key: str,
        source_file: str,
        translation_file: str,
        old_source_file: Optional[str] = None
    ) -> Tuple[Dict[str, Any], List[MergeConflict]]:
        """智能合并单个条目
        
        Args:
            entry_key: 条目键名
            source_file: 新源文件路径
            translation_file: 翻译文件路径
            old_source_file: 旧源文件路径（可选，用于获取翻译时的源内容）
            
        Returns:
            Tuple[Dict, List]: (合并后的翻译, 冲突列表)
        """
        source_data = self._load_json_file(source_file)
        translation_data = self._load_json_file(translation_file)
        
        if source_data is None or translation_data is None:
            return {}, []
        
        source_entries = source_data.get("entries", {})
        translation_entries = translation_data.get("entries", {})
        
        if entry_key not in source_entries or entry_key not in translation_entries:
            return {}, []
        
        new_source = source_entries[entry_key]
        existing_translation = translation_entries[entry_key]
        
        # 获取旧源内容
        if old_source_file:
            old_source_data = self._load_json_file(old_source_file)
            old_source = old_source_data.get("entries", {}).get(entry_key, {}) if old_source_data else {}
        else:
            # 如果没有旧源文件，使用翻译中记录的源哈希来判断
            # 这种情况下无法进行精确的字段级合并，只能标记需要审核
            old_source = {}
        
        merged, conflicts = self.smart_merge(old_source, new_source, existing_translation)
        
        # 设置冲突的 entry_key
        for conflict in conflicts:
            conflict.entry_key = entry_key
        
        return merged, conflicts
    
    def apply_smart_merge(
        self,
        source_file: str,
        translation_file: str,
        old_source_file: Optional[str] = None
    ) -> Tuple[UpdateResult, List[MergeConflict]]:
        """对整个文件应用智能合并
        
        Args:
            source_file: 新源文件路径
            translation_file: 翻译文件路径
            old_source_file: 旧源文件路径（可选）
            
        Returns:
            Tuple[UpdateResult, List]: (更新结果, 所有冲突列表)
        """
        source_data = self._load_json_file(source_file)
        translation_data = self._load_json_file(translation_file)
        
        file_name = Path(source_file).name
        result = UpdateResult(file_name=file_name)
        all_conflicts = []
        
        if source_data is None:
            return result, all_conflicts
        
        source_entries = source_data.get("entries", {})
        existing_translations = translation_data.get("entries", {}) if translation_data else {}
        
        # 获取旧源数据
        old_source_data = self._load_json_file(old_source_file) if old_source_file else None
        old_source_entries = old_source_data.get("entries", {}) if old_source_data else {}
        
        updated_entries = {}
        
        for key, source_entry in source_entries.items():
            if key not in existing_translations:
                # 新增条目
                updated_entries[key] = self.create_placeholder_entry(source_entry, key)
                result.added_entries.append(key)
            else:
                translation = existing_translations[key]
                old_source = old_source_entries.get(key, {})
                
                # 检查源是否变更
                if self._is_source_unchanged(source_entry, translation):
                    # 未变更，直接保留
                    updated_entries[key] = translation
                    result.preserved_entries.append(key)
                else:
                    # 变更了，尝试智能合并
                    merged, conflicts = self.smart_merge(old_source, source_entry, translation)
                    updated_entries[key] = merged
                    
                    if conflicts:
                        result.conflicts.append(key)
                        all_conflicts.extend(conflicts)
                    else:
                        result.merged_entries.append(key)
        
        # 保存更新后的翻译文件
        updated_data = {"entries": updated_entries}
        self._save_json_file(translation_file, updated_data)
        
        return result, all_conflicts
    
    def generate_conflict_report(self, conflicts: List[MergeConflict]) -> str:
        """生成冲突报告
        
        Args:
            conflicts: 冲突列表
            
        Returns:
            str: Markdown 格式的冲突报告
        """
        if not conflicts:
            return "# 合并冲突报告\n\n无冲突。"
        
        lines = []
        lines.append("# 合并冲突报告")
        lines.append("")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"冲突数量: {len(conflicts)}")
        lines.append("")
        
        # 按条目分组
        by_entry = {}
        for conflict in conflicts:
            if conflict.entry_key not in by_entry:
                by_entry[conflict.entry_key] = []
            by_entry[conflict.entry_key].append(conflict)
        
        for entry_key, entry_conflicts in sorted(by_entry.items()):
            lines.append(f"## {entry_key}")
            lines.append("")
            
            for conflict in entry_conflicts:
                lines.append(f"### 字段: {conflict.field}")
                lines.append(f"- **冲突类型**: {conflict.conflict_type}")
                
                if conflict.conflict_type == "field_removed":
                    lines.append(f"- **现有翻译**: {conflict.existing_translation}")
                    lines.append("- **说明**: 源文件中该字段已删除，但翻译中仍有内容")
                elif conflict.conflict_type == "content_change":
                    lines.append(f"- **新源内容**: {conflict.source_value}")
                    lines.append(f"- **现有翻译**: {conflict.existing_translation}")
                    lines.append("- **说明**: 源内容已变更，需要审核翻译是否仍然准确")
                
                lines.append("")
        
        return "\n".join(lines)
