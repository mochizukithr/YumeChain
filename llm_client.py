"""
LLM クライアント
"""
import os
import json
import time
from typing import Dict, Any, Optional, List
import litellm
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

# 環境変数を読み込み
load_dotenv()

class LLMClient:
    """LiteLLMを使用してマルチプロバイダー対応のLLMクライアント"""
    
    def __init__(self, model_name: Optional[str] = None, temperature: Optional[float] = None, 
                 top_p: Optional[float] = None, config_prefix: str = "LLM"):
        """
        初期化
        
        Args:
            model_name: モデル名（指定しない場合は環境変数から取得）
            temperature: Temperature値（指定しない場合は環境変数から取得）
            top_p: Top-p値（指定しない場合は環境変数から取得）
            config_prefix: 環境変数のプレフィックス（例: "LLM", "PLOT", "EPISODE"）
        """
        # プロバイダーの取得（デフォルトはgemini）
        self.provider = os.getenv('LLM_PROVIDER', 'gemini')
        
        # モデル名の取得（優先度: 引数 > 環境変数 > デフォルト）
        default_models = {
            'openai': 'gpt-4o-mini',
            'gemini': 'gemini/gemini-2.5-flash',
            'anthropic': 'claude-3-haiku-20240307',
            'azure': 'gpt-4o-mini'
        }
        
        self.model_name = (
            model_name or 
            os.getenv(f'{config_prefix}_MODEL') or 
            os.getenv('LLM_MODEL') or 
            default_models.get(self.provider, 'gemini-2.5-flash')
        )
        
        # 生成パラメータの取得（優先度: 引数 > 環境変数 > デフォルト）
        self.temperature = (
            temperature if temperature is not None else
            float(os.getenv(f'{config_prefix}_TEMPERATURE') or 
                  os.getenv('LLM_TEMPERATURE') or '1.0')
        )
        
        self.top_p = (
            top_p if top_p is not None else
            float(os.getenv(f'{config_prefix}_TOP_P') or 
                  os.getenv('LLM_TOP_P') or '0.95')
        )
        
        # コンテキストキャッシュの設定
        self.enable_context_cache = os.getenv('ENABLE_CONTEXT_CACHE', 'false').lower() == 'true'
        self.cached_contexts = {}  # キャッシュされたコンテキストを保存
        
        # LiteLLMの設定
        self._setup_litellm()
        
        self.console = Console()
        
        # 設定情報をログ出力
        cache_status = "有効" if self.enable_context_cache else "無効"
        self.console.print(f"[dim]プロバイダー: {self.provider}, モデル: {self.model_name}, Temperature: {self.temperature}, Top-p: {self.top_p}, キャッシュ: {cache_status}[/dim]")
        
        # トークン使用量を追跡
        self.total_input_tokens = 0
        self.total_output_tokens = 0
    
    def _setup_litellm(self):
        """LiteLLMの設定"""
        # デバッグモードの設定（エラー時に詳細情報を表示）
        if os.getenv('LITELLM_DEBUG'):
            litellm.set_verbose = True
        else:
            litellm.set_verbose = False
        
        # プロバイダーごとのAPI キー設定
        if self.provider == 'openai':
            if not os.getenv('OPENAI_API_KEY'):
                raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI provider")
        elif self.provider == 'gemini':
            if not os.getenv('GEMINI_API_KEY'):
                raise ValueError("GEMINI_API_KEY environment variable is required for Gemini provider")
        elif self.provider == 'anthropic':
            if not os.getenv('ANTHROPIC_API_KEY'):
                raise ValueError("ANTHROPIC_API_KEY environment variable is required for Anthropic provider")
        elif self.provider == 'azure':
            if not os.getenv('AZURE_API_KEY'):
                raise ValueError("AZURE_API_KEY environment variable is required for Azure provider")
            if not os.getenv('AZURE_API_BASE'):
                raise ValueError("AZURE_API_BASE environment variable is required for Azure provider")
    
    @classmethod
    def create_for_plot_generation(cls) -> 'LLMClient':
        """プロット生成用のLLMClientを作成"""
        return cls(config_prefix="PLOT")
    
    @classmethod
    def create_for_episode_generation(cls) -> 'LLMClient':
        """エピソード生成用のLLMClientを作成"""
        return cls(config_prefix="EPISODE")
    
    def count_tokens(self, text: str) -> int:
        """テキストのトークン数をカウント"""
        try:
            # LiteLLMを使用してトークン数をカウント
            token_count = litellm.token_counter(model=self.model_name, text=text)
            return token_count
        except Exception as e:
            # トークンカウントでエラーが発生した場合は推定値を返す
            self.console.print(f"[yellow]⚠️ トークンカウントエラー: {str(e)}[/yellow]")
            # 大まかな推定（1トークン = 約4文字）
            return len(text) // 4
    
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
    
    def generate_text(self, prompt: str, progress_description: Optional[str] = None, 
                     cached_keys: List[str] = None) -> str:
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
                    
                    # メッセージリストを構築（キャッシュ考慮）
                    messages = self._build_messages_with_cache(prompt, cached_keys)
                    
                    # プロンプトのトークン数をカウント
                    prompt_token_count = self.count_tokens(prompt)
                    self.console.print(f"[dim]プロンプト: {len(prompt)}文字, {prompt_token_count}トークン[/dim]")
                    self.console.print(f"[dim]モデル: {self.model_name}[/dim]")
                    
                    # API呼び出し
                    self.console.print("[dim]API呼び出し中...[/dim]")
                    
                    # LiteLLMを使用してAPIを呼び出し
                    # Geminiの安全設定を調整（コンテンツフィルター緩和）
                    extra_params = {}
                    if self.provider == 'gemini':
                        # 環境変数でGeminiの安全設定を制御
                        if os.getenv('GEMINI_SAFETY_DISABLED', 'false').lower() == 'true':
                            extra_params["safety_settings"] = [
                                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                            ]
                            self.console.print(f"[dim]Gemini安全フィルターを無効化[/dim]")
                        
                        # Geminiでキャッシュが有効な場合の処理
                        if cached_keys and self.enable_context_cache and self._is_context_cache_supported():
                            # TTL (Time To Live) を設定（オプション、デフォルトは1時間）
                            cache_ttl = os.getenv('GEMINI_CACHE_TTL', '3600')  # 秒単位
                            extra_params["ttl"] = int(cache_ttl)
                            self.console.print(f"[dim]Geminiキャッシュ機能を使用 (TTL: {cache_ttl}秒)[/dim]")
                    
                    response = litellm.completion(
                        model=self.model_name,
                        messages=messages,
                        temperature=self.temperature,
                        top_p=self.top_p,
                        **extra_params
                    )
                    
                    elapsed_time = time.time() - start_time
                    response_text = response.choices[0].message.content
                    
                    # レスポンステキストの検証
                    if response_text is None:
                        # finish_reasonを確認してコンテンツフィルターの場合は特別な処理
                        finish_reason = response.choices[0].finish_reason if response.choices else "unknown"
                        
                        if finish_reason == 'content_filter':
                            self.console.print(f"[red]✗ コンテンツフィルターによってレスポンスがブロックされました[/red]")
                            self.console.print(f"[yellow]⚠️ プロンプトの内容を確認し、以下を試してください：[/yellow]")
                            self.console.print(f"[yellow]  - より穏やかな表現に変更[/yellow]")
                            self.console.print(f"[yellow]  - 暴力的、性的、または不適切な内容を削除[/yellow]")
                            self.console.print(f"[yellow]  - 異なるモデル（gemini-1.5-flash など）を試す[/yellow]")
                            self.console.print(f"[yellow]  - OpenAIなど他のプロバイダーに切り替える[/yellow]")
                            
                            # プロンプトの一部を表示してデバッグを支援
                            if os.getenv('LITELLM_LOG') == 'DEBUG':
                                prompt_preview = prompt[:500] + "..." if len(prompt) > 500 else prompt
                                self.console.print(f"[dim]プロンプト先頭500文字: {prompt_preview}[/dim]")
                            
                            raise Exception(f"Content filtered by safety mechanisms (reason: {finish_reason})")
                        else:
                            self.console.print(f"[red]✗ API から空のレスポンスが返されました (finish_reason: {finish_reason})[/red]")
                            self.console.print(f"[dim]レスポンス詳細: {response}[/dim]")
                            raise Exception(f"API returned None response (finish_reason: {finish_reason})")
                    
                    response_length = len(response_text)
                    
                    # レスポンスのトークン数をカウント
                    response_token_count = self.count_tokens(response_text)
                    total_tokens = prompt_token_count + response_token_count
                    
                    # トークン使用量を記録（レスポンスから取得できる場合はそれを使用）
                    if hasattr(response, 'usage') and response.usage:
                        input_tokens = response.usage.prompt_tokens
                        output_tokens = response.usage.completion_tokens
                    else:
                        input_tokens = prompt_token_count
                        output_tokens = response_token_count
                    
                    self.update_token_usage(input_tokens, output_tokens)
                    
                    self.console.print(f"[green]✓ 完了[/green] (所要時間: {elapsed_time:.1f}秒)")
                    self.console.print(f"[dim]レスポンス: {response_length}文字, {output_tokens}トークン[/dim]")
                    self.console.print(f"[dim]合計トークン数: {input_tokens + output_tokens} (入力: {input_tokens}, 出力: {output_tokens})[/dim]")
                    
                    return response_text
            else:
                # メッセージリストを構築（キャッシュ考慮）
                messages = self._build_messages_with_cache(prompt, cached_keys)
                
                # Geminiの安全設定を調整（コンテンツフィルター緩和）
                extra_params = {}
                if self.provider == 'gemini':
                    # 環境変数でGeminiの安全設定を制御
                    if os.getenv('GEMINI_SAFETY_DISABLED', 'false').lower() == 'true':
                        extra_params["safety_settings"] = [
                            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                        ]
                        self.console.print(f"[dim]Gemini安全フィルターを無効化[/dim]")
                    
                    # Geminiでキャッシュが有効な場合の処理
                    if cached_keys and self.enable_context_cache and self._is_context_cache_supported():
                        # TTL (Time To Live) を設定（オプション、デフォルトは1時間）
                        cache_ttl = os.getenv('GEMINI_CACHE_TTL', '3600')  # 秒単位
                        extra_params["ttl"] = int(cache_ttl)
                        self.console.print(f"[dim]Geminiキャッシュ機能を使用 (TTL: {cache_ttl}秒)[/dim]")
                
                response = litellm.completion(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    **extra_params
                )
                response_text = response.choices[0].message.content
                
                # レスポンステキストの検証
                if response_text is None:
                    # finish_reasonを確認してコンテンツフィルターの場合は特別な処理
                    finish_reason = response.choices[0].finish_reason if response.choices else "unknown"
                    
                    if finish_reason == 'content_filter':
                        self.console.print(f"[red]✗ コンテンツフィルターによってレスポンスがブロックされました[/red]")
                        self.console.print(f"[yellow]⚠️ プロンプトの内容を確認し、以下を試してください：[/yellow]")
                        self.console.print(f"[yellow]  - より穏やかな表現に変更[/yellow]")
                        self.console.print(f"[yellow]  - 暴力的、性的、または不適切な内容を削除[/yellow]")
                        self.console.print(f"[yellow]  - 異なるモデル（gemini-1.5-flash など）を試す[/yellow]")
                        self.console.print(f"[yellow]  - OpenAIなど他のプロバイダーに切り替える[/yellow]")
                        
                        # プロンプトの一部を表示してデバッグを支援
                        if os.getenv('LITELLM_LOG') == 'DEBUG':
                            prompt_preview = prompt[:500] + "..." if len(prompt) > 500 else prompt
                            self.console.print(f"[dim]プロンプト先頭500文字: {prompt_preview}[/dim]")
                        
                        raise Exception(f"Content filtered by safety mechanisms (reason: {finish_reason})")
                    else:
                        self.console.print(f"[red]✗ API から空のレスポンスが返されました (finish_reason: {finish_reason})[/red]")
                        self.console.print(f"[dim]レスポンス詳細: {response}[/dim]")
                        raise Exception(f"API returned None response (finish_reason: {finish_reason})")
                
                return response_text
        except Exception as e:
            if progress_description:
                elapsed_time = time.time() - start_time if 'start_time' in locals() else 0
                self.console.print(f"[red]✗ エラー (所要時間: {elapsed_time:.1f}秒): {str(e)}[/red]")
                
                # LiteLLMの詳細エラー情報を出力
                if hasattr(e, 'response') and e.response:
                    self.console.print(f"[dim]HTTPステータス: {e.response.status_code}[/dim]")
                    self.console.print(f"[dim]レスポンス: {e.response.text}[/dim]")
                
                # APIキーやモデル設定の確認を促す
                self.console.print(f"[yellow]⚠️ 設定確認: プロバイダー={self.provider}, モデル={self.model_name}[/yellow]")
                
            raise Exception(f"LLM API error: {str(e)}")
    
    def generate_plot(self, setting_content: str, target_arc: str = None) -> Dict[str, Any]:
        """プロット生成"""
        from prompt_templates import PLOT_GENERATION_PROMPT, ARC_SPECIFIC_PLOT_GENERATION_PROMPT
        
        self.console.print("[bold blue]📖 プロット生成を開始します[/bold blue]")
        
        # 設定ファイルをキャッシュ対象として登録
        self.cache_setting_content(setting_content)
        
        # キャッシュを考慮したプロンプト作成
        if self.enable_context_cache and self._is_context_cache_supported():
            if target_arc:
                # 特定のアークのプロット生成（キャッシュ版）
                self.console.print(f"[dim]対象編: {target_arc}[/dim]")
                prompt = f"""指定された編のプロットを生成してください。

対象編: {target_arc}

以下の条件で物語のプロットを作成してください：
- 指定された編に焦点を当てる
- その編内の各エピソードの詳細なプロットを含める
- JSON形式で出力する
- 各エピソードは数値のキーで管理
- 形式例：
{{
  "{target_arc}": {{
    "1": "エピソード1のプロット詳細...",
    "2": "エピソード2のプロット詳細..."
  }}
}}"""
            else:
                # 全体のプロット生成（キャッシュ版）
                prompt = """全体の物語プロットを生成してください。

以下の条件で物語のプロットを作成してください：
- 複数の編に分けて構成
- 各編に複数のエピソードを含める
- 各エピソードの詳細なプロットを記載
- JSON形式で出力する
- 各エピソードは数値のキーで管理
- 形式例：
{
  "第一編": {
    "1": "エピソード1のプロット詳細...",
    "2": "エピソード2のプロット詳細..."
  },
  "第二編": {
    "1": "エピソード1のプロット詳細..."
  }
}"""
            cached_keys = ["setting"]
        else:
            # 従来のプロンプト
            if target_arc:
                # 特定のアークのプロット生成
                self.console.print(f"[dim]対象編: {target_arc}[/dim]")
                template = ARC_SPECIFIC_PLOT_GENERATION_PROMPT
                prompt = template.format(setting_content=setting_content, target_arc=target_arc)
            else:
                # 全体のプロット生成
                template = PLOT_GENERATION_PROMPT
                prompt = template.format(setting_content=setting_content)
            cached_keys = None
        
        # プロンプトテンプレートのサイズを確認（従来版使用時のみ）
        if not (self.enable_context_cache and self._is_context_cache_supported()):
            template_size = len(template) - len("{setting_content}") - (len("{target_arc}") if target_arc else 0)
            template_clean = template.replace('{setting_content}', '').replace('{target_arc}', '' if target_arc else '')
            self.console.print(f"[dim]プロンプトテンプレート: {template_size}文字, {self.count_tokens(template_clean)}トークン[/dim]")
        
        # 設定ファイルのトークン数をログ出力
        self.log_token_info(setting_content, "設定ファイル")
        
        # プロンプト全体のサイズを確認
        self.console.print(f"[dim]プロンプトテンプレート適用後の全体サイズ確認[/dim]")
        
        response = self.generate_text(prompt, "プロット生成中...", cached_keys)
        
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
        
        # 設定ファイルをキャッシュ対象として登録
        self.cache_setting_content(setting_content)
        
        # プロンプトテンプレートのサイズを確認
        template_size = len(EPISODE_GENERATION_PROMPT) - len("{setting_content}") - len("{plot_content}")
        template_clean = EPISODE_GENERATION_PROMPT.replace('{setting_content}', '').replace('{plot_content}', '')
        self.console.print(f"[dim]プロンプトテンプレート: {template_size}文字, {self.count_tokens(template_clean)}トークン[/dim]")
        
        # 各コンテンツのトークン数をログ出力
        self.log_token_info(setting_content, "設定ファイル")
        self.log_token_info(plot_content, "プロット")
        
        # キャッシュを考慮したプロンプト作成
        if self.enable_context_cache and self._is_context_cache_supported():
            # キャッシュ使用時は設定ファイルを分離したプロンプト
            prompt = f"""以下のプロットに基づいてエピソードを生成してください：

{plot_content}

生成要件:
- 日本語で書く
- 小説形式で書く
- 会話は「」で囲む
- 地の文で心情や状況を丁寧に描写する
- エピソードとして自然な長さにする（3000-8000文字程度）
- ストーリーの流れを自然にする
- キャラクターの個性を活かす"""
            cached_keys = ["setting"]
        else:
            # 従来のプロンプト
            prompt = EPISODE_GENERATION_PROMPT.format(
                setting_content=setting_content,
                plot_content=plot_content
            )
            cached_keys = None
        
        # プロンプト全体のサイズを確認
        self.console.print(f"[dim]プロンプトテンプレート適用後の全体サイズ確認[/dim]")
        
        episode_content = self.generate_text(prompt, "エピソード生成中...", cached_keys)
        
        self.console.print(f"[green]✓ エピソード生成完了![/green]")
        
        # 生成されたエピソードのサイズをログ出力
        self.log_token_info(episode_content, "生成されたエピソード")
        
        return episode_content
    
    def generate_episode_with_context(self, setting_content: str, arc: str, episode: int, 
                                      plot_data: Dict[str, Any]) -> str:
        """
        前後のエピソード情報を含めてエピソード生成
        
        Args:
            setting_content: 設定ファイルの内容
            arc: 編名
            episode: エピソード番号
            plot_data: プロット全体のデータ
        
        Returns:
            生成されたエピソード本文
        """
        from prompt_templates import EPISODE_GENERATION_WITH_CONTEXT_PROMPT, EPISODE_GENERATION_PROMPT
        
        self.console.print("[bold blue]📝 エピソード生成を開始します（前後情報付き）[/bold blue]")
        
        # 設定ファイルをキャッシュ対象として登録
        self.cache_setting_content(setting_content)
        
        # 現在のエピソードのプロットを取得
        current_plot = plot_data.get(arc, {}).get(str(episode), "")
        if not current_plot:
            raise ValueError(f"Episode {episode} not found in arc '{arc}'")
        
        # 前後のエピソードプロットを取得（ファイル構造ベース）
        previous_plot = self._get_adjacent_episode_plot_by_file_order(plot_data, arc, episode, "previous")
        next_plot = self._get_adjacent_episode_plot_by_file_order(plot_data, arc, episode, "next")
        
        # キャッシュを考慮したプロンプト作成
        if self.enable_context_cache and self._is_context_cache_supported():
            # キャッシュ使用時は設定ファイルを分離したプロンプト
            if previous_plot or next_plot:
                prompt = f"""以下のプロット情報に基づいてエピソードを生成してください：

前の話のプロット:
{previous_plot if previous_plot else "（なし）"}

現在の話のプロット:
{current_plot}

次の話のプロット:
{next_plot if next_plot else "（なし）"}

生成要件:
- 日本語で書く
- 小説形式で書く
- 会話は「」で囲む
- 地の文で心情や状況を丁寧に描写する
- エピソードとして自然な長さにする（3000-8000文字程度）
- 前後のエピソードとの連続性を意識する
- ストーリーの流れを自然にする
- キャラクターの個性を活かす"""
            else:
                prompt = f"""以下のプロットに基づいてエピソードを生成してください：

{current_plot}

生成要件:
- 日本語で書く
- 小説形式で書く
- 会話は「」で囲む
- 地の文で心情や状況を丁寧に描写する
- エピソードとして自然な長さにする（3000-8000文字程度）
- ストーリーの流れを自然にする
- キャラクターの個性を活かす"""
            cached_keys = ["setting"]
        else:
            # 従来のプロンプト
            if previous_plot or next_plot:
                template = EPISODE_GENERATION_WITH_CONTEXT_PROMPT
                prompt = template.format(
                    setting_content=setting_content,
                    previous_plot=previous_plot,
                    current_plot=current_plot,
                    next_plot=next_plot
                )
            else:
                # 前後の情報がない場合は従来のプロンプトを使用
                template = EPISODE_GENERATION_PROMPT
                prompt = template.format(
                    setting_content=setting_content,
                    plot_content=current_plot
                )
            cached_keys = None
        
        # プロンプトテンプレートのサイズを確認
        if not (self.enable_context_cache and self._is_context_cache_supported()):
            template_placeholders = len("{setting_content}") + len("{previous_plot}") + len("{current_plot}") + len("{next_plot}")
            template_size = len(template if 'template' in locals() else EPISODE_GENERATION_PROMPT) - template_placeholders
            self.console.print(f"[dim]プロンプトテンプレート: {template_size}文字[/dim]")
        
        # 各コンテンツのトークン数をログ出力
        self.log_token_info(setting_content, "設定ファイル")
        self.log_token_info(current_plot, "現在の話のプロット")
        if previous_plot:
            self.log_token_info(previous_plot, "前の話のプロット")
        if next_plot:
            self.log_token_info(next_plot, "次の話のプロット")
        
        # プロンプト全体のサイズを確認
        self.console.print(f"[dim]プロンプトテンプレート適用後の全体サイズ確認[/dim]")
        
        episode_content = self.generate_text(prompt, "エピソード生成中...", cached_keys)
        
        self.console.print(f"[green]✓ エピソード生成完了![/green]")
        
        # 生成されたエピソードのサイズをログ出力
        self.log_token_info(episode_content, "生成されたエピソード")
        
        return episode_content
    
    def _is_context_cache_supported(self) -> bool:
        """現在のプロバイダーがコンテキストキャッシュをサポートしているかチェック"""
        # Claude 3.5 Sonnet、Claude 3 Haiku、Claude 3.5 Haiku、Claude 3 Opus がサポート
        anthropic_cache_models = [
            'claude-3-5-sonnet-20241022',
            'claude-3-5-sonnet-20240620', 
            'claude-3-5-haiku-20241022',
            'claude-3-haiku-20240307',
            'claude-3-opus-20240229'
        ]
        
        # OpenAI GPT-4o、GPT-4o-mini もサポート
        openai_cache_models = [
            'gpt-4o',
            'gpt-4o-mini',
            'gpt-4o-2024-11-20',
            'gpt-4o-2024-08-06',
            'gpt-4o-mini-2024-07-18'
        ]
        
        # Google Gemini 1.5 Pro/Flash、2.0 Flash、2.5 Flash がサポート
        gemini_cache_models = [
            'gemini-1.5-pro',
            'gemini-1.5-flash',
            'gemini-2.0-flash',
            'gemini-2.5-flash',
            'gemini/gemini-1.5-pro',
            'gemini/gemini-1.5-flash',
            'gemini/gemini-2.0-flash',
            'gemini/gemini-2.5-flash'
        ]
        
        if self.provider == 'anthropic':
            return any(model in self.model_name for model in anthropic_cache_models)
        elif self.provider == 'openai':
            return any(model in self.model_name for model in openai_cache_models)
        elif self.provider == 'gemini':
            return any(model in self.model_name for model in gemini_cache_models)
        else:
            return False
    
    def _create_cached_message(self, content: str, cache_type: str = "ephemeral") -> Dict[str, Any]:
        """キャッシュ対象のメッセージを作成"""
        if not self._is_context_cache_supported():
            return {"role": "user", "content": content}
        
        if self.provider == 'anthropic':
            # Anthropic Claude のキャッシュ形式
            return {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": content,
                        "cache_control": {"type": cache_type}
                    }
                ]
            }
        elif self.provider == 'openai':
            # OpenAI のキャッシュ形式（将来のサポートに備えて）
            return {
                "role": "user", 
                "content": content
                # OpenAIのキャッシュパラメータは将来追加される可能性があります
            }
        elif self.provider == 'gemini':
            # Google Gemini のキャッシュ形式
            # Geminiではcached_contentとしてキャッシュコンテンツを事前登録し、
            # その後cached_content_token_countを使用する方式
            return {
                "role": "user", 
                "content": content,
                "_cache_hint": True  # LiteLLM経由での実装時の参考用
            }
        else:
            return {"role": "user", "content": content}
    
    def cache_setting_content(self, setting_content: str, cache_key: str = "setting") -> None:
        """設定ファイルの内容をキャッシュ対象として登録"""
        if not self.enable_context_cache:
            return
        
        if not self._is_context_cache_supported():
            self.console.print(f"[yellow]⚠️ {self.provider}/{self.model_name} はコンテキストキャッシュをサポートしていません[/yellow]")
            return
        
        self.cached_contexts[cache_key] = setting_content
        token_count = self.count_tokens(setting_content)
        self.console.print(f"[green]✓ 設定ファイルをキャッシュ対象として登録 ({token_count}トークン)[/green]")
    
    def _build_messages_with_cache(self, prompt: str, cached_keys: List[str] = None) -> List[Dict[str, Any]]:
        """キャッシュされたコンテキストを含むメッセージリストを構築"""
        messages = []
        
        # キャッシュされたコンテキストを追加
        if cached_keys and self.enable_context_cache and self._is_context_cache_supported():
            for key in cached_keys:
                if key in self.cached_contexts:
                    cached_content = self.cached_contexts[key]
                    cached_message = self._create_cached_message(cached_content)
                    messages.append(cached_message)
                    self.console.print(f"[dim]キャッシュされたコンテキスト '{key}' を使用[/dim]")
        
        # メインプロンプトを追加
        messages.append({"role": "user", "content": prompt})
        
        return messages
