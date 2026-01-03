"""术语管理器测试

包含单元测试和属性测试，验证 GlossaryManager 的正确性。
"""

import json
import pytest
from hypothesis import given, strategies as st, settings, assume
from pathlib import Path

from automation.glossary_manager import GlossaryManager


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_glossary_file(tmp_path):
    """创建临时术语表文件"""
    glossary_data = {
        "Vigor": "活力",
        "Spirit": "心魂",
        "Smarts": "聪慧",
        "Agility": "灵巧",
        "Strength": "力量",
        "Edge": "专长",
        "Hindrance": "负赘",
        "Power": "奇术",
        "Wild Card": "不羁角色",
        "Arcane Background": "奥法背景"
    }
    filepath = tmp_path / "test-glossary.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(glossary_data, f, ensure_ascii=False, indent=2)
    return filepath


@pytest.fixture
def glossary_manager(temp_glossary_file):
    """创建 GlossaryManager 实例"""
    return GlossaryManager(str(temp_glossary_file))


@pytest.fixture
def real_glossary_manager():
    """使用真实术语表的 GlossaryManager"""
    glossary_path = Path(__file__).parent.parent.parent / "glossary" / "swade-glossary.json"
    if glossary_path.exists():
        return GlossaryManager(str(glossary_path))
    return None


# ============================================================================
# Unit Tests
# ============================================================================

class TestGlossaryManagerBasic:
    """基本功能单元测试"""
    
    def test_load_glossary(self, glossary_manager):
        """测试术语表加载"""
        assert len(glossary_manager) == 10
        assert "Vigor" in glossary_manager
        assert glossary_manager.get_translation("Vigor") == "活力"
    
    def test_load_nonexistent_file(self, tmp_path):
        """测试加载不存在的文件"""
        gm = GlossaryManager(str(tmp_path / "nonexistent.json"))
        assert len(gm) == 0
    
    def test_apply_glossary_simple(self, glossary_manager):
        """测试简单术语替换"""
        text = "The character has high Vigor."
        result = glossary_manager.apply_glossary(text)
        assert "活力" in result
        assert "Vigor" not in result
    
    def test_apply_glossary_multiple_terms(self, glossary_manager):
        """测试多个术语替换"""
        text = "Vigor and Strength are important attributes."
        result = glossary_manager.apply_glossary(text)
        assert "活力" in result
        assert "力量" in result
    
    def test_apply_glossary_case_insensitive(self, glossary_manager):
        """测试大小写不敏感匹配"""
        text = "VIGOR is important. vigor matters."
        result = glossary_manager.apply_glossary(text)
        # 应该替换所有大小写变体
        assert result.count("活力") == 2
    
    def test_apply_glossary_word_boundary(self, glossary_manager):
        """测试单词边界匹配"""
        text = "Vigorous exercise is good."  # Vigorous 不应被替换
        result = glossary_manager.apply_glossary(text)
        assert "Vigorous" in result  # 保持原样
    
    def test_apply_glossary_long_term_priority(self, glossary_manager):
        """测试长术语优先匹配"""
        text = "Arcane Background is required."
        result = glossary_manager.apply_glossary(text)
        assert "奥法背景" in result
    
    def test_apply_glossary_empty_text(self, glossary_manager):
        """测试空文本"""
        assert glossary_manager.apply_glossary("") == ""
        assert glossary_manager.apply_glossary(None) is None
    
    def test_apply_glossary_with_tracking(self, glossary_manager):
        """测试带追踪的术语替换"""
        text = "Vigor and Vigor again, plus Strength."
        result, replacements = glossary_manager.apply_glossary_with_tracking(text)
        assert "活力" in result
        assert replacements.get("Vigor", 0) == 2
        assert replacements.get("Strength", 0) == 1


