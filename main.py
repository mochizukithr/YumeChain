"""
小説生成 CUI アプリ

LLM（Gemini）を使って設定から小説を生成するアプリケーション
"""
import click
import time
from rich.console import Console
from llm_client import LLMClient
from file_manager import FileManager

@click.group()
def cli():
    """小説生成アプリ - LLMを使って小説を自動生成します"""
    pass

@cli.command()
@click.option('--title', required=True, help='小説のタイトル（ディレクトリ名）')
@click.option('--dry-run', is_flag=True, help='ドライラン（API呼び出しなし）')
def generate_plot(title: str, dry_run: bool):
    """設定ファイルからプロットを生成します"""
    console = Console()
    start_time = time.time()
    
    try:
        console.print(f"[bold cyan]🚀 プロット生成処理を開始します[/bold cyan]")
        console.print(f"[dim]作品名: {title}[/dim]")
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
            character_file = fm.get_novel_dir(title) / "character.md"
            if character_file.exists():
                console.print(f"Character file: {title}/character.md")
            return
        
        # LLMでプロット生成
        llm = LLMClient()
        plot_data = llm.generate_plot(setting_content)
        
        # プロットを保存
        console.print("[dim]💾 プロットを保存中...[/dim]")
        fm.save_plot(title, plot_data)
        console.print(f"[green]✓ プロットファイル保存完了[/green]")
        
        # 処理時間を計算
        elapsed_time = time.time() - start_time
        console.print(f"\n[bold green]🎉 プロット生成処理が完了しました![/bold green]")
        console.print(f"[dim]総処理時間: {elapsed_time:.1f}秒[/dim]")
        
        # トークン使用量サマリーを表示
        llm.show_token_summary()
        
        # 生成されたプロットの概要を表示
        console.print(f"\n[bold]📊 生成されたプロット概要:[/bold]")
        for arc, episodes in plot_data.items():
            console.print(f"  [cyan]【{arc}】[/cyan]: {len(episodes)}話")
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        console.print(f"\n[red]💥 エラーが発生しました: {str(e)}[/red]")
        console.print(f"[dim]処理時間: {elapsed_time:.1f}秒[/dim]")

@cli.command()
@click.option('--title', required=True, help='小説のタイトル（ディレクトリ名）')
@click.option('--arc', required=True, help='編名（例: 中学生編）')
@click.option('--episode', required=True, type=int, help='話番号（1以上の整数）')
@click.option('--dry-run', is_flag=True, help='ドライラン（API呼び出しなし）')
@click.option('--force', is_flag=True, help='既存ファイルを上書き')
def generate_episode(title: str, arc: str, episode: int, dry_run: bool, force: bool):
    """指定した話の本文を生成します"""
    console = Console()
    start_time = time.time()
    
    try:
        console.print(f"[bold cyan]🚀 エピソード生成処理を開始します[/bold cyan]")
        console.print(f"[dim]作品名: {title}[/dim]")
        console.print(f"[dim]編: {arc}[/dim]")
        console.print(f"[dim]話数: {episode}[/dim]")
        console.print(f"[dim]開始時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
        
        fm = FileManager()
        
        # 既存ファイルのチェック
        console.print("[dim]📁 既存ファイルをチェック中...[/dim]")
        if fm.episode_exists(title, arc, episode) and not force:
            console.print(f"[yellow]⚠️  Episode {arc}_{episode:02d}.md already exists.[/yellow]")
            console.print("Use --force to overwrite.")
            return
        
        # 設定とプロットを読み込み
        console.print("[dim]📋 設定ファイルとプロットを読み込み中...[/dim]")
        try:
            setting_content = fm.read_all_settings(title)
            console.print(f"[green]✓ 設定ファイル読み込み完了[/green] ({len(setting_content)}文字)")
            
            episode_plot = fm.get_episode_plot(title, arc, episode)
            console.print(f"[green]✓ エピソードプロット読み込み完了[/green] ({len(episode_plot)}文字)")
        except FileNotFoundError as e:
            console.print(f"[red]✗ エラー: {str(e)}[/red]")
            console.print("Please run 'generate-plot' first.")
            return
        except ValueError as e:
            console.print(f"[red]✗ エラー: {str(e)}[/red]")
            return
        
        if dry_run:
            console.print("[yellow]⚠️  Dry run mode - エピソード生成をスキップします[/yellow]")
            console.print(f"Title: {title}")
            console.print(f"Arc: {arc}")
            console.print(f"Episode: {episode}")
            console.print(f"Plot: {episode_plot[:100]}...")
            character_file = fm.get_novel_dir(title) / "character.md"
            if character_file.exists():
                console.print(f"Using character file: {title}/character.md")
            return
        
        # LLMでエピソード生成
        llm = LLMClient()
        episode_content = llm.generate_episode(setting_content, episode_plot)
        
        # エピソードを保存
        console.print("[dim]💾 エピソードを保存中...[/dim]")
        fm.save_episode(title, arc, episode, episode_content)
        console.print(f"[green]✓ エピソードファイル保存完了[/green]")
        
        # 処理時間を計算
        elapsed_time = time.time() - start_time
        console.print(f"\n[bold green]🎉 エピソード生成処理が完了しました![/bold green]")
        console.print(f"[dim]総処理時間: {elapsed_time:.1f}秒[/dim]")
        console.print(f"[dim]保存先: {title}/stories/{arc}_{episode:02d}.md[/dim]")
        
        # トークン使用量サマリーを表示
        llm.show_token_summary()
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        console.print(f"\n[red]💥 エラーが発生しました: {str(e)}[/red]")
        console.print(f"[dim]処理時間: {elapsed_time:.1f}秒[/dim]")

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
