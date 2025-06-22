"""
Pelican Web Server Manager

Pelicanを使ってMarkdownファイルをWebで表示するためのマネージャー
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import time
import threading
import webbrowser
from rich.console import Console

class PelicanServerManager:
    """Pelicanサーバーの管理クラス"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.temp_dir: Optional[Path] = None
        self.server_process: Optional[subprocess.Popen] = None
        self.console = Console()
        
    def prepare_content(self, title: str) -> bool:
        """指定されたタイトルの小説コンテンツを準備"""
        try:
            # ソースディレクトリ
            source_dir = self.base_dir / "books" / title
            stories_dir = source_dir / "stories"
            
            if not stories_dir.exists():
                self.console.print(f"[red]エラー: {stories_dir} が見つかりません[/red]")
                return False
            
            # 一時ディレクトリの作成
            if self.temp_dir:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = Path(tempfile.mkdtemp(prefix="pelican_"))
            
            # contentディレクトリの作成
            content_dir = self.temp_dir / "content"
            content_dir.mkdir(parents=True)
            
            # storiesディレクトリのmarkdownファイルをコピー
            story_files = list(stories_dir.glob("*.md"))
            if not story_files:
                self.console.print(f"[yellow]警告: {stories_dir} にMarkdownファイルが見つかりません[/yellow]")
                return False
                
            for story_file in story_files:
                # ファイルを直接contentディレクトリにコピー（カテゴリなし）
                dest_file = content_dir / story_file.name
                
                # ファイルの内容を読み、メタデータを確認・追加
                content = story_file.read_text(encoding='utf-8')
                
                # メタデータがある場合はカテゴリを追加/更新
                if content.startswith('---'):
                    lines = content.split('\n')
                    front_matter_end = -1
                    category_found = False
                    
                    # フロントマターの終わりを見つける
                    for i, line in enumerate(lines[1:], 1):
                        if line.strip() == '---':
                            front_matter_end = i
                            break
                    
                    if front_matter_end > 0:
                        # ファイル名ベースの簡単なスラッグを生成
                        slug = story_file.stem.replace('_', '-').lower()
                        
                        # カテゴリが既に存在するかチェック
                        category_found = False
                        slug_found = False
                        new_lines = []
                        
                        for i in range(1, front_matter_end):
                            line = lines[i]
                            if line.startswith('category:'):
                                category_found = True
                                new_lines.append(f'category: {title}')
                            elif line.startswith('slug:'):
                                slug_found = True
                                new_lines.append(f'slug: {slug}')
                            elif line.startswith('lang:'):
                                # lang属性をスキップ
                                continue
                            elif line.startswith('date:'):
                                # 引用符を削除してフォーマット修正
                                if '"' in line:
                                    date_value = line.split('"')[1]
                                    new_lines.append(f'date: {date_value}')
                                else:
                                    new_lines.append(line)
                            else:
                                new_lines.append(line)
                        
                        # カテゴリが見つからない場合は追加
                        if not category_found:
                            new_lines.append(f'category: {title}')
                        
                        # スラッグが見つからない場合は追加
                        if not slug_found:
                            new_lines.append(f'slug: {slug}')
                        
                        # 新しいフロントマターを構築
                        lines = [lines[0]] + new_lines + lines[front_matter_end:]
                        
                        content = '\n'.join(lines)
                else:
                    # メタデータがない場合は基本的なメタデータを追加
                    file_title = story_file.stem.replace('_', ' ')
                    slug = story_file.stem.replace('_', '-').lower()
                    metadata = f"""---
title: "{file_title}"
date: {time.strftime('%Y-%m-%d')}
category: {title}
slug: {slug}
---

"""
                    content = metadata + content
                
                # ファイルを書き込み
                dest_file.write_text(content, encoding='utf-8')
                
                self.console.print(f"[dim]コピー: {story_file.name}[/dim]")
            
            # Pelican設定ファイルをコピー
            config_source = self.base_dir / "pelican_config.py"
            config_dest = self.temp_dir / "pelicanconf.py"
            
            if config_source.exists():
                shutil.copy2(config_source, config_dest)
            else:
                self.console.print("[yellow]警告: pelican_config.py が見つかりません[/yellow]")
            
            # カスタムテーマをコピー
            theme_source = self.base_dir / "theme"
            if theme_source.exists():
                theme_dest = self.temp_dir / "theme"
                shutil.copytree(theme_source, theme_dest)
                self.console.print("[dim]カスタムテーマをコピーしました[/dim]")
            
            # 静的ファイルをコピー
            static_source = self.base_dir / "static"
            if static_source.exists():
                static_dest = content_dir / "static"
                shutil.copytree(static_source, static_dest)
                self.console.print("[dim]静的ファイルをコピーしました[/dim]")
                
            self.console.print(f"[green]✓ コンテンツ準備完了: {len(story_files)}ファイル[/green]")
            return True
            
        except Exception as e:
            self.console.print(f"[red]エラー: コンテンツ準備中にエラーが発生しました: {e}[/red]")
            return False
    
    def build_site(self) -> bool:
        """Pelicanでサイトをビルド"""
        if not self.temp_dir:
            self.console.print("[red]エラー: コンテンツが準備されていません[/red]")
            return False
        
        try:
            # Pelicanでビルド
            cmd = [
                "pelican",
                str(self.temp_dir / "content"),
                "-s", str(self.temp_dir / "pelicanconf.py"),
                "-o", str(self.temp_dir / "output"),
                "-v"  # 詳細出力
            ]
            
            self.console.print("[dim]サイトをビルド中...[/dim]")
            result = subprocess.run(
                cmd,
                cwd=self.temp_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.console.print("[green]✓ サイトビルド完了[/green]")
                if result.stdout:
                    self.console.print(f"[dim]ビルド出力: {result.stdout}[/dim]")
                return True
            else:
                self.console.print(f"[red]ビルドエラー: {result.stderr}[/red]")
                if result.stdout:
                    self.console.print(f"[yellow]標準出力: {result.stdout}[/yellow]")
                return False
                
        except FileNotFoundError:
            self.console.print("[red]エラー: Pelicanが見つかりません。インストールしてください。[/red]")
            return False
        except Exception as e:
            self.console.print(f"[red]ビルドエラー: {e}[/red]")
            return False
    
    def start_server(self, port: int = 8000, auto_open: bool = True) -> bool:
        """開発サーバーを起動"""
        if not self.temp_dir:
            self.console.print("[red]エラー: サイトがビルドされていません[/red]")
            return False
        
        output_dir = self.temp_dir / "output"
        if not output_dir.exists():
            self.console.print("[red]エラー: 出力ディレクトリが見つかりません[/red]")
            return False
        
        try:
            # Pelicanの開発サーバーを起動（autoreload有効）
            cmd = [
                "pelican",
                "--listen",
                "--autoreload",
                "--bind", "127.0.0.1",
                "--port", str(port),
                "-s", str(self.temp_dir / "pelicanconf.py"),
                "-o", str(output_dir)
            ]
            
            self.console.print(f"[cyan]🌐 Pelicanサーバーを起動中... http://localhost:{port}[/cyan]")
            self.console.print("[dim]autoreload有効 - ファイル変更時に自動リビルドします[/dim]")
            
            self.server_process = subprocess.Popen(
                cmd,
                cwd=self.temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # サーバーの起動を少し待つ
            time.sleep(3)
            
            # ブラウザを開く
            if auto_open:
                threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{port}")).start()
            
            self.console.print(f"[green]✓ Pelicanサーバー起動完了[/green]")
            self.console.print(f"[dim]ブラウザで http://localhost:{port} を開いてください[/dim]")
            self.console.print("[dim]ファイルが変更されると自動的にリビルドされます[/dim]")
            self.console.print("[dim]サーバーを停止するには Ctrl+C を押してください[/dim]")
            
            return True
            
        except Exception as e:
            self.console.print(f"[red]サーバー起動エラー: {e}[/red]")
            return False
    
    def stop_server(self):
        """サーバーを停止"""
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
            self.server_process = None
            self.console.print("[yellow]サーバーを停止しました[/yellow]")
    
    def wait_for_server(self):
        """サーバーの終了を待機"""
        if self.server_process:
            try:
                self.server_process.wait()
            except KeyboardInterrupt:
                self.console.print("\n[yellow]サーバーを停止中...[/yellow]")
                self.stop_server()
    
    def cleanup(self):
        """リソースのクリーンアップ"""
        self.stop_server()
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = None