class TestGlossaryManagerUpdate:
    """术语表更新测试"""
    
    def test_update_glossary(self, glossary_manager):
        """测试添加新术语"""
        glossary_manager.update_glossary("NewTerm", "新术语")
        assert glossary_manager.get_translation("NewTerm") == "新术语"
    
    def test_update_glossary_overwrite(self, glossary_manager):
        """测试覆盖已有术语"""
        glossary_manager.update_glossary("Vigor", "新活力")
        assert glossary_manager.get_translation("Vigor") == "新活力"
    
    def test_update_glossary_empty_term(self, glossary_manager):
        """测试空术语"""
        with pytest.raises(ValueError):
            glossary_manager.update_glossary("", "翻译")
    
    def test_batch_update_glossary(self, glossary_manager):
        """测试批量更新"""
        updates = {
            "Term1": "术语1",
            "Term2": "术语2",
            "Term3": "术语3"
        }
        count = glossary_manager.batch_update_glossary(updates)
        assert count == 3
        assert glossary_manager.get_translation("Term1") == "术语1"
    
    def test_remove_term(self, glossary_manager):
        """测试移除术语"""
        assert glossary_manager.remove_term("Vigor")
        assert "Vigor" not in glossary_manager
        assert not glossary_manager.remove_term("NonExistent")


class TestGlossaryManagerMissingTerms:
    """未知术语检测测试"""
    
    def test_find_missing_terms_capitalized(self, glossary_manager):
        """测试检测首字母大写的未知术语"""
        text = "The Paladin has high Vigor."
        missing = glossary_manager.find_missing_terms(text)
        assert "Paladin" in missing
        assert "Vigor" not in missing  # Vigor 在术语表中
    
    def test_find_missing_terms_acronym(self, glossary_manager):
        """测试检测缩写词"""
        text = "The NPC has high HP."
        missing = glossary_manager.find_missing_terms(text)
        assert "NPC" in missing or "HP" in missing
    
    def test_find_missing_terms_empty(self, glossary_manager):
        """测试空文本"""
        assert glossary_manager.find_missing_terms("") == []
    
    def test_suggest_translations(self, glossary_manager):
        """测试翻译建议"""
        suggestions = glossary_manager.suggest_translations("Vigor")
        assert len(suggestions) > 0
        assert "活力" in suggestions[0]


# ============================================================================
# Property-Based Tests
# ============================================================================

import tempfile
import re as regex_module

# 生成有效的术语（英文单词）
term_strategy = st.text(
    alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"),
    min_size=2,
    max_size=20
).filter(lambda x: x[0].isupper() if x else False)

# 生成有效的翻译（中文字符）
translation_strategy = st.text(
    alphabet=st.sampled_from("的一是不了在人有我他这为之大来以个中上们到说国和地也子时道出而要于就下得可你年生自会那后能对着事其里所去行过家十用发天如然作方成者多日都三小军二无同主经公此已工使情明性知全长党面看定见只从现因开些门很起海门"),
    min_size=1,
    max_size=10
)


