# python deepresearch-BraveSearch.py --iterations 3 --query "調査したいトピック"

from openai import AzureOpenAI
import os
import requests
from PIL import Image
import json
from dotenv import load_dotenv
import urllib.parse
import argparse
import re
import sys
import datetime
import time
import concurrent.futures
from bs4 import BeautifulSoup

# 環境変数の読み込み
load_dotenv() 

# --- 設定 ---
MODEL_NAME = "o1-mini"  # 使用するモデル名 ( "gpt-4o", "gpt-4o-mini", "o1-mini" )
MAX_TOKENS = 65536     # モデルの最大トークン数 (gpt-4o: 4096, gpt-4o-mini: 16384, o1-mini: 65536)
                        # トークン数が制限に近づいたら内容を削減
SCRAPE_PAGES = True    # ウェブページのスクレイピングを有効にするかどうか
MAX_SCRAPE_PAGES = 3   # 各検索で何ページまでスクレイピングするか (処理速度とトークン制限のバランス)
MAX_SCRAPE_LENGTH = 3000  # スクレイピングするコンテンツの最大長さ

# -------------

class BraveWebSearch:
    """Brave Web Search APIのクライアントクラス"""
    
    def __init__(self, api_key, brave_endpoint):
        self.api_key = api_key
        self.brave_endpoint = brave_endpoint
        
    def search(self, query, count=5):
        """
        Brave Search APIを使用して検索を実行する
        
        Args:
            query: 検索クエリ
            count: 取得する結果の数
            
        Returns:
            dict: 検索結果
        """
        headers = {
            "Accept": "application/json",
            "X-Loc-Country": "JP",
            "X-Subscription-Token": self.api_key,
            "Accept-Encoding": "gzip",
            "Accept-Language": "ja-JP,ja;q=0.9",
        }
        
        params = {
            "q": query,
            "search_lang": "jp",
            "country": "jp",
            "count": str(count)
        }
        
        try:
            response = requests.get(self.brave_endpoint, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP検索エラー: {e}")
            return None
        except requests.exceptions.ConnectionError:
            print(f"接続エラー: Brave Search APIに接続できません")
            return None
        except Exception as e:
            print(f"検索エラー: {e}")
            return None

# AzureOpenAIのクライアント作成
client = AzureOpenAI(
    api_version="2024-02-01",  
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

# Brave Web Searchのクライアント作成
brave_client = BraveWebSearch(
    api_key = os.getenv("BRAVE_API_KEY"),
    brave_endpoint = os.getenv("BRAVE_ENDPOINT")
)

def scrape_webpage(url):
    """
    指定されたURLのウェブページをスクレイピングする
    
    Args:
        url: スクレイピングするページのURL
        
    Returns:
        str: 抽出されたテキストコンテンツ
    """
    try:
        # ユーザーエージェントを設定して、ブロックされないようにする
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # HTMLを解析
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 不要なタグを削除
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
            tag.decompose()
        
        # テキストを抽出して整形
        text = soup.get_text(separator='\n')
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = '\n'.join(lines)
        
        # 長いテキストを制限
        if len(text) > MAX_SCRAPE_LENGTH:
            text = text[:MAX_SCRAPE_LENGTH] + "...(省略)"
        
        return text
    except requests.exceptions.Timeout:
        return f"スクレイピングがタイムアウトしました: {url}"
    except requests.exceptions.HTTPError as e:
        return f"HTTPエラー発生: {e} - URL: {url}"
    except requests.exceptions.ConnectionError:
        return f"接続エラー: {url} に接続できません"
    except Exception as e:
        return f"スクレイピングエラー: {str(e)} - URL: {url}"

def parallel_scrape_webpages(urls, titles):
    """
    複数のウェブページを並行してスクレイピングする
    
    Args:
        urls: スクレイピングするURLのリスト
        titles: 各URLのタイトルのリスト
        
    Returns:
        list: スクレイピング結果のリスト
    """
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(scrape_webpage, url): (url, title) 
                         for url, title in zip(urls, titles)}
        
        for future in concurrent.futures.as_completed(future_to_url):
            url, title = future_to_url[future]
            try:
                content = future.result()
                results.append({
                    "url": url,
                    "title": title,
                    "content": content
                })
            except Exception as e:
                print(f"ページ {url} の処理中にエラー: {e}")
    
    return results

def extract_next_search_topic(llm_output):
    """
    LLMの出力からnextSearchTopicの値を抽出する関数
    
    Args:
        llm_output: LLMから返されたテキスト出力
        
    Returns:
        str or None: 次の検索トピック
    """
    try:
        # JSONブロックを抽出する正規表現
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', llm_output)
        if json_match:
            json_str = json_match.group(1)
        else:
            # JSONブロックが見つからない場合は、全体をJSONとして解析を試みる
            json_str = llm_output
        
        # 不要な文字を取り除く
        json_str = json_str.strip()
        
        # JSON形式に変換
        data = json.loads(json_str)
        
        # nextSearchTopicの値を取り出す
        return data.get('nextSearchTopic')
    
    except Exception as e:
        print(f"nextSearchTopic抽出エラー: {e}")
        return None

def extract_should_continue(llm_output):
    """
    LLMの出力からshouldContinueの値を抽出する関数
    
    Args:
        llm_output: LLMから返されたテキスト出力
        
    Returns:
        bool: 検索を続けるかどうか
    """
    try:
        # JSONブロックを抽出する正規表現
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', llm_output)
        if json_match:
            json_str = json_match.group(1)
        else:
            # JSONブロックが見つからない場合は、全体をJSONとして解析を試みる
            json_str = llm_output
        
        # 不要な文字を取り除く
        json_str = json_str.strip()
        
        # JSON形式に変換
        data = json.loads(json_str)
        
        # shouldContinueの値を取り出す（デフォルトはTrue）
        should_continue = data.get('shouldContinue', True)
        
        # 文字列の場合はブール値に変換
        if isinstance(should_continue, str):
            should_continue = should_continue.lower() in ['true', 'yes', '1']
        
        return should_continue
    
    except Exception as e:
        print(f"shouldContinue抽出エラー: {e}")
        return True

def ensure_diverse_results(new_results, previous_urls):
    """
    新しい検索結果から、以前に取得したURLと重複しない結果だけを返す
    
    Args:
        new_results: 新しい検索結果
        previous_urls: 以前に取得したURLのセット
        
    Returns:
        tuple: (多様化された結果のリスト, 更新されたURLのセット)
    """
    if not new_results or 'web' not in new_results or 'results' not in new_results['web']:
        return [], previous_urls
    
    diverse_results = []
    
    for result in new_results['web']['results']:
        url = result.get('url')
        if url and url not in previous_urls:
            diverse_results.append(result)
            previous_urls.add(url)
    
    return diverse_results, previous_urls

def format_search_results(results, previous_urls=None):
    """
    検索結果をLLMに渡す形式にフォーマットする
    
    Args:
        results: Brave Search APIからの検索結果
        previous_urls: 以前に取得したURLのセット
        
    Returns:
        tuple: (フォーマットされた検索結果のテキスト, スクレイピングデータのリスト, 更新されたURLのセット)
    """
    if previous_urls is None:
        previous_urls = set()
    
    if not results or not results.get('web', {}).get('results'):
        return "検索結果が見つかりませんでした。", [], previous_urls
    
    # 多様化された結果を取得
    diverse_results, previous_urls = ensure_diverse_results(results, previous_urls)
    
    if not diverse_results:
        return "新しい検索結果が見つかりませんでした。", [], previous_urls
    
    formatted_results = []
    urls_to_scrape = []
    titles_to_scrape = []
    
    for i, result in enumerate(diverse_results, 1):
        title = result.get('title', 'タイトルなし')
        description = result.get('description', '説明なし')
        url = result.get('url', 'URLなし')
        
        formatted_result = f"【{i}】\nタイトル: {title}\n内容: {description}\nURL: {url}\n"
        formatted_results.append(formatted_result)
        
        # スクレイピング対象のURLとタイトルを収集
        if SCRAPE_PAGES and i <= MAX_SCRAPE_PAGES:
            urls_to_scrape.append(url)
            titles_to_scrape.append(title)
    
    # 並行してスクレイピング
    scraped_contents = []
    if urls_to_scrape:
        print(f"  {len(urls_to_scrape)}ページを並行スクレイピング中...")
        scraped_contents = parallel_scrape_webpages(urls_to_scrape, titles_to_scrape)
    
    return "\n".join(formatted_results), scraped_contents, previous_urls

def clean_report(report_text):
    """
    レポートのテキストを整形して重複を削除する関数
    
    Args:
        report_text: 生成されたレポートのテキスト
        
    Returns:
        str: 整形されたレポートのテキスト
    """
    # 連続する重複行を削除
    lines = report_text.split('\n')
    clean_lines = []
    prev_line = None
    
    for line in lines:
        if line != prev_line:
            clean_lines.append(line)
            prev_line = line
    
    # 重複した見出しを修正
    report_text = '\n'.join(clean_lines)
    report_text = re.sub(r'(### [^#\n]+)\n\1', r'\1', report_text)
    
    # 参考文献セクションが複数ある場合は最初のものだけ残す
    ref_sections = re.finditer(r'(### 参考文献.*?)(?=###|\Z)', report_text, re.DOTALL)
    refs = list(ref_sections)
    
    if len(refs) > 1:
        # 最初の参考文献セクションだけを保持
        first_ref = refs[0].group()
        
        # 参考文献の各項目を抽出
        ref_items = re.findall(r'(\d+\.\s+\[.*?\].*?)(?=\d+\.\s+\[|\Z)', first_ref, re.DOTALL)
        unique_refs = []
        seen_urls = set()
        
        # URLが重複しない参考文献項目だけを保持
        for item in ref_items:
            url_match = re.search(r'\]\((https?://[^\)]+)\)', item)
            if url_match:
                url = url_match.group(1)
                if url not in seen_urls:
                    unique_refs.append(item)
                    seen_urls.add(url)
            else:
                unique_refs.append(item)
        
        # 整形された参考文献セクション
        clean_ref_section = "### 参考文献\n" + ''.join(unique_refs)
        
        # レポートの他の部分と組み合わせる
        parts = report_text.split(refs[0].group(), 1)
        report_text = parts[0] + clean_ref_section
        
        # 最後のセクションがあれば追加
        if len(parts) > 1 and "### " in parts[1]:
            last_section = re.search(r'###.*', parts[1], re.DOTALL)
            if last_section:
                report_text += "\n\n" + last_section.group()
    
    return report_text

def manage_token_usage(all_findings_text, detailed_content, max_tokens):
    """
    トークン数を管理し、必要に応じてコンテンツを削減
    
    Args:
        all_findings_text: 検索結果のテキスト
        detailed_content: スクレイピングしたコンテンツ
        max_tokens: 最大トークン数
        
    Returns:
        tuple: (調整された検索結果のテキスト, 調整されたスクレイピングコンテンツ)
    """
    # 簡易的なトークン数推定（英語で約4文字＝1トークン、日本語はより多い）
    estimated_tokens = len(all_findings_text) / 4 + len(detailed_content) / 4
    
    # トークン数が制限に近づいたら内容を削減
    if estimated_tokens > max_tokens * 0.7:  # 70%以上で削減
        # スクレイプしたコンテンツを短くする
        detailed_content_parts = detailed_content.split("---\n\n")
        shortened_parts = []
        
        max_length_per_part = 1000  # 各部分の最大長を1000文字に制限
        for part in detailed_content_parts:
            if part:
                shortened = part[:max_length_per_part] + "...(省略)"
                shortened_parts.append(shortened)
        
        detailed_content = "---\n\n".join(shortened_parts)
        
        # それでも長すぎる場合はさらに削減
        if (len(all_findings_text) / 4 + len(detailed_content) / 4) > max_tokens * 0.7:
            # 検索結果を要約版に
            findings_parts = all_findings_text.split("### 検索トピック")
            shortened_findings = [findings_parts[0]]  # 最初の部分は保持
            
            # 各検索トピックの最初の結果だけを保持
            for i in range(1, len(findings_parts)):
                topic_part = findings_parts[i]
                first_result = re.split(r'【2】', topic_part, 1)[0]
                shortened_findings.append(first_result + "...(他の結果は省略)")
            
            all_findings_text = "### 検索トピック".join(shortened_findings)
    
    return all_findings_text, detailed_content



def main():
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description=f'DeepResearch: {MODEL_NAME}モデルとBrave Search APIを使用した深い調査') # 説明を動的に
    parser.add_argument('--iterations', type=int, default=3, help='検索の最大繰り返し回数')
    parser.add_argument('--query', type=str, required=True, help='最初の検索クエリ')
    parser.add_argument('--scrape', action='store_true', help='ウェブページのスクレイピングを有効にする')
    args = parser.parse_args()
    
    max_iterations = args.iterations
    initial_query = args.query
    
    # コマンドラインからスクレイピング設定を上書き
    global SCRAPE_PAGES
    if args.scrape:
        SCRAPE_PAGES = True
    
    # 調査情報の初期化
    current_query = initial_query
    iterations_done = 0
    all_findings = []
    scraped_data = []
    searched_topics = [current_query]
    previous_urls = set()  # 既に処理したURLを追跡
    
    print(f"調査トピック: {initial_query}")
    print(f"最大繰り返し回数: {max_iterations}")
    print(f"使用モデル: {MODEL_NAME}")
    print(f"ウェブスクレイピング: {'有効' if SCRAPE_PAGES else '無効'}")
    
    # 調査のメインループ
    while iterations_done < max_iterations:
        iterations_done += 1
        print(f"\n--- 調査ラウンド {iterations_done}/{max_iterations} ---")
        print(f"現在の検索クエリ: {current_query}")
        
        # Brave Search APIで検索実行
        search_results = brave_client.search(current_query)
        if not search_results:
            print("検索結果が取得できませんでした。")
            break
        
        # 検索結果のフォーマットとスクレイピング
        formatted_results, current_scraped_data, previous_urls = format_search_results(search_results, previous_urls)
        all_findings.append({"query": current_query, "results": formatted_results})
        scraped_data.extend(current_scraped_data)
        
        print(f"検索結果を取得しました（{len(search_results.get('web', {}).get('results', []))}件）")
        if SCRAPE_PAGES:
            print(f"スクレイピングしたページ数: {len(current_scraped_data)}件")
        
        # 全ての検索結果とトピックをまとめる
        all_results_text = ""
        for i, finding in enumerate(all_findings, 1):
            all_results_text += f"### 検索トピック {i}: {finding['query']}\n"
            all_results_text += finding['results'] + "\n\n"
        
        # プロンプト内のプレースホルダーを置換
        research_prompt = """You are a research agent investigating the following topic.
What have you found? What questions remain unanswered? What specific aspects should be investigated next?

## User's Query
{{#sys.query#}}

## Current Findings
{{#conversation.findings#}}

## Searched Topics
{{#conversation.topics#}}

## Output
- Do not output topics that are exactly the same as already searched topics.
- If further information search is needed, set nextSearchTopic.
- If sufficient information has been obtained, set shouldContinue to false.
- Please output in json format

```json
nextSearchTopic: str | None
shouldContinue: bool 
```"""
        
        # プレースホルダーを実際の値に置換
        research_prompt = research_prompt.replace("{{#sys.query#}}", initial_query)
        research_prompt = research_prompt.replace("{{#conversation.findings#}}", all_results_text)
        research_prompt = research_prompt.replace("{{#conversation.topics#}}", ", ".join(searched_topics))
        
        # モデルに分析を依頼
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": research_prompt}],
            max_completion_tokens = MAX_TOKENS
        )
        
        # 分析結果を受け取り
        analysis_result = response.choices[0].message.content
        
        # 次の検索トピックを取得
        next_topic = extract_next_search_topic(analysis_result)
        should_continue = extract_should_continue(analysis_result)
        
        # 次の検索トピックが取得できなかった場合はデフォルトトピックを使用
        if not next_topic:
            next_topic = f"{initial_query} 追加情報"
            print(f"次の検索トピックが見つからなかったため、デフォルトトピック「{next_topic}」を使用します。")
        
        # 次の検索トピックを設定
        current_query = next_topic
        searched_topics.append(current_query)
    
    print(f"調査が完了しました（{iterations_done}回の検索を実行）。")
    
    # 全ての検索結果をまとめる
    all_findings_text = ""
    for i, finding in enumerate(all_findings, 1):
        all_findings_text += f"### 検索トピック {i}: {finding['query']}\n"
        all_findings_text += finding['results'] + "\n\n"
    
    # スクレイピングしたデータを組み込んだコンテンツを作成
    detailed_content = ""
    if scraped_data:
        for i, page_data in enumerate(scraped_data, 1):
            detailed_content += f"\n## スクレイピングしたコンテンツ {i}: {page_data['title']}\n"
            detailed_content += f"URL: {page_data['url']}\n\n"
            detailed_content += f"{page_data['content']}\n\n"
            detailed_content += "---\n\n"
    
    # トークン管理
    all_findings_text, detailed_content = manage_token_usage(all_findings_text, detailed_content, MAX_TOKENS)
    
    # 最終レポート用プロンプト
    final_prompt = """Based on the investigation results, create a comprehensive analysis of the topic.
Provide important insights, conclusions, and remaining uncertainties. Cite sources where appropriate. This analysis should be very comprehensive and detailed. It is expected to be a long text.

## Topic
{{#sys.query#}}

## Search Results
{{#conversation.findings#}}

## Detailed Page Contents
{{#detailed.content#}}

日本語で答えてください。レポートは明確に構成し、重複した内容や参考文献の繰り返しを避けてください。
ウェブページのコンテンツを分析に十分に活用してください。情報源を適切に引用してください。
"""
    
    # プレースホルダーを実際の値に置換
    final_prompt = final_prompt.replace("{{#sys.query#}}", initial_query)
    final_prompt = final_prompt.replace("{{#conversation.findings#}}", all_findings_text)
    final_prompt = final_prompt.replace("{{#detailed.content#}}", detailed_content)
    
    final_response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": final_prompt}],
        max_completion_tokens = MAX_TOKENS
    )
    
    # レポートを受け取り、整形する
    final_report = final_response.choices[0].message.content
    final_report = clean_report(final_report)
    
    # レポートの先頭にメタデータを追加
    timestamp = datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M")
    final_report = f"""# {initial_query} - 調査レポート
- 調査日時: {timestamp}
- 検索回数: {iterations_done}
- 使用モデル: {MODEL_NAME}

{final_report}
"""
    
    # 最終レポートの表示
    print("\n===== 最終調査レポート =====\n")
    print(final_report)
    
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nユーザーにより処理が中断されました。")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)