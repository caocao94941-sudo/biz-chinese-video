#!/usr/bin/env python3
"""Generate SRT subtitles from audio timing data.

Each subtitle block shows three lines: pinyin / Chinese / English.
Timestamps are derived from the TTS timing.json.

Usage:
    python scripts/generate_subtitles.py --output-dir output/2026-05-28
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.utils.db_helper import get_connection, get_sentences, OUTPUT_DIR


def ms_to_srt_time(ms: int) -> str:
    """Convert milliseconds to SRT timestamp format: HH:MM:SS,mmm"""
    hours = ms // 3600000
    ms %= 3600000
    minutes = ms // 60000
    ms %= 60000
    seconds = ms // 1000
    millis = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def generate_srt(
    output_dir: Path,
    sentence_gap_ms: int = 1500,
    db_path: str = None,
) -> Path:
    """Generate SRT subtitle file from timing.json and database.

    Returns:
        Path to generated SRT file
    """
    timing_path = output_dir / "audio" / "timing.json"
    if not timing_path.exists():
        print(f"ERROR: timing.json not found at {timing_path}")
        print("Run generate_audio.py first.")
        sys.exit(1)

    with open(timing_path, "r", encoding="utf-8") as f:
        timing = json.load(f)

    lesson_id = timing["lesson_id"]
    gap_ms = timing.get("sentence_gap_ms", sentence_gap_ms)

    # Get sentence data from DB for pinyin and English
    conn = get_connection(db_path)
    sentences = get_sentences(conn, lesson_id)
    conn.close()

    # Build sentence lookup by sort_order
    sentence_map = {s.sort_order: s for s in sentences}

    srt_lines = []
    current_ms = 0
    subtitle_idx = 1

    for entry in timing["sentences"]:
        sort_order = entry["sort_order"]
        duration_ms = entry["duration_ms"]
        sentence = sentence_map.get(sort_order)

        if not sentence:
            current_ms += duration_ms + gap_ms
            continue

        start_time = ms_to_srt_time(current_ms)
        end_time = ms_to_srt_time(current_ms + duration_ms)

        # Three-line subtitle: pinyin / Chinese / English
        srt_lines.append(str(subtitle_idx))
        srt_lines.append(f"{start_time} --> {end_time}")
        srt_lines.append(sentence.text_pinyin)
        srt_lines.append(sentence.text_zh)
        srt_lines.append(sentence.text_en)
        srt_lines.append("")  # blank line separator

        subtitle_idx += 1
        current_ms += duration_ms + gap_ms

    srt_content = "\n".join(srt_lines)
    srt_path = output_dir / "subtitles.srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    print(f"Generated {subtitle_idx - 1} subtitle blocks")
    print(f"Total duration: {current_ms / 1000:.1f}s")
    print(f"SRT file: {srt_path}")

    return srt_path


def main():
    parser = argparse.ArgumentParser(description="Generate SRT subtitles")
    parser.add_argument("--output-dir", type=str)
    args = parser.parse_args()

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        from datetime import date
        output_dir = OUTPUT_DIR / date.today().isoformat()

    generate_srt(output_dir)


if __name__ == "__main__":
    main()
