"""多模块管理器测试"""

import json
import pytest
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume

from automation.multi_module import MultiModuleManager
from automation.multi_module.models import (
    ModuleInfo,
    ModuleStructure,
    SharedContent,
    TranslationReuse,
    ReuseReport,
)


class TestMultiModuleManager:
    """MultiModuleManager 单元测试"""
    
    def test_detect_modules_from_files(self, temp_dir):
        """测试从文件检测模块"""
        # 创建测试文件
        source_dir = temp_dir / "en-US"
        source_dir.mkdir()
        
        (source_dir / "swade-core-rules.swade-edges.json").write_text(
            '{"entries": {}}', encoding='utf-8'
        )
        (source_dir / "swpf-core-rules.swpf-edges.json").write_text(
            '{"entries": {}}', encoding='utf-8'
        )
        
        manager = MultiModuleManager(str(temp_dir))
        modules = manager.detect_modules_from_files()
        
        assert "swade-core-rules" in modules
        assert "swpf-core-rules" in modules
    
    def test_get_module_files(self, temp_dir):
        """测试获取模块文件列表"""
        source_dir = temp_dir / "en-US"
        target_dir = temp_dir / "zh_Hans"
        source_dir.mkdir()
        target_dir.mkdir()
        
        # 创建源文件
        (source_dir / "swade-core-rules.swade-edges.json").write_text(
            '{"entries": {}}', encoding='utf-8'
        )
        (source_dir / "swade-core-rules.swade-powers.json").write_text(
            '{"entries": {}}', encoding='utf-8'
        )
        
        # 创建目标文件（只有一个）
        (target_dir / "swade-core-rules.swade-edges.json").write_text(
            '{"entries": {}}', encoding='utf-8'
        )
        
        manager = MultiModuleManager(str(temp_dir))
        source_files, target_files = manager.get_module_files("swade-core-rules")
        
        assert len(source_files) == 2
        assert len(target_files) == 1
        assert "swade-core-rules.swade-edges.json" in source_files
        assert "swade-core-rules.swade-powers.json" in source_files
    
    def test_analyze_module_structure(self, temp_dir):
        """测试分析模块结构"""
        source_dir = temp_dir / "en-US"
        target_dir = temp_dir / "zh_Hans"
        source_dir.mkdir()
        target_dir.mkdir()
        
        # 创建源文件
        (source_dir / "swade-core-rules.swade-edges.json").write_text(
            '{"entries": {}}', encoding='utf-8'
        )
        (source_dir / "swade-core-rules.swade-powers.json").write_text(
            '{"entries": {}}', encoding='utf-8'
        )
        
        # 只创建一个目标文件
        (target_dir / "swade-core-rules.swade-edges.json").write_text(
            '{"entries": {}}', encoding='utf-8'
        )
        
        manager = MultiModuleManager(str(temp_dir))
        structure = manager.analyze_module_structure("swade-core-rules")
        
        assert structure.module_id == "swade-core-rules"
        assert len(structure.source_files) == 2
        assert len(structure.target_files) == 1
        assert len(structure.missing_files) == 1
        assert "swade-core-rules.swade-powers.json" in structure.missing_files
        assert not structure.is_complete
    
    def test_create_module_structure(self, temp_dir):
        """测试创建模块结构"""
        source_dir = temp_dir / "en-US"
        source_dir.mkdir()
        
        # 创建源文件
        (source_dir / "swade-core-rules.swade-edges.json").write_text(
            '{"entries": {"Edge1": {"name": "Edge1"}}}', encoding='utf-8'
        )
        (source_dir / "swade-core-rules.swade-powers.json").write_text(
            '{"entries": {"Power1": {"name": "Power1"}}}', encoding='utf-8'
        )
        
        manager = MultiModuleManager(str(temp_dir))
        created = manager.create_module_structure("swade-core-rules")
        
        assert len(created) == 2
        
        # 验证文件已创建
        target_dir = temp_dir / "zh_Hans"
        assert (target_dir / "swade-core-rules.swade-edges.json").exists()
        assert (target_dir / "swade-core-rules.swade-powers.json").exists()
        
        # 验证文件内容
        with open(target_dir / "swade-core-rules.swade-edges.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert "entries" in data
            assert data["entries"] == {}
    
    def test_find_translation(self, temp_dir):
        """测试查找翻译"""
        source_dir = temp_dir / "en-US"
        target_dir = temp_dir / "zh_Hans"
        source_dir.mkdir()
        target_dir.mkdir()
        
        # 创建源文件
        (source_dir / "swade-core-rules.swade-edges.json").write_text(
            '{"entries": {"Alertness": {"name": "Alertness"}}}', encoding='utf-8'
        )
        
        # 创建已翻译的目标文件
        (target_dir / "swade-core-rules.swade-edges.json").write_text(
            '{"entries": {"Alertness": {"name": "警觉", "description": "不容易被突袭"}}}',
            encoding='utf-8'
        )
        
        manager = MultiModuleManager(str(temp_dir))
        result = manager.find_translation("Alertness")
        
        assert result is not None
        module_id, compendium, translation = result
        assert module_id == "swade-core-rules"
        assert compendium == "swade-edges"
        assert translation["name"] == "警觉"
    
    def test_find_translation_not_found(self, temp_dir):
        """测试查找不存在的翻译"""
        source_dir = temp_dir / "en-US"
        target_dir = temp_dir / "zh_Hans"
        source_dir.mkdir()
        target_dir.mkdir()
        
        (source_dir / "swade-core-rules.swade-edges.json").write_text(
            '{"entries": {}}', encoding='utf-8'
        )
        (target_dir / "swade-core-rules.swade-edges.json").write_text(
            '{"entries": {}}', encoding='utf-8'
        )
        
        manager = MultiModuleManager(str(temp_dir))
        result = manager.find_translation("NonExistent")
        
        assert result is None

    def test_detect_shared_content(self, temp_dir):
        """测试检测共享内容"""
        source_dir = temp_dir / "en-US"
        target_dir = temp_dir / "zh_Hans"
        source_dir.mkdir()
        target_dir.mkdir()
        
        # 创建两个模块的源文件，包含相同的条目
        (source_dir / "swade-core-rules.swade-edges.json").write_text(
            '{"entries": {"Alertness": {"name": "Alertness"}, "Unique1": {"name": "Unique1"}}}',
            encoding='utf-8'
        )
        (source_dir / "swpf-core-rules.swpf-edges.json").write_text(
            '{"entries": {"Alertness": {"name": "Alertness"}, "Unique2": {"name": "Unique2"}}}',
            encoding='utf-8'
        )
        
        manager = MultiModuleManager(str(temp_dir))
        shared = manager.detect_shared_content()
        
        # 应该检测到 Alertness 是共享的
        shared_names = [sc.entry_name for sc in shared]
        assert "Alertness" in shared_names
        assert "Unique1" not in shared_names
        assert "Unique2" not in shared_names
    
    def test_reuse_translation(self, temp_dir):
        """测试复用翻译"""
        source_dir = temp_dir / "en-US"
        target_dir = temp_dir / "zh_Hans"
        source_dir.mkdir()
        target_dir.mkdir()
        
        # 创建源文件
        (source_dir / "swade-core-rules.swade-edges.json").write_text(
            '{"entries": {"Alertness": {"name": "Alertness"}}}', encoding='utf-8'
        )
        (source_dir / "swpf-core-rules.swpf-edges.json").write_text(
            '{"entries": {"Alertness": {"name": "Alertness"}}}', encoding='utf-8'
        )
        
        # 创建已翻译的目标文件（只有 swade-core-rules）
        (target_dir / "swade-core-rules.swade-edges.json").write_text(
            '{"entries": {"Alertness": {"name": "警觉", "description": "不容易被突袭"}}}',
            encoding='utf-8'
        )
        (target_dir / "swpf-core-rules.swpf-edges.json").write_text(
            '{"entries": {}}', encoding='utf-8'
        )
        
        manager = MultiModuleManager(str(temp_dir))
        reuse = manager.reuse_translation("Alertness", "swpf-core-rules", "swpf-edges")
        
        assert reuse is not None
        assert reuse.entry_name == "Alertness"
        assert reuse.source_module == "swade-core-rules"
        assert reuse.target_module == "swpf-core-rules"
        assert reuse.translation["name"] == "警觉"
    
    def test_apply_translation_reuse(self, temp_dir):
        """测试应用翻译复用"""
        source_dir = temp_dir / "en-US"
        target_dir = temp_dir / "zh_Hans"
        source_dir.mkdir()
        target_dir.mkdir()
        
        # 创建源文件
        (source_dir / "swade-core-rules.swade-edges.json").write_text(
            '{"entries": {"Alertness": {"name": "Alertness"}}}', encoding='utf-8'
        )
        (source_dir / "swpf-core-rules.swpf-edges.json").write_text(
            '{"entries": {"Alertness": {"name": "Alertness"}}}', encoding='utf-8'
        )
        
        # 创建目标文件
        (target_dir / "swade-core-rules.swade-edges.json").write_text(
            '{"entries": {"Alertness": {"name": "警觉", "description": "不容易被突袭"}}}',
            encoding='utf-8'
        )
        (target_dir / "swpf-core-rules.swpf-edges.json").write_text(
            '{"entries": {}}', encoding='utf-8'
        )
        
        manager = MultiModuleManager(str(temp_dir))
        reuse = manager.reuse_translation("Alertness", "swpf-core-rules", "swpf-edges")
        
        assert reuse is not None
        success = manager.apply_translation_reuse(reuse)
        assert success
        
        # 验证翻译已应用
        with open(target_dir / "swpf-core-rules.swpf-edges.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert "Alertness" in data["entries"]
            assert data["entries"]["Alertness"]["name"] == "警觉"
            assert "_meta" in data["entries"]["Alertness"]
            assert "reused_from" in data["entries"]["Alertness"]["_meta"]


class TestModuleStructureCreation:
    """模块结构创建测试 - Requirements 9.4"""
    
    def test_create_structure_for_new_module(self, temp_dir):
        """测试为新模块创建结构"""
        source_dir = temp_dir / "en-US"
        source_dir.mkdir()
        
        # 创建新模块的源文件
        (source_dir / "new-module.compendium1.json").write_text(
            '{"entries": {"Entry1": {"name": "Entry1"}}}', encoding='utf-8'
        )
        (source_dir / "new-module.compendium2.json").write_text(
            '{"entries": {"Entry2": {"name": "Entry2"}}}', encoding='utf-8'
        )
        
        manager = MultiModuleManager(str(temp_dir))
        created = manager.create_module_structure("new-module")
        
        assert len(created) == 2
        
        # 验证目标目录已创建
        target_dir = temp_dir / "zh_Hans"
        assert target_dir.exists()
        
        # 验证文件已创建
        assert (target_dir / "new-module.compendium1.json").exists()
        assert (target_dir / "new-module.compendium2.json").exists()
    
    def test_create_structure_preserves_existing(self, temp_dir):
        """测试创建结构时保留已有文件"""
        source_dir = temp_dir / "en-US"
        target_dir = temp_dir / "zh_Hans"
        source_dir.mkdir()
        target_dir.mkdir()
        
        # 创建源文件
        (source_dir / "test-module.comp1.json").write_text(
            '{"entries": {"Entry1": {"name": "Entry1"}}}', encoding='utf-8'
        )
        (source_dir / "test-module.comp2.json").write_text(
            '{"entries": {"Entry2": {"name": "Entry2"}}}', encoding='utf-8'
        )
        
        # 创建已有的目标文件（带翻译）
        existing_content = '{"entries": {"Entry1": {"name": "条目1"}}}'
        (target_dir / "test-module.comp1.json").write_text(
            existing_content, encoding='utf-8'
        )
        
        manager = MultiModuleManager(str(temp_dir))
        created = manager.create_module_structure("test-module")
        
        # 只应该创建缺失的文件
        assert len(created) == 1
        assert created[0].name == "test-module.comp2.json"
        
        # 验证已有文件未被覆盖
        with open(target_dir / "test-module.comp1.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert data["entries"]["Entry1"]["name"] == "条目1"


# ========== Property-Based Tests ==========

import tempfile

# 生成有效的条目名称
entry_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S'), 
                           whitelist_characters=' -_'),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip())

# 生成有效的模块 ID
module_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Ll', 'N'), 
                           whitelist_characters='-'),
    min_size=3,
    max_size=20
).filter(lambda x: x and not x.startswith('-') and not x.endswith('-'))

