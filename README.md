# YumeChain - AI 小説生成ツール

LLM（OpenAI、Gemini、Anthropic など）を使って設定から小説を自動生成する Python パッケージです。

## 機能

- 設定ファイル（Markdown）からプロット生成
- プロットから各話の本文生成
- 複数の LLM プロバイダー対応（OpenAI、Gemini、Anthropic、Azure）
- インタラクティブな CLI インターフェース
- Flask による Web 表示機能（ポート指定対応）
- ドライランモード対応
- コンテキストキャッシュ機能
- はてなブログ投稿機能（AtomPub API 経由）

## インストール

### 開発版として使用する場合

1. リポジトリをクローン

```bash
git clone <repository-url>
cd llm-x-reader
```

2. uv を使って開発環境をセットアップ

```bash
uv sync
```

3. 環境変数を設定

```bash
cp .env.example .env
# .env ファイルを編集してLLM API Keyを設定
```

### パッケージとしてインストール（将来対応）

```bash
pip install yumechain
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

### コンテキストキャッシュ機能

長い設定ファイルを効率的に処理するために、コンテキストキャッシュ機能を利用できます。

#### 対応プロバイダー・モデル

**Anthropic Claude (推奨):**

- `claude-3-5-sonnet-20241022`、`claude-3-5-haiku-20241022`
- `claude-3-haiku-20240307`、`claude-3-opus-20240229`

**OpenAI:**

- `gpt-4o`、`gpt-4o-mini`とその各バージョン

#### 設定方法

```bash
# コンテキストキャッシュを有効化
ENABLE_CONTEXT_CACHE=true

# 対応モデルを使用
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=your_actual_api_key
```

#### 効果

- **コスト削減**: 設定ファイルがキャッシュされ、毎回の送信が不要
- **処理高速化**: キャッシュ部分の処理が高速化
- **自動フォールバック**: 非対応モデルでは従来方式で動作

#### テスト

```bash
# コンテキストキャッシュ機能をテスト
uv run script/test_context_cache.py
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
- **コスト効率**: キャッシュ対応モデル（Claude、GPT-4o）+ `ENABLE_CONTEXT_CACHE=true`

## 使用方法

### パッケージとして使用（推奨）

yumechain がインストールされている場合：

```bash
yumechain
```

### 開発環境での使用

開発環境では以下の方法で実行できます：

```bash
# インタラクティブメニューを表示
uv run yumechain/cli.py

# または直接コマンドを実行
uv run yumechain/cli.py init --title "昭和転生"
```

### インタラクティブメニュー（推奨）

オプション無しで実行すると、使いやすいメニューが表示されます：

```bash
yumechain
```

メニューから番号を選択することで、各機能を手軽に実行できます。必要な情報（タイトル、編、話数など）は対話的に選択できるため、長いコマンドラインオプションを覚える必要がありません。

### コマンドライン直接実行

従来通り、コマンドラインで直接実行することも可能です：

### 1. 新しい小説プロジェクトを初期化

```bash
yumechain init --title "昭和転生"
```

### 2. 設定ファイルを編集

生成された `books/昭和転生/setting.md` を編集して、世界観やキャラクターを設定します。

### 3. プロット生成

#### 全編のプロット生成

```bash
yumechain generate-plot --title "昭和転生"
```

#### 特定の編のプロット生成

```bash
yumechain generate-plot --title "昭和転生" --arc "中学生編"
```

**特定編生成のメリット:**

- 既存のプロットに新しい編を追加できる
- 特定の編だけ書き直したい場合に便利
- 長大な作品の場合、編ごとに分けて生成することでトークン制限を回避

### 4. 各話の本文生成

```bash
yumechain generate-episode --title "昭和転生" --arc "中学生編" --episodes "1"
```

### 5. プロジェクト状態確認

```bash
yumechain status --title "昭和転生"
```

### 6. 生成した小説を Web ブラウザで読む

```bash
yumechain read --title "昭和転生"
```

**オプション:**

- `--port <ポート番号>`: サーバーポートを指定（デフォルト: 5000）
- `--auto-port`: 利用可能なポートを自動で検索
- `--no-browser`: ブラウザの自動起動を無効化

**使用例:**

```bash
# デフォルトポート（5000）で起動
yumechain read --title "昭和転生"

# カスタムポート指定
yumechain read --title "昭和転生" --port 8080

# 利用可能なポートを自動検索
yumechain read --title "昭和転生" --auto-port

# ポート指定 + ブラウザ自動起動無効化
yumechain read --title "昭和転生" --port 3000 --no-browser
```

## Web 表示機能

YumeChain では Flask を使用した軽量な Web 表示機能を提供します。

