#!/usr/bin/env python3
"""Compose final video from poster frames + audio + subtitles using ffmpeg.

Pipeline:
1. Read timing.json for per-sentence durations
2. Build ffmpeg concat demuxer input (each frame shown for its sentence duration + gap)
3. Concatenate audio files with silence gaps
4. Overlay subtitles (burned in)
5. Output final MP4

Usage:
    python scripts/compose_video.py --output-dir output/2026-05-28
    python scripts/compose_video.py --output-dir output/2026-05-28 --format vertical
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.utils.db_helper import OUTPUT_DIR

SENTENCE_GAP_S = 1.5


def create_concat_audio(audio_dir: Path, timing: dict, output_path: Path) -> float:
    """Concatenate sentence audio files with silence gaps.

    Returns total duration in seconds.
    """
    sentences = timing["sentences"]
    gap_ms = timing.get("sentence_gap_ms", int(SENTENCE_GAP_S * 1000))
    gap_s = gap_ms / 1000

    # Build ffmpeg filter for concatenation with silence
    inputs = []
    filter_parts = []

    for i, entry in enumerate(sentences):
        audio_file = audio_dir / entry["file"]
        if not audio_file.exists():
            print(f"WARNING: Audio file not found: {audio_file}")
            continue
        inputs.extend(["-i", str(audio_file)])

    n = len(inputs) // 2  # number of input files

    if n == 0:
        print("ERROR: No audio files found")
        sys.exit(1)

    # Use ffmpeg concat with silence between clips
    # Generate silence audio for gaps
    silence_filter = f"anullsrc=r=24000:cl=mono[silence]"

    # Build complex filter
    filter_parts = [silence_filter]
    concat_inputs = []

    for i in range(n):
        # Each sentence audio
        concat_inputs.append(f"[{i}:a]")
        if i < n - 1:
            # Add silence gap (except after last sentence)
            trim_label = f"[gap{i}]"
            filter_parts.append(f"[silence]atrim=0:{gap_s},asetpts=PTS-STARTPTS{trim_label}")
            concat_inputs.append(trim_label)

    total_streams = len(concat_inputs)
    concat_str = "".join(concat_inputs)
    filter_parts.append(f"{concat_str}concat=n={total_streams}:v=0:a=1[outa]")

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-f", "lavfi", "-i", silence_filter.split("[")[0],
        "-filter_complex", filter_complex,
        "-map", "[outa]",
        "-c:a", "aac", "-b:a", "128k",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ffmpeg concat audio error:\n{result.stderr[-500:]}")
        # Fallback: simple concat without silence
        return _simple_concat_audio(audio_dir, timing, output_path)

    # Calculate total duration
    total_ms = sum(e["duration_ms"] for e in sentences) + gap_ms * (n - 1)
    return total_ms / 1000


def _simple_concat_audio(audio_dir: Path, timing: dict, output_path: Path) -> float:
    """Fallback: concatenate audio files using concat demuxer (no silence gaps)."""
    sentences = timing["sentences"]
    gap_ms = timing.get("sentence_gap_ms", int(SENTENCE_GAP_S * 1000))

    # Create a silence file for gaps
    silence_path = audio_dir / "_silence.mp3"
    gap_s = gap_ms / 1000
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono",
        "-t", str(gap_s),
        "-c:a", "libmp3lame", "-b:a", "32k",
        str(silence_path),
    ], capture_output=True)

    # Build concat list
    concat_list = audio_dir / "_concat.txt"
    with open(concat_list, "w") as f:
        for i, entry in enumerate(sentences):
            audio_file = audio_dir / entry["file"]
            if audio_file.exists():
                f.write(f"file '{audio_file.name}'\n")
                if i < len(sentences) - 1:
                    f.write(f"file '{silence_path.name}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c:a", "aac", "-b:a", "128k",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ffmpeg simple concat error:\n{result.stderr[-500:]}")
        sys.exit(1)

    total_ms = sum(e["duration_ms"] for e in sentences) + gap_ms * (len(sentences) - 1)
    return total_ms / 1000


def create_frame_slideshow(
    frames_dir: Path,
    timing: dict,
    output_path: Path,
    width: int,
    height: int,
) -> None:
    """Create a video slideshow from frames, each shown for its sentence duration + gap."""
    sentences = timing["sentences"]
    gap_ms = timing.get("sentence_gap_ms", int(SENTENCE_GAP_S * 1000))

    # Build concat demuxer input
    concat_list = frames_dir / "_concat.txt"
    with open(concat_list, "w") as f:
        for i, entry in enumerate(sentences):
            frame_file = frames_dir / f"frame_{entry['sort_order']:03d}.png"
            if not frame_file.exists():
                print(f"WARNING: Frame not found: {frame_file}")
                continue
            # Duration = sentence audio + gap (except last)
            duration_s = entry["duration_ms"] / 1000
            if i < len(sentences) - 1:
                duration_s += gap_ms / 1000
            f.write(f"file '{frame_file.name}'\n")
            f.write(f"duration {duration_s:.3f}\n")
        # ffmpeg concat demuxer needs the last file repeated without duration
        last_frame = frames_dir / f"frame_{sentences[-1]['sort_order']:03d}.png"
        if last_frame.exists():
            f.write(f"file '{last_frame.name}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-r", "30",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ffmpeg slideshow error:\n{result.stderr[-500:]}")
        sys.exit(1)


def merge_video_audio(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
) -> None:
    """Merge video and audio tracks into final output."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ffmpeg merge error:\n{result.stderr[-500:]}")
        sys.exit(1)


