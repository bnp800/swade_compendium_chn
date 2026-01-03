"""pytest 配置和共享 fixtures"""

import pytest
import json
import tempfile
from pathlib import Path


@pytest.fixture
def temp_dir():
    """创建临时目录用于测试"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_source_json():
    """示例源 JSON 数据"""
    return {
        "entries": {
            "Alertness": {
                "name": "Alertness",
                "description": "<p>Not easily surprised.</p>",
                "category": "Background"
            },
            "Ambidextrous": {
                "name": "Ambidextrous",
                "description": "<p>Ignore -2 penalty for off-hand.</p>",
                "category": "Background"
            }
        }
    }


@pytest.fixture
def sample_target_json():
    """示例目标 JSON 数据（已翻译）"""
    return {
        "entries": {
            "Alertness": {
                "name": "警觉",
                "description": "<p>不容易被突袭。</p>",
                "category": "背景"
            }
        }
    }


@pytest.fixture
def sample_glossary():
    """示例术语表"""
    return {
        "Edge": "专长",
        "Hindrance": "障碍",
        "Power": "异能",
        "Skill": "技能",
        "Attribute": "属性",
        "Vigor": "活力",
        "Spirit": "心魂",
        "Smarts": "灵巧",
        "Agility": "敏捷",
        "Strength": "力量"
    }


@pytest.fixture
def create_json_file(temp_dir):
    """创建 JSON 文件的工厂 fixture"""
    def _create(filename: str, content: dict) -> Path:
        filepath = temp_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        return filepath
    return _create
