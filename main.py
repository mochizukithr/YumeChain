"""
小説生成 CUI アプリ

LLM（Gemini）を使って設定から小説を生成するアプリケーション
"""
import click
import time
import sys
import termios
import tty
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table
from llm_client import LLMClient
from file_manager import FileManager
from pelican_manager import PelicanServerManager
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
    """編と話数を選択"""
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
    
    # 話数の選択
    fm = FileManager()
    try:
        plot_data = fm.read_plot(title)
        episodes = plot_data[selected_arc]
        max_episode = len(episodes)
        
        console.print(f"\n[bold]📝 '{selected_arc}' の話数 (1-{max_episode}):[/bold]")
        episode_input = Prompt.ask("[cyan]話数をカンマ区切りで入力してください（例: 1,3,5）[/cyan]", default="1")
        
        episode_numbers = parse_episode_numbers(episode_input, max_episode)
        if episode_numbers:
            return selected_arc, episode_numbers
        else:
            console.print(f"[red]無効な話数です。1-{max_episode} の範囲で入力してください。[/red]")
            return None, None
    except:
        console.print("[red]プロットの読み込みに失敗しました[/red]")
        return None, None

def handle_init_command():
    """init コマンドのハンドラ"""
    console = Console()
    title = Prompt.ask("[cyan]新しい小説のタイトルを入力[/cyan]")
    
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
    """status コマンドのハンドラ"""
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
    """generate-plot コマンドのハンドラ"""
    title = select_novel_title()
    if not title:
        return
    
    console = Console()
    
    # アーク選択のオプションを提供
    existing_arcs = get_available_arcs(title)
    arc = None
    
    if existing_arcs:
        console.print(f"\n[bold]📖 '{title}' の既存の編:[/bold]")
        for i, existing_arc in enumerate(existing_arcs, 1):
            console.print(f"  {i}. {existing_arc}")
        console.print("  0. 全体のプロットを生成")
        console.print("  -1. 特定の編のみを生成（新規編名を入力）")
        
        # 有効な選択肢を作成（-1は文字として扱えないので、'n'に変更）
        valid_choices = [str(i) for i in range(len(existing_arcs) + 1)] + ['n']
        
        while True:
            choice = get_single_char_input("\n[cyan]選択してください (新規編の場合は'n')[/cyan]", valid_choices, "0")
            
            if choice == "0":
                arc = None  # 全体生成
                break
            elif choice == "n":
                arc = Prompt.ask("[cyan]生成したい編名を入力[/cyan]")
                break
            else:
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(existing_arcs):
                        arc = existing_arcs[idx]
                        break
                except ValueError:
                    pass
            console.print("[red]無効な選択です。もう一度選択してください。[/red]")
    else:
        # 既存のプロットがない場合、特定編生成オプションを提供
        generate_specific = get_yes_no_input("[cyan]特定の編のみ生成しますか？（全体生成の場合はNo）[/cyan]", 'n')
        if generate_specific:
            arc = Prompt.ask("[cyan]生成したい編名を入力[/cyan]")
    
    dry_run = get_yes_no_input("[cyan]ドライラン（API呼び出しなし）で実行しますか？[/cyan]", 'n')
    
    start_time = time.time()
    
    try:
        console.print(f"[bold cyan]🚀 プロット生成処理を開始します[/bold cyan]")
        console.print(f"[dim]作品名: {title}[/dim]")
        if arc:
            console.print(f"[dim]対象編: {arc}[/dim]")
        console.print(f"[dim]開始時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
        
        fm = FileManager()
        
        # ディレクトリ構造を作成
        console.print("[dim]📁 ディレクトリ構造を確認中...[/dim]")
        fm.create_novel_structure(title)
        
        # 設定ファイルを読み込み
        console.print("[dim]📋 設定ファイルを読み込み中...[/dim]")
        try:
            setting_content = fm.read_all_settings(title)
            console.print(f"[green]✓ 設定ファイル読み込み完了[/green] ({len(setting_content)}文字)")
        except FileNotFoundError:
            console.print(f"[red]✗ エラー: setting.md not found in {title}/ directory[/red]")
            console.print(f"Please edit the template file that was created.")
            return
        
        if dry_run:
            console.print("[yellow]⚠️  Dry run mode - プロット生成をスキップします[/yellow]")
            console.print(f"Setting file: {title}/setting.md")
            if arc:
                console.print(f"Target arc: {arc}")
            character_file = fm.get_novel_dir(title) / "character.md"
            if character_file.exists():
                console.print(f"Character file: {title}/character.md")
            return
        
        # LLMでプロット生成
        llm = LLMClient()
        plot_data = llm.generate_plot(setting_content, target_arc=arc)
        
        # プロットを保存
        console.print("[dim]💾 プロットを保存中...[/dim]")
        # 特定のアークの場合は既存データとマージ
        fm.save_plot(title, plot_data, merge=(arc is not None))
        console.print(f"[green]✓ プロットファイル保存完了[/green]")
        
        # 処理時間を計算
        elapsed_time = time.time() - start_time
        console.print(f"\n[bold green]🎉 プロット生成処理が完了しました![/bold green]")
        console.print(f"[dim]総処理時間: {elapsed_time:.1f}秒[/dim]")
        
        # トークン使用量サマリーを表示
        llm.show_token_summary()
        
        # 生成されたプロットの概要を表示
        console.print(f"\n[bold]📊 生成されたプロット概要:[/bold]")
        for arc_name, episodes in plot_data.items():
            console.print(f"  [cyan]【{arc_name}】[/cyan]: {len(episodes)}話")
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        console.print(f"\n[red]💥 エラーが発生しました: {str(e)}[/red]")
        console.print(f"[dim]処理時間: {elapsed_time:.1f}秒[/dim]")

def handle_generate_episode_command():
    """generate-episode コマンドのハンドラ（複数エピソード対応）"""
    title = select_novel_title()
    if not title:
        return
    
    arc, episode_list = select_arc_and_episodes(title)
    if not arc or not episode_list:
        return
    
    console = Console()
    dry_run = get_yes_no_input("[cyan]ドライラン（API呼び出しなし）で実行しますか？[/cyan]", 'n')
    force = get_yes_no_input("[cyan]既存ファイルを上書きしますか？[/cyan]", 'n')
    
    # 複数エピソードの確認
    console.print(f"\n[bold cyan]� 生成予定のエピソード:[/bold cyan]")
    console.print(f"[dim]作品名: {title}[/dim]")
    console.print(f"[dim]編: {arc}[/dim]")
    
    # エピソードリストを整理して表示
    if len(episode_list) == 1:
        console.print(f"[dim]話数: {episode_list[0]}[/dim]")
    else:
        # 連続する番号をまとめて表示
        ranges = []
        start = episode_list[0]
        end = start
        
        for i in range(1, len(episode_list)):
            if episode_list[i] == end + 1:
                end = episode_list[i]
            else:
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = end = episode_list[i]
        
        # 最後の範囲を追加
        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")
        
        console.print(f"[dim]話数: {', '.join(ranges)} (計{len(episode_list)}話)[/dim]")
    
    if not get_yes_no_input("\n[cyan]この内容で実行しますか？[/cyan]", 'y'):
        console.print("[yellow]処理をキャンセルしました[/yellow]")
        return
    
    start_time = time.time()
    success_count = 0
    error_count = 0
    
    try:
        console.print(f"\n[bold cyan]🚀 エピソード生成処理を開始します[/bold cyan]")
        console.print(f"[dim]開始時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
        
        fm = FileManager()
        
        # 設定とプロットを読み込み（一度だけ）
        console.print("[dim]📋 設定ファイルとプロットを読み込み中...[/dim]")
        try:
            setting_content = fm.read_all_settings(title)
            console.print(f"[green]✓ 設定ファイル読み込み完了[/green] ({len(setting_content)}文字)")
        except FileNotFoundError as e:
            console.print(f"[red]✗ エラー: {str(e)}[/red]")
            console.print("Please run 'generate-plot' first.")
            return
        
        if dry_run:
            console.print("[yellow]⚠️  Dry run mode - エピソード生成をスキップします[/yellow]")
            for episode in episode_list:
                try:
                    episode_plot = fm.get_episode_plot(title, arc, episode)
                    console.print(f"[dim]Episode {episode}: {episode_plot[:50]}...[/dim]")
                except ValueError as e:
                    console.print(f"[red]Episode {episode}: {str(e)}[/red]")
            return
        
        # LLMクライアントを初期化
        llm = LLMClient()
        
        # 各エピソードを処理
        for i, episode in enumerate(episode_list, 1):
            console.print(f"\n[bold]📝 エピソード {episode} を処理中...[/bold] ({i}/{len(episode_list)})")
            
            try:
                # 既存ファイルのチェック
                if fm.episode_exists(title, arc, episode) and not force:
                    console.print(f"[yellow]⚠️  Episode {arc}_{episode:02d}.md already exists - スキップ[/yellow]")
                    continue
                
                # エピソードプロットを取得
                try:
                    episode_plot = fm.get_episode_plot(title, arc, episode)
                    console.print(f"[green]✓ エピソードプロット読み込み完了[/green] ({len(episode_plot)}文字)")
                except ValueError as e:
                    console.print(f"[red]✗ エラー: {str(e)}[/red]")
                    error_count += 1
                    continue
                
                # LLMでエピソード生成
                console.print(f"[dim]🤖 LLMでエピソード {episode} を生成中...[/dim]")
                episode_content = llm.generate_episode(setting_content, episode_plot)
                
                # エピソードを保存
                console.print(f"[dim]💾 エピソード {episode} を保存中...[/dim]")
                fm.save_episode(title, arc, episode, episode_content)
                console.print(f"[green]✓ エピソード {episode} 保存完了[/green]")
                success_count += 1
                
            except Exception as e:
                console.print(f"[red]✗ エピソード {episode} でエラー: {str(e)}[/red]")
                error_count += 1
                continue
        
        # 処理時間を計算
        elapsed_time = time.time() - start_time
        console.print(f"\n[bold green]🎉 エピソード生成処理が完了しました![/bold green]")
        console.print(f"[dim]総処理時間: {elapsed_time:.1f}秒[/dim]")
        console.print(f"[green]成功: {success_count}話[/green] [red]エラー: {error_count}話[/red]")
        
        if success_count > 0:
            console.print(f"[dim]保存先: {title}/stories/{arc}_XX.md[/dim]")
        
        # トークン使用量サマリーを表示
        if not dry_run:
            llm.show_token_summary()
        
    except KeyboardInterrupt:
        elapsed_time = time.time() - start_time
        console.print(f"\n[yellow]⚠️  処理が中断されました[/yellow]")
        console.print(f"[dim]処理時間: {elapsed_time:.1f}秒[/dim]")
        console.print(f"[green]成功: {success_count}話[/green] [red]エラー: {error_count}話[/red]")
    except Exception as e:
        elapsed_time = time.time() - start_time
        console.print(f"\n[red]💥 エラーが発生しました: {str(e)}[/red]")
        console.print(f"[dim]処理時間: {elapsed_time:.1f}秒[/dim]")
        console.print(f"[green]成功: {success_count}話[/green] [red]エラー: {error_count}話[/red]")

def handle_read_command():
    """read コマンドのハンドラ"""
    title = select_novel_title()
    if not title:
        return
    
    console = Console()
    port = IntPrompt.ask("[cyan]サーバーポート番号[/cyan]", default=8000)
    no_browser = not get_yes_no_input("[cyan]ブラウザを自動で開きますか？[/cyan]", 'y')
    
    try:
        console.print(f"[bold cyan]📖 小説リーダーを起動します[/bold cyan]")
        console.print(f"[dim]作品名: {title}[/dim]")
        console.print(f"[dim]ポート: {port}[/dim]")
        
        # PelicanServerManagerを初期化
        base_dir = Path.cwd()
        manager = PelicanServerManager(base_dir)
        
        # コンテンツの準備
        console.print("[dim]📝 コンテンツを準備中...[/dim]")
        if not manager.prepare_content(title):
            return
        
        # サイトのビルド
        console.print("[dim]🔨 サイトをビルド中...[/dim]")
        if not manager.build_site():
            manager.cleanup()
            return
        
        # サーバーの起動
        if not manager.start_server(port=port, auto_open=not no_browser):
            manager.cleanup()
            return
        
        # サーバーの終了を待機
        try:
            manager.wait_for_server()
        finally:
            manager.cleanup()
            console.print("[green]✓ リーダーを終了しました[/green]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]ユーザーによって中断されました[/yellow]")
        if 'manager' in locals():
            manager.cleanup()
    except Exception as e:
        console.print(f"[red]✗ エラー: {str(e)}[/red]")
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
@click.option('--port', default=8000, help='サーバーポート番号 (デフォルト: 8000)')
@click.option('--no-browser', is_flag=True, help='ブラウザを自動で開かない')
def read(title: str, port: int, no_browser: bool):
    """小説をWebブラウザで読む（Pelicanサーバー起動）"""
    console = Console()
    
    try:
        console.print(f"[bold cyan]📖 小説リーダーを起動します[/bold cyan]")
        console.print(f"[dim]作品名: {title}[/dim]")
        console.print(f"[dim]ポート: {port}[/dim]")
        
        # PelicanServerManagerを初期化
        base_dir = Path.cwd()
        manager = PelicanServerManager(base_dir)
        
        # コンテンツの準備
        console.print("[dim]📝 コンテンツを準備中...[/dim]")
        if not manager.prepare_content(title):
            return
        
        # サイトのビルド
        console.print("[dim]🔨 サイトをビルド中...[/dim]")
        if not manager.build_site():
            manager.cleanup()
            return
        
        # サーバーの起動
        if not manager.start_server(port=port, auto_open=not no_browser):
            manager.cleanup()
            return
        
        # サーバーの終了を待機
        try:
            manager.wait_for_server()
        finally:
            manager.cleanup()
            console.print("[green]✓ リーダーを終了しました[/green]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]ユーザーによって中断されました[/yellow]")
        if 'manager' in locals():
            manager.cleanup()
    except Exception as e:
        console.print(f"[red]✗ エラー: {str(e)}[/red]")
        if 'manager' in locals():
            manager.cleanup()

@cli.command()
@click.option('--title', required=True, help='小説のタイトル（ディレクトリ名）')
@click.option('--arc', help='特定の編のプロットのみを生成（例: 中学生編）')
@click.option('--dry-run', is_flag=True, help='ドライラン（API呼び出しなし）')
def generate_plot(title: str, arc: str, dry_run: bool):
    """設定ファイルからプロットを生成します"""
    console = Console()
    start_time = time.time()
    
    try:
        console.print(f"[bold cyan]🚀 プロット生成処理を開始します[/bold cyan]")
        console.print(f"[dim]作品名: {title}[/dim]")
        if arc:
            console.print(f"[dim]対象編: {arc}[/dim]")
        console.print(f"[dim]開始時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
        
        fm = FileManager()
        
        # ディレクトリ構造を作成
        console.print("[dim]📁 ディレクトリ構造を確認中...[/dim]")
        fm.create_novel_structure(title)
        
        # 設定ファイルを読み込み
        console.print("[dim]📋 設定ファイルを読み込み中...[/dim]")
        try:
            setting_content = fm.read_all_settings(title)
            console.print(f"[green]✓ 設定ファイル読み込み完了[/green] ({len(setting_content)}文字)")
        except FileNotFoundError:
            console.print(f"[red]✗ エラー: setting.md not found in {title}/ directory[/red]")
            console.print(f"Please edit the template file that was created.")
            return
        
        if dry_run:
            console.print("[yellow]⚠️  Dry run mode - プロット生成をスキップします[/yellow]")
            console.print(f"Setting file: {title}/setting.md")
            if arc:
                console.print(f"Target arc: {arc}")
            character_file = fm.get_novel_dir(title) / "character.md"
            if character_file.exists():
                console.print(f"Character file: {title}/character.md")
            return
        
        # LLMでプロット生成
        llm = LLMClient()
        plot_data = llm.generate_plot(setting_content, target_arc=arc)
        
        # プロットを保存
        console.print("[dim]💾 プロットを保存中...[/dim]")
        # 特定のアークの場合は既存データとマージ
        fm.save_plot(title, plot_data, merge=(arc is not None))
        console.print(f"[green]✓ プロットファイル保存完了[/green]")
        
        # 処理時間を計算
        elapsed_time = time.time() - start_time
        console.print(f"\n[bold green]🎉 プロット生成処理が完了しました![/bold green]")
        console.print(f"[dim]総処理時間: {elapsed_time:.1f}秒[/dim]")
        
        # トークン使用量サマリーを表示
        llm.show_token_summary()
        
        # 生成されたプロットの概要を表示
        console.print(f"\n[bold]📊 生成されたプロット概要:[/bold]")
        for arc_name, episodes in plot_data.items():
            console.print(f"  [cyan]【{arc_name}】[/cyan]: {len(episodes)}話")
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        console.print(f"\n[red]💥 エラーが発生しました: {str(e)}[/red]")
        console.print(f"[dim]処理時間: {elapsed_time:.1f}秒[/dim]")

@cli.command()
@click.option('--title', required=True, help='小説のタイトル（ディレクトリ名）')
@click.option('--arc', required=True, help='編名（例: 中学生編）')
@click.option('--episodes', required=True, help='話番号（例: 1, 1-3, 1,3,5, 2-4,7,9-10）')
@click.option('--dry-run', is_flag=True, help='ドライラン（API呼び出しなし）')
@click.option('--force', is_flag=True, help='既存ファイルを上書き')
def generate_episode(title: str, arc: str, episodes: str, dry_run: bool, force: bool):
    """指定した話の本文を生成します（複数指定可能）"""
    console = Console()
    start_time = time.time()
    
    try:
        fm = FileManager()
        
        # プロットを読み込んで最大エピソード番号を取得
        try:
            plot_data = fm.read_plot(title)
            if arc not in plot_data:
                console.print(f"[red]✗ エラー: 編 '{arc}' がプロットに見つかりません[/red]")
                return
            max_episode = len(plot_data[arc])
        except FileNotFoundError:
            console.print(f"[red]✗ エラー: プロットファイルが見つかりません[/red]")
            console.print("Please run 'generate-plot' first.")
            return
        
        # エピソード番号を解析
        try:
            episode_list = parse_episode_numbers(episodes, max_episode)
        except ValueError as e:
            console.print(f"[red]✗ エラー: {str(e)}[/red]")
            return
        
        success_count = 0
        error_count = 0
        
        console.print(f"[bold cyan]🚀 エピソード生成処理を開始します[/bold cyan]")
        console.print(f"[dim]作品名: {title}[/dim]")
        console.print(f"[dim]編: {arc}[/dim]")
        
        # エピソードリストを整理して表示
        if len(episode_list) == 1:
            console.print(f"[dim]話数: {episode_list[0]}[/dim]")
        else:
            # 連続する番号をまとめて表示
            ranges = []
            start = episode_list[0]
            end = start
            
            for i in range(1, len(episode_list)):
                if episode_list[i] == end + 1:
                    end = episode_list[i]
                else:
                    if start == end:
                        ranges.append(str(start))
                    else:
                        ranges.append(f"{start}-{end}")
                    start = end = episode_list[i]
            
            # 最後の範囲を追加
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            
            console.print(f"[dim]話数: {', '.join(ranges)} (計{len(episode_list)}話)[/dim]")
        
        console.print(f"[dim]開始時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
        
        # 設定ファイルを読み込み（一度だけ）
        console.print("[dim]📋 設定ファイルを読み込み中...[/dim]")
        try:
            setting_content = fm.read_all_settings(title)
            console.print(f"[green]✓ 設定ファイル読み込み完了[/green] ({len(setting_content)}文字)")
        except FileNotFoundError:
            console.print(f"[red]✗ エラー: setting.md not found in {title}/ directory[/red]")
            console.print(f"Please edit the template file that was created.")
            return
        
        if dry_run:
            console.print("[yellow]⚠️  Dry run mode - エピソード生成をスキップします[/yellow]")
            for episode in episode_list:
                try:
                    episode_plot = fm.get_episode_plot(title, arc, episode)
                    console.print(f"[dim]Episode {episode}: {episode_plot[:50]}...[/dim]")
                except ValueError as e:
                    console.print(f"[red]Episode {episode}: {str(e)}[/red]")
            return
        
        # LLMクライアントを初期化
        llm = LLMClient()
        
        # 各エピソードを処理
        for i, episode in enumerate(episode_list, 1):
            console.print(f"\n[bold]📝 エピソード {episode} を処理中...[/bold] ({i}/{len(episode_list)})")
            
            try:
                # 既存ファイルのチェック
                if fm.episode_exists(title, arc, episode) and not force:
                    console.print(f"[yellow]⚠️  Episode {arc}_{episode:02d}.md already exists - スキップ[/yellow]")
                    continue
                
                # エピソードプロットを取得
                try:
                    episode_plot = fm.get_episode_plot(title, arc, episode)
                    console.print(f"[green]✓ エピソードプロット読み込み完了[/green] ({len(episode_plot)}文字)")
                except ValueError as e:
                    console.print(f"[red]✗ エラー: {str(e)}[/red]")
                    error_count += 1
                    continue
                
                # LLMでエピソード生成
                console.print(f"[dim]🤖 LLMでエピソード {episode} を生成中...[/dim]")
                episode_content = llm.generate_episode(setting_content, episode_plot)
                
                # エピソードを保存
                console.print(f"[dim]💾 エピソード {episode} を保存中...[/dim]")
                fm.save_episode(title, arc, episode, episode_content)
                console.print(f"[green]✓ エピソード {episode} 保存完了[/green]")
                success_count += 1
                
            except Exception as e:
                console.print(f"[red]✗ エピソード {episode} でエラー: {str(e)}[/red]")
                error_count += 1
                continue
        
        # 処理時間を計算
        elapsed_time = time.time() - start_time
        console.print(f"\n[bold green]🎉 エピソード生成処理が完了しました![/bold green]")
        console.print(f"[dim]総処理時間: {elapsed_time:.1f}秒[/dim]")
        console.print(f"[green]成功: {success_count}話[/green] [red]エラー: {error_count}話[/red]")
        
        if success_count > 0:
            console.print(f"[dim]保存先: {title}/stories/{arc}_XX.md[/dim]")
        
        # トークン使用量サマリーを表示
        llm.show_token_summary()
        
    except KeyboardInterrupt:
        elapsed_time = time.time() - start_time
        console.print(f"\n[yellow]⚠️  処理が中断されました[/yellow]")
        console.print(f"[dim]処理時間: {elapsed_time:.1f}秒[/dim]")
        console.print(f"[green]成功: {success_count}話[/green] [red]エラー: {error_count}話[/red]")
    except Exception as e:
        elapsed_time = time.time() - start_time
        console.print(f"\n[red]💥 エラーが発生しました: {str(e)}[/red]")
        console.print(f"[dim]処理時間: {elapsed_time:.1f}秒[/dim]")
        console.print(f"[green]成功: {success_count}話[/green] [red]エラー: {error_count}話[/red]")

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

def main():
    """メイン関数"""
    cli()

if __name__ == "__main__":
    main()
