#!/usr/bin/env python3
"""Generate poster frames using Pillow (no browser dependency).

Replaces the Playwright-based generate_poster.py to run on low-memory servers.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from dataclasses import asdict

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.utils.db_helper import (
    get_connection, get_full_lesson_data,
    get_vocabulary_up_to_sentence, get_grammar_up_to_sentence,
    ASSETS_DIR, OUTPUT_DIR, TEMPLATES_DIR,
)
from scripts.utils.pinyin_helper import highlight_pinyin

# --- Constants ---
DIMENSIONS = {"vertical": (1080, 1920), "horizontal": (1920, 1080)}

# Colors
BG_DARK = (10, 22, 40)
BLUE_PRIMARY = (37, 99, 235)
BLUE_LIGHT = (96, 165, 250)
YELLOW = (251, 191, 36)
WHITE = (255, 255, 255)
WHITE_70 = (255, 255, 255, 178)
WHITE_50 = (255, 255, 255, 128)
WHITE_30 = (255, 255, 255, 77)
CARD_BG = (15, 23, 42, 200)
CARD_BORDER = (59, 130, 246, 77)

# --- Font helpers ---
_font_cache = {}

def get_font(size, bold=False):
    """Load a CJK-capable font at given size."""
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    
    font_paths = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/unifont/unifont.otf",
    ]
    
    for fp in font_paths:
        if Path(fp).exists():
            try:
                font = ImageFont.truetype(fp, size)
                _font_cache[key] = font
                return font
            except Exception:
                continue
    
    font = ImageFont.load_default()
    _font_cache[key] = font
    return font


def draw_rounded_rect(draw, xy, radius, fill=None, outline=None, width=1):
    """Draw a rounded rectangle."""
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_text_wrapped(draw, text, x, y, max_width, font, fill=WHITE, line_spacing=8):
    """Draw text with word wrapping. Returns final y position."""
    if not text:
        return y
    chars = list(text)
    lines = []
    current = ""
    for ch in chars:
        test = current + ch
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(current)
            current = ch
        else:
            current = test
    if current:
        lines.append(current)
    
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        bbox = font.getbbox(line)
        y += (bbox[3] - bbox[1]) + line_spacing
    return y


# Placeholder for render functions - will be added incrementally
def render_frame_pillow(lesson_data, sentence_idx, width, height, output_path, conn=None):
    """Render a single poster frame using Pillow."""
    lesson = lesson_data["lesson"]
    sentences = lesson_data["sentences"]
    current = sentences[sentence_idx]
    current_order = current.sort_order

    # Progressive accumulation
    if conn:
        vocabulary = get_vocabulary_up_to_sentence(conn, lesson.id, current_order)
        grammar_points = get_grammar_up_to_sentence(conn, lesson.id, current_order)
    else:
        vocabulary = [v for v in lesson_data["vocabulary"] if v.first_appear_sentence <= current_order]
        grammar_points = [g for g in lesson_data["grammar"] if g.first_appear_sentence <= current_order]

    new_vocab = [v for v in vocabulary if v.first_appear_sentence == current_order]
    new_grammar = [g for g in grammar_points if g.first_appear_sentence == current_order]
    current_grammar = grammar_points[-1] if grammar_points else None

    is_vertical = height > width
    img = Image.new("RGBA", (width, height), BG_DARK + (255,))
    draw = ImageDraw.Draw(img)

    # Decorative gradient circles
    _draw_bg_decoration(img, width, height)

    margin = 40
    content_w = width - margin * 2
    y = 32

    # 1. Topic banner
    y = _draw_topic_banner(draw, lesson, margin, y, content_w, is_vertical)

    # 2. Sentence card
    y = _draw_sentence_card(draw, current, margin, y, content_w, is_vertical)

    # 3. Progress dots
    y = _draw_progress_dots(draw, sentences, current_order, margin, y, content_w)

    if is_vertical:
        # Vertical: vocab and grammar side by side
        card_w = (content_w - 20) // 2
        card_y = y + 16
        _draw_vocab_card(draw, vocabulary, new_vocab, lesson, margin, card_y, card_w, is_vertical)
        _draw_grammar_card(draw, grammar_points, new_grammar, current_grammar, margin + card_w + 20, card_y, card_w, is_vertical)
        y = card_y + 420
    else:
        # Horizontal: sentence on left, vocab+grammar on right (already handled by layout)
        card_w = content_w
        y = _draw_vocab_card(draw, vocabulary, new_vocab, lesson, margin, y + 16, card_w, is_vertical)
        y = _draw_grammar_card(draw, grammar_points, new_grammar, current_grammar, margin, y + 12, card_w, is_vertical)

    # 4. Business tip
    _draw_business_tip(draw, lesson, margin, y + 16, content_w)

    img = img.convert("RGB")
    img.save(str(output_path), "PNG")


def _draw_bg_decoration(img, width, height):
    """Draw subtle gradient circles on background."""
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    # Top-right glow
    d.ellipse([width - 400, -200, width + 200, 400], fill=(59, 130, 246, 20))
    # Bottom-left glow
    d.ellipse([-100, height - 300, 300, height + 100], fill=(59, 130, 246, 15))
    img.paste(Image.alpha_composite(img, overlay))


def _draw_topic_banner(draw, lesson, x, y, w, is_vertical):
    """Draw the topic banner. Returns new y."""
    h = 100 if is_vertical else 80
    font_size = 36 if is_vertical else 28
    draw_rounded_rect(draw, (x, y, x + w, y + h), 20, fill=BLUE_PRIMARY)
    f_title = get_font(font_size, bold=True)
    f_pinyin = get_font(18)
    title_text = f"今日主题: {lesson.title_zh}"
    draw.text((x + 80, y + 14), title_text, font=f_title, fill=WHITE)
    draw.text((x + 80, y + 14 + font_size + 6), lesson.title_pinyin or "", font=f_pinyin, fill=WHITE_70)
    # Icon
    f_icon = get_font(28)
    draw.text((x + 24, y + (h - 28) // 2), "📅", font=f_icon, fill=WHITE)
    # HSK badge
    f_badge = get_font(16, bold=True)
    badge_text = lesson.hsk_level or "HSK1"
    bw = f_badge.getbbox(badge_text)[2] + 20
    draw_rounded_rect(draw, (x + w - bw - 10, y + 10, x + w - 10, y + 38), 8, fill=(30, 64, 175))
    draw.text((x + w - bw, y + 14), badge_text, font=f_badge, fill=WHITE)
    return y + h + 16


def _draw_sentence_card(draw, sentence, x, y, w, is_vertical):
    """Draw the current sentence card. Returns new y."""
    f_zh = get_font(34 if is_vertical else 28, bold=True)
    f_py = get_font(20 if is_vertical else 16)
    f_en = get_font(20 if is_vertical else 16)

    # Measure text heights
    zh_h = _text_height(draw, sentence.text_zh, f_zh, w - 60)
    py_h = _text_height(draw, sentence.text_pinyin, f_py, w - 60) if sentence.text_pinyin else 0
    en_h = _text_height(draw, sentence.text_en, f_en, w - 60) if sentence.text_en else 0
    card_h = zh_h + py_h + en_h + 60

    draw_rounded_rect(draw, (x, y, x + w, y + card_h), 20, fill=CARD_BG, outline=CARD_BORDER, width=1)

    ty = y + 20
    ty = draw_text_wrapped(draw, sentence.text_zh, x + 28, ty, w - 60, f_zh, fill=WHITE)
    ty = draw_text_wrapped(draw, sentence.text_pinyin, x + 28, ty + 4, w - 60, f_py, fill=WHITE_50)
    draw_text_wrapped(draw, sentence.text_en, x + 28, ty + 4, w - 60, f_en, fill=WHITE_70)

    return y + card_h + 8


def _text_height(draw, text, font, max_width):
    """Calculate wrapped text height."""
    if not text:
        return 0
    chars = list(text)
    lines = []
    current = ""
    for ch in chars:
        test = current + ch
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(current)
            current = ch
        else:
            current = test
    if current:
        lines.append(current)
    line_h = font.getbbox("测")[3] + 8
    return line_h * len(lines)


def _draw_progress_dots(draw, sentences, current_order, x, y, w):
    """Draw sentence progress indicator dots. Returns new y."""
    total = len(sentences)
    dot_r = 5
    active_w = 14
    gap = 10
    total_w = (total - 1) * (dot_r * 2 + gap) + active_w * 2
    sx = x + (w - total_w) // 2
    dy = y + 8
    for s in sentences:
        if s.sort_order == current_order:
            draw.rounded_rectangle((sx, dy, sx + active_w * 2, dy + dot_r * 2), radius=dot_r, fill=BLUE_LIGHT)
            sx += active_w * 2 + gap
        else:
            draw.ellipse((sx, dy, sx + dot_r * 2, dy + dot_r * 2), fill=WHITE_30)
            sx += dot_r * 2 + gap
    return dy + dot_r * 2 + 8


def _draw_vocab_card(draw, vocabulary, new_vocab, lesson, x, y, w, is_vertical):
    """Draw vocabulary card. Returns new y."""
    f_header = get_font(20, bold=True)
    f_word = get_font(20, bold=True)
    f_detail = get_font(16)
    f_new = get_font(12, bold=True)

    item_h = 32
    max_items = 6 if is_vertical else 4
    items = vocabulary[:max_items]
    card_h = 50 + max(len(items), 1) * item_h + 20

    draw_rounded_rect(draw, (x, y, x + w, y + card_h), 20, fill=CARD_BG, outline=CARD_BORDER, width=1)

    # Header
    draw.text((x + 20, y + 14), f"📖 {lesson.hsk_level} 词汇 Vocabulary", font=f_header, fill=BLUE_LIGHT)
    count_text = str(len(vocabulary))
    draw.text((x + w - 40, y + 16), count_text, font=f_detail, fill=WHITE_50)

    iy = y + 50
    if not items:
        draw.text((x + 20, iy), "词汇将随课文逐步出现...", font=f_detail, fill=WHITE_30)
    else:
        for v in items:
            is_new = v in new_vocab
            color = YELLOW if is_new else WHITE
            draw.text((x + 20, iy), v.icon_emoji or "·", font=f_detail, fill=WHITE)
            draw.text((x + 52, iy), v.word_zh, font=f_word, fill=color)
            draw.text((x + 140, iy), v.word_pinyin, font=f_detail, fill=BLUE_LIGHT)
            draw.text((x + 280, iy), v.word_en[:20], font=f_detail, fill=WHITE_50)
            if is_new:
                draw_rounded_rect(draw, (x + w - 60, iy + 2, x + w - 16, iy + 22), 4, fill=YELLOW)
                draw.text((x + w - 56, iy + 3), "NEW", font=f_new, fill=(0, 0, 0))
            iy += item_h

    return y + card_h


def _draw_grammar_card(draw, grammar_points, new_grammar, current_grammar, x, y, w, is_vertical):
    """Draw grammar card. Returns new y."""
    f_header = get_font(20, bold=True)
    f_pattern = get_font(22, bold=True)
    f_detail = get_font(16)
    f_small = get_font(14)
    f_new = get_font(12, bold=True)

    card_h = 280 if is_vertical else 200

    draw_rounded_rect(draw, (x, y, x + w, y + card_h), 20, fill=CARD_BG, outline=CARD_BORDER, width=1)

    # Header
    draw.text((x + 20, y + 14), "💡 语法点 Grammar", font=f_header, fill=YELLOW)
    count_text = str(len(grammar_points))
    draw.text((x + w - 40, y + 16), count_text, font=f_detail, fill=WHITE_50)

    gy = y + 50
    if not current_grammar:
        draw.text((x + 20, gy), "语法点将随课文逐步出现...", font=f_detail, fill=WHITE_30)
    else:
        is_new = current_grammar in new_grammar
        # Pattern box
        box_h = 40
        box_color = (245, 158, 11, 46) if is_new else (245, 158, 11, 30)
        draw_rounded_rect(draw, (x + 16, gy, x + w - 16, gy + box_h), 10, fill=box_color)
        draw.text((x + 28, gy + 8), current_grammar.pattern_zh, font=f_pattern, fill=YELLOW)
        if is_new:
            draw_rounded_rect(draw, (x + w - 70, gy + 8, x + w - 26, gy + 28), 4, fill=YELLOW)
            draw.text((x + w - 66, gy + 9), "NEW", font=f_new, fill=(0, 0, 0))
        gy += box_h + 10

        # Explanation
        if current_grammar.explanation_zh:
            gy = draw_text_wrapped(draw, current_grammar.explanation_zh, x + 20, gy, w - 40, f_detail, fill=WHITE_70)
        # Example
        if current_grammar.example_zh:
            draw.text((x + 20, gy + 4), "例句：", font=f_small, fill=WHITE_30)
            gy += 22
            draw.text((x + 20, gy), current_grammar.example_zh, font=f_detail, fill=WHITE)
            gy += 24
            if current_grammar.example_en:
                draw.text((x + 20, gy), current_grammar.example_en[:40], font=f_small, fill=WHITE_50)

        # History
        if len(grammar_points) > 1:
            hy = y + card_h - 30 * min(len(grammar_points) - 1, 3) - 10
            for g in grammar_points[:-1][:3]:
                draw.text((x + 20, hy), f"✓ {g.pattern_zh}", font=f_small, fill=WHITE_30)
                hy += 24

    return y + card_h


def _draw_business_tip(draw, lesson, x, y, w):
    """Draw business tip section."""
    if not lesson.business_tip_zh:
        return
    f_title = get_font(20, bold=True)
    f_body = get_font(16)

    card_h = 100
    draw_rounded_rect(draw, (x, y, x + w, y + card_h), 20, fill=(37, 99, 235, 50), outline=CARD_BORDER, width=1)
    draw.text((x + 70, y + 14), "商务小贴士 Business Tip", font=f_title, fill=YELLOW)
    draw.text((x + 20, y + 18), "💼", font=get_font(24), fill=WHITE)
    draw_text_wrapped(draw, lesson.business_tip_zh, x + 70, y + 44, w - 90, f_body, fill=WHITE_70)


async def generate_frames(lesson_id, output_dir, video_format="both", db_path=None):
    """Generate all poster frames for a lesson."""
    conn = get_connection(db_path)
    lesson_data = get_full_lesson_data(conn, lesson_id)

    if not lesson_data:
        print(f"ERROR: Lesson {lesson_id} not found")
        conn.close()
        return {}

    sentences = lesson_data["sentences"]
    print(f"Generating {len(sentences)} frames for: {lesson_data['lesson'].title_zh}")

    formats_to_render = []
    if video_format in ("vertical", "both"):
        formats_to_render.append("vertical")
    if video_format in ("horizontal", "both"):
        formats_to_render.append("horizontal")

    all_frame_paths = {}

    for fmt in formats_to_render:
        width, height = DIMENSIONS[fmt]
        fmt_dir = output_dir / f"frames_{fmt}"
        fmt_dir.mkdir(parents=True, exist_ok=True)
        frame_paths = []

        for i, sentence in enumerate(sentences):
            frame_path = fmt_dir / f"frame_{i+1:03d}.png"
            render_frame_pillow(lesson_data, i, width, height, frame_path, conn=conn)
            frame_paths.append(frame_path)

            vocab_count = len([v for v in lesson_data["vocabulary"] if v.first_appear_sentence <= sentence.sort_order])
            print(f"  [{fmt}] Frame {i+1}/{len(sentences)}: {sentence.text_zh[:20]}... (vocab: {vocab_count})")

        all_frame_paths[fmt] = frame_paths

    conn.close()
    return all_frame_paths


def main():
    parser = argparse.ArgumentParser(description="Generate poster frames (Pillow)")
    parser.add_argument("--lesson-id", type=int, default=1)
    parser.add_argument("--output-dir", type=str)
    parser.add_argument("--format", choices=["vertical", "horizontal", "both"], default="both")
    args = parser.parse_args()

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        from datetime import date
        output_dir = OUTPUT_DIR / date.today().isoformat()
    output_dir.mkdir(parents=True, exist_ok=True)

    frame_paths = asyncio.run(generate_frames(args.lesson_id, output_dir, args.format))
    for fmt, paths in frame_paths.items():
        print(f"\n{fmt}: {len(paths)} frames generated")


if __name__ == "__main__":
    main()