### Flask Web サーバー

- **特徴**: 軽量 Web フレームワーク
- **メリット**: 高速起動、シンプルな構成、小説読書に最適化された UI
- **用途**: 小説の閲覧、リアルタイム表示
- **ポート**: 5000（デフォルト、変更可能）

### ポート指定機能

複数のサーバーを同時に起動したり、ポートの競合を回避するために、柔軟なポート指定機能を提供：

- **固定ポート指定**: `--port` オプションで任意のポート番号を指定
- **自動ポート検索**: `--auto-port` オプションで利用可能なポートを自動検索
- **インタラクティブ設定**: メニューからの起動時も対話的にポート設定可能

## はてなブログ投稿機能

生成した小説エピソードを直接はてなブログに投稿できます。Markdown 形式のコンテンツを自動的に HTML に変換し、段落内の改行も正しく`<br>`タグに変換されるため、読みやすい形で投稿されます。

### 特徴

- **自動 HTML 変換**: Markdown 形式のコンテンツを自動的に HTML に変換
- **改行の保持**: 段落内の改行を`<br>`タグに変換して、元の改行を保持
- **プレビュー機能**: 投稿前に Markdown または HTML 形式でプレビュー可能
- **下書き対応**: 下書きとして保存可能
- **カテゴリ設定**: 複数カテゴリの設定に対応

### はてなブログの設定

投稿機能を使用するには、以下の環境変数を `.env` ファイルに設定してください：

```bash
# はてなブログ投稿設定
HATENA_USERNAME=your_hatena_username
HATENA_API_KEY=your_hatena_api_key
HATENA_BLOG_ID=your_blog_id.hatenablog.com
```

**API キーの取得方法:**

1. はてなブログの管理画面にログイン
2. 設定 → 詳細設定 → API キー
3. AtomPub API キーを確認

### 7. はてなブログに投稿

#### 投稿可能なエピソード一覧を表示

```bash
yumechain publish --title "昭和転生"
```

#### 特定のエピソードを投稿

```bash
yumechain publish --title "昭和転生" --episode "中学生編_01"
```

#### オプション

- `--blog-title`: ブログ記事のタイトル（指定しない場合はエピソード名を使用）
- `--categories`: カテゴリ（カンマ区切りで複数指定可能）
- `--draft`: 下書きとして投稿
- `--preview`: 投稿内容をプレビュー表示のみ（実際には投稿しない）
- `--preview-html`: 投稿内容を HTML 形式でプレビュー表示（改行変換結果を確認可能）

**使用例:**

```bash
# Markdownプレビュー表示
yumechain publish --title "昭和転生" --episode "中学生編_01" --preview

# HTML変換後のプレビュー表示
yumechain publish --title "昭和転生" --episode "中学生編_01" --preview-html

# カスタムタイトルとカテゴリで投稿
yumechain publish --title "昭和転生" --episode "中学生編_01" \
  --blog-title "昭和転生 第1話：タイムスリップ" \
  --categories "小説,転生,昭和"

# 下書きとして投稿
yumechain publish --title "昭和転生" --episode "中学生編_01" --draft
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

yumechain/               # YumeChainパッケージ
├─ cli.py               # コマンドラインインターフェース
├─ llm_client.py        # LLMクライアント
├─ file_manager.py      # ファイル管理
├─ flask_manager.py     # Flask Webサーバー管理
├─ prompt_templates.py  # プロンプトテンプレート
├─ static/              # 静的ファイル
│  └─ css/
│     └─ novel.css      # 小説表示用CSS
└─ theme/               # 表示テーマ
   └─ templates/
      ├─ base.html
      ├─ index.html
      └─ article.html
```

**注意**: 生成された小説プロジェクトは`books/`ディレクトリ配下に保存され、`.gitignore`で除外されます。

## コマンドリファレンス

### init

新しい小説プロジェクトを初期化します。

```bash
yumechain init --title <小説タイトル>
```

### generate-plot

設定ファイルからプロットを生成します。

```bash
# 全編のプロット生成
yumechain generate-plot --title <小説タイトル> [--dry-run]

# 特定の編のプロット生成
yumechain generate-plot --title <小説タイトル> --arc <編名> [--dry-run]
```

**オプション:**

- `--arc <編名>`: 特定の編のプロットのみ生成。既存プロットとマージされます
- `--dry-run`: ドライラン（API 呼び出しなし）

### generate-episode

指定した話の本文を生成します。

```bash
yumechain generate-episode --title <小説タイトル> --arc <編名> --episodes <話番号> [--dry-run] [--force]
```

**話番号の指定方法:**

- 単一話: `1`
- 範囲指定: `1-3`
- 複数指定: `1,3,5`
- 組み合わせ: `2-4,7,9-10`

