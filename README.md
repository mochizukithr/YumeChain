# 小説生成 CUI アプリ

LLM（Gemini）を使って設定から小説を自動生成する Python アプリケーションです。

## 機能

- 設定ファイル（Markdown）からプロット生成
- プロットから各話の本文生成
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
uv add google-generativeai click python-dotenv
```

3. 環境変数を設定

```bash
cp .env.example .env
# .env ファイルを編集してGoogle API Keyを設定
```

## 使用方法

### 1. 新しい小説プロジェクトを初期化

```bash
uv run main.py init --title "昭和転生"
```

### 2. 設定ファイルを編集

生成された `昭和転生/setting.md` を編集して、世界観やキャラクターを設定します。

### 3. プロット生成

```bash
uv run main.py generate-plot --title "昭和転生"
```

### 4. 各話の本文生成

```bash
uv run main.py generate-episode --title "昭和転生" --arc "中学生編" --episode 1
```

### 5. プロジェクト状態確認

```bash
uv run main.py status --title "昭和転生"
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
uv run main.py generate-plot --title <小説タイトル> [--dry-run]
```

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

## オプション

- `--dry-run`: API 呼び出しを行わず、実行内容のプレビューのみ表示
- `--force`: 既存ファイルを上書き

## 必要な環境変数

- `GOOGLE_API_KEY`: Google Gemini API キー

## ライセンス

MIT License
