"""
YumeChain: Novel generation app using LLM

LLM（Gemini）を使って設定から小説を生成するアプリケーション
"""
from pathlib import Path
import importlib.resources

__version__ = "0.1.0"
__author__ = "Your Name"
__description__ = "Novel generation app using LLM (Gemini)"

def get_package_path():
    """パッケージのパスを取得"""
    return Path(__file__).parent

def get_theme_path():
    """テーマディレクトリのパスを取得"""
    return get_package_path() / "theme"

def get_static_path():
    """staticディレクトリのパスを取得"""
    return get_package_path() / "static"
