import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'weibo.db')
STOP_WORDS_FILE = os.path.join(DATA_DIR, 'stop_words.json')

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

WEIBO_LOGIN_URL = "https://weibo.com"
SCROLL_PAUSE_TIME = 2
MAX_SCROLL_COUNT = 5

def load_stop_words():
    """加载用户自定义屏蔽词"""
    default_stop_words = {
        '转发', '微博', 'http', 'https', 'com', 'www', 'weibo', 'sinaimg', 'cn', 't', 'co',
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
        '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
        '自己', '这', '那', '可以', '能', '会', '要', '什么', '怎么', '为什么', '这个', '那个',
        '这样', '那样', '还是', '展开', '全文', '收起', '查看', '更多', '详情',
        '点击', '链接', '图片', '视频', '话题', '超话', '热搜'
    }
    
    if os.path.exists(STOP_WORDS_FILE):
        try:
            with open(STOP_WORDS_FILE, 'r', encoding='utf-8') as f:
                custom_words = json.load(f)
                return default_stop_words | set(custom_words)
        except:
            return default_stop_words
    return default_stop_words

def save_stop_words(words):
    """保存用户自定义屏蔽词"""
    try:
        with open(STOP_WORDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(words), f, ensure_ascii=False, indent=2)
        return True
    except:
        return False
