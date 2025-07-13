"""
YumeChain CLI アプリケーション

LLM（Gemini）を使って設定から小説を生成するアプリケーション
"""
import click
import time
import sys
import termios
import tty
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table
from .llm_client import LLMClient
from .file_manager import FileManager
from .hatena_client import HatenaBlogClient
import json
import os

def getch():
    """単一文字を入力待ちして即座に返す（macOS/Linux用）"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def get_single_char_input(prompt_text, valid_chars, default=None):
    """
    単一文字入力を受け取る関数
    
    Args:
        prompt_text: プロンプトメッセージ
        valid_chars: 有効な文字のリスト
        default: デフォルト値（Enterが押された場合）
    
    Returns:
        入力された文字
    """
    console = Console()
    console.print(f"{prompt_text} ", end="")
    
    if default:
        console.print(f"[dim](デフォルト: {default})[/dim] ", end="")
    
    while True:
        try:
            char = getch()
            
            # Enterキーの場合
            if char == '\n' or char == '\r':
                if default:
                    console.print(default)
                    return default
                else:
                    console.print()
                    continue
            
            # Ctrl+Cの場合
            if ord(char) == 3:  # Ctrl+C
                console.print()
                raise KeyboardInterrupt
            
            # 有効な文字の場合
            if char in valid_chars:
                console.print(char)
                return char
            
            # 無効な文字の場合（何も表示せず続行）
            
        except KeyboardInterrupt:
            console.print("\n[yellow]操作がキャンセルされました[/yellow]")
            raise

def get_yes_no_input(prompt_text, default=None):
    """
    y/n の単一文字入力を受け取る関数
    
    Args:
        prompt_text: プロンプトメッセージ
        default: デフォルト値（'y' または 'n'）
    
    Returns:
        True (y の場合) または False (n の場合)
    """
    valid_chars = ['y', 'n', 'Y', 'N']
    result = get_single_char_input(prompt_text + " [y/n]", valid_chars, default)
    return result.lower() == 'y'

def show_interactive_menu():
    """インタラクティブなメニューを表示"""
    console = Console()
    
    while True:
        console.clear()
        console.print("\n[bold cyan]📚 小説生成アプリ - メニュー[/bold cyan]")
        console.print("[dim]LLMを使って小説を自動生成します[/dim]\n")
        
        # メニューテーブルを作成
        table = Table(show_header=True, header_style="bold green")
        table.add_column("番号", style="cyan", no_wrap=True)
        table.add_column("コマンド", style="magenta")
        table.add_column("説明", style="white")
        
        table.add_row("1", "init", "新しい小説プロジェクトを初期化")
        table.add_row("2", "status", "プロジェクトの状態を表示")
        table.add_row("3", "generate-plot", "設定ファイルからプロットを生成")
        table.add_row("4", "generate-episode", "指定した話の本文を生成")
        table.add_row("5", "read", "小説をWebブラウザで読む")
        table.add_row("6", "publish", "小説をはてなブログに投稿")
        table.add_row("0", "exit", "終了")
        
        console.print(table)
        console.print()
        
        choice = get_single_char_input("[cyan]選択してください[/cyan]", ["0", "1", "2", "3", "4", "5", "6"], "0")
        
        if choice == "0":
            console.print("[yellow]アプリを終了します。[/yellow]")
            break
        elif choice == "1":
            handle_init_command()
        elif choice == "2":
            handle_status_command()
        elif choice == "3":
            handle_generate_plot_command()
        elif choice == "4":
            handle_generate_episode_command()
        elif choice == "5":
            handle_read_command()
        elif choice == "6":
            handle_publish_command()
        
        console.print("\n[dim]Press any key to continue...[/dim]")
        getch()

def get_available_novels():
    """利用可能な小説のリストを取得"""
    books_dir = Path("books")
    if not books_dir.exists():
        return []
    return [d.name for d in books_dir.iterdir() if d.is_dir()]

def select_novel_title():
    """小説タイトルを選択"""
    console = Console()
    novels = get_available_novels()
    
    if not novels:
        console.print("[red]❌ 利用可能な小説プロジェクトがありません[/red]")
        console.print("[dim]まず 'init' コマンドで新しいプロジェクトを作成してください[/dim]")
        return None
    
    console.print("\n[bold]📚 利用可能な小説:[/bold]")
    for i, novel in enumerate(novels, 1):
        console.print(f"  {i}. {novel}")
    console.print(f"  0. 新しい名前を入力")
    
    # 有効な選択肢を作成
    valid_choices = [str(i) for i in range(len(novels) + 1)]
    
    while True:
        choice = get_single_char_input("\n[cyan]選択してください[/cyan]", valid_choices, "1")
        
        if choice == "0":
            return Prompt.ask("[cyan]小説のタイトルを入力[/cyan]")
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(novels):
                return novels[idx]
        except ValueError:
            pass
        
        console.print("[red]無効な選択です。もう一度選択してください。[/red]")

def get_available_arcs(title):
    """指定した小説の利用可能な編を取得"""
    fm = FileManager()
    try:
        plot_data = fm.read_plot(title)
        return list(plot_data.keys())
    except:
        return []

def parse_episode_numbers(episodes_str, max_episode):
    """
    エピソード番号の文字列を解析して、エピソード番号のリストを返す
    
    Args:
        episodes_str: エピソード番号の文字列（例: "1", "1,3,5", "2-5", "1-3,7,9-10"）
        max_episode: 最大エピソード番号
    
    Returns:
        list: エピソード番号のリスト
    
    Raises:
        ValueError: 無効な形式の場合
    """
    episodes = set()
    
    # カンマで分割
    parts = episodes_str.split(',')
    
    for part in parts:
        part = part.strip()
        
        if '-' in part:
            # 範囲指定（例: "2-5"）
            try:
                start, end = part.split('-', 1)
                start = int(start.strip())
                end = int(end.strip())
                
                if start > end:
                    raise ValueError(f"範囲が無効です: {part} (開始が終了より大きい)")
                
                for ep in range(start, end + 1):
                    if 1 <= ep <= max_episode:
                        episodes.add(ep)
                    else:
                        raise ValueError(f"エピソード番号 {ep} は範囲外です (1-{max_episode})")
                        
            except ValueError as e:
                if "invalid literal" in str(e):
                    raise ValueError(f"無効な範囲形式: {part}")
                raise
        else:
            # 単一の番号
            try:
                ep = int(part)
                if 1 <= ep <= max_episode:
                    episodes.add(ep)
                else:
                    raise ValueError(f"エピソード番号 {ep} は範囲外です (1-{max_episode})")
            except ValueError as e:
                if "invalid literal" in str(e):
                    raise ValueError(f"無効な番号: {part}")
                raise
    
    return sorted(list(episodes))

def select_arc_and_episodes(title):
    """編と話数（複数対応）を選択"""
    console = Console()
    arcs = get_available_arcs(title)
    
    if not arcs:
        console.print("[red]❌ プロットが見つかりません[/red]")
        console.print("[dim]まず 'generate-plot' コマンドでプロットを生成してください[/dim]")
        return None, None
    
    console.print(f"\n[bold]📖 '{title}' の利用可能な編:[/bold]")
    for i, arc in enumerate(arcs, 1):
        console.print(f"  {i}. {arc}")
    
    # 有効な選択肢を作成
    valid_choices = [str(i) for i in range(1, len(arcs) + 1)]
    
    while True:
        choice = get_single_char_input("\n[cyan]編を選択してください[/cyan]", valid_choices, "1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(arcs):
                selected_arc = arcs[idx]
                break
        except ValueError:
            pass
        console.print("[red]無効な選択です。もう一度選択してください。[/red]")
    
    # 話数の選択（複数対応）
    fm = FileManager()
    try:
        plot_data = fm.read_plot(title)
        episodes = plot_data[selected_arc]
        max_episode = len(episodes)
        
        console.print(f"\n[bold]📝 '{selected_arc}' の話数 (1-{max_episode}):[/bold]")
        console.print("[dim]例: 1, 1-3, 1,3,5, 2-4,7,9-10[/dim]")
        
        while True:
            episodes_str = Prompt.ask("[cyan]話数を入力してください[/cyan]", default="1")
            
            try:
                episode_list = parse_episode_numbers(episodes_str, max_episode)
                if episode_list:
                    return selected_arc, episode_list
                else:
                    console.print("[red]有効なエピソード番号を入力してください。[/red]")
            except ValueError as e:
                console.print(f"[red]エラー: {str(e)}[/red]")
                console.print(f"[dim]有効な範囲: 1-{max_episode}[/dim]")
                
    except:
        console.print("[red]プロットの読み込みに失敗しました[/red]")
        return None, None

def handle_init_command():
    """'init' コマンドの処理"""
    title = Prompt.ask("[cyan]小説のタイトルを入力[/cyan]")
    console = Console()
    try:
        console.print(f"[bold cyan]🚀 新しい小説プロジェクトを初期化します[/bold cyan]")
        console.print(f"[dim]作品名: {title}[/dim]")
        
        fm = FileManager()
        fm.create_novel_structure(title)
        
        console.print(f"[green]✓ Novel project '{title}' initialized![/green]")
        console.print(f"[dim]次のステップ: {title}/setting.md を編集してから 'generate-plot' を実行してください[/dim]")
    except Exception as e:
        console.print(f"[red]✗ エラー: {str(e)}[/red]")

def handle_status_command():
    """'status' コマンドの処理"""
    title = select_novel_title()
    if not title:
        return
    
    console = Console()
    try:
        fm = FileManager()
        novel_dir = fm.get_novel_dir(title)
        
        if not novel_dir.exists():
            console.print(f"[red]✗ Novel project '{title}' does not exist.[/red]")
            return
        
        console.print(f"[bold cyan]📊 Novel project: {title}[/bold cyan]")
        console.print(f"[dim]Directory: {novel_dir}[/dim]")
        
        # setting.md の状態
        setting_file = novel_dir / "setting.md"
        if setting_file.exists():
            console.print("[green]✓ setting.md exists[/green]")
        else:
            console.print("[red]✗ setting.md missing[/red]")
        
        # character.md の状態
        character_file = novel_dir / "character.md"
        if character_file.exists():
            console.print("[green]✓ character.md exists[/green]")
        else:
            console.print("[yellow]○ character.md missing (optional)[/yellow]")
        
        # plot.json の状態
        plot_file = novel_dir / "plot.json"
        if plot_file.exists():
            console.print("[green]✓ plot.json exists[/green]")
            try:
                plot_data = fm.read_plot(title)
                total_episodes = sum(len(episodes) for episodes in plot_data.values())
                console.print(f"[dim]  - {len(plot_data)} arcs, {total_episodes} episodes planned[/dim]")
            except:
                console.print("[red]  - (corrupted plot file)[/red]")
        else:
            console.print("[red]✗ plot.json missing[/red]")
        
        # stories の状態
        stories_dir = novel_dir / "stories"
        if stories_dir.exists():
            story_files = list(stories_dir.glob("*.md"))
            console.print(f"[green]✓ stories/ directory with {len(story_files)} episodes[/green]")
        else:
            console.print("[red]✗ stories/ directory missing[/red]")
            
    except Exception as e:
        console.print(f"[red]✗ エラー: {str(e)}[/red]")

def handle_generate_plot_command():
    """'generate-plot' コマンドの処理"""
    title = select_novel_title()
    if not title:
        return
    
    console = Console()
    console.print(f"[bold cyan]🛠️ プロット生成中...[/bold cyan]")
    
    try:
        fm = FileManager()
        setting = fm.read_setting(title)
        
        # LLMを使ってプロットを生成
        llm = LLMClient.create_for_plot_generation()
        plot = llm.generate_plot(setting)
        
        # プロットをファイルに保存
        fm.save_plot(title, plot)
        
        console.print(f"[green]✓ プロットが生成されました: {title}/plot.json[/green]")
    except Exception as e:
        console.print(f"[red]✗ エラー: {str(e)}[/red]")

def handle_generate_episode_command():
    """'generate-episode' コマンドの処理"""
    title = select_novel_title()
    if not title:
        return
    
    console = Console()
    
    # 利用可能な編を取得
    arcs = get_available_arcs(title)
    if not arcs:
        console.print("[red]❌ プロットが見つかりません[/red]")
        console.print("[dim]まず 'generate-plot' コマンドでプロットを生成してください[/dim]")
        return
    
    # 編の選択
    selected_arc, episode_list = select_arc_and_episodes(title)
    if not selected_arc or not episode_list:
        return
    
    console.print(f"[bold cyan]🛠️ エピソード生成中...[/bold cyan]")
    
    try:
        fm = FileManager()
        setting = fm.read_setting(title)
        plot_data = fm.read_plot(title)
        
        # 各エピソードを生成
        llm = LLMClient.create_for_episode_generation()
        for episode_number in episode_list:
            console.print(f"\n[bold]エピソード {episode_number} を生成中...[/bold]")
            
            # LLMを使ってエピソードを生成（新しい方式：コンテキスト付きエピソード生成）
            episode_content = llm.generate_episode_with_context(
                book_title=title,
                setting_content=setting,
                arc=selected_arc,
                episode=episode_number,
                plot_data=plot_data
            )
            
            # エピソードをファイルに保存
            fm.save_episode(title, selected_arc, episode_number, episode_content)
        
        console.print(f"[green]✓ エピソードが生成されました: {title}/stories/[/green]")
    except Exception as e:
        console.print(f"[red]✗ エラー: {str(e)}[/red]")

def handle_read_command():
    """'read' コマンドの処理"""
    console = Console()
    
    # ポート番号を入力
    port = IntPrompt.ask(
        "[cyan]サーバーポート番号を入力してください[/cyan]",
        default=8000,
        show_default=True
    )
    
    # 自動ポート検索の選択
    auto_port = Confirm.ask(
        "[cyan]ポートが使用中の場合、自動で別のポートを探しますか？[/cyan]",
        default=True
    )
    
    # ブラウザ自動起動の選択
    auto_open = Confirm.ask(
        "[cyan]ブラウザを自動で開きますか？[/cyan]",
        default=True
    )
    
    try:
        base_dir = Path.cwd()
        
        # FastAPIServerManager を使用
        from .fastapi_manager import FastAPIServerManager
        manager = FastAPIServerManager(base_dir, default_port=port)
        
        # 自動ポート検索が有効な場合
        if auto_port:
            available_port = manager.find_available_port(start_port=port)
            if available_port and available_port != port:
                port = available_port
                console.print(f"[cyan]💡 利用可能なポートを見つけました: {port}[/cyan]")
        
        # 全ての小説のコンテンツを準備
        if not manager.prepare_all_content():
            console.print("[red]✗ コンテンツの準備に失敗しました[/red]")
            return
        
        # サーバーを起動
        if not manager.start_server(port=port, auto_open=auto_open):
            console.print("[red]✗ サーバーの起動に失敗しました[/red]")
            return
        
        console.print(f"[bold green]✓ 小説をFastAPIで表示中...[/bold green]")
        console.print(f"[dim]URL: http://localhost:{port}[/dim]")
        
        # サーバーの終了を待機
        manager.wait_for_server()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]サーバーを停止中...[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ エラー: {str(e)}[/red]")
    finally:
        if 'manager' in locals():
            manager.cleanup()

def handle_publish_command():
    """'publish' コマンドの処理"""
    title = select_novel_title()
    if not title:
        return
    
    console = Console()
    
    # はてなブログの認証情報を環境変数から取得
    hatena_username = os.getenv('HATENA_USERNAME')
    hatena_api_key = os.getenv('HATENA_API_KEY')
    hatena_blog_id = os.getenv('HATENA_BLOG_ID')
    
    if not all([hatena_username, hatena_api_key, hatena_blog_id]):
        console.print("[red]✗ はてなブログの認証情報が設定されていません[/red]")
        console.print("[yellow]以下の環境変数を .env ファイルに設定してください:[/yellow]")
        console.print("- HATENA_USERNAME (はてなユーザー名)")
        console.print("- HATENA_API_KEY (はてなブログAPI キー)")
        console.print("- HATENA_BLOG_ID (ブログID、例: xxxxx.hatenablog.com)")
        return
    
    # エピソード一覧を表示
    fm = FileManager()
    novel_dir = fm.get_novel_dir(title)
    stories_dir = novel_dir / "stories"
    
    if not stories_dir.exists():
        console.print(f"[red]✗ stories ディレクトリが見つかりません: {stories_dir}[/red]")
        return
    
    story_files = list(stories_dir.glob("*.md"))
    if not story_files:
        console.print("[yellow]投稿可能なエピソードが見つかりません[/yellow]")
        return
    
    console.print(f"\n[bold cyan]📚 投稿可能なエピソード ({title})[/bold cyan]")
    table = Table()
    table.add_column("No.", style="cyan", no_wrap=True)
    table.add_column("エピソード名", style="white")
    
    episodes = []
    for i, story_file in enumerate(sorted(story_files), 1):
        episode_name = story_file.stem
        episodes.append(episode_name)
        table.add_row(str(i), episode_name)
    
    console.print(table)
    
    # エピソードの選択
    choice = IntPrompt.ask("\n[cyan]投稿するエピソード番号を入力[/cyan]", 
                         default=1, 
                         choices=[str(i) for i in range(1, len(episodes) + 1)])
    
    selected_episode = episodes[choice - 1]
    
    # 追加オプションの選択
    blog_title = Prompt.ask("[cyan]ブログ記事のタイトル[/cyan] (Enterでデフォルト)", default="")
    categories = Prompt.ask("[cyan]カテゴリ (カンマ区切り)[/cyan]", default="")
    draft = Confirm.ask("[cyan]下書きとして投稿しますか？[/cyan]", default=False)
    
    # 投稿処理を実行
    try:
        # エピソード内容を読み込み
        episode_file = stories_dir / f"{selected_episode}.md"
        with open(episode_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # ブログタイトルを決定
        final_blog_title = blog_title if blog_title else f"{title} - {selected_episode}"
        
        # カテゴリを処理
        category_list = []
        if categories:
            category_list = [cat.strip() for cat in categories.split(',')]
        
        # はてなブログクライアントを初期化
        hatena_client = HatenaBlogClient(hatena_username, hatena_api_key, hatena_blog_id)
        
        # 投稿確認
        console.print(f"\n[bold cyan]📤 はてなブログに投稿します[/bold cyan]")
        console.print(f"[dim]ブログ: {hatena_blog_id}[/dim]")
        console.print(f"[dim]タイトル: {final_blog_title}[/dim]")
        console.print(f"[dim]下書き: {'はい' if draft else 'いいえ'}[/dim]")
        
        if not get_yes_no_input("投稿を実行しますか？", 'n'):
            console.print("[yellow]投稿がキャンセルされました[/yellow]")
            return
        
        # 投稿を実行
        console.print("[cyan]投稿中...[/cyan]")
        result = hatena_client.create_entry(
            title=final_blog_title,
            content=content,
            categories=category_list,
            draft=draft
        )
        
        # 結果を表示
        entry_data = result.get('entry', {})
        entry_link = None
        
        # リンクを取得
        if 'link' in entry_data:
            links = entry_data['link']
            if isinstance(links, list):
                for link in links:
                    if isinstance(link, dict) and link.get('@rel') == 'alternate':
                        entry_link = link.get('@href')
                        break
            elif isinstance(links, dict) and links.get('@rel') == 'alternate':
                entry_link = links.get('@href')
        
        console.print(f"[bold green]✓ はてなブログに投稿が完了しました！[/bold green]")
        console.print(f"[dim]タイトル: {final_blog_title}[/dim]")
        if entry_link:
            console.print(f"[dim]URL: {entry_link}[/dim]")
        
        if draft:
            console.print("[yellow]💡 下書きとして保存されました。公開するにはブログ管理画面から設定してください。[/yellow]")
    
    except Exception as e:
        console.print(f"[red]✗ エラー: {str(e)}[/red]")
        if "401" in str(e):
            console.print("[yellow]認証エラーです。はてなブログの認証情報を確認してください。[/yellow]")
        elif "403" in str(e):
            console.print("[yellow]アクセス権限がありません。ブログIDとAPI設定を確認してください。[/yellow]")

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """小説生成アプリ - LLMを使って小説を自動生成します"""
    if ctx.invoked_subcommand is None:
        show_interactive_menu()

@cli.command()
@click.option('--title', required=True, help='小説のタイトル（ディレクトリ名）')
def init(title: str):
    """新しい小説プロジェクトを初期化します"""
    console = Console()
    try:
        console.print(f"[bold cyan]🚀 新しい小説プロジェクトを初期化します[/bold cyan]")
        console.print(f"[dim]作品名: {title}[/dim]")
        
        fm = FileManager()
        fm.create_novel_structure(title)
        
        console.print(f"[green]✓ Novel project '{title}' initialized![/green]")
        console.print(f"[dim]次のステップ: {title}/setting.md を編集してから 'generate-plot' を実行してください[/dim]")
    except Exception as e:
        console.print(f"[red]✗ エラー: {str(e)}[/red]")

@cli.command()
@click.option('--title', required=True, help='小説のタイトル（ディレクトリ名）')
def status(title: str):
    """プロジェクトの状態を表示します"""
    console = Console()
    try:
        fm = FileManager()
        novel_dir = fm.get_novel_dir(title)
        
        if not novel_dir.exists():
            console.print(f"[red]✗ Novel project '{title}' does not exist.[/red]")
            return
        
        console.print(f"[bold cyan]📊 Novel project: {title}[/bold cyan]")
        console.print(f"[dim]Directory: {novel_dir}[/dim]")
        
        # setting.md の状態
        setting_file = novel_dir / "setting.md"
        if setting_file.exists():
            console.print("[green]✓ setting.md exists[/green]")
        else:
            console.print("[red]✗ setting.md missing[/red]")
        
        # character.md の状態
        character_file = novel_dir / "character.md"
        if character_file.exists():
            console.print("[green]✓ character.md exists[/green]")
        else:
            console.print("[yellow]○ character.md missing (optional)[/yellow]")
        
        # plot.json の状態
        plot_file = novel_dir / "plot.json"
        if plot_file.exists():
            console.print("[green]✓ plot.json exists[/green]")
            try:
                plot_data = fm.read_plot(title)
                total_episodes = sum(len(episodes) for episodes in plot_data.values())
                console.print(f"[dim]  - {len(plot_data)} arcs, {total_episodes} episodes planned[/dim]")
            except:
                console.print("[red]  - (corrupted plot file)[/red]")
        else:
            console.print("[red]✗ plot.json missing[/red]")
        
        # stories の状態
        stories_dir = novel_dir / "stories"
        if stories_dir.exists():
            story_files = list(stories_dir.glob("*.md"))
            console.print(f"[green]✓ stories/ directory with {len(story_files)} episodes[/green]")
        else:
            console.print("[red]✗ stories/ directory missing[/red]")
            
    except Exception as e:
        console.print(f"[red]✗ エラー: {str(e)}[/red]")

@cli.command("generate-plot")
@click.option('--title', required=True, help='小説のタイトル（ディレクトリ名）')
@click.option('--arc', help='特定の編のプロットのみ生成')
@click.option('--dry-run', is_flag=True, help='ドライラン（API呼び出しなし）')
def generate_plot(title: str, arc: Optional[str], dry_run: bool):
    """設定ファイルからプロットを生成します"""
    console = Console()
    
    if dry_run:
        console.print("[yellow]🏃‍♂️ ドライランモードで実行中...[/yellow]")
    
    console.print(f"[bold cyan]🛠️ プロット生成中...[/bold cyan]")
    
    try:
        fm = FileManager()
        setting = fm.read_setting(title)
        
        if dry_run:
            console.print("[yellow]💡 ドライランモード: LLM API呼び出しをスキップします[/yellow]")
            console.print(f"[dim]設定内容: {setting[:100]}...[/dim]")
            return
        
        # LLMを使ってプロットを生成
        llm = LLMClient.create_for_plot_generation()
        
        if arc:
            # 特定の編のプロット生成
            console.print(f"[cyan]編 '{arc}' のプロットを生成中...[/cyan]")
            plot = llm.generate_arc_plot(setting, arc)
            
            # 既存のプロットがある場合は読み込み、なければ新規作成
            try:
                existing_plot = fm.read_plot(title)
            except:
                existing_plot = {}
            
            # 新しい編のプロットを追加
            existing_plot[arc] = plot
            fm.save_plot(title, existing_plot)
        else:
            # 全編のプロット生成
            plot = llm.generate_plot(setting)
            fm.save_plot(title, plot)
        
        console.print(f"[green]✓ プロットが生成されました: {title}/plot.json[/green]")
    except Exception as e:
        console.print(f"[red]✗ エラー: {str(e)}[/red]")

@cli.command("generate-episode")
@click.option('--title', required=True, help='小説のタイトル（ディレクトリ名）')
@click.option('--arc', required=True, help='編名')
@click.option('--episodes', required=True, help='話番号（例: 1, 1-3, 1,3,5）')
@click.option('--dry-run', is_flag=True, help='ドライラン（API呼び出しなし）')
@click.option('--force', is_flag=True, help='既存ファイルを上書き')
def generate_episode(title: str, arc: str, episodes: str, dry_run: bool, force: bool):
    """指定した話の本文を生成します"""
    console = Console()
    
    if dry_run:
        console.print("[yellow]🏃‍♂️ ドライランモードで実行中...[/yellow]")
    
    # プロットから最大エピソード数を取得
    try:
        fm = FileManager()
        plot_data = fm.read_plot(title)
        
        if arc not in plot_data:
            console.print(f"[red]エラー: 編 '{arc}' がプロットに見つかりません[/red]")
            return
        
        max_episode = len(plot_data[arc])
        
    except Exception as e:
        console.print(f"[red]✗ エラー: {str(e)}[/red]")
        return
    
    try:
        episode_numbers = parse_episode_numbers(episodes, max_episode)
    except ValueError as e:
        console.print(f"[red]エラー: {str(e)}[/red]")
        return
    
    console.print(f"[bold cyan]🛠️ エピソード生成中...[/bold cyan]")
    
    try:
        fm = FileManager()
        setting = fm.read_setting(title)
        plot_data = fm.read_plot(title)
        
        # 各エピソードを生成
        llm = LLMClient.create_for_episode_generation()
        for episode_number in episode_numbers:
            console.print(f"\n[bold]エピソード {episode_number} を生成中...[/bold]")
            
            # ドライランの場合
            if dry_run:
                console.print(f"[yellow]💡 ドライランモード: エピソード {episode_number} の生成をスキップします[/yellow]")
                continue
            
            # LLMを使ってエピソードを生成（新しい方式：コンテキスト付きエピソード生成）
            episode_content = llm.generate_episode_with_context(
                book_title=title,
                setting_content=setting,
                arc=arc,
                episode=episode_number,
                plot_data=plot_data
            )
            
            # エピソードをファイルに保存
            fm.save_episode(title, arc, episode_number, episode_content)
        
        console.print(f"[green]✓ エピソードが生成されました: {title}/stories/[/green]")
    except Exception as e:
        console.print(f"[red]✗ エラー: {str(e)}[/red]")

@cli.command()
@click.option('--title', required=True, help='小説のタイトル（ディレクトリ名）')
@click.option('--episode', help='投稿するエピソード名（指定しない場合は全エピソードのリストを表示）')
@click.option('--blog-title', help='ブログ記事のタイトル（指定しない場合はエピソード名を使用）')
@click.option('--categories', help='カテゴリ（カンマ区切りで複数指定可能）')
@click.option('--draft', is_flag=True, help='下書きとして投稿')
@click.option('--preview', is_flag=True, help='投稿内容をプレビュー表示のみ（実際には投稿しない）')
@click.option('--preview-html', is_flag=True, help='投稿内容をHTML形式でプレビュー表示')
def publish(title: str, episode: Optional[str], blog_title: Optional[str], 
           categories: Optional[str], draft: bool, preview: bool, preview_html: bool):
    """小説エピソードをはてなブログに投稿します"""
    console = Console()
    
    try:
        fm = FileManager()
        novel_dir = fm.get_novel_dir(title)
        
        if not novel_dir.exists():
            console.print(f"[red]✗ 小説プロジェクト '{title}' が見つかりません[/red]")
            return
        
        stories_dir = novel_dir / "stories"
        if not stories_dir.exists():
            console.print(f"[red]✗ stories ディレクトリが見つかりません: {stories_dir}[/red]")
            return
        
        # エピソードが指定されていない場合、利用可能なエピソードを表示
        if not episode:
            story_files = list(stories_dir.glob("*.md"))
            if not story_files:
                console.print("[yellow]投稿可能なエピソードが見つかりません[/yellow]")
                return
            
            console.print(f"[bold cyan]📚 利用可能なエピソード ({title})[/bold cyan]")
            table = Table()
            table.add_column("No.", style="cyan", no_wrap=True)
            table.add_column("エピソード名", style="white")
            table.add_column("ファイル名", style="dim")
            
            for i, story_file in enumerate(sorted(story_files), 1):
                episode_name = story_file.stem
                table.add_row(str(i), episode_name, story_file.name)
            
            console.print(table)
            console.print("\n[dim]投稿するには --episode オプションでエピソード名を指定してください[/dim]")
            console.print("[dim]例: yumechain publish --title 小説名 --episode エピソード名[/dim]")
            return
        
        # 指定されたエピソードファイルを確認
        episode_file = stories_dir / f"{episode}.md"
        if not episode_file.exists():
            console.print(f"[red]✗ エピソードファイルが見つかりません: {episode_file}[/red]")
            return
        
        # エピソード内容を読み込み
        with open(episode_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # ブログタイトルを決定
        if not blog_title:
            blog_title = f"{title} - {episode}"
        
        # カテゴリを処理
        category_list = []
        if categories:
            category_list = [cat.strip() for cat in categories.split(',')]
        
        # プレビューモードの場合
        if preview or preview_html:
            console.print(f"[bold cyan]📝 投稿プレビュー[/bold cyan]")
            console.print(f"[bold]タイトル:[/bold] {blog_title}")
            console.print(f"[bold]カテゴリ:[/bold] {', '.join(category_list) if category_list else 'なし'}")
            console.print(f"[bold]下書き:[/bold] {'はい' if draft else 'いいえ'}")
            
            if preview_html:
                # HTMLプレビュー
                console.print(f"[bold]HTML変換後の内容:[/bold]")
                console.print(f"[dim]{'-' * 50}[/dim]")
                
                # はてなブログクライアントを作成してHTML変換を実行
                hatena_client = HatenaBlogClient("dummy", "dummy", "dummy.hatenablog.com")
                html_content = hatena_client._markdown_to_html(content)
                
                # HTMLの最初の500文字を表示
                preview_content = html_content[:500] + "..." if len(html_content) > 500 else html_content
                console.print(preview_content)
                console.print(f"[dim]{'-' * 50}[/dim]")
                console.print(f"[bold]元の文字数:[/bold] {len(content)} 文字")
                console.print(f"[bold]HTML文字数:[/bold] {len(html_content)} 文字")
            else:
                # 通常のMarkdownプレビュー
                console.print(f"[bold]内容:[/bold]")
                console.print(f"[dim]{'-' * 50}[/dim]")
                # 内容の最初の200文字を表示
                preview_content = content[:200] + "..." if len(content) > 200 else content
                console.print(preview_content)
                console.print(f"[dim]{'-' * 50}[/dim]")
                console.print(f"[bold]文字数:[/bold] {len(content)} 文字")
            return
        
        # はてなブログの認証情報を環境変数から取得
        hatena_username = os.getenv('HATENA_USERNAME')
        hatena_api_key = os.getenv('HATENA_API_KEY')
        hatena_blog_id = os.getenv('HATENA_BLOG_ID')
        
        if not all([hatena_username, hatena_api_key, hatena_blog_id]):
            console.print("[red]✗ はてなブログの認証情報が設定されていません[/red]")
            console.print("[yellow]以下の環境変数を .env ファイルに設定してください:[/yellow]")
            console.print("- HATENA_USERNAME (はてなユーザー名)")
            console.print("- HATENA_API_KEY (はてなブログAPI キー)")
            console.print("- HATENA_BLOG_ID (ブログID、例: xxxxx.hatenablog.com)")
            return
        
        # はてなブログクライアントを初期化
        hatena_client = HatenaBlogClient(hatena_username, hatena_api_key, hatena_blog_id)
        
        # 投稿確認
        console.print(f"[bold cyan]📤 はてなブログに投稿します[/bold cyan]")
        console.print(f"[dim]ブログ: {hatena_blog_id}[/dim]")
        console.print(f"[dim]タイトル: {blog_title}[/dim]")
        console.print(f"[dim]下書き: {'はい' if draft else 'いいえ'}[/dim]")
        
        if not get_yes_no_input("投稿を実行しますか？", 'n'):
            console.print("[yellow]投稿がキャンセルされました[/yellow]")
            return
        
        # 投稿を実行
        console.print("[cyan]投稿中...[/cyan]")
        result = hatena_client.create_entry(
            title=blog_title,
            content=content,
            categories=category_list,
            draft=draft
        )
        
        # 結果を表示
        entry_data = result.get('entry', {})
        entry_link = None
        
        # リンクを取得
        if 'link' in entry_data:
            links = entry_data['link']
            if isinstance(links, list):
                for link in links:
                    if isinstance(link, dict) and link.get('@rel') == 'alternate':
                        entry_link = link.get('@href')
                        break
            elif isinstance(links, dict) and links.get('@rel') == 'alternate':
                entry_link = links.get('@href')
        
        console.print(f"[bold green]✓ はてなブログに投稿が完了しました！[/bold green]")
        console.print(f"[dim]タイトル: {blog_title}[/dim]")
        if entry_link:
            console.print(f"[dim]URL: {entry_link}[/dim]")
        
        if draft:
            console.print("[yellow]💡 下書きとして保存されました。公開するにはブログ管理画面から設定してください。[/yellow]")
    
    except Exception as e:
        console.print(f"[red]✗ エラー: {str(e)}[/red]")
        if "401" in str(e):
            console.print("[yellow]認証エラーです。はてなブログの認証情報を確認してください。[/yellow]")
        elif "403" in str(e):
            console.print("[yellow]アクセス権限がありません。ブログIDとAPI設定を確認してください。[/yellow]")

@cli.command()
@click.option('--port', default=8000, type=int, help='サーバーポート（デフォルト: 8000）')
@click.option('--auto-port', is_flag=True, help='利用可能なポートを自動で検索')
@click.option('--no-browser', is_flag=True, help='ブラウザの自動起動を無効化')
def read(port: int, auto_port: bool, no_browser: bool):
    """小説をWebブラウザで読みます"""
    console = Console()
    
    try:
        base_dir = Path.cwd()
        
        # FastAPIServerManager を使用
        from .fastapi_manager import FastAPIServerManager
        manager = FastAPIServerManager(base_dir, default_port=port)
        
        # 自動ポート検索が有効な場合
        if auto_port:
            available_port = manager.find_available_port(start_port=port)
            if available_port:
                port = available_port
                console.print(f"[cyan]💡 利用可能なポートを見つけました: {port}[/cyan]")
            else:
                console.print(f"[yellow]警告: ポート {port} 以降で利用可能なポートが見つかりませんでした[/yellow]")
                console.print(f"[yellow]デフォルトポート {port} で試行します[/yellow]")
        
        # 全ての小説のコンテンツを準備
        if not manager.prepare_all_content():
            console.print("[red]✗ コンテンツの準備に失敗しました[/red]")
            return
        
        # サーバーを起動
        if not manager.start_server(port=port, auto_open=not no_browser):
            console.print("[red]✗ サーバーの起動に失敗しました[/red]")
            return
        
        console.print(f"[bold green]✓ 小説をFastAPIで表示中...[/bold green]")
        console.print(f"[dim]URL: http://localhost:{port}[/dim]")
        console.print(f"[dim]API仕様: http://localhost:{port}/docs[/dim]")
        
        # サーバーの終了を待機
        manager.wait_for_server()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]サーバーを停止中...[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ エラー: {str(e)}[/red]")
    finally:
        if 'manager' in locals():
            manager.cleanup()

def main():
    """メイン関数"""
    cli()

if __name__ == "__main__":
    main()
