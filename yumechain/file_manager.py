"""
ファイル操作ユーティリティ
"""
import os
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
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
            from .prompt_templates import SETTING_TEMPLATE
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
    
    def save_plot(self, title: str, plot_data: Dict[str, Any], merge: bool = False) -> None:
        """プロットをJSONファイルに保存"""
        plot_file = self.get_novel_dir(title) / "plot.json"
        
        if merge and plot_file.exists():
            # 既存のプロットとマージ
            try:
                existing_data = self.read_plot(title)
                existing_data.update(plot_data)
                plot_data = existing_data
            except Exception as e:
                print(f"Warning: Could not merge with existing plot: {e}")
        
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
    
    def generate_yaml_frontmatter(self, title: str, arc: str, episode: int, content: str) -> str:
        """YAMLフロントマターを生成"""
        # 設定ファイルから情報を読み取り
        try:
            setting_content = self.read_setting(title)
        except:
            setting_content = ""
        
        # プロットから情報を取得（存在する場合）
        try:
            plot_data = self.read_plot(title)
            episode_plot = plot_data.get(arc, {}).get(str(episode), "")
            # プロットの最初の行をdescriptionとして使用
            description = episode_plot.split('\n')[0][:100] + "..." if episode_plot else ""
        except:
            description = ""
        
        # 本文から章タイトルを抽出
        chapter_title = ""
        content_lines = content.strip().split('\n')
        for line in content_lines:
            if line.startswith('# '):
                chapter_title = line[2:].strip()
                break
        
        if not chapter_title:
            chapter_title = f"第{episode}話"
        
        # 現在の日付を取得
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # YAMLフロントマターを生成
        yaml_frontmatter = f"""---
title: "{chapter_title} {title}"
author: "Gemini"
date: "{current_date}"
lang: "ja"
description: "{description or f'AI生成小説。'}"
series: "{title}"
volume: 1
chapter: "{episode}"
---

"""
        return yaml_frontmatter

    def save_episode(self, title: str, arc: str, episode: int, content: str) -> None:
        """エピソードをPandoc対応Markdownファイルに保存"""
        stories_dir = self.get_novel_dir(title) / "stories"
        episode_file = stories_dir / f"{arc}_{episode:02d}.md"
        
        # YAMLフロントマターを追加
        yaml_frontmatter = self.generate_yaml_frontmatter(title, arc, episode, content)
        full_content = yaml_frontmatter + content
        
        episode_file.write_text(full_content, encoding='utf-8')
        print(f"Episode saved to: {episode_file}")
    
    def read_episode(self, title: str, arc: str, episode: int) -> str:
        """エピソードファイルの内容を読み込み"""
        stories_dir = self.get_novel_dir(title) / "stories"
        episode_file = stories_dir / f"{arc}_{episode:02d}.md"
        
        if not episode_file.exists():
            return ""
        
        content = episode_file.read_text(encoding='utf-8')
        
        # YAMLフロントマターを除去して本文のみを返す
        if content.startswith('---'):
            # YAMLフロントマターの終了位置を見つける
            lines = content.split('\n')
            end_marker = -1
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == '---':
                    end_marker = i
                    break
            
            if end_marker > 0:
                # フロントマター以降の内容を返す
                return '\n'.join(lines[end_marker + 1:]).strip()
        
        return content.strip()
    
    def get_previous_episode_content(self, title: str, arc: str, episode: int, plot_data: Dict[str, Any] = None) -> str:
        """前のエピソードの内容を取得（ファイル順序ベース）"""
        if plot_data is None:
            try:
                plot_data = self.read_plot(title)
            except FileNotFoundError:
                return ""
        
        # 全エピソードを（arc, episode）のタプルリストで取得
        all_episodes = []
        for arc_name, episodes in plot_data.items():
            for ep_num_str, plot in episodes.items():
                try:
                    ep_num = int(ep_num_str)
                    all_episodes.append((arc_name, ep_num))
                except ValueError:
                    continue
        
        # ファイル名順でソート（arc名でソート、その後episode番号でソート）
        all_episodes.sort(key=lambda x: (x[0], x[1]))
        
        # 現在のエピソードのインデックスを検索
        current_index = None
        for i, (arc_name, ep_num) in enumerate(all_episodes):
            if arc_name == arc and ep_num == episode:
                current_index = i
                break
        
        if current_index is None or current_index == 0:
            return ""  # 最初のエピソードまたは見つからない場合
        
        # 前のエピソードを取得
        prev_arc, prev_episode = all_episodes[current_index - 1]
        prev_content = self.read_episode(title, prev_arc, prev_episode)
        
        if prev_content:
            self.console.print(f"[dim]前のエピソード内容を取得: {prev_arc}_{prev_episode}[/dim]")
        else:
            self.console.print(f"[dim]前のエピソード内容: なし[/dim]")
        
        return prev_content

    def episode_exists(self, title: str, arc: str, episode: int) -> bool:
        """エピソードファイルが存在するかチェック"""
        stories_dir = self.get_novel_dir(title) / "stories"
        episode_file = stories_dir / f"{arc}_{episode:02d}.md"
        return episode_file.exists()
