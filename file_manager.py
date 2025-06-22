"""
ファイル操作ユーティリティ
"""
import os
import json
from pathlib import Path
from typing import Dict, Any
from rich.console import Console

class FileManager:
    """小説プロジェクトのファイル管理"""
    
    def __init__(self, base_dir: str = "books"):
        """初期化"""
        self.base_dir = Path(base_dir)
        self.console = Console()
    
    def get_novel_dir(self, title: str) -> Path:
        """小説ディレクトリのパスを取得"""
        return self.base_dir / title
    
    def create_novel_structure(self, title: str) -> None:
        """小説ディレクトリ構造を作成"""
        novel_dir = self.get_novel_dir(title)
        # books ディレクトリも含めて作成
        novel_dir.mkdir(parents=True, exist_ok=True)
        
        # stories ディレクトリを作成
        stories_dir = novel_dir / "stories"
        stories_dir.mkdir(exist_ok=True)
        
        # setting.md のテンプレートを作成（存在しない場合のみ）
        setting_file = novel_dir / "setting.md"
        if not setting_file.exists():
            from prompt_templates import SETTING_TEMPLATE
            setting_file.write_text(SETTING_TEMPLATE, encoding='utf-8')
            print(f"Created template setting file: {setting_file}")
    
    def read_setting(self, title: str) -> str:
        """設定ファイルを読み込み"""
        setting_file = self.get_novel_dir(title) / "setting.md"
        if not setting_file.exists():
            raise FileNotFoundError(f"Setting file not found: {setting_file}")
        
        return setting_file.read_text(encoding='utf-8')
    
    def read_character(self, title: str) -> str:
        """キャラクターファイルを読み込み"""
        character_file = self.get_novel_dir(title) / "character.md"
        if not character_file.exists():
            # character.md が存在しない場合は空文字を返す
            return ""
        
        return character_file.read_text(encoding='utf-8')
    
    def read_all_settings(self, title: str) -> str:
        """設定ファイルとキャラクターファイルを統合して読み込み"""
        setting_content = self.read_setting(title)
        character_content = self.read_character(title)
        
        if character_content:
            # キャラクターファイルが存在する場合は統合
            combined_content = f"{setting_content}\n\n---\n\n{character_content}"
        else:
            combined_content = setting_content
        
        return combined_content
    
    def save_plot(self, title: str, plot_data: Dict[str, Any]) -> None:
        """プロットをJSONファイルに保存"""
        plot_file = self.get_novel_dir(title) / "plot.json"
        with open(plot_file, 'w', encoding='utf-8') as f:
            json.dump(plot_data, f, ensure_ascii=False, indent=2)
        print(f"Plot saved to: {plot_file}")
    
    def read_plot(self, title: str) -> Dict[str, Any]:
        """プロットファイルを読み込み"""
        plot_file = self.get_novel_dir(title) / "plot.json"
        if not plot_file.exists():
            raise FileNotFoundError(f"Plot file not found: {plot_file}")
        
        with open(plot_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_episode_plot(self, title: str, arc: str, episode: int) -> str:
        """指定話のプロットを取得"""
        plot_data = self.read_plot(title)
        
        if arc not in plot_data:
            raise ValueError(f"Arc '{arc}' not found in plot")
        
        episode_str = str(episode)
        if episode_str not in plot_data[arc]:
            raise ValueError(f"Episode {episode} not found in arc '{arc}'")
        
        return plot_data[arc][episode_str]
    
    def save_episode(self, title: str, arc: str, episode: int, content: str) -> None:
        """エピソードをMarkdownファイルに保存"""
        stories_dir = self.get_novel_dir(title) / "stories"
        episode_file = stories_dir / f"{arc}_{episode:02d}.md"
        
        episode_file.write_text(content, encoding='utf-8')
        print(f"Episode saved to: {episode_file}")
    
    def episode_exists(self, title: str, arc: str, episode: int) -> bool:
        """エピソードファイルが存在するかチェック"""
        stories_dir = self.get_novel_dir(title) / "stories"
        episode_file = stories_dir / f"{arc}_{episode:02d}.md"
        return episode_file.exists()
