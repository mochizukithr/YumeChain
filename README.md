# 小説生成 CUI アプリ

LLM（OpenAI、Gemini、Anthropic など）を使って設定から小説を自動生成する Python アプリケーションです。

## 機能

- 設定ファイル（Markdown）からプロット生成
- プロットから各話の本文生成
- 複数の LLM プロバイダー対応（OpenAI、Gemini、Anthropic、Azure）
- CLI による簡単操作
- ドライランモード対応

## インストール

1. リポジトリをクローン

```bash
git clone <repository-url>
cd llm-x-reader
```

2. 依存関係をインストール

```bash
uv add google-generativeai click python-dotenv litellm
```

3. 環境変数を設定

```bash
cp .env.example .env
# .env ファイルを編集してGoogle API Keyを設定
```

## LLM プロバイダー設定

プロット生成とエピソード生成で異なる LLM プロバイダー、モデル、パラメータを設定できます。

### 基本設定（.env ファイル）

```bash
# LLM プロバイダー設定（openai, gemini, anthropic, azure から選択）
LLM_PROVIDER=gemini

# デフォルト設定（全処理共通）
LLM_MODEL=gemini/gemini-1.5-flash
LLM_TEMPERATURE=1.0
LLM_TOP_P=0.95

# プロバイダー別 API キー
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_API_KEY=your_gemini_api_key_here  # 互換性のため
ANTHROPIC_API_KEY=your_anthropic_api_key_here
AZURE_API_KEY=your_azure_api_key_here
AZURE_API_BASE=https://your-resource.openai.azure.com/

# プロット生成専用設定（オプション）
PLOT_MODEL=gemini/gemini-1.5-flash
PLOT_TEMPERATURE=0.8
PLOT_TOP_P=0.9

# エピソード生成専用設定（オプション）
EPISODE_MODEL=gemini/gemini-1.5-flash
EPISODE_TEMPERATURE=1.0
EPISODE_TOP_P=0.95
```

### プロバイダー別推奨モデル

**OpenAI:**

- `gpt-4o` (最高品質、高コスト)
- `gpt-4o-mini` (推奨、コスト効率良)
- `gpt-3.5-turbo` (低コスト)

**Gemini:**

- `gemini/gemini-1.5-flash` (推奨、高速)
- `gemini/gemini-1.5-pro` (高品質)
- `gemini/gemini-2.0-flash` (最新、高性能)

**Anthropic:**

- `claude-3-haiku-20240307` (高速、低コスト)
- `claude-3-sonnet-20240229` (バランス)
- `claude-3-opus-20240229` (最高品質)

**Azure:**

- お使いのデプロイメント名を指定

### プロバイダー切り替え例

**OpenAI を使用する場合:**

```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_actual_api_key
```

**Gemini を使用する場合（デフォルト）:**

```bash
LLM_PROVIDER=gemini
LLM_MODEL=gemini/gemini-1.5-flash
GEMINI_API_KEY=your_actual_api_key
```

**Anthropic を使用する場合:**

```bash
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-haiku-20240307
ANTHROPIC_API_KEY=your_actual_api_key
```

### 設定の優先順位

1. **専用設定**（`PLOT_*` または `EPISODE_*`）
2. **デフォルト設定**（`LLM_*`）
3. **内蔵デフォルト値**

例：プロット生成では `PLOT_TEMPERATURE` → `LLM_TEMPERATURE` → `1.0` の順で設定値が決定されます。

### 推奨設定

- **プロット生成**: `TEMPERATURE=0.8` (より構造的で一貫性のある出力)
- **エピソード生成**: `TEMPERATURE=1.0` (より創造的で表現豊かな出力)

### パフォーマンスとコストの考慮

- **高速・低コスト**: Gemini Flash、Claude Haiku、GPT-4o-mini
- **高品質**: Gemini Pro、Claude Opus、GPT-4o
- **バランス**: Claude Sonnet

## 使用方法

### インタラクティブメニュー（推奨）

オプション無しで実行すると、使いやすいメニューが表示されます：

```bash
uv run main.py
```

