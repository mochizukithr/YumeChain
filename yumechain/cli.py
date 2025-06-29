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
import json

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
        table.add_row("0", "exit", "終了")
        
        console.print(table)
        console.print()
        
        choice = get_single_char_input("[cyan]選択してください[/cyan]", ["0", "1", "2", "3", "4", "5"], "0")
        
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
    title = select_novel_title()
    if not title:
        return

    console = Console()
    
    # ポート番号を入力
    port = IntPrompt.ask(
        "[cyan]サーバーポート番号を入力してください[/cyan]",
        default=5000,
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
        
        # FlaskServerManager を使用
        from .flask_manager import FlaskServerManager
        manager = FlaskServerManager(base_dir, default_port=port)
        
        # 自動ポート検索が有効な場合
        if auto_port:
            available_port = manager.find_available_port(start_port=port)
            if available_port and available_port != port:
                port = available_port
                console.print(f"[cyan]💡 利用可能なポートを見つけました: {port}[/cyan]")
        
        # コンテンツを準備
        if not manager.prepare_content(title):
            console.print("[red]✗ コンテンツの準備に失敗しました[/red]")
            return
        
        # サーバーを起動
        if not manager.start_server(port=port, auto_open=auto_open):
            console.print("[red]✗ サーバーの起動に失敗しました[/red]")
            return
        
        console.print(f"[bold green]✓ 小説をFlaskで表示中...[/bold green]")
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

@cli.command()
@click.option('--title', required=True, help='小説のタイトル（ディレクトリ名）')
def generate_plot(title: str):
    """プロットを生成します"""
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

@cli.command()
@click.option('--title', required=True, help='小説のタイトル（ディレクトリ名）')
@click.option('--arc', required=True, help='編の名前')
@click.option('--episodes', required=True, help='生成する話数（カンマ区切りまたは範囲指定）')
def generate_episode(title: str, arc: str, episodes: str):
    """エピソードを生成します"""
    console = Console()
    
    # エピソード番号を解析
    max_episode = 0
    try:
        fm = FileManager()
        plot_data = fm.read_plot(title)
        if arc in plot_data:
            episodes_list = plot_data[arc]
            max_episode = len(episodes_list)
        else:
            console.print(f"[red]❌ 指定された編が見つかりません: {arc}[/red]")
            return
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
@click.option('--port', default=5000, type=int, help='サーバーポート（デフォルト: 5000）')
@click.option('--auto-port', is_flag=True, help='利用可能なポートを自動で検索')
@click.option('--no-browser', is_flag=True, help='ブラウザの自動起動を無効化')
def read(title: str, port: int, auto_port: bool, no_browser: bool):
    """小説をWebブラウザで読みます"""
    console = Console()
    
    try:
        base_dir = Path.cwd()
        
        # FlaskServerManager を使用
        from .flask_manager import FlaskServerManager
        manager = FlaskServerManager(base_dir, default_port=port)
        
        # 自動ポート検索が有効な場合
        if auto_port:
            available_port = manager.find_available_port(start_port=port)
            if available_port:
                port = available_port
                console.print(f"[cyan]💡 利用可能なポートを見つけました: {port}[/cyan]")
            else:
                console.print(f"[yellow]警告: ポート {port} 以降で利用可能なポートが見つかりませんでした[/yellow]")
                console.print(f"[yellow]デフォルトポート {port} で試行します[/yellow]")
        
        # コンテンツを準備
        if not manager.prepare_content(title):
            console.print("[red]✗ コンテンツの準備に失敗しました[/red]")
            return
        
        # サーバーを起動
        if not manager.start_server(port=port, auto_open=not no_browser):
            console.print("[red]✗ サーバーの起動に失敗しました[/red]")
            return
        
        console.print(f"[bold green]✓ 小説をFlaskで表示中...[/bold green]")
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

def main():
    """メイン関数"""
    cli()

if __name__ == "__main__":
    main()
