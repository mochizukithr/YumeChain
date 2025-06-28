"""
Flask Web Server Manager

Flaskを使ってMarkdownファイルをWebで表示するためのマネージャー
"""
import os
import shutil
import threading
import webbrowser
import socket
from pathlib import Path
from typing import Optional, List, Dict, Any
import time
from rich.console import Console
from datetime import datetime
import re


class FlaskServerManager:
    """Flaskサーバーの管理クラス"""
    
    def __init__(self, base_dir: Path, default_port: int = 5000):
        self.base_dir = base_dir
        self.default_port = default_port
        self.console = Console()
        self.server_thread: Optional[threading.Thread] = None
        self.flask_app = None
        self.novels_data: Dict[str, Any] = {}
        
    def prepare_content(self, title: str) -> bool:
        """指定されたタイトルの小説コンテンツを準備"""
        try:
            # ソースディレクトリ
            source_dir = self.base_dir / "books" / title
            stories_dir = source_dir / "stories"
            
            if not stories_dir.exists():
                self.console.print(f"[red]エラー: {stories_dir} が見つかりません[/red]")
                return False
            
            # storiesディレクトリのmarkdownファイルを読み込み
            story_files = list(stories_dir.glob("*.md"))
            if not story_files:
                self.console.print(f"[yellow]警告: {stories_dir} にMarkdownファイルが見つかりません[/yellow]")
                return False
            
            # 小説データを準備
            self.novels_data[title] = {
                'title': title,
                'stories': [],
                'metadata': {}
            }
            
            # 設定ファイルやキャラクターファイルを読み込み
            self._load_novel_metadata(source_dir, title)
            
            # 各ストーリーファイルを処理
            for story_file in sorted(story_files):
                story_data = self._process_story_file(story_file, title)
                if story_data:
                    self.novels_data[title]['stories'].append(story_data)
            
            self.console.print(f"[green]✓ コンテンツ準備完了: {len(story_files)}ファイル[/green]")
            return True
            
        except Exception as e:
            self.console.print(f"[red]エラー: コンテンツ準備中にエラーが発生しました: {e}[/red]")
            return False
    
    def _load_novel_metadata(self, source_dir: Path, title: str):
        """小説のメタデータを読み込み"""
        # setting.md を読み込み
        setting_file = source_dir / "setting.md"
        if setting_file.exists():
            self.novels_data[title]['metadata']['setting'] = setting_file.read_text(encoding='utf-8')
        
        # character.md を読み込み
        character_file = source_dir / "character.md"
        if character_file.exists():
            self.novels_data[title]['metadata']['character'] = character_file.read_text(encoding='utf-8')
    
    def _process_story_file(self, story_file: Path, title: str) -> Optional[Dict[str, Any]]:
        """ストーリーファイルを処理してデータを抽出"""
        try:
            content = story_file.read_text(encoding='utf-8')
            
            # YAMLフロントマターを解析
            metadata = self._extract_yaml_metadata(content)
            
            # 本文を抽出
            body = self._extract_body(content)
            
            # ファイル名から情報を抽出
            filename_parts = story_file.stem.split('_')
            arc = filename_parts[0] if len(filename_parts) > 1 else "未分類"
            episode_num = filename_parts[1] if len(filename_parts) > 1 else "01"
            
            return {
                'filename': story_file.name,
                'slug': story_file.stem.replace('_', '-').lower(),
                'title': metadata.get('title', f"{arc} 第{episode_num}話"),
                'arc': arc,
                'episode': episode_num,
                'body': body,
                'metadata': metadata,
                'date': metadata.get('date', datetime.now().strftime('%Y-%m-%d'))
            }
            
        except Exception as e:
            self.console.print(f"[red]ファイル処理エラー ({story_file.name}): {e}[/red]")
            return None
    
    def _extract_yaml_metadata(self, content: str) -> Dict[str, str]:
        """YAMLフロントマターからメタデータを抽出"""
        metadata = {}
        
        if content.startswith('---'):
            lines = content.split('\n')
            end_marker = -1
            
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == '---':
                    end_marker = i
                    break
            
            if end_marker > 0:
                for line in lines[1:end_marker]:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metadata[key.strip()] = value.strip().strip('"')
        
        return metadata
    
    def _extract_body(self, content: str) -> str:
        """YAMLフロントマターを除いた本文を抽出"""
        if content.startswith('---'):
            lines = content.split('\n')
            end_marker = -1
            
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == '---':
                    end_marker = i
                    break
            
            if end_marker > 0:
                return '\n'.join(lines[end_marker + 1:]).strip()
        
        return content.strip()
    
    def _format_content_to_html(self, content: str) -> str:
        """本文をHTMLに変換"""
        # 空行で段落を分割
        paragraphs = content.split('\n\n')
        html_content = []
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # Markdownヘッダーを変換
            if paragraph.startswith('# '):
                # h1タグに変換（記事タイトルとは区別するためh2を使用）
                header_text = paragraph[2:].strip()
                html_content.append(f'<h2>{header_text}</h2>')
            elif paragraph.startswith('## '):
                # h3タグに変換
                header_text = paragraph[3:].strip()
                html_content.append(f'<h3>{header_text}</h3>')
            elif paragraph.startswith('### '):
                # h4タグに変換
                header_text = paragraph[4:].strip()
                html_content.append(f'<h4>{header_text}</h4>')
            else:
                # 通常の段落として処理（改行を<br>に変換）
                formatted_paragraph = paragraph.replace('\n', '<br>')
                html_content.append(f'<p>{formatted_paragraph}</p>')
        
        return '\n'.join(html_content)
    
    def start_server(self, port: Optional[int] = None, auto_open: bool = True) -> bool:
        """Flaskサーバーを起動"""
        # ポートが指定されていない場合はデフォルトポートを使用
        if port is None:
            port = self.default_port
            
        try:
            # Flaskアプリを作成
            self.flask_app = self._create_flask_app()
            
            self.console.print(f"[cyan]🌐 Flaskサーバーを起動中... http://localhost:{port}[/cyan]")
            self.console.print("[dim]小説を読みやすい形で表示します[/dim]")
            
            # サーバーを別スレッドで起動
            def run_server():
                try:
                    self.flask_app.run(
                        host='0.0.0.0',
                        port=port,
                        debug=False,
                        use_reloader=False
                    )
                except OSError as e:
                    if "Address already in use" in str(e):
                        self.console.print(f"[red]エラー: ポート {port} は既に使用されています[/red]")
                        self.console.print(f"[yellow]ヒント: 別のポート番号を指定してください（例: --port 5001）[/yellow]")
                    else:
                        self.console.print(f"[red]サーバー起動エラー: {e}[/red]")
                except Exception as e:
                    self.console.print(f"[red]予期しないエラー: {e}[/red]")
            
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            
            # サーバーの起動を少し待つ
            time.sleep(2)
            
            # ブラウザを開く
            if auto_open:
                threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{port}")).start()
            
            self.console.print(f"[green]✓ Flaskサーバー起動完了[/green]")
            self.console.print(f"[dim]ブラウザで http://localhost:{port} を開いてください[/dim]")
            self.console.print("[dim]サーバーを停止するには Ctrl+C を押してください[/dim]")
            
            return True
            
        except Exception as e:
            self.console.print(f"[red]エラー: Flaskサーバーの起動に失敗しました: {e}[/red]")
            return False
    
    def _create_flask_app(self):
        """Flaskアプリケーションを作成"""
        try:
            from flask import Flask, render_template_string, request, abort
        except ImportError:
            self.console.print("[red]エラー: Flaskがインストールされていません[/red]")
            self.console.print("[dim]pip install flask を実行してください[/dim]")
            raise
        
        app = Flask(__name__)
        
        # 静的ファイルのパスを設定
        from . import get_static_path
        static_path = get_static_path()
        
        @app.route('/')
        def index():
            """小説一覧ページ"""
            novels = list(self.novels_data.keys())
            return render_template_string(INDEX_TEMPLATE, novels=novels, novels_data=self.novels_data)
        
        @app.route('/novel/<novel_title>')
        def novel_index(novel_title):
            """特定の小説の話一覧"""
            if novel_title not in self.novels_data:
                abort(404)
            
            novel_data = self.novels_data[novel_title]
            return render_template_string(NOVEL_INDEX_TEMPLATE, novel=novel_data)
        
        @app.route('/novel/<novel_title>/<story_slug>')
        def story_detail(novel_title, story_slug):
            """個別のストーリー表示"""
            if novel_title not in self.novels_data:
                abort(404)
            
            novel_data = self.novels_data[novel_title]
            story = None
            story_index = -1
            
            for i, s in enumerate(novel_data['stories']):
                if s['slug'] == story_slug:
                    story = s
                    story_index = i
                    break
            
            if not story:
                abort(404)
            
            # 前後のストーリーを取得
            prev_story = novel_data['stories'][story_index - 1] if story_index > 0 else None
            next_story = novel_data['stories'][story_index + 1] if story_index < len(novel_data['stories']) - 1 else None
            
            return render_template_string(
                STORY_DETAIL_TEMPLATE, 
                novel=novel_data, 
                story=story, 
                prev_story=prev_story, 
                next_story=next_story,
                formatted_content=self._format_content_to_html(story['body'])
            )
        
        @app.route('/static/<path:filename>')
        def static_files(filename):
            """静的ファイルの提供"""
            from flask import send_from_directory
            return send_from_directory(str(static_path), filename)
        
        return app
    
    def wait_for_server(self):
        """サーバーの終了を待機"""
        if self.server_thread:
            try:
                while self.server_thread.is_alive():
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
    
    def cleanup(self):
        """リソースのクリーンアップ"""
        self.console.print("[dim]クリーンアップ中...[/dim]")
    
    def find_available_port(self, start_port: int = 5000, max_attempts: int = 10) -> Optional[int]:
        """利用可能なポートを見つける"""
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.bind(('localhost', port))
                    return port
            except OSError:
                continue
        return None


