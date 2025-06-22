"""
利用可能なGeminiモデルを一覧表示
"""
import os
import google.generativeai as genai
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    print("GOOGLE_API_KEY environment variable is required")
    exit(1)

genai.configure(api_key=api_key)

print("Available Gemini models:")
print("-" * 50)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"Model: {model.name}")
        print(f"  Display Name: {model.display_name}")
        print(f"  Description: {model.description}")
        print(f"  Supported methods: {model.supported_generation_methods}")
        print()
