-- 种子数据：基础自我介绍场景

-- Lesson 1: 个人介绍
INSERT INTO lessons (slug, title_zh, title_pinyin, title_en, hsk_level, category, topic_image, business_tip_zh, business_tip_en)
VALUES (
    'self_intro',
    '个人介绍',
    'gèrén jièshào',
    'Self Introduction',
    'HSK1-2',
    '商务汉语',
    'self_intro.png',
    '在商务场合，自我介绍要简洁、自信、突出核心能力。',
    'In business situations, self-introduction should be concise, confident and highlight your core strengths.'
);

-- Sentences for Lesson 1
INSERT INTO sentences (lesson_id, sort_order, text_zh, text_pinyin, text_en, highlight_words, duration_ms) VALUES
(1, 1, '大家好，我叫张三。',       'Dàjiā hǎo, wǒ jiào Zhāng Sān.',           'Hello everyone, my name is Zhang San.',        '["大家","我叫"]',     3000),
(1, 2, '我今年二十五岁。',         'Wǒ jīnnián èrshíwǔ suì.',                  'I am twenty-five years old this year.',         '["今年","岁"]',       2800),
(1, 3, '我是中国人。',             'Wǒ shì Zhōngguó rén.',                     'I am Chinese.',                                 '["中国"]',            2200),
(1, 4, '我在北京工作。',           'Wǒ zài Běijīng gōngzuò.',                  'I work in Beijing.',                            '["北京","工作"]',     2500),
(1, 5, '我在一个公司工作。',       'Wǒ zài yí gè gōngsī gōngzuò.',             'I work at a company.',                          '["公司","工作"]',     3000),
(1, 6, '我是销售。',               'Wǒ shì xiāoshòu.',                         'I am in sales.',                                '["销售"]',            2200),
(1, 7, '很高兴认识大家。',         'Hěn gāoxìng rènshi dàjiā.',                 'Nice to meet everyone.',                        '["高兴","认识"]',     2800);

-- Vocabulary for Lesson 1
-- first_appear_sentence = 该词汇首次出现在第几句
INSERT INTO vocabulary (lesson_id, sort_order, word_zh, word_pinyin, word_en, word_pos, hsk_level, icon_emoji, first_appear_sentence) VALUES
(1, 1, '大家',   'dàjiā',     'everyone',       'pron.',  'HSK1', '👥', 1),
(1, 2, '我叫',   'wǒ jiào',   'my name is',     'v.',     'HSK1', '🙋', 1),
(1, 3, '中国',   'Zhōngguó',  'China',          'n.',     'HSK1', '🇨🇳', 3),
(1, 4, '工作',   'gōngzuò',   'work/job',       'n./v.',  'HSK1', '💼', 4),
(1, 5, '公司',   'gōngsī',    'company',        'n.',     'HSK2', '🏢', 5),
(1, 6, '销售',   'xiāoshòu',  'sales',          'n./v.',  'HSK2', '📊', 6),
(1, 7, '高兴',   'gāoxìng',   'happy/glad',     'adj.',   'HSK1', '😊', 7),
(1, 8, '认识',   'rènshi',    'to know/meet',   'v.',     'HSK1', '🤝', 7);

-- Grammar for Lesson 1
-- first_appear_sentence = 该语法首次出现在第几句
INSERT INTO grammar (lesson_id, sort_order, pattern_zh, pattern_pinyin, pattern_en, explanation_zh, explanation_en, example_zh, example_pinyin, example_en, hsk_level, first_appear_sentence) VALUES
(1, 1,
    '我叫……',
    'wǒ jiào...',
    'My name is...',
    '用于自我介绍时说出自己的名字。',
    'Used to state your name during self-introduction.',
    '我叫李明。',
    'Wǒ jiào Lǐ Míng.',
    'My name is Li Ming.',
    'HSK1',
    1
),
(1, 2,
    '我在……工作',
    'wǒ zài... gōngzuò',
    'I work at/in...',
    '表示在某个地点或机构工作。"在"后面接地点或单位名称。',
    'Indicates working at a place or organization. Place/organization follows "在".',
    '我在上海一家银行工作。',
    'Wǒ zài Shànghǎi yì jiā yínháng gōngzuò.',
    'I work at a bank in Shanghai.',
    'HSK2',
    4
),
(1, 3,
    '很高兴认识……',
    'hěn gāoxìng rènshi...',
    'Nice to meet...',
    '初次见面时的礼貌用语，表示认识对方很开心。',
    'A polite expression used when meeting someone for the first time.',
    '很高兴认识你！',
    'Hěn gāoxìng rènshi nǐ!',
    'Nice to meet you!',
    'HSK1-2',
    7
);

-- Schedule: 排期今天
INSERT INTO schedule (lesson_id, publish_date, voice, video_format, status)
VALUES (1, date('now'), 'zh-CN-XiaoxiaoNeural', 'both', 'pending');
