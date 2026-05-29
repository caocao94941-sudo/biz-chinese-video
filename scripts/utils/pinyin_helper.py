"""Pinyin utilities for biz-chinese-video project."""

import re
from pypinyin import pinyin, Style


def to_pinyin(text: str, style: Style = Style.TONE) -> str:
    """Convert Chinese text to pinyin with tone marks.

    Args:
        text: Chinese text
        style: pypinyin style (TONE for marks, TONE3 for numbers)

    Returns:
        Pinyin string with spaces between syllables
    """
    result = pinyin(text, style=style, errors="default")
    return " ".join([item[0] for item in result])


def to_pinyin_preserve_non_chinese(text: str) -> str:
    """Convert Chinese characters to pinyin while preserving non-Chinese characters.

    Handles mixed text like "我在北京工作。" → "Wǒ zài Běijīng gōngzuò."
    """
    output = []
    i = 0
    while i < len(text):
        char = text[i]
        if _is_chinese_char(char):
            # Collect consecutive Chinese characters
            start = i
            while i < len(text) and _is_chinese_char(text[i]):
                i += 1
            chunk = text[start:i]
            py = pinyin(chunk, style=Style.TONE, errors="default")
            output.append(" ".join([p[0] for p in py]))
        else:
            output.append(char)
            i += 1
    return "".join(output)


def highlight_pinyin(text_zh: str, text_pinyin: str, highlight_words: list[str]) -> str:
    """Generate HTML with highlighted words in both Chinese and pinyin.

    Returns HTML string with <mark> tags around highlighted words.
    """
    result = text_zh
    for word in highlight_words:
        result = result.replace(word, f"<mark>{word}</mark>")
    return result


def _is_chinese_char(char: str) -> bool:
    """Check if a character is a CJK unified ideograph."""
    cp = ord(char)
    return (
        (0x4E00 <= cp <= 0x9FFF)
        or (0x3400 <= cp <= 0x4DBF)
        or (0x20000 <= cp <= 0x2A6DF)
        or (0x2A700 <= cp <= 0x2B73F)
        or (0x2B740 <= cp <= 0x2B81F)
        or (0x2B820 <= cp <= 0x2CEAF)
        or (0xF900 <= cp <= 0xFAFF)
        or (0x2F800 <= cp <= 0x2FA1F)
    )


def capitalize_pinyin(pinyin_str: str) -> str:
    """Capitalize the first letter of a pinyin string (for sentence start)."""
    if not pinyin_str:
        return pinyin_str
    return pinyin_str[0].upper() + pinyin_str[1:]
