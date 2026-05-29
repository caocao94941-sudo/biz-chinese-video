#!/usr/bin/env python3
"""Initialize the SQLite database with schema and seed data."""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.utils.db_helper import (
    DB_PATH, init_db, get_connection, get_full_lesson_data
)


def main():
    # Remove existing DB if --reset flag
    if "--reset" in sys.argv and DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing database: {DB_PATH}")

    # Ensure db directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if DB_PATH.exists() and "--reset" not in sys.argv:
        print(f"Database already exists: {DB_PATH}")
        print("Use --reset to recreate.")
    else:
        init_db()
        print(f"Database initialized: {DB_PATH}")

    # Verify data
    conn = get_connection()
    data = get_full_lesson_data(conn, 1)
    if data:
        lesson = data["lesson"]
        print(f"\n--- Lesson 1: {lesson.title_zh} ({lesson.title_en}) ---")
        print(f"HSK Level: {lesson.hsk_level}")
        print(f"Sentences: {len(data['sentences'])}")
        for s in data["sentences"]:
            print(f"  {s.sort_order}. {s.text_zh}")
            print(f"     {s.text_pinyin}")
            print(f"     {s.text_en}")
        print(f"Vocabulary: {len(data['vocabulary'])}")
        for v in data["vocabulary"]:
            print(f"  {v.icon_emoji or '·'} {v.word_zh} ({v.word_pinyin}) - {v.word_en} [{v.hsk_level}]")
        print(f"Grammar: {len(data['grammar'])}")
        for g in data["grammar"]:
            print(f"  · {g.pattern_zh} - {g.pattern_en} [{g.hsk_level}]")
        print(f"Business Tip: {lesson.business_tip_zh}")
    else:
        print("ERROR: No lesson data found!")
        sys.exit(1)

    conn.close()
    print("\nDatabase ready.")


if __name__ == "__main__":
    main()