def compose_video(
    output_dir: Path,
    video_format: str = "both",
) -> list[Path]:
    """Full video composition pipeline.

    Returns list of final video paths.
    """
    timing_path = output_dir / "audio" / "timing.json"
    if not timing_path.exists():
        print("ERROR: timing.json not found. Run generate_audio.py first.")
        sys.exit(1)

    with open(timing_path, "r", encoding="utf-8") as f:
        timing = json.load(f)

    audio_dir = output_dir / "audio"

    # Step 1: Concatenate audio
    print("Step 1: Concatenating audio...")
    combined_audio = output_dir / "combined_audio.m4a"
    total_duration = _simple_concat_audio(audio_dir, timing, combined_audio)
    print(f"  Combined audio: {total_duration:.1f}s")

    formats = []
    if video_format in ("vertical", "both"):
        formats.append(("vertical", 1080, 1920))
    if video_format in ("horizontal", "both"):
        formats.append(("horizontal", 1920, 1080))

    final_videos = []

    for fmt_name, width, height in formats:
        frames_dir = output_dir / f"frames_{fmt_name}"
        if not frames_dir.exists():
            print(f"WARNING: Frames directory not found: {frames_dir}")
            print(f"  Run generate_poster.py with --format {fmt_name} first.")
            continue

        print(f"\nStep 2 [{fmt_name}]: Creating slideshow...")
        slideshow_path = output_dir / f"slideshow_{fmt_name}.mp4"
        create_frame_slideshow(frames_dir, timing, slideshow_path, width, height)

        print(f"Step 3 [{fmt_name}]: Merging video + audio...")
        final_path = output_dir / f"final_{fmt_name}.mp4"
        merge_video_audio(slideshow_path, combined_audio, final_path)

        # Get file size
        size_mb = final_path.stat().st_size / (1024 * 1024)
        print(f"  Output: {final_path} ({size_mb:.1f} MB)")

        final_videos.append(final_path)

        # Cleanup intermediate slideshow
        slideshow_path.unlink(missing_ok=True)

    # Cleanup combined audio
    combined_audio.unlink(missing_ok=True)

    return final_videos


def main():
    parser = argparse.ArgumentParser(description="Compose final video")
    parser.add_argument("--output-dir", type=str)
    parser.add_argument("--format", choices=["vertical", "horizontal", "both"], default="both")
    args = parser.parse_args()

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        from datetime import date
        output_dir = OUTPUT_DIR / date.today().isoformat()

    videos = compose_video(output_dir, args.format)

    print(f"\n{'='*50}")
    print(f"Generated {len(videos)} video(s):")
    for v in videos:
        print(f"  {v}")


if __name__ == "__main__":
    main()