メニューから番号を選択することで、各機能を手軽に実行できます。必要な情報（タイトル、編、話数など）は対話的に選択できるため、長いコマンドラインオプションを覚える必要がありません。

### コマンドライン直接実行

従来通り、コマンドラインで直接実行することも可能です：

### 1. 新しい小説プロジェクトを初期化

```bash
uv run main.py init --title "昭和転生"
```

### 2. 設定ファイルを編集

生成された `昭和転生/setting.md` を編集して、世界観やキャラクターを設定します。

### 3. プロット生成

#### 全編のプロット生成

```bash
uv run main.py generate-plot --title "昭和転生"
```

#### 特定の編のプロット生成

```bash
uv run main.py generate-plot --title "昭和転生" --arc "中学生編"
```

**特定編生成のメリット:**

- 既存のプロットに新しい編を追加できる
- 特定の編だけ書き直したい場合に便利
- 長大な作品の場合、編ごとに分けて生成することでトークン制限を回避

### 4. 各話の本文生成

```bash
uv run main.py generate-episode --title "昭和転生" --arc "中学生編" --episode 1
```

### 5. プロジェクト状態確認

```bash
uv run main.py status --title "昭和転生"
```

### 6. 生成した小説を Web ブラウザで読む

```bash
uv run main.py read --title "昭和転生"
```

**オプション:**

- `--port <ポート番号>`: サーバーポートを指定（デフォルト: 8000）
- `--no-browser`: ブラウザの自動起動を無効化

例:

```bash
# ポート8080でサーバー起動、ブラウザ自動起動なし
uv run main.py read --title "昭和転生" --port 8080 --no-browser
```

## ディレクトリ構成

```
books/                   # 小説プロジェクトのルートディレクトリ
└─ 昭和転生/
   ├─ setting.md         # 世界観・構成・その他設定
   ├─ character.md       # キャラクター詳細設定
   ├─ plot.json          # 生成されたプロット
   └─ stories/           # 生成された本文
      ├─ 中学生編_01.md
      ├─ 中学生編_02.md
      └─ ...
```

**注意**: 生成された小説プロジェクトは`books/`ディレクトリ配下に保存され、`.gitignore`で除外されます。

## コマンドリファレンス

### init

新しい小説プロジェクトを初期化します。

```bash
uv run main.py init --title <小説タイトル>
```

### generate-plot

設定ファイルからプロットを生成します。

```bash
# 全編のプロット生成
uv run main.py generate-plot --title <小説タイトル> [--dry-run]

# 特定の編のプロット生成
uv run main.py generate-plot --title <小説タイトル> --arc <編名> [--dry-run]
```

**オプション:**

- `--arc <編名>`: 特定の編のプロットのみ生成。既存プロットとマージされます
- `--dry-run`: ドライラン（API 呼び出しなし）

### generate-episode

指定した話の本文を生成します。

```bash
uv run main.py generate-episode --title <小説タイトル> --arc <編名> --episode <話番号> [--dry-run] [--force]
```

### status

プロジェクトの状態を表示します。

```bash
uv run main.py status --title <小説タイトル>
```

### read

生成した小説を Web ブラウザで読みやすく表示します。

```bash
uv run main.py read --title <小説タイトル> [--port <ポート番号>] [--no-browser]
```

**特徴:**

- Pelican を使用した美しい Web レイアウト
- 小説読書に特化したカスタム CSS
- レスポンシブデザイン対応
- 記事間のナビゲーション機能

## オプション

- `--dry-run`: API 呼び出しを行わず、実行内容のプレビューのみ表示
- `--force`: 既存ファイルを上書き

## 必要な環境変数

使用するプロバイダーに応じて、以下の API キーが必要です：

- `OPENAI_API_KEY`: OpenAI の API キー
- `GEMINI_API_KEY` または `GOOGLE_API_KEY`: Google Gemini の API キー
- `ANTHROPIC_API_KEY`: Anthropic の API キー
- `AZURE_API_KEY` と `AZURE_API_BASE`: Azure OpenAI の設定

## ライセンス

MIT License
