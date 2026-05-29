"""SQLite database helper for biz-chinese-video project."""

import sqlite3
import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# Project root: demos/biz-chinese-video/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "db" / "biz_chinese.db"
SCHEMA_PATH = PROJECT_ROOT / "db" / "schema.sql"
SEED_PATH = PROJECT_ROOT / "db" / "seed_data.sql"
ASSETS_DIR = PROJECT_ROOT / "assets"
OUTPUT_DIR = PROJECT_ROOT / "output"
TEMPLATES_DIR = PROJECT_ROOT / "templates"


@dataclass
class Lesson:
    id: int
    slug: str
    title_zh: str
    title_pinyin: str
    title_en: str
    hsk_level: str
    category: str
    topic_image: Optional[str]
    business_tip_zh: Optional[str]
    business_tip_en: Optional[str]


@dataclass
class Sentence:
    id: int
    lesson_id: int
    sort_order: int
    text_zh: str
    text_pinyin: str
    text_en: str
    highlight_words: list = field(default_factory=list)
    duration_ms: int = 3000


@dataclass
class Vocabulary:
    id: int
    lesson_id: int
    sort_order: int
    word_zh: str
    word_pinyin: str
    word_en: str
    word_pos: Optional[str]
    hsk_level: str
    icon_emoji: Optional[str]
    first_appear_sentence: int = 1


@dataclass
class Grammar:
    id: int
    lesson_id: int
    sort_order: int
    pattern_zh: str
    pattern_pinyin: Optional[str]
    pattern_en: Optional[str]
    explanation_zh: Optional[str]
    explanation_en: Optional[str]
    example_zh: Optional[str]
    example_pinyin: Optional[str]
    example_en: Optional[str]
    hsk_level: str
    first_appear_sentence: int = 1


