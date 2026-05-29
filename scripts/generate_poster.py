#!/usr/bin/env python3
"""Generate poster frames from lesson data using Playwright + HTML templates.

Each sentence produces one frame. The frame shows:
- Topic banner with lesson title
- Hero image
- Current sentence (highlighted)
- Vocabulary panel
- Grammar panel (cycles through grammar points)
- Business tip

Usage:
    python scripts/generate_poster.py --lesson-id 1 --output-dir output/2026-05-28
    python scripts/generate_poster.py --lesson-id 1 --format vertical
    python scripts/generate_poster.py --lesson-id 1 --format both
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from dataclasses import asdict

from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.utils.db_helper import (
    get_connection, get_full_lesson_data,
    get_vocabulary_up_to_sentence, get_grammar_up_to_sentence,
    ASSETS_DIR, OUTPUT_DIR, TEMPLATES_DIR
)
from scripts.utils.pinyin_helper import highlight_pinyin


# Template dimensions
DIMENSIONS = {
    "vertical": (1080, 1920),
    "horizontal": (1920, 1080),
}


def build_template_context(
    lesson_data: dict,
    sentence_idx: int,
    conn=None,
) -> dict:
    """Build Jinja2 template context for a specific sentence frame.

    Vocabulary and grammar are progressively accumulated:
    only items whose first_appear_sentence <= current sentence are shown.
    """
    lesson = lesson_data["lesson"]
    sentences = lesson_data["sentences"]

    current = sentences[sentence_idx]
    current_order = current.sort_order

    # Build highlighted HTML for current sentence
    current_html = highlight_pinyin(current.text_zh, current.text_pinyin, current.highlight_words)

    # Progressive accumulation: only show vocab/grammar up to current sentence
    if conn:
        vocabulary = get_vocabulary_up_to_sentence(conn, lesson.id, current_order)
        grammar_points = get_grammar_up_to_sentence(conn, lesson.id, current_order)
    else:
        vocabulary = [v for v in lesson_data["vocabulary"] if v.first_appear_sentence <= current_order]
        grammar_points = [g for g in lesson_data["grammar"] if g.first_appear_sentence <= current_order]

    # Newly appeared items (for highlighting in template)
    new_vocab = [v for v in vocabulary if v.first_appear_sentence == current_order]
    new_grammar = [g for g in grammar_points if g.first_appear_sentence == current_order]

    # Show the latest grammar point in detail
    current_grammar = grammar_points[-1] if grammar_points else None

    # Topic image path
    topic_image_path = None
    if lesson.topic_image:
        img_path = ASSETS_DIR / "images" / "topics" / lesson.topic_image
        if img_path.exists():
            topic_image_path = str(img_path)

    return {
        "lesson": lesson,
        "sentences": sentences,
        "current_sentence": current,
        "current_sentence_html": current_html,
        "vocabulary": vocabulary,
        "new_vocab": new_vocab,
        "grammar_points": grammar_points,
        "new_grammar": new_grammar,
        "current_grammar": current_grammar,
        "topic_image_path": topic_image_path,
        "sentence_idx": sentence_idx,
        "total_sentences": len(sentences),
    }


async def render_frame(
    page,
    html_content: str,
    output_path: Path,
    width: int,
    height: int,
):
    """Render HTML to PNG using Playwright."""
    await page.set_content(html_content, wait_until="networkidle")
    await page.set_viewport_size({"width": width, "height": height})
    await page.screenshot(path=str(output_path), full_page=False)


async def generate_frames(
    lesson_id: int,
    output_dir: Path,
    video_format: str = "both",
    db_path: str = None,
):
    """Generate all poster frames for a lesson.

    Args:
        lesson_id: Lesson ID in database
        output_dir: Output directory for frames
        video_format: 'vertical', 'horizontal', or 'both'
        db_path: Optional database path override
    """
    conn = get_connection(db_path)
    lesson_data = get_full_lesson_data(conn, lesson_id)

    if not lesson_data:
        print(f"ERROR: Lesson {lesson_id} not found")
        conn.close()
        return []

    sentences = lesson_data["sentences"]
    print(f"Generating {len(sentences)} frames for: {lesson_data['lesson'].title_zh}")

    # Setup Jinja2
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

    formats_to_render = []
    if video_format in ("vertical", "both"):
        formats_to_render.append("vertical")
    if video_format in ("horizontal", "both"):
        formats_to_render.append("horizontal")

    all_frame_paths = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for fmt in formats_to_render:
            template = env.get_template(f"poster_{fmt}.html")
            width, height = DIMENSIONS[fmt]

            fmt_dir = output_dir / f"frames_{fmt}"
            fmt_dir.mkdir(parents=True, exist_ok=True)

            frame_paths = []

            page = await browser.new_page()
            await page.set_viewport_size({"width": width, "height": height})

            for i, sentence in enumerate(sentences):
                ctx = build_template_context(lesson_data, i, conn=conn)
                ctx_render = {
                    "lesson": ctx["lesson"],
                    "sentences": ctx["sentences"],
                    "current_sentence": ctx["current_sentence"],
                    "current_sentence_html": ctx["current_sentence_html"],
                    "vocabulary": ctx["vocabulary"],
                    "new_vocab": ctx["new_vocab"],
                    "grammar_points": ctx["grammar_points"],
                    "new_grammar": ctx["new_grammar"],
                    "current_grammar": ctx["current_grammar"],
                    "topic_image_path": ctx["topic_image_path"],
                }
                html = template.render(**ctx_render)

                frame_path = fmt_dir / f"frame_{i+1:03d}.png"
                await render_frame(page, html, frame_path, width, height)
                frame_paths.append(frame_path)

                vocab_count = len(ctx["vocabulary"])
                new_count = len(ctx["new_vocab"])
                print(f"  [{fmt}] Frame {i+1}/{len(sentences)}: {sentence.text_zh[:20]}... (vocab: {vocab_count}, +{new_count} new)")

            await page.close()
            all_frame_paths[fmt] = frame_paths

        await browser.close()

    conn.close()
    return all_frame_paths


def main():
    parser = argparse.ArgumentParser(description="Generate poster frames")
    parser.add_argument("--lesson-id", type=int, default=1, help="Lesson ID")
    parser.add_argument("--output-dir", type=str, help="Output directory")
    parser.add_argument("--format", choices=["vertical", "horizontal", "both"], default="both")
    args = parser.parse_args()

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        from datetime import date
        output_dir = OUTPUT_DIR / date.today().isoformat()

    output_dir.mkdir(parents=True, exist_ok=True)

    frame_paths = asyncio.run(
        generate_frames(args.lesson_id, output_dir, args.format)
    )

    for fmt, paths in frame_paths.items():
        print(f"\n{fmt}: {len(paths)} frames generated in {output_dir}/frames_{fmt}/")


if __name__ == "__main__":
    main()
