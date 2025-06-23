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

## 注意事項

- 使用するプロバイダーに対応する API キーが必要です
- **Gemini モデルは `gemini/` プレフィックスが必要**（例: `gemini/gemini-1.5-flash`）
- モデル名は各プロバイダーの仕様に合わせて正確に記述してください
- Azure の場合、デプロイメント名を指定します（モデル名ではありません）
- レート制限やコストに注意してください
