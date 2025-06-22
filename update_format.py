#!/usr/bin/env python3
"""
既存ファイルを新しいフォーマットに変換
"""

from file_manager import FileManager
from pathlib import Path

def update_existing_episode():
    """既存のエピソードファイルを新しいフォーマットに更新"""
    fm = FileManager()
    
    # 既存のエピソードファイルを読み込み
    episode_file = Path("books/昭和転生/stories/中学生編_01.md")
    
    if episode_file.exists():
        # 既存の内容を読み込み
        existing_content = episode_file.read_text(encoding='utf-8')
        
        # YAMLフロントマターがすでに存在するかチェック
        if existing_content.startswith('---'):
            print("ファイルにはすでにYAMLフロントマターが含まれています")
            return
        
        # 章タイトルを追加（存在しない場合）
        if not existing_content.strip().startswith('# '):
            existing_content = "# 第1話　目覚め\n\n" + existing_content
        
        # 新しいフォーマットで保存
        fm.save_episode("昭和転生", "中学生編", 1, existing_content)
        print("ファイルが新しいフォーマットに更新されました")
    else:
        print("エピソードファイルが見つかりません")

if __name__ == "__main__":
    update_existing_episode()
