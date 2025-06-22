#!/usr/bin/env python
# -*- coding: utf-8 -*- #

# 基本設定
AUTHOR = 'LLM-X-Reader'
SITENAME = 'Novel Reader'
SITESUBTITLE = 'AIが生成した小説を読みやすく表示'
SITEURL = 'http://localhost:8000'

# パス設定
PATH = 'content'
OUTPUT_PATH = 'output'

# 言語とタイムゾーン
TIMEZONE = 'Asia/Tokyo'
DEFAULT_LANG = 'ja'

# フィード設定（本番用なので開発時は無効化）
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# ソーシャルウィジェット
SOCIAL = ()

# ページネーション
DEFAULT_PAGINATION = 10

# 相対URL（開発時）
RELATIVE_URLS = True

# テーマ設定
THEME = 'theme'  # カスタムテーマを使用

# HTML出力の設定
DISPLAY_PAGES_ON_MENU = True
DISPLAY_CATEGORIES_ON_MENU = True

# 記事の表示設定
ARTICLE_ORDER_BY = 'basename'  # ファイル名順で並び替え
DEFAULT_CATEGORY = 'Stories'
DIRECT_TEMPLATES = ['index', 'tags', 'categories', 'archives']
PAGINATED_TEMPLATES = {
    'index': None,
    'tag': None,
    'category': None,
    'author': None,
}

# マークダウンの拡張機能
MARKDOWN = {
    'extension_configs': {
        'markdown.extensions.codehilite': {'css_class': 'highlight'},
        'markdown.extensions.extra': {},
        'markdown.extensions.meta': {},
        'markdown.extensions.toc': {'permalink': True},
        'markdown.extensions.nl2br': {},  # 段落内改行を<br>タグに変換
    },
    'output_format': 'html5',
}

# 記事のURL形式（シンプルなスラッグベース）
ARTICLE_URL = '{slug}.html'
ARTICLE_SAVE_AS = '{slug}.html'

# カテゴリのURL形式
CATEGORY_URL = 'category/{slug}.html'
CATEGORY_SAVE_AS = 'category/{slug}.html'

# スラッグの設定
SLUG_REGEX_SUBSTITUTIONS = [
    (r'[^\w\s-]', ''),  # 英数字、スペース、ハイフン以外を削除
    (r'[-\s]+', '-'),   # スペースとハイフンを正規化
]

# 静的ファイル
STATIC_PATHS = ['images', 'extra', 'static']
EXTRA_PATH_METADATA = {
    'static/css/novel.css': {'path': 'css/novel.css'},
}

# プラグイン
PLUGIN_PATHS = []
PLUGINS = []

# 開発サーバー設定
BIND = '127.0.0.1'
PORT = 8000
