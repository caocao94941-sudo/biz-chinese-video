# 商务中文播客视频生成器

每日自动生成商务中文学习视频（HSK1-2），包含 TTS 语音、拼音字幕、词汇/语法卡片。

## 快速开始

```bash
cd demos/biz-chinese-video

# 1. 安装依赖
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
.venv/bin/playwright install-deps chromium

# 2. 初始化数据库（含种子数据）
.venv/bin/python scripts/init_db.py --reset

# 3. 一键生成今日视频
.venv/bin/python scripts/daily_runner.py --lesson-id 1
```

输出在 `output/YYYY-MM-DD/` 目录下。

## 架构

```
SQLite DB → 海报帧 (Playwright) → TTS 音频 (edge-tts) → 字幕 (SRT) → 视频 (ffmpeg)
```

| 步骤 | 脚本 | 输入 | 输出 |
|------|------|------|------|
| 初始化 DB | `scripts/init_db.py` | schema.sql + seed_data.sql | db/biz_chinese.db |
| 海报帧 | `scripts/generate_poster.py` | DB + HTML 模板 | frames_vertical/ + frames_horizontal/ |
| TTS 语音 | `scripts/generate_audio.py` | DB 句子 | audio/*.mp3 + timing.json |
| 字幕 | `scripts/generate_subtitles.py` | timing.json + DB | subtitles.srt |
| 合成视频 | `scripts/compose_video.py` | 帧 + 音频 | final_vertical.mp4 + final_horizontal.mp4 |
| 每日调度 | `scripts/daily_runner.py` | schedule 表 | 完整视频 |

## 视频格式

- **竖屏** 1080×1920 — 抖音、小红书、Instagram Reels
- **横屏** 1920×1080 — YouTube、B站

默认同时生成两种格式，可用 `--format vertical` 或 `--format horizontal` 指定。

## 数据库

SQLite 数据库包含 5 张表：

| 表 | 用途 |
|----|------|
| `lessons` | 课程主题（标题、HSK 等级、配图、商务小贴士） |
| `sentences` | 课文句子（中文、拼音、英文、高亮词） |
| `vocabulary` | 词汇（拼音、释义、词性、HSK 等级） |
| `grammar` | 语法点（模式、解释、例句） |
| `schedule` | 排期（日期、语音、格式、状态） |

添加新课程：直接往 `db/seed_data.sql` 追加 INSERT 语句，或用 SQLite 客户端操作 `db/biz_chinese.db`。

## 命令参考

```bash
# 单步执行
.venv/bin/python scripts/generate_poster.py --lesson-id 1 --format both
.venv/bin/python scripts/generate_audio.py --lesson-id 1 --voice male
.venv/bin/python scripts/generate_subtitles.py
.venv/bin/python scripts/compose_video.py --format vertical

# 一键生成（推荐）
.venv/bin/python scripts/daily_runner.py --lesson-id 1
.venv/bin/python scripts/daily_runner.py --lesson-id 1 --voice male --format vertical

# 按排期生成
.venv/bin/python scripts/daily_runner.py                    # 今日排期
.venv/bin/python scripts/daily_runner.py --date 2026-06-01  # 指定日期
```

## TTS 语音

| 名称 | 快捷方式 | edge-tts 全名 |
|------|---------|---------------|
| 中文女声 | `female` | `zh-CN-XiaoxiaoNeural` |
| 中文男声 | `male` | `zh-CN-YunxiNeural` |

语速默认 -15%（适合 HSK1-2 学习者）。

## 素材命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 主题图片 | `assets/images/topics/{slug}.png` | `self_intro.png` |
| 输出目录 | `output/YYYY-MM-DD/` | `output/2026-05-28/` |
| 音频文件 | `{sort_order:02d}_{前6字}.mp3` | `01_大家好，我叫.mp3` |

## 目录结构

```
demos/biz-chinese-video/
├── db/
│   ├── schema.sql          # 建表 DDL
│   └── seed_data.sql       # 种子数据
├── assets/images/topics/   # 主题配图
├── templates/
│   ├── poster_vertical.html    # 竖屏海报模板
│   └── poster_horizontal.html  # 横屏海报模板
├── scripts/
│   ├── init_db.py
│   ├── generate_poster.py
│   ├── generate_audio.py
│   ├── generate_subtitles.py
│   ├── compose_video.py
│   ├── daily_runner.py
│   └── utils/
│       ├── db_helper.py
│       └── pinyin_helper.py
├── output/                 # 生成产物（gitignore）
├── requirements.txt
└── README.md
```

## 定时执行

用 cron 实现每日自动生成：

```bash
# 每天早上 6:00 生成
0 6 * * * cd /path/to/demos/biz-chinese-video && .venv/bin/python scripts/daily_runner.py >> /var/log/biz-chinese.log 2>&1
```

## 依赖

- Python 3.12+
- ffmpeg
- Chromium（Playwright 自动安装）
- edge-tts、pypinyin、Playwright、Pillow、Jinja2