class TestGlossaryApplicationConsistency:
    """
    Property 4: Glossary Application Consistency
    
    *For any* text containing terms from the glossary, applying the glossary 
    SHALL replace all occurrences of each term with its translation, and the 
    result SHALL be consistent (same term always maps to same translation).
    
    **Validates: Requirements 3.1, 3.4, 7.5**
    """
    
    @pytest.mark.property
    @settings(max_examples=100, deadline=5000)
    @given(
        terms=st.lists(term_strategy, min_size=1, max_size=5, unique=True),
        translations=st.lists(translation_strategy, min_size=1, max_size=5)
    )
    def test_glossary_consistency_property(self, terms, translations):
        """
        Property: 术语应用一致性
        
        对于任意术语表和包含这些术语的文本，应用术语表后：
        1. 同一术语的所有出现都被替换为相同的翻译
        2. 替换是确定性的（多次应用结果相同）
        
        **Feature: translation-automation-workflow, Property 4: Glossary Application Consistency**
        **Validates: Requirements 3.1, 3.4, 7.5**
        """
        # 确保 terms 和 translations 长度匹配
        min_len = min(len(terms), len(translations))
        assume(min_len > 0)
        terms = terms[:min_len]
        translations = translations[:min_len]
        
        # 过滤掉空术语和空翻译
        valid_pairs = [(t, tr) for t, tr in zip(terms, translations) if t and tr]
        assume(len(valid_pairs) > 0)
        
        # 创建术语表
        glossary_data = {t: tr for t, tr in valid_pairs}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(glossary_data, f, ensure_ascii=False)
            glossary_file = f.name
        
        try:
            gm = GlossaryManager(glossary_file)
            
            # 构建包含术语的测试文本
            test_terms = list(glossary_data.keys())
            text = f"The {test_terms[0]} is important. Another {test_terms[0]} here."
            
            # 应用术语表
            result1 = gm.apply_glossary(text)
            result2 = gm.apply_glossary(text)
            
            # 属性1: 确定性 - 多次应用结果相同
            assert result1 == result2, "Glossary application should be deterministic"
            
            # 属性2: 一致性 - 同一术语的所有出现都被替换为相同翻译
            expected_translation = glossary_data[test_terms[0]]
            # 计算翻译出现次数
            translation_count = result1.count(expected_translation)
            # 原文中术语出现2次，翻译后应该有2次翻译
            assert translation_count == 2, f"All occurrences should be replaced consistently"
        finally:
            import os
            os.unlink(glossary_file)
    
    @pytest.mark.property
    @settings(max_examples=100, deadline=5000)
    @given(
        term=term_strategy,
        translation=translation_strategy,
        repeat_count=st.integers(min_value=1, max_value=5)
    )
    def test_all_occurrences_replaced(self, term, translation, repeat_count):
        """
        Property: 所有出现都被替换
        
        对于任意术语，文本中该术语的所有出现都应被替换。
        
        **Feature: translation-automation-workflow, Property 4: Glossary Application Consistency**
        **Validates: Requirements 3.1, 3.4, 7.5**
        """
        assume(term and translation)
        assume(len(term) >= 2)
        
        # 创建术语表
        glossary_data = {term: translation}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(glossary_data, f, ensure_ascii=False)
            glossary_file = f.name
        
        try:
            gm = GlossaryManager(glossary_file)
            
            # 构建包含多次术语的文本
            text = " ".join([f"The {term} is here."] * repeat_count)
            
            # 应用术语表
            result = gm.apply_glossary(text)
            
            # 验证：原术语不应出现在结果中（大小写不敏感）
            pattern = rf'\b{regex_module.escape(term)}\b'
            remaining_matches = regex_module.findall(pattern, result, regex_module.IGNORECASE)
            assert len(remaining_matches) == 0, f"Term '{term}' should be fully replaced"
            
            # 验证：翻译应出现正确次数
            assert result.count(translation) == repeat_count, \
                f"Translation should appear {repeat_count} times"
        finally:
            import os
            os.unlink(glossary_file)
    
    @pytest.mark.property
    @settings(max_examples=100, deadline=5000)
    @given(
        terms=st.lists(term_strategy, min_size=2, max_size=5, unique=True),
        translations=st.lists(translation_strategy, min_size=2, max_size=5)
    )
    def test_no_cross_contamination(self, terms, translations):
        """
        Property: 术语替换不会相互干扰
        
        多个术语的替换应该独立进行，不会相互影响。
        
        **Feature: translation-automation-workflow, Property 4: Glossary Application Consistency**
        **Validates: Requirements 3.1, 3.4, 7.5**
        """
        min_len = min(len(terms), len(translations))
        assume(min_len >= 2)
        terms = terms[:min_len]
        translations = translations[:min_len]
        
        # 过滤掉空值和确保术语不是彼此的子串
        valid_pairs = [(t, tr) for t, tr in zip(terms, translations) if t and tr and len(t) >= 2]
        assume(len(valid_pairs) >= 2)
        
        # 确保术语之间不是子串关系
        for i, (t1, _) in enumerate(valid_pairs):
            for j, (t2, _) in enumerate(valid_pairs):
                if i != j:
                    assume(t1.lower() not in t2.lower() and t2.lower() not in t1.lower())
        
        # 创建术语表
        glossary_data = {t: tr for t, tr in valid_pairs}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(glossary_data, f, ensure_ascii=False)
            glossary_file = f.name
        
        try:
            gm = GlossaryManager(glossary_file)
            
            # 构建包含所有术语的文本
            term_list = list(glossary_data.keys())
            text = " and ".join([f"The {t}" for t in term_list])
            
            # 应用术语表
            result = gm.apply_glossary(text)
            
            # 验证每个翻译都出现了
            for term, translation in glossary_data.items():
                assert translation in result, f"Translation '{translation}' for '{term}' should be in result"
        finally:
            import os
            os.unlink(glossary_file)