### status

プロジェクトの状態を表示します。

```bash
yumechain status --title <小説タイトル>
```

### read

生成した小説を Web ブラウザで読みやすく表示します。

```bash
yumechain read --title <小説タイトル> [--port <ポート番号>] [--auto-port] [--no-browser]
```

**オプション:**

- `--port <ポート番号>`: サーバーポートを指定（デフォルト: 5000）
- `--auto-port`: 利用可能なポートを自動で検索
- `--no-browser`: ブラウザの自動起動を無効化

**特徴:**

- Flask による軽量 Web サーバー
- 小説読書に特化したカスタム CSS
- レスポンシブデザイン対応
- 記事間のナビゲーション機能
- ポートの競合回避機能

**使用例:**

```bash
# デフォルトポートで起動
yumechain read --title "昭和転生"

# カスタムポート指定
yumechain read --title "昭和転生" --port 8080

# 自動ポート検索
yumechain read --title "昭和転生" --auto-port

# ブラウザ自動起動無効化
yumechain read --title "昭和転生" --no-browser
```

### publish

生成した小説エピソードをはてなブログに投稿します。

```bash
# 投稿可能なエピソード一覧を表示
yumechain publish --title <小説タイトル>

# 特定のエピソードを投稿
yumechain publish --title <小説タイトル> --episode <エピソード名> [オプション]
```

**主要オプション:**

- `--episode <エピソード名>`: 投稿するエピソード名を指定
- `--blog-title <タイトル>`: ブログ記事のタイトル（省略時はエピソード名を使用）
- `--categories <カテゴリ>`: カテゴリ（カンマ区切りで複数指定可能）
- `--draft`: 下書きとして投稿
- `--preview`: 投稿内容をプレビュー表示のみ（実際には投稿しない）
- `--preview-html`: 投稿内容を HTML 形式でプレビュー表示（改行変換結果を確認可能）

**使用例:**

```bash
# エピソード一覧表示
yumechain publish --title "昭和転生"

# 基本的な投稿
yumechain publish --title "昭和転生" --episode "中学生編_01"

# プレビュー表示
yumechain publish --title "昭和転生" --episode "中学生編_01" --preview

# HTML変換後のプレビュー表示
yumechain publish --title "昭和転生" --episode "中学生編_01" --preview-html

# カスタムタイトルとカテゴリ付きで投稿
yumechain publish --title "昭和転生" --episode "中学生編_01" \
  --blog-title "昭和転生 第1話：タイムスリップ" \
  --categories "小説,転生,昭和"

# 下書きとして投稿
yumechain publish --title "昭和転生" --episode "中学生編_01" --draft
```

**前提条件:**

はてなブログ投稿機能を使用するには、以下の環境変数が必要です：

- `HATENA_USERNAME`: はてなユーザー名
- `HATENA_API_KEY`: はてなブログ AtomPub API キー
- `HATENA_BLOG_ID`: ブログ ID（例: xxxxx.hatenablog.com）

## オプション

- `--dry-run`: API 呼び出しを行わず、実行内容のプレビューのみ表示
- `--force`: 既存ファイルを上書き

## 開発情報

### パッケージ構造

YumeChain は以下のコンポーネントで構成されています：

- **CLI**: `yumechain.cli` - コマンドラインインターフェース
- **LLM クライアント**: `yumechain.llm_client` - 複数 LLM プロバイダー対応
- **ファイル管理**: `yumechain.file_manager` - プロジェクトファイル操作
- **Web 表示**: `yumechain.flask_manager` - 小説の Web 表示機能
- **プロンプトテンプレート**: `yumechain.prompt_templates` - LLM 用プロンプト定義
- **テーマとスタイル**: `yumechain/theme/`, `yumechain/static/` - Web 表示用カスタマイズ

### スクリプト

プロジェクトには以下のテスト・ユーティリティスクリプトが含まれています：

- `script/test_context_cache.py` - コンテキストキャッシュ機能のテスト
- `script/test_episode_generation_with_previous.py` - エピソード生成のテスト
- `script/test_litellm.py` - LiteLLM 統合のテスト
- `script/list_models.py` - 利用可能なモデル一覧表示

## 必要な環境変数

使用するプロバイダーに応じて、以下の API キーが必要です：

- `OPENAI_API_KEY`: OpenAI の API キー
- `GEMINI_API_KEY` または `GOOGLE_API_KEY`: Google Gemini の API キー
- `ANTHROPIC_API_KEY`: Anthropic の API キー
- `AZURE_API_KEY` と `AZURE_API_BASE`: Azure OpenAI の設定

## ライセンス

MIT License
