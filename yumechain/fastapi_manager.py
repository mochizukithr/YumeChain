"""
FastAPI Web Server Manager

FastAPIを使ってMarkdownファイルをWebで表示するためのマネージャー
"""
import os
import threading
import webbrowser
import socket
from pathlib import Path
from typing import Optional, List, Dict, Any
import time
from rich.console import Console
from datetime import datetime
import re
import markdown
import uvicorn


class FastAPIServerManager:
    """FastAPIサーバーの管理クラス"""
    
    def __init__(self, base_dir: Path, default_port: int = 8000):
        self.base_dir = base_dir
        self.default_port = default_port
        self.console = Console()
        self.server_thread: Optional[threading.Thread] = None
        self.fastapi_app = None
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

    def prepare_all_content(self) -> bool:
        """booksフォルダ内のすべての小説コンテンツを準備"""
        try:
            books_dir = self.base_dir / "books"
            if not books_dir.exists():
                self.console.print(f"[red]エラー: {books_dir} が見つかりません[/red]")
                return False
            
            # booksディレクトリ内のすべてのフォルダを取得
            novel_dirs = [d for d in books_dir.iterdir() if d.is_dir()]
            if not novel_dirs:
                self.console.print(f"[yellow]警告: {books_dir} に小説フォルダが見つかりません[/yellow]")
                return False
            
            success_count = 0
            for novel_dir in novel_dirs:
                title = novel_dir.name
                if self.prepare_content(title):
                    success_count += 1
                else:
                    self.console.print(f"[yellow]警告: {title} の準備をスキップしました[/yellow]")
            
            if success_count == 0:
                self.console.print("[red]エラー: 読み込める小説が見つかりませんでした[/red]")
                return False
            
            self.console.print(f"[green]✓ 全体のコンテンツ準備完了: {success_count}個の小説[/green]")
            return True
            
        except Exception as e:
            self.console.print(f"[red]エラー: 全体のコンテンツ準備中にエラーが発生しました: {e}[/red]")
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
        """MarkdownをHTMLに変換"""
        # markdownライブラリを使用してHTMLに変換
        html = markdown.markdown(
            content,
            extensions=['extra', 'codehilite', 'toc'],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight'
                }
            }
        )
        return html
    
    def start_server(self, port: Optional[int] = None, auto_open: bool = True) -> bool:
        """FastAPIサーバーを起動"""
        # ポートが指定されていない場合はデフォルトポートを使用
        if port is None:
            port = self.default_port
            
        try:
            # FastAPIアプリを作成
            self.fastapi_app = self._create_fastapi_app()
            
            self.console.print(f"[cyan]🌐 FastAPIサーバーを起動中... http://localhost:{port}[/cyan]")
            self.console.print("[dim]小説を読みやすい形で表示します[/dim]")
            
            # サーバーを別スレッドで起動
            def run_server():
                try:
                    uvicorn.run(
                        self.fastapi_app,
                        host="0.0.0.0",
                        port=port,
                        log_level="info"
                    )
                except OSError as e:
                    if "Address already in use" in str(e):
                        self.console.print(f"[red]エラー: ポート {port} は既に使用されています[/red]")
                        self.console.print(f"[yellow]ヒント: 別のポート番号を指定してください（例: --port 8001）[/yellow]")
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
            
            self.console.print(f"[green]✓ FastAPIサーバー起動完了[/green]")
            self.console.print(f"[dim]ブラウザで http://localhost:{port} を開いてください[/dim]")
            self.console.print(f"[dim]API仕様は http://localhost:{port}/docs で確認できます[/dim]")
            self.console.print("[dim]サーバーを停止するには Ctrl+C を押してください[/dim]")
            
            return True
            
        except Exception as e:
            self.console.print(f"[red]エラー: FastAPIサーバーの起動に失敗しました: {e}[/red]")
            return False
    
    def _create_fastapi_app(self):
        """FastAPIアプリケーションを作成"""
        try:
            from fastapi import FastAPI, HTTPException
            from fastapi.responses import HTMLResponse, JSONResponse
            from fastapi.staticfiles import StaticFiles
            from fastapi.templating import Jinja2Templates
            from fastapi import Request
            from pydantic import BaseModel
        except ImportError:
            self.console.print("[red]エラー: FastAPIがインストールされていません[/red]")
            self.console.print("[dim]uv add fastapi uvicorn jinja2 を実行してください[/dim]")
            raise
        
        app = FastAPI(
            title="小説リーダー API",
            description="AIが生成した小説を読みやすく表示するAPI",
            version="1.0.0"
        )
        
        # テンプレートエンジンの設定
        templates_dir = Path(__file__).parent / "templates"
        templates = Jinja2Templates(directory=str(templates_dir))
        
        # レスポンスモデル
        class NovelInfo(BaseModel):
            title: str
            story_count: int
            metadata: Dict[str, Any]
        
        class StoryInfo(BaseModel):
            filename: str
            slug: str
            title: str
            arc: str
            episode: str
            date: str
            metadata: Dict[str, Any]
        
        class StoryDetail(BaseModel):
            filename: str
            slug: str
            title: str
            arc: str
            episode: str
            date: str
            body: str
            html_content: str
            metadata: Dict[str, Any]
        
        # 静的ファイルのマウント
        static_path = Path(__file__).parent / "static"
        if static_path.exists():
            app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
        
        @app.get("/", response_class=HTMLResponse)
        async def root(request: Request):
            """ルートページ - 小説一覧（HTMX版）"""
            novels = list(self.novels_data.keys())
            novel_data = {}
            for title, data in self.novels_data.items():
                novel_data[title] = {
                    'story_count': len(data['stories'])
                }
            
            return templates.TemplateResponse("index.html", {
                "request": request,
                "novels": novels,
                "novel_data": novel_data
            })
        
        @app.get("/api/novels", response_model=Dict[str, NovelInfo])
        async def get_novels():
            """小説一覧を取得"""
            result = {}
            for title, data in self.novels_data.items():
                result[title] = NovelInfo(
                    title=title,
                    story_count=len(data['stories']),
                    metadata=data.get('metadata', {})
                )
            return result
        
        @app.get("/api/novels/{novel_title}", response_model=NovelInfo)
        async def get_novel(novel_title: str):
            """特定の小説の情報を取得"""
            if novel_title not in self.novels_data:
                raise HTTPException(status_code=404, detail="小説が見つかりません")
            
            data = self.novels_data[novel_title]
            return NovelInfo(
                title=novel_title,
                story_count=len(data['stories']),
                metadata=data.get('metadata', {})
            )
        
        @app.get("/api/novels/{novel_title}/stories", response_model=List[StoryInfo])
        async def get_stories(novel_title: str):
            """特定の小説のエピソード一覧を取得"""
            if novel_title not in self.novels_data:
                raise HTTPException(status_code=404, detail="小説が見つかりません")
            
            stories = self.novels_data[novel_title]['stories']
            return [
                StoryInfo(
                    filename=story['filename'],
                    slug=story['slug'],
                    title=story['title'],
                    arc=story['arc'],
                    episode=story['episode'],
                    date=story['date'],
                    metadata=story['metadata']
                )
                for story in stories
            ]
        
        @app.get("/api/novels/{novel_title}/stories/{story_slug}", response_model=StoryDetail)
        async def get_story(novel_title: str, story_slug: str):
            """特定のエピソードの詳細を取得"""
            if novel_title not in self.novels_data:
                raise HTTPException(status_code=404, detail="小説が見つかりません")
            
            stories = self.novels_data[novel_title]['stories']
            story = None
            
            for s in stories:
                if s['slug'] == story_slug:
                    story = s
                    break
            
            if not story:
                raise HTTPException(status_code=404, detail="エピソードが見つかりません")
            
            return StoryDetail(
                filename=story['filename'],
                slug=story['slug'],
                title=story['title'],
                arc=story['arc'],
                episode=story['episode'],
                date=story['date'],
                body=story['body'],
                html_content=self._format_content_to_html(story['body']),
                metadata=story['metadata']
            )
        
        @app.get("/api/novels/{novel_title}/stories/{story_slug}/html", response_class=HTMLResponse)
        async def get_story_html(novel_title: str, story_slug: str):
            """特定のエピソードをHTML形式で表示"""
            if novel_title not in self.novels_data:
                raise HTTPException(status_code=404, detail="小説が見つかりません")
            
            stories = self.novels_data[novel_title]['stories']
            story = None
            story_index = -1
            
            for i, s in enumerate(stories):
                if s['slug'] == story_slug:
                    story = s
                    story_index = i
                    break
            
            if not story:
                raise HTTPException(status_code=404, detail="エピソードが見つかりません")
            
            # 前後のストーリーを取得
            prev_story = stories[story_index - 1] if story_index > 0 else None
            next_story = stories[story_index + 1] if story_index < len(stories) - 1 else None
            
            html_content = f"""
            <!DOCTYPE html>
            <html lang="ja">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{story['title']} - {novel_title}</title>
                <style>
                    body {{ font-family: 'Noto Sans JP', serif; line-height: 1.8; margin: 0; padding: 20px; background: #f9f9f9; }}
                    .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                    h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                    .nav {{ display: flex; justify-content: space-between; margin: 30px 0; }}
                    .nav a {{ padding: 10px 20px; background: #3498db; color: white; text-decoration: none; border-radius: 5px; }}
                    .nav a:hover {{ background: #2980b9; }}
                    .story-content {{ margin: 30px 0; }}
                    .story-content p {{ margin-bottom: 1.5em; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <nav>
                        <a href="/">ホーム</a>
                        <a href="/api/novels/{novel_title}/stories">エピソード一覧</a>
                    </nav>
                    
                    <h1>{story['title']}</h1>
                    <div class="story-content">
                        {self._format_content_to_html(story['body'])}
                    </div>
                    
                    <div class="nav">
                        {'<a href="/api/novels/' + novel_title + '/stories/' + prev_story['slug'] + '/html">前: ' + prev_story['title'] + '</a>' if prev_story else '<div></div>'}
                        {'<a href="/api/novels/' + novel_title + '/stories/' + next_story['slug'] + '/html">次: ' + next_story['title'] + '</a>' if next_story else '<div></div>'}
                    </div>
                </div>
            </body>
            </html>
            """
            return html_content
        
        @app.get("/novel/{novel_title}", response_class=HTMLResponse)
        async def get_novel_page(request: Request, novel_title: str):
            """小説のエピソード一覧ページ（HTMX）"""
            if novel_title not in self.novels_data:
                return templates.TemplateResponse("novel_detail.html", {
                    "request": request,
                    "novel_found": False,
                    "novel_title": novel_title
                })
            
            data = self.novels_data[novel_title]
            stories = data['stories']
            
            return templates.TemplateResponse("novel_detail.html", {
                "request": request,
                "novel_found": True,
                "novel_title": novel_title,
                "story_count": len(stories),
                "last_updated": stories[-1]['date'] if stories else '不明',
                "stories": stories
            })
        
        @app.get("/novel/{novel_title}/episode/{story_slug}", response_class=HTMLResponse)
        async def get_episode_page(request: Request, novel_title: str, story_slug: str):
            """エピソード表示ページ（HTMX）"""
            if novel_title not in self.novels_data:
                return templates.TemplateResponse("episode_reader.html", {
                    "request": request,
                    "story_found": False
                })
            
            stories = self.novels_data[novel_title]['stories']
            story = None
            story_index = -1
            
            for i, s in enumerate(stories):
                if s['slug'] == story_slug:
                    story = s
                    story_index = i
                    break
            
            if not story:
                return templates.TemplateResponse("episode_reader.html", {
                    "request": request,
                    "story_found": False
                })
            
            # 前後のストーリーを取得
            prev_story = stories[story_index - 1] if story_index > 0 else None
            next_story = stories[story_index + 1] if story_index < len(stories) - 1 else None
            
            # HTMLコンテンツを生成
            story_with_html = story.copy()
            story_with_html['html_content'] = self._format_content_to_html(story['body'])
            
            return templates.TemplateResponse("episode_reader.html", {
                "request": request,
                "story_found": True,
                "novel_title": novel_title,
                "story": story_with_html,
                "prev_story": prev_story,
                "next_story": next_story
            })
        
        @app.get("/search", response_class=HTMLResponse)
        async def search_novels(request: Request, q: str = ""):
            """小説検索機能（HTMX）"""
            query = q.strip()
            
            if not query:
                # 空の検索の場合は全小説を表示
                novels = list(self.novels_data.keys())
            else:
                # 簡単な検索実装（タイトルまたはストーリータイトルに含まれるかチェック）
                novels = []
                query_lower = query.lower()
                for novel_title, data in self.novels_data.items():
                    if query_lower in novel_title.lower():
                        novels.append(novel_title)
                    else:
                        # ストーリーのタイトルもチェック
                        for story in data['stories']:
                            if query_lower in story['title'].lower():
                                novels.append(novel_title)
                                break
            
            # 小説データを準備
            novel_data = {}
            for title in novels:
                novel_data[title] = {
                    'story_count': len(self.novels_data[title]['stories'])
                }
            
            return templates.TemplateResponse("search_results.html", {
                "request": request,
                "novels": novels,
                "novel_data": novel_data
            })

        return app
    
    def wait_for_server(self):
        """サーバーの終了を待機"""
        if hasattr(self, 'server_thread') and self.server_thread:
            try:
                while self.server_thread.is_alive():
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
    
    def cleanup(self):
        """リソースのクリーンアップ"""
        self.console.print("[dim]クリーンアップ中...[/dim]")
    
    def find_available_port(self, start_port: int = 8000, max_attempts: int = 10) -> Optional[int]:
        """利用可能なポートを見つける"""
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.bind(('localhost', port))
                    return port
            except OSError:
                continue
        return None