class TestGlossaryManagerAdvanced:
    """高级功能测试"""
    
    def test_update_translations_for_term(self, glossary_manager, tmp_path):
        """测试批量更新翻译文件"""
        # 创建测试翻译文件
        translation_file = tmp_path / "translations" / "test.json"
        translation_file.parent.mkdir(parents=True, exist_ok=True)
        
        content = {
            "entries": {
                "Test Entry": {
                    "name": "测试条目",
                    "description": "这个条目需要高活力。活力很重要。"
                }
            }
        }
        with open(translation_file, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        
        # 更新术语
        result = glossary_manager.update_translations_for_term(
            "Vigor", "活力", "新活力", str(tmp_path / "translations")
        )
        
        assert len(result.updated_files) == 1
        assert result.updated_entries == 2  # 两处 "活力"
        
        # 验证文件内容已更新
        with open(translation_file, 'r', encoding='utf-8') as f:
            updated_content = f.read()
        assert "新活力" in updated_content
        assert "活力" not in updated_content or "新活力" in updated_content
    
    def test_update_term_and_translations(self, glossary_manager, tmp_path):
        """测试同时更新术语表和翻译文件"""
        # 创建测试翻译文件
        translation_file = tmp_path / "translations" / "test.json"
        translation_file.parent.mkdir(parents=True, exist_ok=True)
        
        content = {"text": "需要高活力"}
        with open(translation_file, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False)
        
        # 更新术语和翻译
        result = glossary_manager.update_term_and_translations(
            "Vigor", "新活力", str(tmp_path / "translations")
        )
        
        # 验证术语表已更新
        assert glossary_manager.get_translation("Vigor") == "新活力"
        
        # 验证翻译文件已更新
        assert len(result.updated_files) == 1
    
    def test_generate_missing_terms_report(self, glossary_manager):
        """测试生成未知术语报告"""
        text = "The Paladin has high Vigor."
        report = glossary_manager.generate_missing_terms_report(text)
        
        assert "# 未知术语报告" in report
        assert "Paladin" in report
    
    def test_export_glossary_json(self, glossary_manager, tmp_path):
        """测试导出 JSON 格式"""
        output_path = tmp_path / "export.json"
        glossary_manager.export_glossary(str(output_path), "json")
        
        assert output_path.exists()
        with open(output_path, 'r', encoding='utf-8') as f:
            exported = json.load(f)
        assert "Vigor" in exported
    
    def test_export_glossary_csv(self, glossary_manager, tmp_path):
        """测试导出 CSV 格式"""
        output_path = tmp_path / "export.csv"
        glossary_manager.export_glossary(str(output_path), "csv")
        
        assert output_path.exists()
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "Vigor" in content
        assert "活力" in content
    
    def test_export_glossary_md(self, glossary_manager, tmp_path):
        """测试导出 Markdown 格式"""
        output_path = tmp_path / "export.md"
        glossary_manager.export_glossary(str(output_path), "md")
        
        assert output_path.exists()
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "| Vigor | 活力 |" in content
    
    def test_import_glossary_json(self, tmp_path):
        """测试导入 JSON 格式"""
        # 创建导入文件
        import_file = tmp_path / "import.json"
        import_data = {"NewTerm1": "新术语1", "NewTerm2": "新术语2"}
        with open(import_file, 'w', encoding='utf-8') as f:
            json.dump(import_data, f, ensure_ascii=False)
        
        # 创建空术语表
        glossary_file = tmp_path / "glossary.json"
        with open(glossary_file, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        
        gm = GlossaryManager(str(glossary_file))
        count = gm.import_glossary(str(import_file))
        
        assert count == 2
        assert gm.get_translation("NewTerm1") == "新术语1"
    
    def test_import_glossary_csv(self, tmp_path):
        """测试导入 CSV 格式"""
        import csv
        
        # 创建导入文件
        import_file = tmp_path / "import.csv"
        with open(import_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["English", "Chinese"])
            writer.writerow(["Term1", "术语1"])
            writer.writerow(["Term2", "术语2"])
        
        # 创建空术语表
        glossary_file = tmp_path / "glossary.json"
        with open(glossary_file, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        
        gm = GlossaryManager(str(glossary_file))
        count = gm.import_glossary(str(import_file))
        
        assert count == 2
        assert gm.get_translation("Term1") == "术语1"
