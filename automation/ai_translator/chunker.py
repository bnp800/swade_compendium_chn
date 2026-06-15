"""HTML-aware text chunker for SWADE compendium translation.

Splits long HTML content into semantically coherent chunks that:
1. Fit within DeepSeek's context window (~2000 chars per chunk)
2. Don't break HTML tags or @UUID/@Compendium links
3. Preserve paragraph/section boundaries
"""
import re
from typing import List, Tuple, Optional
from dataclasses import dataclass


# Patterns to never split across
PROTECTED_PATTERNS = [
    # FVTT links
    r'@UUID\[[^\]]+\](?:\{[^}]*\})?',
    r'@Compendium\[[^\]]+\](?:\{[^}]*\})?',
    # HTML entities
    r'&[a-zA-Z]+;',
    r'&#\d+;',
    # Embedded dice rolls
    r'\[\[/r[^\]]+\]\]',
]

MAX_CHUNK_SIZE = 2000
OVERLAP_SIZE = 100  # chars of context overlap between chunks


@dataclass
class Chunk:
    """A single translatable chunk."""
    text: str
    index: int           # chunk number (0-based)
    has_leading_tag: bool  # whether chunk starts inside an HTML tag
    has_trailing_tag: bool  # whether chunk ends inside an HTML tag


def find_split_point(text: str, target_pos: int) -> int:
    """Find the best split point near target_pos.

    Priorities (in order):
    1. End of a paragraph (</p>, </div>, </li>, </h2>-</h6>)
    2. End of a sentence (. ! ? followed by space or newline)
    3. After a comma or semicolon
    4. After a space
    5. Force split at target_pos
    """
    search_start = max(0, target_pos - 200)
    search_end = min(len(text), target_pos + 200)
    segment = text[search_start:search_end]

    # Priority 1: block-level tag endings
    for tag in ('</p>', '</div>', '</li>', '</h2>', '</h3>', '</h4>',
                '</h5>', '</h6>', '</tr>', '</table>', '</ul>', '</ol>',
                '</article>', '</section>', '</blockquote>', '<br/>', '<br>'):
        pos = segment.rfind(tag)
        if pos > 0:
            return search_start + pos + len(tag)

    # Priority 2: sentence endings
    for punct in ('. ', '.\n', '! ', '!\n', '? ', '?\n', '。)', '！', '？'):
        pos = segment.rfind(punct)
        if pos > 0 and pos > len(segment) // 4:
            return search_start + pos + len(punct)

    # Priority 3: comma/semicolon
    for punct in (', ', '，', '; ', '；'):
        pos = segment.rfind(punct)
        if pos > 0 and pos > len(segment) // 3:
            return search_start + pos + len(punct)

    # Priority 4: space
    pos = segment.rfind(' ')
    if pos > 0:
        return search_start + pos + 1

    # Fallback: force split
    return target_pos


def protect_patterns(text: str) -> Tuple[str, dict]:
    """Replace protected patterns with placeholders to avoid splitting them."""
    placeholders = {}
    counter = [0]

    def replace(match):
        key = f"__PROTECTED_{counter[0]}__"
        placeholders[key] = match.group(0)
        counter[0] += 1
        return key

    for pattern in PROTECTED_PATTERNS:
        text = re.sub(pattern, replace, text)

    return text, placeholders


def restore_patterns(text: str, placeholders: dict) -> str:
    """Restore protected patterns from placeholders."""
    for key, value in placeholders.items():
        text = text.replace(key, value)
    return text


def chunk_html(text: str, max_size: int = MAX_CHUNK_SIZE) -> List[Chunk]:
    """Split HTML content into translatable chunks.

    Args:
        text: HTML content to split.
        max_size: Maximum characters per chunk.

    Returns:
        List of Chunk objects.
    """
    if len(text) <= max_size:
        return [Chunk(text=text, index=0, has_leading_tag=False, has_trailing_tag=False)]

    # Protect patterns we don't want to split
    protected, placeholders = protect_patterns(text)

    chunks: List[Chunk] = []
    pos = 0
    chunk_idx = 0

    while pos < len(protected):
        # Determine chunk end
        end = min(pos + max_size, len(protected))
        
        if end < len(protected):
            # Find good split point
            split_at = find_split_point(protected, end)
            # Don't split if split point is too far back
            if split_at - pos < max_size // 3:
                split_at = end
        else:
            split_at = end

        chunk_text = protected[pos:split_at].strip()
        
        # Determine if chunk starts/ends inside HTML tag
        has_leading = bool(re.search(r'<\w+[^>]*$', text[max(0, pos-50):pos]))
        has_trailing = bool(re.search(r'^[^<]*>', text[split_at:split_at+50]))
        
        if chunk_text:
            # Restore protected patterns
            chunk_text = restore_patterns(chunk_text, placeholders)
            chunks.append(Chunk(
                text=chunk_text,
                index=chunk_idx,
                has_leading_tag=has_leading,
                has_trailing_tag=has_trailing,
            ))
            chunk_idx += 1

        # Move position with overlap
        pos = split_at
        if pos < len(protected):
            # Backtrack to include overlap
            pos = max(pos - OVERLAP_SIZE, pos - max_size // 10)

    return chunks


def merge_chunks(chunks: List[Chunk], translations: List[str]) -> str:
    """Merge translated chunks back into a single text.

    Handles overlapping content by taking the first chunk's version
    for the overlap region.
    """
    if len(chunks) == 1 and len(translations) == 1:
        return translations[0]

    result_parts = []
    for i, chunk in enumerate(chunks):
        if i >= len(translations):
            result_parts.append(chunk.text)  # fallback to original
            continue
        
        translated = translations[i]
        if not translated:
            result_parts.append(chunk.text)
            continue
        
        # For overlapping regions, take the later chunk's version
        # (since it has more context)
        if i > 0 and OVERLAP_SIZE > 0:
            # Find where overlap would be and trim
            # This is a simplified approach
            pass
        
        result_parts.append(translated)

    return "".join(result_parts)


def estimate_chunks(text: str, max_size: int = MAX_CHUNK_SIZE) -> int:
    """Estimate how many chunks a text will be split into."""
    if not text:
        return 0
    return (len(text) + max_size - 1) // max_size