# HTMLテンプレート
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>小説リーダー</title>
    <link rel="stylesheet" type="text/css" href="/static/css/novel.css">
    <style>
        .novel-list {
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
        }
        .novel-card {
            background: white;
            margin: 20px 0;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 4px solid #007bff;
        }
        .novel-title {
            color: #2c3e50;
            font-size: 1.5em;
            margin-bottom: 10px;
            text-decoration: none;
        }
        .novel-title:hover {
            color: #007bff;
        }
        .novel-meta {
            color: #6c757d;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>小説リーダー</h1>
            <p>AIが生成した小説を読みやすく表示</p>
        </header>
        
        <div class="novel-list">
            <h2>利用可能な小説</h2>
            {% for novel_title in novels %}
            <div class="novel-card">
                <a href="/novel/{{ novel_title }}" class="novel-title">{{ novel_title }}</a>
                <div class="novel-meta">
                    {{ novels_data[novel_title]['stories']|length }}話
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

NOVEL_INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ novel.title }} - 小説リーダー</title>
    <link rel="stylesheet" type="text/css" href="/static/css/novel.css">
</head>
<body>
    <div class="container">
        <header>
            <h1><a href="/">小説リーダー</a></h1>
            <p>{{ novel.title }}</p>
        </header>
        
        <nav>
            <ul>
                <li><a href="/">ホーム</a></li>
            </ul>
        </nav>
        
        <div class="articles-list">
            <h2>{{ novel.title }} - 話一覧</h2>
            <ul>
                {% for story in novel.stories %}
                <li>
                    <a href="/novel/{{ novel.title }}/{{ story.slug }}">{{ story.title }}</a>
                    <div class="article-meta">
                        {{ story.date }}
                    </div>
                </li>
                {% endfor %}
            </ul>
        </div>
    </div>
