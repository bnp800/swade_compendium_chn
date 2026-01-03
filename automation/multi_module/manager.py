"""多模块管理器实现"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import (
    ModuleInfo,
    ModuleStructure,
    SharedContent,
    TranslationReuse,
    ReuseReport,
)


class MultiModuleManager:
    """多模块翻译管理器
    
    支持多个 SWADE 扩展模块的翻译管理，包括：
    - 模块结构自动创建
    - 跨模块翻译复用
    - 共享内容检测
    """
    
    # 已知的 SWADE 模块列表
    KNOWN_MODULES = {
        "swade-core-rules": ModuleInfo(
            id="swade-core-rules",
            title="Savage Worlds Adventure Edition Core Rules",
            compendiums=[
                "swade-armor", "swade-bestiary", "swade-edges",
                "swade-equipment", "swade-hindrances", "swade-modern-firearms",
                "swade-personal-weapons", "swade-powers", "swade-races",
                "swade-racial-abilities", "swade-rules", "swade-skills",
                "swade-special-weapons", "swade-specialabilities",
                "swade-tables", "swade-vehicles"
            ]
        ),
        "swpf-core-rules": ModuleInfo(
            id="swpf-core-rules",
            title="Pathfinder for Savage Worlds",
            compendiums=[
                "swpf-abilities", "swpf-actors", "swpf-edges",
                "swpf-gear", "swpf-hindrances", "swpf-macros",
                "swpf-powers", "swpf-rules", "swpf-skills", "swpf-tables"
            ]
        ),
        "swpf-bestiary": ModuleInfo(
            id="swpf-bestiary",
            title="Savage Pathfinder Bestiary",
            compendiums=[
                "swpf-bestiary", "swpf-bestiary-abilities",
                "swpf-bestiary-ancestries", "swpf-bestiary-journal"
            ]
        ),
    }
    
    def __init__(self, base_dir: str):
        """初始化多模块管理器
        
        Args:
            base_dir: 翻译项目根目录 (包含 en-US 和 zh_Hans 目录)
        """
        self.base_dir = Path(base_dir)
        self.source_dir = self.base_dir / "en-US"
        self.target_dir = self.base_dir / "zh_Hans"
        self._translation_cache: Dict[str, Dict[str, Dict]] = {}
    
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
    
    def get_module_info(self, module_id: str) -> Optional[ModuleInfo]:
        """获取模块信息
        
        Args:
            module_id: 模块 ID
            
        Returns:
            Optional[ModuleInfo]: 模块信息，未知模块返回 None
        """
        return self.KNOWN_MODULES.get(module_id)
    
    def detect_modules_from_files(self) -> List[str]:
        """从现有文件检测模块列表
        
        扫描 en-US 目录，根据文件名前缀检测存在的模块。
        
        Returns:
            List[str]: 检测到的模块 ID 列表
        """
        modules = set()
        
        if not self.source_dir.exists():
            return []
        
        for json_file in self.source_dir.glob("*.json"):
            # 文件名格式: module-id.compendium-name.json
            name = json_file.stem
            if "." in name:
                module_id = name.split(".")[0]
                modules.add(module_id)
        
        return sorted(modules)

    def get_module_files(self, module_id: str) -> Tuple[List[str], List[str]]:
        """获取模块的源文件和目标文件列表
        
        Args:
            module_id: 模块 ID
            
        Returns:
            Tuple[List[str], List[str]]: (源文件列表, 目标文件列表)
        """
        source_files = []
        target_files = []
        
        prefix = f"{module_id}."
        
        if self.source_dir.exists():
            for json_file in sorted(self.source_dir.glob("*.json")):
                if json_file.name.startswith(prefix):
                    source_files.append(json_file.name)
        
        if self.target_dir.exists():
            for json_file in sorted(self.target_dir.glob("*.json")):
                if json_file.name.startswith(prefix):
                    target_files.append(json_file.name)
        
        return source_files, target_files
    
    def analyze_module_structure(self, module_id: str) -> ModuleStructure:
        """分析模块的翻译文件结构
        
        检查模块的源文件和目标文件，识别缺失的翻译文件。
        
        Args:
            module_id: 模块 ID
            
        Returns:
            ModuleStructure: 模块结构信息
        """
        source_files, target_files = self.get_module_files(module_id)
        
        # 找出缺失的目标文件
        target_set = set(target_files)
        missing_files = [f for f in source_files if f not in target_set]
        
        return ModuleStructure(
            module_id=module_id,
            source_files=source_files,
            target_files=target_files,
            missing_files=missing_files
        )
    
    def create_module_structure(self, module_id: str) -> List[Path]:
        """为模块创建翻译文件结构
        
        为新模块自动创建翻译文件结构，包括：
        - 创建 zh_Hans 目录（如不存在）
        - 为每个源文件创建对应的空翻译文件
        
        Args:
            module_id: 模块 ID
            
        Returns:
            List[Path]: 创建的文件路径列表
        """
        created_files = []
        
        # 确保目标目录存在
        self.target_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取源文件列表
        source_files, existing_target_files = self.get_module_files(module_id)
        existing_set = set(existing_target_files)
        
        # 为每个缺失的源文件创建占位翻译文件
        for source_file in source_files:
            if source_file not in existing_set:
                target_path = self.target_dir / source_file
                
                # 创建空的翻译文件结构
                placeholder_content = {"entries": {}}
                self._save_json_file(str(target_path), placeholder_content)
                created_files.append(target_path)
        
        return created_files
    
    def create_all_module_structures(self) -> Dict[str, List[Path]]:
        """为所有检测到的模块创建翻译文件结构
        
        Returns:
            Dict[str, List[Path]]: 每个模块创建的文件路径列表
        """
        result = {}
        
        for module_id in self.detect_modules_from_files():
            created = self.create_module_structure(module_id)
            if created:
                result[module_id] = created
        
        return result
    
    def register_module(
        self, 
        module_id: str, 
        title: str, 
        compendiums: List[str]
    ) -> ModuleInfo:
        """注册新模块
        
        将新模块添加到已知模块列表中。
        
        Args:
            module_id: 模块 ID
            title: 模块标题
            compendiums: compendium 列表
            
        Returns:
            ModuleInfo: 注册的模块信息
        """
        module_info = ModuleInfo(
            id=module_id,
            title=title,
            compendiums=compendiums
        )
        self.KNOWN_MODULES[module_id] = module_info
        return module_info

    # ========== 跨模块翻译复用功能 ==========
    
    def _load_translation_cache(self, module_id: str) -> Dict[str, Dict]:
        """加载模块的翻译缓存
        
        Args:
            module_id: 模块 ID
            
        Returns:
            Dict[str, Dict]: 条目名称到翻译的映射
        """
        if module_id in self._translation_cache:
            return self._translation_cache[module_id]
        
        cache: Dict[str, Dict] = {}
        _, target_files = self.get_module_files(module_id)
        
        for filename in target_files:
            file_path = self.target_dir / filename
            data = self._load_json_file(str(file_path))
            if data:
                entries = data.get("entries", {})
                for name, translation in entries.items():
                    # 只缓存已翻译的条目
                    if self._is_entry_translated(name, translation):
                        cache[name] = {
                            "translation": translation,
                            "source_file": filename,
                            "compendium": filename.replace(f"{module_id}.", "").replace(".json", "")
                        }
        
        self._translation_cache[module_id] = cache
        return cache
    
    def _is_entry_translated(self, entry_name: str, translation: Dict) -> bool:
        """检查条目是否已翻译
        
        Args:
            entry_name: 条目名称
            translation: 翻译数据
            
        Returns:
            bool: 是否已翻译
        """
        if not translation:
            return False
        
        # 检查是否被标记为 deprecated
        meta = translation.get("_meta", {})
        if meta.get("deprecated", False):
            return False
        
        # 检查 name 字段
        translated_name = translation.get("name", "")
        if not translated_name:
            return False
        
        # 如果 name 与原名相同，检查是否有其他翻译内容
        if translated_name == entry_name:
            # 检查 description 是否有内容
            desc = translation.get("description", "")
            return bool(desc)
        
        return True
    
    def find_translation(
        self, 
        entry_name: str, 
        exclude_module: Optional[str] = None
    ) -> Optional[Tuple[str, str, Dict]]:
        """在所有模块中查找条目的翻译
        
        Args:
            entry_name: 条目名称
            exclude_module: 要排除的模块 ID
            
        Returns:
            Optional[Tuple[str, str, Dict]]: (模块ID, compendium名, 翻译数据)，未找到返回 None
        """
        for module_id in self.detect_modules_from_files():
            if module_id == exclude_module:
                continue
            
            cache = self._load_translation_cache(module_id)
            if entry_name in cache:
                info = cache[entry_name]
                return (module_id, info["compendium"], info["translation"])
        
        return None
    
    def detect_shared_content(self) -> List[SharedContent]:
        """检测跨模块的共享内容
        
        扫描所有模块，找出在多个模块中出现的相同条目名称。
        
        Returns:
            List[SharedContent]: 共享内容列表
        """
        # 收集所有条目及其来源
        entry_sources: Dict[str, List[Tuple[str, str]]] = {}
        
        for module_id in self.detect_modules_from_files():
            source_files, _ = self.get_module_files(module_id)
            
            for filename in source_files:
                file_path = self.source_dir / filename
                data = self._load_json_file(str(file_path))
                if data:
                    compendium = filename.replace(f"{module_id}.", "").replace(".json", "")
                    entries = data.get("entries", {})
                    for name in entries.keys():
                        if name not in entry_sources:
                            entry_sources[name] = []
                        entry_sources[name].append((module_id, compendium))
        
        # 找出在多个模块中出现的条目
        shared_content = []
        for entry_name, sources in entry_sources.items():
            if len(sources) > 1:
                # 按模块分组
                modules = list(set(s[0] for s in sources))
                if len(modules) > 1:
                    # 确实跨模块共享
                    source_module, source_compendium = sources[0]
                    target_modules = [s[0] for s in sources[1:]]
                    
                    # 查找翻译
                    translation = None
                    result = self.find_translation(entry_name)
                    if result:
                        _, _, translation = result
                    
                    shared_content.append(SharedContent(
                        entry_name=entry_name,
                        source_module=source_module,
                        source_compendium=source_compendium,
                        target_modules=target_modules,
                        translation=translation
                    ))
        
        return shared_content
    
    def reuse_translation(
        self, 
        entry_name: str, 
        target_module: str, 
        target_compendium: str
    ) -> Optional[TranslationReuse]:
        """复用已有翻译到目标模块
        
        从其他模块查找条目的翻译，并复用到目标模块。
        
        Args:
            entry_name: 条目名称
            target_module: 目标模块 ID
            target_compendium: 目标 compendium 名称
            
        Returns:
            Optional[TranslationReuse]: 复用记录，未找到翻译返回 None
        """
        # 查找翻译
        result = self.find_translation(entry_name, exclude_module=target_module)
        if not result:
            return None
        
        source_module, source_compendium, translation = result
        
        return TranslationReuse(
            entry_name=entry_name,
            source_module=source_module,
            source_compendium=source_compendium,
            target_module=target_module,
            target_compendium=target_compendium,
            translation=translation
        )
    
    def apply_translation_reuse(
        self, 
        reuse: TranslationReuse,
        overwrite: bool = False
    ) -> bool:
        """应用翻译复用
        
        将复用的翻译写入目标文件。
        
        Args:
            reuse: 翻译复用记录
            overwrite: 是否覆盖已有翻译
            
        Returns:
            bool: 是否成功应用
        """
        target_file = self.target_dir / f"{reuse.target_module}.{reuse.target_compendium}.json"
        
        # 加载目标文件
        data = self._load_json_file(str(target_file))
        if data is None:
            data = {"entries": {}}
        
        entries = data.get("entries", {})
        
        # 检查是否已有翻译
        if reuse.entry_name in entries and not overwrite:
            existing = entries[reuse.entry_name]
            if self._is_entry_translated(reuse.entry_name, existing):
                return False  # 已有翻译，不覆盖
        
        # 复制翻译，添加复用标记
        translation = dict(reuse.translation)
        if "_meta" not in translation:
            translation["_meta"] = {}
        translation["_meta"]["reused_from"] = {
            "module": reuse.source_module,
            "compendium": reuse.source_compendium
        }
        
        entries[reuse.entry_name] = translation
        data["entries"] = entries
        
        # 保存文件
        self._save_json_file(str(target_file), data)
        
        # 清除缓存
        if reuse.target_module in self._translation_cache:
            del self._translation_cache[reuse.target_module]
        
        return True

    def reuse_all_translations(
        self, 
        target_module: str,
        overwrite: bool = False
    ) -> ReuseReport:
        """为目标模块复用所有可用的翻译
        
        扫描目标模块的所有条目，从其他模块查找并复用翻译。
        
        Args:
            target_module: 目标模块 ID
            overwrite: 是否覆盖已有翻译
            
        Returns:
            ReuseReport: 复用报告
        """
        report = ReuseReport()
        
        source_files, _ = self.get_module_files(target_module)
        
        for filename in source_files:
            file_path = self.source_dir / filename
            data = self._load_json_file(str(file_path))
            if not data:
                continue
            
            compendium = filename.replace(f"{target_module}.", "").replace(".json", "")
            entries = data.get("entries", {})
            
            for entry_name in entries.keys():
                # 尝试复用翻译
                reuse = self.reuse_translation(entry_name, target_module, compendium)
                if reuse:
                    report.total_shared_entries += 1
                    if self.apply_translation_reuse(reuse, overwrite):
                        report.reused_translations += 1
                        report.reuse_details.append(reuse)
                    else:
                        report.missing_translations += 1
        
        # 检测共享内容
        report.shared_content = [
            sc for sc in self.detect_shared_content()
            if target_module in sc.target_modules or sc.source_module == target_module
        ]
        
        return report
    
    def generate_reuse_report(self, report: ReuseReport) -> str:
        """生成翻译复用报告 (Markdown 格式)
        
        Args:
            report: 复用报告
            
        Returns:
            str: Markdown 格式的报告
        """
        from datetime import datetime
        
        lines = []
        lines.append("# 翻译复用报告")
        lines.append("")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 总体统计
        lines.append("## 总体统计")
        lines.append("")
        lines.append(f"- **共享条目总数**: {report.total_shared_entries}")
        lines.append(f"- **已复用翻译**: {report.reused_translations}")
        lines.append(f"- **缺失翻译**: {report.missing_translations}")
        lines.append(f"- **复用率**: {report.reuse_percentage:.1f}%")
        lines.append("")
        
        # 复用详情
        if report.reuse_details:
            lines.append("## 复用详情")
            lines.append("")
            lines.append("| 条目名称 | 来源模块 | 来源 Compendium | 目标模块 | 目标 Compendium |")
            lines.append("|----------|----------|-----------------|----------|-----------------|")
            
            for reuse in report.reuse_details[:50]:  # 限制显示数量
                lines.append(
                    f"| {reuse.entry_name} | {reuse.source_module} | "
                    f"{reuse.source_compendium} | {reuse.target_module} | "
                    f"{reuse.target_compendium} |"
                )
            
            if len(report.reuse_details) > 50:
                lines.append(f"| ... | 还有 {len(report.reuse_details) - 50} 条记录 | | | |")
            
            lines.append("")
        
        # 共享内容
        if report.shared_content:
            lines.append("## 跨模块共享内容")
            lines.append("")
            
            translated = [sc for sc in report.shared_content if sc.is_translated]
            untranslated = [sc for sc in report.shared_content if not sc.is_translated]
            
            lines.append(f"- **已翻译**: {len(translated)}")
            lines.append(f"- **未翻译**: {len(untranslated)}")
            lines.append("")
            
            if untranslated:
                lines.append("### 未翻译的共享内容")
                lines.append("")
                for sc in untranslated[:20]:
                    modules = ", ".join([sc.source_module] + sc.target_modules)
                    lines.append(f"- **{sc.entry_name}** (出现在: {modules})")
                
                if len(untranslated) > 20:
                    lines.append(f"- ... 还有 {len(untranslated) - 20} 个条目")
                
                lines.append("")
        
        return "\n".join(lines)
    
    def clear_cache(self) -> None:
        """清除翻译缓存"""
        self._translation_cache.clear()
    
    def get_all_translations(self) -> Dict[str, Dict[str, Dict]]:
        """获取所有模块的翻译
        
        Returns:
            Dict[str, Dict[str, Dict]]: 模块ID -> 条目名称 -> 翻译数据
        """
        result = {}
        for module_id in self.detect_modules_from_files():
            result[module_id] = self._load_translation_cache(module_id)
        return result
