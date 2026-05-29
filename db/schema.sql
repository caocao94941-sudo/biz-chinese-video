-- 商务中文播客视频生成系统 - 数据库 Schema
-- SQLite3

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- 课程主题表
CREATE TABLE IF NOT EXISTS lessons (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT    NOT NULL UNIQUE,          -- 英文标识，用于关联素材文件名
    title_zh        TEXT    NOT NULL,                 -- 中文标题
    title_pinyin    TEXT    NOT NULL,                 -- 拼音
    title_en        TEXT    NOT NULL,                 -- 英文标题
    hsk_level       TEXT    NOT NULL DEFAULT 'HSK1',  -- HSK1 / HSK2 / HSK1-2 / HSK3 / HSK4
    category        TEXT    NOT NULL DEFAULT '商务汉语', -- 分类标签
    topic_image     TEXT,                             -- 主题配图文件名（相对 assets/images/topics/）
    business_tip_zh TEXT,                             -- 商务小贴士中文
    business_tip_en TEXT,                             -- 商务小贴士英文
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- 课文句子表（按顺序）
CREATE TABLE IF NOT EXISTS sentences (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id       INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    sort_order      INTEGER NOT NULL,                 -- 句子顺序（从 1 开始）
    text_zh         TEXT    NOT NULL,                 -- 中文原文
    text_pinyin     TEXT    NOT NULL,                 -- 拼音
    text_en         TEXT    NOT NULL,                 -- 英文翻译
    highlight_words TEXT,                             -- JSON: 需要高亮的关键词列表 ["负责","市场"]
    duration_ms     INTEGER DEFAULT 3000,             -- 预估朗读时长（毫秒），TTS 后会更新
    UNIQUE(lesson_id, sort_order)
);

-- 词汇表
CREATE TABLE IF NOT EXISTS vocabulary (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id       INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    sort_order      INTEGER NOT NULL DEFAULT 0,       -- 显示顺序
    word_zh         TEXT    NOT NULL,                 -- 中文词汇
    word_pinyin     TEXT    NOT NULL,                 -- 拼音
    word_en         TEXT    NOT NULL,                 -- 英文释义
    word_pos        TEXT,                             -- 词性：n./v./adj./adv./pron./conj.
    hsk_level       TEXT    NOT NULL DEFAULT 'HSK1',  -- HSK 等级
    icon_emoji      TEXT,                             -- 图标 emoji（可选）
    first_appear_sentence INTEGER NOT NULL DEFAULT 1, -- 首次出现的句子 sort_order
    UNIQUE(lesson_id, word_zh)
);

-- 语法点表
CREATE TABLE IF NOT EXISTS grammar (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id       INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    pattern_zh      TEXT    NOT NULL,                 -- 语法模式中文：我叫……
    pattern_pinyin  TEXT,                             -- 拼音
    pattern_en      TEXT,                             -- 英文说明
    explanation_zh  TEXT,                             -- 中文解释
    explanation_en  TEXT,                             -- 英文解释
    example_zh      TEXT,                             -- 例句中文
    example_pinyin  TEXT,                             -- 例句拼音
    example_en      TEXT,                             -- 例句英文
    hsk_level       TEXT    NOT NULL DEFAULT 'HSK1',
    first_appear_sentence INTEGER NOT NULL DEFAULT 1, -- 首次出现的句子 sort_order
    UNIQUE(lesson_id, sort_order)
);

-- 排期表
CREATE TABLE IF NOT EXISTS schedule (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id       INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    publish_date    TEXT    NOT NULL,                 -- YYYY-MM-DD
    voice           TEXT    NOT NULL DEFAULT 'zh-CN-XiaoxiaoNeural', -- TTS 语音
    video_format    TEXT    NOT NULL DEFAULT 'both',  -- vertical / horizontal / both
    status          TEXT    NOT NULL DEFAULT 'pending', -- pending / generating / generated / published / failed
    output_path     TEXT,                             -- 生成后的输出路径
    error_message   TEXT,                             -- 失败时的错误信息
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    generated_at    TEXT,
    UNIQUE(lesson_id, publish_date)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_sentences_lesson ON sentences(lesson_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_vocabulary_lesson ON vocabulary(lesson_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_grammar_lesson ON grammar(lesson_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_schedule_date ON schedule(publish_date, status);