</body>
</html>
"""

STORY_DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ story.title }} - {{ novel.title }}</title>
    <link rel="stylesheet" type="text/css" href="/static/css/novel.css">
</head>
<body>
    <div class="container">
        <header>
            <h1><a href="/">小説リーダー</a></h1>
            <p>{{ novel.title }}</p>
        </header>
        
        <nav>
            <ul>
                <li><a href="/">ホーム</a></li>
                <li><a href="/novel/{{ novel.title }}">{{ novel.title }}</a></li>
            </ul>
        </nav>
        
        <article>
            <h1>{{ story.title }}</h1>
            <div class="story-content">
                {{ formatted_content | safe }}
            </div>
            
            <div class="article-nav">
                {% if prev_story %}
                <div class="nav-prev">
                    <a href="/novel/{{ novel.title }}/{{ prev_story.slug }}" class="nav-link">
                        <span class="nav-label">前の話</span>
                        <span class="nav-title">{{ prev_story.title }}</span>
                    </a>
                </div>
                {% else %}
                <div class="nav-placeholder"></div>
                {% endif %}
                
                {% if next_story %}
                <div class="nav-next">
                    <a href="/novel/{{ novel.title }}/{{ next_story.slug }}" class="nav-link">
                        <span class="nav-label">次の話</span>
                        <span class="nav-title">{{ next_story.title }}</span>
                    </a>
                </div>
                {% else %}
                <div class="nav-placeholder"></div>
                {% endif %}
            </div>
        </article>
    </div>
</body>
</html>
"""
