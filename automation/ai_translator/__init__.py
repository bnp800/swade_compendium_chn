"""AI-powered translation module for SWADE compendium content.

Uses DeepSeek v4 to automatically translate compendium entries
while preserving HTML structure, CSS classes, and FVTT hyperlinks.

Quick start:
    export DEEPSEEK_API_KEY=your_key
    python -m automation.ai_translator.translate_compendium \\
        en-US/swade-core-rules.swade-edges.json \\
        --output zh_Hans/swade-core-rules.swade-edges.json

Or translate a whole directory:
    python -m automation.ai_translator.translate_compendium \\
        --dir en-US/ --target zh_Hans/
"""

from .client import DeepSeekClient, create_client_from_env
from .translator import CompendiumTranslator, translate_directory
from .prompts import PromptBuilder, TranslationValidator
from .chunker import chunk_html, merge_chunks

__version__ = "0.1.0"
__all__ = [
    "DeepSeekClient",
    "create_client_from_env",
    "CompendiumTranslator",
    "translate_directory",
    "PromptBuilder",
    "TranslationValidator",
    "chunk_html",
    "merge_chunks",
]
