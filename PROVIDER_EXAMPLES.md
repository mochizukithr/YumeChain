# LLM プロバイダー切り替え使用例

## 基本的な使用方法

1. `.env`ファイルに必要な環境変数を設定
2. `LLM_PROVIDER`を変更することでプロバイダーを切り替え

## プロバイダー別設定例

### Gemini を使用する場合（デフォルト）

```bash
LLM_PROVIDER=gemini
LLM_MODEL=gemini/gemini-1.5-flash
GEMINI_API_KEY=your_actual_gemini_api_key
```

### OpenAI を使用する場合

```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_actual_openai_api_key
```

### Anthropic Claude を使用する場合

```bash
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-haiku-20240307
ANTHROPIC_API_KEY=your_actual_anthropic_api_key
```

### Azure OpenAI を使用する場合

```bash
LLM_PROVIDER=azure
LLM_MODEL=your_deployment_name
AZURE_API_KEY=your_actual_azure_api_key
AZURE_API_BASE=https://your-resource.openai.azure.com/
```

## プロット・エピソード別設定

プロット生成とエピソード生成で異なるモデルやパラメータを使用できます：

```bash
# プロット生成は構造化重視でGemini Flash
PLOT_MODEL=gemini/gemini-1.5-flash
PLOT_TEMPERATURE=0.8

# エピソード生成は創造性重視でGPT-4o
EPISODE_MODEL=gpt-4o
EPISODE_TEMPERATURE=1.2
```

## コンテキストキャッシュ機能

長いプロンプトの一部（特に設定ファイル）をキャッシュして、API 呼び出しコストを削減できます。

### 対応プロバイダー・モデル

#### Anthropic Claude (推奨)

```bash
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022  # またはhaiku、opus
ANTHROPIC_API_KEY=your_actual_anthropic_api_key
ENABLE_CONTEXT_CACHE=true
```

対応モデル:

- `claude-3-5-sonnet-20241022`
- `claude-3-5-sonnet-20240620`
- `claude-3-5-haiku-20241022`
- `claude-3-haiku-20240307`
- `claude-3-opus-20240229`

#### OpenAI GPT-4o

```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini  # またはgpt-4o
OPENAI_API_KEY=your_actual_openai_api_key
ENABLE_CONTEXT_CACHE=true
```

対応モデル:

- `gpt-4o`
- `gpt-4o-mini`
- `gpt-4o-2024-11-20`
- `gpt-4o-2024-08-06`
- `gpt-4o-mini-2024-07-18`

#### Google Gemini (推奨)

```bash
LLM_PROVIDER=gemini
LLM_MODEL=gemini/gemini-2.5-flash  # または1.5-pro、2.0-flash等
GEMINI_API_KEY=your_actual_gemini_api_key
ENABLE_CONTEXT_CACHE=true
# オプション: キャッシュの有効期限（秒単位、デフォルト: 3600）
GEMINI_CACHE_TTL=7200
```

対応モデル:

- `gemini/gemini-1.5-pro`
- `gemini/gemini-1.5-flash`
- `gemini/gemini-2.0-flash`
- `gemini/gemini-2.5-flash`

### 使用効果

コンテキストキャッシュを有効にすると:

1. **設定ファイルがキャッシュされる** - 毎回の API 呼び出しで設定ファイル全体を送信する必要がなくなります
2. **API コストが削減される** - キャッシュされた部分は低コストで処理されます
3. **レスポンス時間が短縮される** - キャッシュされたコンテンツの処理が高速化されます

### 注意事項（コンテキストキャッシュ）

- キャッシュは一定時間後に自動削除されます（プロバイダーにより異なる）
- 設定ファイルが変更された場合、新しいセッションでキャッシュが更新されます
- 対応していないモデルでは自動的に通常のプロンプトにフォールバックします

## 注意事項

- 使用するプロバイダーに対応する API キーが必要です
- **Gemini モデルは `gemini/` プレフィックスが必要**（例: `gemini/gemini-1.5-flash`）
- モデル名は各プロバイダーの仕様に合わせて正確に記述してください
- Azure の場合、デプロイメント名を指定します（モデル名ではありません）
- レート制限やコストに注意してください
