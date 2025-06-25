# YumeChain セットアップガイド

このガイドでは、MacBook Air M1 での YumeChain パッケージの初期セットアップ手順を説明します。

## 前提条件

- MacBook Air M1 (Apple Silicon)
- macOS Monterey 以降
- インターネット接続

## 1. システム要件の確認

### macOS のバージョン確認

```bash
sw_vers
```

MacBook Air M1 では macOS Monterey (12.x) 以降が推奨されます。

## 2. Homebrew のインストール

Homebrew はパッケージ管理ツールです。ターミナルを開いて以下を実行してください。

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

インストール後、パスを通します：

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
source ~/.zshrc
```

### Homebrew のインストール確認

```bash
brew --version
```

## 3. Python のインストール

### Python 3.12+ のインストール

YumeChain は Python 3.12 以降が必要です。

```bash
brew install python@3.12
```

### Python のバージョン確認

```bash
python3 --version
```

Python 3.12.x が表示されることを確認してください。

## 4. uv のインストール

uv は高速な Python パッケージマネージャーです。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

インストール後、ターミナルを再起動するか、以下を実行してください：

```bash
source ~/.zshrc
```

### uv のインストール確認

```bash
uv --version
```

## 5. Git のセットアップ

### Git のインストール確認

```bash
git --version
```

Git がインストールされていない場合：

```bash
brew install git
```

### Git の基本設定（初回のみ）

```bash
git config --global user.name "あなたの名前"
git config --global user.email "your.email@example.com"
```

## 6. YumeChain プロジェクトのセットアップ

### リポジトリのクローン

```bash
cd ~/
git clone <repository-url>
cd llm-x-reader
```

### Python 環境のセットアップ

```bash
uv sync
```

このコマンドで以下が自動実行されます：

- 仮想環境の作成
- 依存関係のインストール
- パッケージの開発モードでのインストール

### インストールの確認

```bash
uv run yumechain --help
```

コマンドが正常に実行されれば、インストール完了です。

## 7. LLM API キーの設定

### 環境変数ファイルの作成

```bash
cp .env.example .env
```

### .env ファイルの編集

お好みのテキストエディタで `.env` ファイルを開き、使用する LLM プロバイダーの API キーを設定してください。

```bash
# Visual Studio Code を使用する場合
code .env

# nano エディタを使用する場合
nano .env

# vim を使用する場合
vim .env
```

### 推奨設定例

**Gemini を使用する場合（推奨・無料枠あり）:**

```bash
LLM_PROVIDER=gemini
LLM_MODEL=gemini/gemini-2.5-flash
GEMINI_API_KEY=your_actual_gemini_api_key_here
LLM_TEMPERATURE=1.0
LLM_TOP_P=0.95
```

**OpenAI を使用する場合:**

```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_actual_openai_api_key_here
LLM_TEMPERATURE=1.0
LLM_TOP_P=0.95
```

### API キーの取得方法

**Gemini API キー:**

1. [Google AI Studio](https://aistudio.google.com/) にアクセス
2. Google アカウントでログイン
3. "Get API key" をクリック
4. 新しい API キーを作成

**OpenAI API キー:**

1. [OpenAI Platform](https://platform.openai.com/) にアクセス
2. アカウント作成・ログイン
3. API Keys セクションでキーを作成

## 8. 動作確認

### 基本動作テスト

```bash
# インタラクティブメニューの起動
uv run yumechain

# または直接ヘルプを表示
uv run yumechain --help
```

### テストプロジェクトの作成

```bash
# 新しい小説プロジェクトを作成
uv run yumechain init --title "テスト小説"
```

### 生成されたファイルの確認

```bash
ls -la books/テスト小説/
```

以下のファイルが生成されていることを確認してください：

- `setting.md` - 世界観・設定ファイル
- `character.md` - キャラクター設定ファイル

## 9. 追加の開発ツール（オプション）

### Visual Studio Code のインストール

```bash
brew install --cask visual-studio-code
```

### 便利な VS Code 拡張機能

- Python
- Markdown All in One
- GitLens

### ターミナルエミュレータ（オプション）

より使いやすいターミナルをお好みで：

```bash
# iTerm2
brew install --cask iterm2

# Warp
brew install --cask warp
```

## 10. トラブルシューティング

### よくある問題と解決方法

#### Python のバージョンエラー

```bash
Error: Python 3.12+ is required
```

解決方法：

```bash
brew install python@3.12
# シェルを再起動後
uv sync
```

#### uv コマンドが見つからない

```bash
command not found: uv
```

解決方法：

```bash
source ~/.zshrc
# または新しいターミナルウィンドウを開く
```

#### API キーエラー

```bash
Error: API key not found
```

解決方法：

1. `.env` ファイルが存在することを確認
2. API キーが正しく設定されていることを確認
3. API キーに余分なスペースがないことを確認

#### 依存関係のエラー

```bash
uv sync
```

これで依存関係が再インストールされます。

### パフォーマンス最適化

#### M1 Mac 固有の設定

```bash
# Rosetta が必要な場合（通常は不要）
arch -x86_64 brew install <package-name>
```

### 権限の問題

ファイルの書き込み権限エラーが発生した場合：

```bash
chmod 755 ~/llm-x-reader
```

## 11. 次のステップ

セットアップが完了したら、以下のドキュメントを参照してください：

1. **[README.md](./README.md)** - 基本的な使用方法
2. **[PROVIDER_EXAMPLES.md](./PROVIDER_EXAMPLES.md)** - LLM プロバイダー設定例

### 最初の小説生成

```bash
# インタラクティブモードで開始（推奨）
uv run yumechain

# メニューから以下を順番に実行：
# 1. 新しいプロジェクトを作成
# 2. 設定ファイルを編集
# 3. プロット生成
# 4. エピソード生成
# 5. Web ブラウザで閲覧
```

## サポート

問題が発生した場合は、以下を確認してください：

1. このセットアップガイドの手順を再度確認
2. [Issues](https://github.com/your-repo/issues) でよくある問題を検索
3. 新しい Issue を作成する際は、以下の情報を含めてください：
   - macOS のバージョン
   - Python のバージョン
   - エラーメッセージの全文
   - 実行したコマンド

---

**注意**: このガイドは MacBook Air M1 を対象としていますが、他の Apple Silicon Mac でも同様に動作します。Intel Mac の場合は、Homebrew のパスが `/usr/local/bin/brew` になる点が異なります。