# 生成翻译数据
translation_strategy = st.fixed_dictionaries({
    'name': st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    'description': st.text(min_size=0, max_size=200),
})


class TestTranslationReuseProperty:
    """
    Property 13: Translation Reuse Across Modules
    
    *For any* content that appears in multiple modules (e.g., shared abilities),
    if the content is translated in one module, it SHALL be available for reuse
    in other modules.
    
    **Validates: Requirements 9.5**
    """
    
    @given(
        entry_name=entry_name_strategy,
        translation_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        translation_desc=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=100, deadline=None)
    def test_translation_reuse_across_modules(
        self, 
        entry_name, 
        translation_name,
        translation_desc
    ):
        """
        Property 13: Translation Reuse Across Modules
        
        For any content that appears in multiple modules, if the content is
        translated in one module, it SHALL be available for reuse in other modules.
        
        **Feature: translation-automation-workflow, Property 13: Translation Reuse Across Modules**
        **Validates: Requirements 9.5**
        """
        # 确保条目名称有效
        assume(entry_name.strip())
        assume(translation_name.strip())
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            source_dir = temp_dir / "en-US"
            target_dir = temp_dir / "zh_Hans"
            source_dir.mkdir(exist_ok=True)
            target_dir.mkdir(exist_ok=True)
            
            # 创建两个模块的源文件，包含相同的条目
            source_entry = {"name": entry_name, "description": "Original description"}
            
            module1_source = {"entries": {entry_name: source_entry}}
            module2_source = {"entries": {entry_name: source_entry}}
            
            (source_dir / "module1.comp.json").write_text(
                json.dumps(module1_source, ensure_ascii=False), encoding='utf-8'
            )
            (source_dir / "module2.comp.json").write_text(
                json.dumps(module2_source, ensure_ascii=False), encoding='utf-8'
            )
            
            # 在 module1 中创建翻译
            translation = {
                "name": translation_name,
                "description": translation_desc
            }
            module1_target = {"entries": {entry_name: translation}}
            
            (target_dir / "module1.comp.json").write_text(
                json.dumps(module1_target, ensure_ascii=False), encoding='utf-8'
            )
            (target_dir / "module2.comp.json").write_text(
                '{"entries": {}}', encoding='utf-8'
            )
            
            manager = MultiModuleManager(str(temp_dir))
            
            # Property: 如果内容在一个模块中已翻译，应该可以在其他模块中复用
            result = manager.find_translation(entry_name, exclude_module="module2")
            
            # 验证翻译可以被找到
            assert result is not None, f"Translation for '{entry_name}' should be found"
            
            found_module, found_compendium, found_translation = result
            assert found_module == "module1"
            assert found_translation["name"] == translation_name
            
            # 验证可以复用到 module2
            reuse = manager.reuse_translation(entry_name, "module2", "comp")
            assert reuse is not None, f"Should be able to reuse translation for '{entry_name}'"
            assert reuse.source_module == "module1"
            assert reuse.target_module == "module2"
            assert reuse.translation["name"] == translation_name
            
            # 验证应用复用后翻译被正确写入
            success = manager.apply_translation_reuse(reuse)
            assert success, "Translation reuse should be applied successfully"
            
            # 验证目标文件中的翻译
            with open(target_dir / "module2.comp.json", 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert entry_name in data["entries"]
                assert data["entries"][entry_name]["name"] == translation_name
    
    @given(
        entry_names=st.lists(
            entry_name_strategy,
            min_size=1,
            max_size=5,
            unique=True
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_shared_content_detection(self, entry_names):
        """
        Property: 共享内容检测准确性
        
        For any set of entries that appear in multiple modules, the system
        SHALL correctly detect them as shared content.
        
        **Feature: translation-automation-workflow, Property 13: Translation Reuse Across Modules**
        **Validates: Requirements 9.5**
        """
        # 过滤有效的条目名称
        valid_names = [n for n in entry_names if n.strip()]
        assume(len(valid_names) >= 1)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            source_dir = temp_dir / "en-US"
            source_dir.mkdir(exist_ok=True)
            
            # 创建两个模块，共享部分条目
            shared_entries = valid_names[:max(1, len(valid_names) // 2)]
            unique_entries_m1 = valid_names[len(shared_entries):]
            
            # Module 1: 共享条目 + 独有条目
            m1_entries = {name: {"name": name} for name in shared_entries + unique_entries_m1}
            (source_dir / "module1.comp.json").write_text(
                json.dumps({"entries": m1_entries}, ensure_ascii=False), encoding='utf-8'
            )
            
            # Module 2: 只有共享条目
            m2_entries = {name: {"name": name} for name in shared_entries}
            (source_dir / "module2.comp.json").write_text(
                json.dumps({"entries": m2_entries}, ensure_ascii=False), encoding='utf-8'
            )
            
            manager = MultiModuleManager(str(temp_dir))
            shared = manager.detect_shared_content()
            
            shared_names = {sc.entry_name for sc in shared}
            
            # Property: 所有共享条目都应该被检测到
            for name in shared_entries:
                assert name in shared_names, f"Shared entry '{name}' should be detected"
            
            # Property: 独有条目不应该被标记为共享
            for name in unique_entries_m1:
                assert name not in shared_names, f"Unique entry '{name}' should not be shared"


@pytest.fixture
def temp_dir(tmp_path):
    """创建临时目录用于测试"""
    return tmp_path
