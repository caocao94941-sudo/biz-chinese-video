#!/usr/bin/env python3
"""Generate TTS audio for each sentence using edge-tts.

Produces one MP3 per sentence + a combined audio file.
Updates sentence duration_ms in the database after generation.

Usage:
    python scripts/generate_audio.py --lesson-id 1
    python scripts/generate_audio.py --lesson-id 1 --voice zh-CN-YunxiNeural
    python scripts/generate_audio.py --lesson-id 1 --output-dir output/2026-05-28
"""

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path

import edge_tts

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.utils.db_helper import (
    get_connection, get_full_lesson_data, update_sentence_duration, OUTPUT_DIR
)

# Default voice options
VOICES = {
    "female": "zh-CN-XiaoxiaoNeural",
    "male": "zh-CN-YunxiNeural",
}

# Pause between sentences (seconds)
SENTENCE_GAP = 1.5

# Speech rate adjustment for HSK1-2 learners (slower)
RATE = "-15%"


def get_audio_duration_ms(filepath: Path) -> int:
    """Get actual audio duration in milliseconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(filepath)],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        import json as _json
        info = _json.loads(result.stdout)
        duration_s = float(info.get("format", {}).get("duration", 0))
        return int(duration_s * 1000)
    return 0


async def generate_sentence_audio(
    text: str,
    output_path: Path,
    voice: str = "zh-CN-XiaoxiaoNeural",
    rate: str = RATE,
) -> int:
    """Generate TTS audio for a single sentence.

    Returns:
        Duration in milliseconds (from ffprobe, not WordBoundary)
    """
    communicate = edge_tts.Communicate(text, voice, rate=rate)

    with open(output_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])

    # Use ffprobe for accurate duration
    duration_ms = get_audio_duration_ms(output_path)

    if duration_ms == 0:
        # Fallback: estimate from file size
        file_size = output_path.stat().st_size
        duration_ms = int(file_size / 16 * 8)

    return duration_ms


async def generate_lesson_audio(
    lesson_id: int,
    output_dir: Path,
    voice: str = "zh-CN-XiaoxiaoNeural",
    db_path: str = None,
) -> dict:
    """Generate audio for all sentences in a lesson.

    Returns:
        Dict with 'sentence_files' (list of paths) and 'durations' (list of ms)
    """
    conn = get_connection(db_path)
    lesson_data = get_full_lesson_data(conn, lesson_id)

    if not lesson_data:
        print(f"ERROR: Lesson {lesson_id} not found")
        conn.close()
        return {}

    sentences = lesson_data["sentences"]
    lesson = lesson_data["lesson"]
    print(f"Generating audio for: {lesson.title_zh} ({len(sentences)} sentences)")
    print(f"Voice: {voice}, Rate: {RATE}")

    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    sentence_files = []
    durations = []

    for sentence in sentences:
        filename = f"{sentence.sort_order:02d}_{sentence.text_zh[:6].rstrip('，。！？')}.mp3"
        filepath = audio_dir / filename

        duration_ms = await generate_sentence_audio(
            sentence.text_zh, filepath, voice
        )

        # Update DB with actual duration
        update_sentence_duration(conn, sentence.id, duration_ms)

        sentence_files.append(filepath)
        durations.append(duration_ms)

        print(f"  [{sentence.sort_order}/{len(sentences)}] {sentence.text_zh} → {duration_ms}ms")

    conn.close()

    # Save timing metadata
    timing = {
        "lesson_id": lesson_id,
        "voice": voice,
        "rate": RATE,
        "sentence_gap_ms": int(SENTENCE_GAP * 1000),
        "sentences": [
            {
                "sort_order": s.sort_order,
                "text_zh": s.text_zh,
                "file": str(sentence_files[i].name),
                "duration_ms": durations[i],
            }
            for i, s in enumerate(sentences)
        ],
    }

    timing_path = audio_dir / "timing.json"
    with open(timing_path, "w", encoding="utf-8") as f:
        json.dump(timing, f, ensure_ascii=False, indent=2)

    print(f"\nTiming metadata saved: {timing_path}")
    total_ms = sum(durations) + int(SENTENCE_GAP * 1000) * (len(sentences) - 1)
    print(f"Total estimated duration: {total_ms/1000:.1f}s")

    return {
        "sentence_files": sentence_files,
        "durations": durations,
        "timing_path": timing_path,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate TTS audio")
    parser.add_argument("--lesson-id", type=int, default=1)
    parser.add_argument("--voice", type=str, default="zh-CN-XiaoxiaoNeural",
                        help="TTS voice name or shortcut (female/male)")
    parser.add_argument("--output-dir", type=str)
    args = parser.parse_args()

    # Resolve voice shortcut
    voice = VOICES.get(args.voice, args.voice)

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        from datetime import date
        output_dir = OUTPUT_DIR / date.today().isoformat()

    output_dir.mkdir(parents=True, exist_ok=True)

    result = asyncio.run(
        generate_lesson_audio(args.lesson_id, output_dir, voice)
    )

    if result:
        print(f"\nAudio files: {len(result['sentence_files'])}")
        for f in result["sentence_files"]:
            print(f"  {f}")


if __name__ == "__main__":
    main()
