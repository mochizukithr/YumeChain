"""
LLM クライアント
"""
import os
import json
import time
from typing import Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

# 環境変数を読み込み
load_dotenv()

class LLMClient:
    """Gemini APIを使用するLLMクライアント"""
    
    def __init__(self):
        """初期化"""
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        model_name = os.getenv('GEMINI_MODEL', 'gemini-pro')  # デフォルトはgemini-pro
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.console = Console()
        
        # トークン使用量を追跡
        self.total_input_tokens = 0
        self.total_output_tokens = 0
    
    def count_tokens(self, text: str) -> int:
        """テキストのトークン数をカウント"""
        try:
            token_count = self.model.count_tokens(text)
            return token_count.total_tokens
        except Exception as e:
            # トークンカウントでエラーが発生した場合は0を返す
            self.console.print(f"[yellow]⚠️ トークンカウントエラー: {str(e)}[/yellow]")
            return 0
    
    def log_token_info(self, text: str, label: str):
        """トークン情報をログ出力"""
        char_count = len(text)
        token_count = self.count_tokens(text)
        self.console.print(f"[dim]{label}: {char_count}文字, {token_count}トークン[/dim]")
    
    def update_token_usage(self, input_tokens: int, output_tokens: int):
        """トークン使用量を更新"""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
    
    def show_token_summary(self):
        """トークン使用量のサマリーを表示"""
        total_tokens = self.total_input_tokens + self.total_output_tokens
        self.console.print(f"\n[bold cyan]📊 トークン使用量サマリー:[/bold cyan]")
        self.console.print(f"[dim]入力トークン: {self.total_input_tokens:,}[/dim]")
        self.console.print(f"[dim]出力トークン: {self.total_output_tokens:,}[/dim]")
        self.console.print(f"[dim]合計トークン: {total_tokens:,}[/dim]")
    
    def generate_text(self, prompt: str, progress_description: Optional[str] = None) -> str:
        """テキスト生成"""
        try:
            if progress_description:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    TimeElapsedColumn(),
                    console=self.console,
                    transient=False
                ) as progress:
                    task = progress.add_task(progress_description, total=None)
                    start_time = time.time()
                    self.console.print(f"[dim]開始時刻: {time.strftime('%H:%M:%S')}[/dim]")
                    
                    # プロンプトのトークン数をカウント
                    prompt_token_count = self.count_tokens(prompt)
                    self.console.print(f"[dim]プロンプト: {len(prompt)}文字, {prompt_token_count}トークン[/dim]")
                    self.console.print(f"[dim]モデル: {self.model.model_name}[/dim]")
                    
                    # API呼び出し
                    self.console.print("[dim]API呼び出し中...[/dim]")
                    response = self.model.generate_content(prompt)
                    
                    elapsed_time = time.time() - start_time
                    response_length = len(response.text) if response.text else 0
                    
                    # レスポンスのトークン数をカウント
                    response_token_count = self.count_tokens(response.text) if response.text else 0
                    total_tokens = prompt_token_count + response_token_count
                    
                    # トークン使用量を記録
                    self.update_token_usage(prompt_token_count, response_token_count)
                    
                    self.console.print(f"[green]✓ 完了[/green] (所要時間: {elapsed_time:.1f}秒)")
                    self.console.print(f"[dim]レスポンス: {response_length}文字, {response_token_count}トークン[/dim]")
                    self.console.print(f"[dim]合計トークン数: {total_tokens} (入力: {prompt_token_count}, 出力: {response_token_count})[/dim]")
                    
                    return response.text
            else:
                response = self.model.generate_content(prompt)
                return response.text
        except Exception as e:
            if progress_description:
                elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
                self.console.print(f"[red]✗ エラー (所要時間: {elapsed_time:.1f}秒): {str(e)}[/red]")
            raise Exception(f"LLM API error: {str(e)}")
    
    def generate_plot(self, setting_content: str) -> Dict[str, Any]:
        """プロット生成"""
        from prompt_templates import PLOT_GENERATION_PROMPT
        
        self.console.print("[bold blue]📖 プロット生成を開始します[/bold blue]")
        
        # プロンプトテンプレートのサイズを確認
        template_size = len(PLOT_GENERATION_PROMPT) - len("{setting_content}")  # プレースホルダー分を除く
        self.console.print(f"[dim]プロンプトテンプレート: {template_size}文字, {self.count_tokens(PLOT_GENERATION_PROMPT.replace('{setting_content}', ''))}トークン[/dim]")
        
        # 設定ファイルのトークン数をログ出力
        self.log_token_info(setting_content, "設定ファイル")
        
        prompt = PLOT_GENERATION_PROMPT.format(setting_content=setting_content)
        
        # プロンプト全体のサイズを確認
        self.console.print(f"[dim]プロンプトテンプレート適用後の全体サイズ確認[/dim]")
        
        response = self.generate_text(prompt, "プロット生成中...")
        
        # JSON部分を抽出
        try:
            self.console.print("[dim]レスポンスをパース中...[/dim]")
            # ```json で囲まれている場合は中身を抽出
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                # JSONが直接返された場合
                json_str = response.strip()
            
            plot_data = json.loads(json_str)
            
            # 生成されたプロットの統計を表示
            total_episodes = sum(len(episodes) for episodes in plot_data.values())
            self.console.print(f"[green]✓ プロット生成完了![/green]")
            self.console.print(f"[dim]生成された構成: {len(plot_data)}編, 全{total_episodes}話[/dim]")
            
            # 生成されたJSONデータのサイズも記録
            json_output = json.dumps(plot_data, ensure_ascii=False, indent=2)
            self.log_token_info(json_output, "生成されたプロットJSON")
            
            return plot_data
        except json.JSONDecodeError as e:
            self.console.print(f"[red]✗ JSONパースエラー: {str(e)}[/red]")
            self.console.print(f"[dim]レスポンス内容: {response[:200]}...[/dim]")
            raise Exception(f"Failed to parse JSON response: {str(e)}\nResponse: {response}")
    
    def generate_episode(self, setting_content: str, plot_content: str) -> str:
        """エピソード生成"""
        from prompt_templates import EPISODE_GENERATION_PROMPT
        
        self.console.print("[bold blue]📝 エピソード生成を開始します[/bold blue]")
        
        # プロンプトテンプレートのサイズを確認
        template_size = len(EPISODE_GENERATION_PROMPT) - len("{setting_content}") - len("{plot_content}")
        self.console.print(f"[dim]プロンプトテンプレート: {template_size}文字, {self.count_tokens(EPISODE_GENERATION_PROMPT.replace('{setting_content}', '').replace('{plot_content}', ''))}トークン[/dim]")
        
        # 各コンテンツのトークン数をログ出力
        self.log_token_info(setting_content, "設定ファイル")
        self.log_token_info(plot_content, "プロット")
        
        prompt = EPISODE_GENERATION_PROMPT.format(
            setting_content=setting_content,
            plot_content=plot_content
        )
        
        # プロンプト全体のサイズを確認
        self.console.print(f"[dim]プロンプトテンプレート適用後の全体サイズ確認[/dim]")
        
        episode_content = self.generate_text(prompt, "エピソード生成中...")
        
        self.console.print(f"[green]✓ エピソード生成完了![/green]")
        
        # 生成されたエピソードのサイズをログ出力
        self.log_token_info(episode_content, "生成されたエピソード")
        
        return episode_content
