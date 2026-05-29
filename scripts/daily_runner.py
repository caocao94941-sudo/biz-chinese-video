#!/usr/bin/env python3
"""Daily runner: orchestrates the full video generation pipeline.

Checks the schedule table for today's pending lessons, then runs:
1. generate_poster.py → poster frames
2. generate_audio.py → TTS audio
3. generate_subtitles.py → SRT subtitles
4. compose_video.py → final MP4

Usage:
    # Generate today's scheduled lessons
    python scripts/daily_runner.py

    # Generate a specific lesson (bypass schedule)
    python scripts/daily_runner.py --lesson-id 1

    # Generate for a specific date
    python scripts/daily_runner.py --date 2026-05-28

    # Override voice and format
    python scripts/daily_runner.py --lesson-id 1 --voice male --format vertical
"""

import argparse
import asyncio
import sys
import traceback
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.utils.db_helper import (
    get_connection, get_today_schedule, get_schedule_by_date,
    get_full_lesson_data, update_schedule_status, OUTPUT_DIR
)
from scripts.generate_poster_pillow import generate_frames
from scripts.generate_audio import generate_lesson_audio, VOICES
from scripts.generate_subtitles import generate_srt
from scripts.compose_video import compose_video


async def run_pipeline(
    lesson_id: int,
    output_dir: Path,
    voice: str = "zh-CN-XiaoxiaoNeural",
    video_format: str = "both",
    schedule_id: int = None,
    db_path: str = None,
) -> bool:
    """Run the full generation pipeline for one lesson.

    Returns True on success, False on failure.
    """
    conn = get_connection(db_path)

    # Mark as generating
    if schedule_id:
        update_schedule_status(conn, schedule_id, "generating")

    lesson_data = get_full_lesson_data(conn, lesson_id)
    if not lesson_data:
        print(f"ERROR: Lesson {lesson_id} not found")
        if schedule_id:
            update_schedule_status(conn, schedule_id, "failed", error_message="Lesson not found")
        conn.close()
        return False

    lesson = lesson_data["lesson"]
    print(f"\n{'='*60}")
    print(f"Generating video for: {lesson.title_zh} ({lesson.title_en})")
    print(f"HSK Level: {lesson.hsk_level}")
    print(f"Voice: {voice}")
    print(f"Format: {video_format}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}\n")

    conn.close()

    try:
        # Step 1: Generate poster frames
        print("[1/4] Generating poster frames...")
        frame_paths = await generate_frames(lesson_id, output_dir, video_format, db_path)
        if not frame_paths:
            raise RuntimeError("No frames generated")
        for fmt, paths in frame_paths.items():
            print(f"  {fmt}: {len(paths)} frames")

        # Step 2: Generate TTS audio
        print("\n[2/4] Generating TTS audio...")
        audio_result = await generate_lesson_audio(lesson_id, output_dir, voice, db_path)
        if not audio_result:
            raise RuntimeError("Audio generation failed")
        print(f"  {len(audio_result['sentence_files'])} audio files")

        # Step 3: Generate subtitles
        print("\n[3/4] Generating subtitles...")
        srt_path = generate_srt(output_dir, db_path=db_path)
        print(f"  SRT: {srt_path}")

        # Step 4: Compose video
        print("\n[4/4] Composing final video...")
        videos = compose_video(output_dir, video_format)

        print(f"\n{'='*60}")
        print(f"SUCCESS: {len(videos)} video(s) generated")
        for v in videos:
            size_mb = v.stat().st_size / (1024 * 1024)
            print(f"  {v.name} ({size_mb:.1f} MB)")
        print(f"{'='*60}")

        # Update schedule
        if schedule_id:
            conn = get_connection(db_path)
            update_schedule_status(
                conn, schedule_id, "generated",
                output_path=str(output_dir)
            )
            conn.close()

        return True

    except Exception as e:
        print(f"\nERROR: Pipeline failed: {e}")
        traceback.print_exc()

        if schedule_id:
            conn = get_connection(db_path)
            update_schedule_status(
                conn, schedule_id, "failed",
                error_message=str(e)
            )
            conn.close()

        return False


def main():
    parser = argparse.ArgumentParser(description="Daily video generation runner")
    parser.add_argument("--lesson-id", type=int, help="Specific lesson ID (bypasses schedule)")
    parser.add_argument("--date", type=str, help="Date to generate for (YYYY-MM-DD)")
    parser.add_argument("--voice", type=str, default="female",
                        help="Voice: female, male, or full edge-tts voice name")
    parser.add_argument("--format", choices=["vertical", "horizontal", "both"], default="both")
    parser.add_argument("--output-dir", type=str, help="Override output directory")
    args = parser.parse_args()

    voice = VOICES.get(args.voice, args.voice)
    target_date = args.date or date.today().isoformat()

    if args.lesson_id:
        # Direct lesson generation (bypass schedule)
        output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR / target_date
        output_dir.mkdir(parents=True, exist_ok=True)

        success = asyncio.run(
            run_pipeline(args.lesson_id, output_dir, voice, args.format)
        )
        sys.exit(0 if success else 1)

    # Schedule-based generation
    conn = get_connection()
    if args.date:
        schedules = get_schedule_by_date(conn, args.date)
    else:
        schedules = get_today_schedule(conn)
    conn.close()

    if not schedules:
        print(f"No pending lessons scheduled for {target_date}")
        sys.exit(0)

    print(f"Found {len(schedules)} lesson(s) scheduled for {target_date}")

    results = []
    for sched in schedules:
        output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR / target_date
        output_dir.mkdir(parents=True, exist_ok=True)

        sched_voice = voice if args.voice != "female" else sched.voice
        sched_format = args.format if args.format != "both" else sched.video_format

        success = asyncio.run(
            run_pipeline(
                sched.lesson_id, output_dir, sched_voice, sched_format,
                schedule_id=sched.id
            )
        )
        results.append((sched, success))

    # Summary
    print(f"\n{'='*60}")
    print("Daily Generation Summary")
    print(f"{'='*60}")
    for sched, success in results:
        status = "OK" if success else "FAILED"
        print(f"  Lesson {sched.lesson_id}: {status}")

    failed = sum(1 for _, s in results if not s)
    if failed:
        print(f"\n{failed} lesson(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
