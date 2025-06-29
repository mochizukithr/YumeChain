"""
はてなブログAPIクライアント

はてなブログAtomPub APIを使ってブログ記事の投稿・更新を行う
"""
import os
import base64
import hashlib
import hmac
import requests
import xmltodict
import html
import markdown
import re
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import quote


class HatenaBlogClient:
    """はてなブログAPIクライアント"""
    
    def __init__(self, username: str, api_key: str, blog_id: str):
        """
        初期化
        
        Args:
            username: はてなユーザー名
            api_key: はてなブログAPI キー
            blog_id: ブログID（xxxxx.hatenablog.comの形式）
        """
        self.username = username
        self.api_key = api_key
        self.blog_id = blog_id
        self.base_url = f"https://blog.hatena.ne.jp/{username}/{blog_id}/atom"
    
    def _markdown_to_html(self, content: str) -> str:
        """
        MarkdownをHTMLに変換し、段落内の改行をbrタグに変換
        
        Args:
            content: Markdown形式のコンテンツ
            
        Returns:
            HTML形式のコンテンツ
        """
        # 改行を正規化
        normalized_content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Markdownの拡張機能を有効にしてHTMLに変換
        md = markdown.Markdown(extensions=[
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
            'markdown.extensions.toc',
            'markdown.extensions.nl2br'  # 改行を<br>に変換
        ])
        
        html_content = md.convert(normalized_content)
        
        # 段落内の単純な改行を<br>タグに変換
        # ただし、すでに<br>が含まれている場合は重複を避ける
        def convert_newlines_in_paragraphs(match):
            paragraph_content = match.group(1)
            # 既にbrタグが含まれていない改行のみを変換
            paragraph_content = re.sub(r'(?<!>)\n(?!<)', '<br>\n', paragraph_content)
            return f'<p>{paragraph_content}</p>'
        
        # <p>タグ内の改行を<br>に変換（nl2brでカバーされない場合のフォールバック）
        html_content = re.sub(r'<p>(.*?)</p>', convert_newlines_in_paragraphs, html_content, flags=re.DOTALL)
        
        return html_content
    
    def _create_auth_header(self, method: str, uri: str, body: str = "") -> str:
        """
        WSSE認証ヘッダーを作成
        
        Args:
            method: HTTPメソッド
            uri: リクエストURI
            body: リクエストボディ
            
        Returns:
            WSSE認証ヘッダー文字列
        """
        # ノンスを生成
        nonce = base64.b64encode(os.urandom(24)).decode('ascii')
        
        # タイムスタンプを生成
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # パスワードダイジェストを作成
        digest_input = nonce + timestamp + self.api_key
        password_digest = base64.b64encode(
            hashlib.sha1(digest_input.encode('utf-8')).digest()
        ).decode('ascii')
        
        # WSSEヘッダーを構築
        wsse_header = (
            f'UsernameToken Username="{self.username}", '
            f'PasswordDigest="{password_digest}", '
            f'Nonce="{nonce}", '
            f'Created="{timestamp}"'
        )
        
        return wsse_header
    
    def _make_request(self, method: str, endpoint: str, data: Optional[str] = None) -> requests.Response:
        """
        APIリクエストを実行
        
        Args:
            method: HTTPメソッド
            endpoint: エンドポイント
            data: リクエストデータ
            
        Returns:
            レスポンス
        """
        url = f"{self.base_url}/{endpoint}"
        
        headers = {
            'Content-Type': 'application/xml',
            'X-WSSE': self._create_auth_header(method, url, data or "")
        }
        
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, data=data)
        elif method.upper() == 'PUT':
            response = requests.put(url, headers=headers, data=data)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        return response
    
    def get_blogs(self) -> Dict[str, Any]:
        """
        ブログ一覧を取得
        
        Returns:
            ブログ一覧データ
        """
        response = self._make_request('GET', 'entry')
        response.raise_for_status()
        
        return xmltodict.parse(response.text)
    
    def create_entry(self, title: str, content: str, categories: Optional[list] = None, 
                    draft: bool = False) -> Dict[str, Any]:
        """
        新しい記事を作成
        
        Args:
            title: 記事タイトル
            content: 記事内容（Markdown）
            categories: カテゴリリスト
            draft: 下書きフラグ
            
        Returns:
            作成された記事の情報
        """
        # MarkdownをHTMLに変換
        html_content = self._markdown_to_html(content)
        
        # タイトルとコンテンツをXMLエスケープ
        escaped_title = html.escape(title)
        escaped_content = html.escape(html_content)
        
        # カテゴリタグを構築
        category_tags = ""
        if categories:
            for category in categories:
                escaped_category = html.escape(category)
                category_tags += f'  <category term="{escaped_category}" />\n'
        
        # アトムエントリを構築（content typeをtext/htmlに変更）
        entry_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:app="http://www.w3.org/2007/app">
  <title>{escaped_title}</title>
  <author><name>{self.username}</name></author>
  <content type="text/html">{escaped_content}</content>
{category_tags}  <app:control>
    <app:draft>{"yes" if draft else "no"}</app:draft>
  </app:control>
</entry>'''
        
        response = self._make_request('POST', 'entry', entry_xml)
        response.raise_for_status()
        
        return xmltodict.parse(response.text)
    
    def update_entry(self, entry_id: str, title: str, content: str, 
                    categories: Optional[list] = None, draft: bool = False) -> Dict[str, Any]:
        """
        記事を更新
        
        Args:
            entry_id: 記事ID
            title: 記事タイトル
            content: 記事内容（Markdown）
            categories: カテゴリリスト
            draft: 下書きフラグ
            
        Returns:
            更新された記事の情報
        """
        # MarkdownをHTMLに変換
        html_content = self._markdown_to_html(content)
        
        # タイトルとコンテンツをXMLエスケープ
        escaped_title = html.escape(title)
        escaped_content = html.escape(html_content)
        
        # カテゴリタグを構築
        category_tags = ""
        if categories:
            for category in categories:
                escaped_category = html.escape(category)
                category_tags += f'  <category term="{escaped_category}" />\n'
        
        # アトムエントリを構築（content typeをtext/htmlに変更）
        entry_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:app="http://www.w3.org/2007/app">
  <title>{escaped_title}</title>
  <author><name>{self.username}</name></author>
  <content type="text/html">{escaped_content}</content>
{category_tags}  <app:control>
    <app:draft>{"yes" if draft else "no"}</app:draft>
  </app:control>
</entry>'''
        
        response = self._make_request('PUT', f'entry/{entry_id}', entry_xml)
        response.raise_for_status()
        
        return xmltodict.parse(response.text)
    
    def delete_entry(self, entry_id: str) -> bool:
        """
        記事を削除
        
        Args:
            entry_id: 記事ID
            
        Returns:
            削除成功フラグ
        """
        response = self._make_request('DELETE', f'entry/{entry_id}')
        
        return response.status_code == 200
    
    def get_entry(self, entry_id: str) -> Dict[str, Any]:
        """
        記事を取得
        
        Args:
            entry_id: 記事ID
            
        Returns:
            記事データ
        """
        response = self._make_request('GET', f'entry/{entry_id}')
        response.raise_for_status()
        
        return xmltodict.parse(response.text)