@dataclass
class Schedule:
    id: int
    lesson_id: int
    publish_date: str
    voice: str
    video_format: str
    status: str
    output_path: Optional[str]
    error_message: Optional[str]


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """Get a database connection with row_factory set."""
    path = db_path or str(DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str = None):
    """Initialize database from schema.sql and seed_data.sql."""
    conn = get_connection(db_path)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    if SEED_PATH.exists():
        with open(SEED_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
    conn.close()


def get_lesson(conn: sqlite3.Connection, lesson_id: int) -> Optional[Lesson]:
    """Fetch a lesson by ID."""
    row = conn.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    if not row:
        return None
    return Lesson(**{k: row[k] for k in Lesson.__dataclass_fields__})


def get_lesson_by_slug(conn: sqlite3.Connection, slug: str) -> Optional[Lesson]:
    """Fetch a lesson by slug."""
    row = conn.execute("SELECT * FROM lessons WHERE slug = ?", (slug,)).fetchone()
    if not row:
        return None
    return Lesson(**{k: row[k] for k in Lesson.__dataclass_fields__})


def get_sentences(conn: sqlite3.Connection, lesson_id: int) -> list[Sentence]:
    """Fetch all sentences for a lesson, ordered by sort_order."""
    rows = conn.execute(
        "SELECT * FROM sentences WHERE lesson_id = ? ORDER BY sort_order",
        (lesson_id,),
    ).fetchall()
    results = []
    for row in rows:
        d = {k: row[k] for k in Sentence.__dataclass_fields__}
        # Parse highlight_words JSON
        hw = d.get("highlight_words")
        d["highlight_words"] = json.loads(hw) if hw else []
        results.append(Sentence(**d))
    return results


def get_vocabulary(conn: sqlite3.Connection, lesson_id: int) -> list[Vocabulary]:
    """Fetch all vocabulary for a lesson, ordered by sort_order."""
    rows = conn.execute(
        "SELECT * FROM vocabulary WHERE lesson_id = ? ORDER BY sort_order",
        (lesson_id,),
    ).fetchall()
    return [Vocabulary(**{k: row[k] for k in Vocabulary.__dataclass_fields__}) for row in rows]


def get_grammar(conn: sqlite3.Connection, lesson_id: int) -> list[Grammar]:
    """Fetch all grammar points for a lesson, ordered by sort_order."""
    rows = conn.execute(
        "SELECT * FROM grammar WHERE lesson_id = ? ORDER BY sort_order",
        (lesson_id,),
    ).fetchall()
    return [Grammar(**{k: row[k] for k in Grammar.__dataclass_fields__}) for row in rows]


def get_vocabulary_up_to_sentence(conn: sqlite3.Connection, lesson_id: int, sentence_order: int) -> list[Vocabulary]:
    """Fetch vocabulary that has appeared up to (and including) the given sentence."""
    rows = conn.execute(
        "SELECT * FROM vocabulary WHERE lesson_id = ? AND first_appear_sentence <= ? ORDER BY first_appear_sentence, sort_order",
        (lesson_id, sentence_order),
    ).fetchall()
    return [Vocabulary(**{k: row[k] for k in Vocabulary.__dataclass_fields__}) for row in rows]


def get_grammar_up_to_sentence(conn: sqlite3.Connection, lesson_id: int, sentence_order: int) -> list[Grammar]:
    """Fetch grammar points that have appeared up to (and including) the given sentence."""
    rows = conn.execute(
        "SELECT * FROM grammar WHERE lesson_id = ? AND first_appear_sentence <= ? ORDER BY first_appear_sentence, sort_order",
        (lesson_id, sentence_order),
    ).fetchall()
    return [Grammar(**{k: row[k] for k in Grammar.__dataclass_fields__}) for row in rows]


def get_today_schedule(conn: sqlite3.Connection) -> list[Schedule]:
    """Fetch today's pending schedules."""
    rows = conn.execute(
        "SELECT * FROM schedule WHERE publish_date = date('now') AND status = 'pending'"
    ).fetchall()
    return [Schedule(**{k: row[k] for k in Schedule.__dataclass_fields__}) for row in rows]


def get_schedule_by_date(conn: sqlite3.Connection, date_str: str) -> list[Schedule]:
    """Fetch schedules for a specific date."""
    rows = conn.execute(
        "SELECT * FROM schedule WHERE publish_date = ? ORDER BY id",
        (date_str,),
    ).fetchall()
    return [Schedule(**{k: row[k] for k in Schedule.__dataclass_fields__}) for row in rows]


def update_schedule_status(
    conn: sqlite3.Connection,
    schedule_id: int,
    status: str,
    output_path: str = None,
    error_message: str = None,
):
    """Update schedule status."""
    if status == "generated":
        conn.execute(
            "UPDATE schedule SET status=?, output_path=?, generated_at=datetime('now') WHERE id=?",
            (status, output_path, schedule_id),
        )
    elif status == "failed":
        conn.execute(
            "UPDATE schedule SET status=?, error_message=? WHERE id=?",
            (status, error_message, schedule_id),
        )
    else:
        conn.execute(
            "UPDATE schedule SET status=? WHERE id=?",
            (status, schedule_id),
        )
    conn.commit()


def update_sentence_duration(conn: sqlite3.Connection, sentence_id: int, duration_ms: int):
    """Update sentence duration after TTS generation."""
    conn.execute(
        "UPDATE sentences SET duration_ms=? WHERE id=?",
        (duration_ms, sentence_id),
    )
    conn.commit()


def get_full_lesson_data(conn: sqlite3.Connection, lesson_id: int) -> dict:
    """Fetch all data for a lesson in one call. Returns dict with all components."""
    lesson = get_lesson(conn, lesson_id)
    if not lesson:
        return None
    return {
        "lesson": lesson,
        "sentences": get_sentences(conn, lesson_id),
        "vocabulary": get_vocabulary(conn, lesson_id),
        "grammar": get_grammar(conn, lesson_id),
    }
