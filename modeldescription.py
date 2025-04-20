import os
import requests
from bs4 import BeautifulSoup
import concurrent.futures
from openai import AzureOpenAI
from dotenv import load_dotenv
import base64

# .env ファイルから環境変数を読み込む
load_dotenv()

# スクレイピング設定
MAX_SCRAPE_LENGTH = 100000  # スクレイピングするコンテンツの最大長さ（100万トークン相当）

def scrape_webpage(url):
    """
    指定されたURLのウェブページをスクレイピングする
    
    Args:
        url: スクレイピングするページのURL
        
    Returns:
        dict: 抽出されたタイトル、メタ説明、テキストコンテンツを含む辞書
    """
    try:
        # ユーザーエージェントを設定して、ブロックされないようにする
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # HTMLを解析
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # タイトルの取得
        title = soup.title.string if soup.title else "タイトルなし"
        
        # メタ説明を取得
        meta_description = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and "content" in meta_tag.attrs:
            meta_description = meta_tag["content"]
        
        # h1, h2, h3タグの内容を取得（見出し情報は重要）
        headings = []
        for h in soup.find_all(['h1', 'h2', 'h3']):
            text = h.get_text().strip()
            if text:
                headings.append(f"{h.name}: {text}")
        
        # 不要なタグを削除
        for tag in soup(["script", "style", "nav", "footer", "aside", "iframe", "noscript"]):
            tag.decompose()
        
        # 本文のテキストを取得（pタグとリスト要素）
        main_content = []
        for element in soup.find_all(['p', 'li', 'div.content', 'div.description']):
            text = element.get_text().strip()
            if text and len(text) > 20:  # 短すぎるテキストは除外
                main_content.append(text)
        
        # キーワードの強調されたテキストを取得（strong, b, emタグなど）
        emphasized = []
        for em in soup.find_all(['strong', 'b', 'em']):
            text = em.get_text().strip()
            if text and len(text) > 3:  # 短すぎる強調は除外
                emphasized.append(text)
        
        # スクレイピングしたデータを結合
        all_text = "\n\n".join([
            f"タイトル: {title}",
            f"メタ説明: {meta_description}",
            "見出し:\n" + "\n".join(headings),
            "主要なコンテンツ:\n" + "\n\n".join(main_content),
            "強調されたテキスト:\n" + "\n".join(emphasized)
        ])
        
        # 長いテキストを制限
        if len(all_text) > MAX_SCRAPE_LENGTH:
            all_text = all_text[:MAX_SCRAPE_LENGTH] + "...(省略)"
        
        return {
            "title": title,
            "meta_description": meta_description,
            "content": all_text
        }
        
    except requests.exceptions.Timeout:
        return {"error": f"スクレイピングがタイムアウトしました: {url}"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTPエラー発生: {e} - URL: {url}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"接続エラー: {url} に接続できません"}
    except Exception as e:
        return {"error": f"スクレイピングエラー: {str(e)} - URL: {url}"}

def parallel_scrape_webpages(urls):
    """
    複数のウェブページを並行してスクレイピングする
    
    Args:
        urls: スクレイピングするURLのリスト
        
    Returns:
        list: スクレイピング結果のリスト
    """
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(scrape_webpage, url): url for url in urls}
        
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                content = future.result()
                results.append({
                    "url": url,
                    "data": content
                })
                print(f"スクレイピング完了: {url}")
            except Exception as e:
                print(f"ページ {url} の処理中にエラー: {e}")
    
    return results

# def extract_llm_from_image():
#     # クライアントの作成
#     client = AzureOpenAI(
#         api_version="2024-02-01",
#         api_key=os.getenv("AZURE_OPENAI_API_KEY"),
#         azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
#     )

#     # 画像ファイルのパスを指定
#     file_path = 'images/models.png'

#     # ファイルをバイナリモードで開いて読み込む
#     with open(file_path, 'rb') as image_file:
#         encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

#     # data URIスキームに従ってフォーマットする
#     image_url = f"data:image/png;base64,{encoded_string}"

#     # GPT-4-1でリクエストを送信
#     response = client.chat.completions.create(
#         model="gpt-4.1",
#         messages=[
#             {
#                 "role": "user",
#                 "content": [
#                     {
#                         "type": "text",
#                         "text": "この画像にあるLLMモデルをすべて抽出し、改行区切りのリストで返してください。「・」記号を付けないでください。"
#                     },
#                     {
#                         "type": "image_url",
#                         "image_url": {
#                             "url": image_url
#                         }
#                     }
#                 ]
#             }
#         ],
#         max_tokens=16384
#     )

#     # 応答内容を取得して表示
#     content = response.choices[0].message.content
#     print("画像から抽出されたLLMモデル一覧:")
#     print(content)
    
#     # 改行で分割してリストに変換
#     models = [model.strip() for model in content.split('\n') if model.strip()]
    
#     return models

def generate_model_descriptions(scraped_data):
    """
    スクレイピングしたコンテンツを基にAzure OpenAIを使って
    モデル説明文を生成します
    
    Args:
        scraped_data: スクレイピングされたデータのリスト
        
    Returns:
        dict: モデル名をキー、説明文を値とする辞書
    """
    try:
        # AzureOpenAIクライアントの初期化
        client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-01"
        )
        
        # スクレイピングしたデータを整形
        formatted_content = ""
        for item in scraped_data:
            url = item["url"]
            data = item["data"]
            
            if "error" in data:
                formatted_content += f"\n## URL: {url}\n{data['error']}\n\n"
            else:
                formatted_content += f"\n## URL: {url}\n{data['content']}\n\n"
        
        # プロンプトを設計して正確な長さの説明文を生成
        prompt = f"""あなたはAI言語モデルの特徴を的確に表現する専門家です。
スクレイピングしたWebサイトの内容から、各モデルの最も際立った特徴や主な利用シーンを分析し、
各モデルを正確に35文字の簡潔な説明文を日本語で作成してください。

要件:
1. 説明文は必ず35文字になるようにしてください
2. 各モデルの最も重要な特徴や強みを端的に表現してください
3. 具体的な使用例や得意分野がわかるようにしてください
4. 専門的すぎる表現は避け、一般ユーザーにもわかりやすい表現を使ってください
5. 出力形式は以下のJSONフォーマットで返してください:
{{
  "モデル名1": "説明文1",
  "モデル名2": "説明文2",
  ...
}}

指定モデル:
GPT-4.1  
GPT-4.1 mini  
GPT-4.1 nano  
GPT-4o  
GPT-4o mini  
o1 mini
Claude 3.7 Sonnet
Claude 3.5 Sonnet（v2）
Claude 3.5 Sonnet（v1）
Claude 3.5 Haiku
Claude 3 Haiku
Amazon Nova Pro
Amazon Nova Lite
Amazon Nova Micro
Llama 3.3 70B
Llama 3.2 90B Instruct
Llama 3.1 405B Instruct

以下はスクレイピングした内容です：
{formatted_content}"""

        # まず徹底的に分析させる
        analysis_prompt = f"""各モデルの特徴を徹底的に分析してください。
以下の項目について各モデルの情報を整理してください:
1. 主な用途や得意分野
2. 特徴的な機能
3. コンテキスト長
4. 特殊な能力（コード生成、推論など）
5. 速度や効率性
6. 独自の強み

スクレイピングされた情報から事実に基づいて分析してください。
情報が不足している場合は「情報不足」と明記してください。

分析対象モデル:
GPT-4.1  
GPT-4.1 mini  
GPT-4.1 nano  
GPT-4o  
GPT-4o mini  
o1 mini
Claude 3.7 Sonnet
Claude 3.5 Sonnet（v2）
Claude 3.5 Sonnet（v1）
Claude 3.5 Haiku
Claude 3 Haiku
Amazon Nova Pro
Amazon Nova Lite
Amazon Nova Micro
Llama 3.3 70B
Llama 3.2 90B Instruct
Llama 3.1 405B Instruct

以下はスクレイピングした内容です:
{formatted_content}"""

        # 分析ステップ
        analysis_response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "あなたはAI言語モデルの特徴を詳細に分析する専門家です。"},
                {"role": "user", "content": analysis_prompt}
            ],
            max_tokens=32768
        )
        
        analysis_result = analysis_response.choices[0].message.content.strip()
        
        # 分析結果を元に説明文を生成
        final_prompt = f"""あなたはAI言語モデルの特徴を簡潔に伝えるエキスパートです。
以下の分析結果を基に、各モデルを35文字の簡潔な説明文にまとめてください。

要件:
1. 説明文は必ず35文字になるようにしてください
2. 各モデルの最も重要な特徴や強みを端的に表現してください
3. 具体的な使用例や得意分野がわかるようにしてください
4. 専門的すぎる表現は避け、一般ユーザーにもわかりやすい表現を使ってください
5. 独自性を持たせ、各モデルの違いが明確にわかるようにしてください
6. 出力形式は以下のJSONフォーマットで返してください:
{{
  "モデル名1": "説明文1",
  "モデル名2": "説明文2",
  ...
}}

モデル分析結果:
{analysis_result}"""

        # 最終生成
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "モデルの特徴を正確かつ簡潔に表現するエキスパートです。JSONフォーマットで回答します。"},
                {"role": "user", "content": final_prompt}
            ],
            max_tokens=32768,
            response_format={"type": "json_object"}
        )
        
        # 生成された説明文を取得して辞書に変換
        import json
        model_descriptions = json.loads(response.choices[0].message.content.strip())
        
        # 文字数の検証
        for model, description in model_descriptions.items():
            char_count = len(description)
            if char_count != 35:
                print(f"警告: {model}の説明文は{char_count}文字です（目標: 35文字）")
        
        return model_descriptions
    
    except Exception as e:
        print(f"説明文生成エラー: {str(e)}")
        return {}

def main():
    # # 画像からLLMモデルを抽出
    # extracted_models = extract_llm_from_image()
    
    # スクレイピングするURLのリスト
    urls = [
        "https://azure.microsoft.com/en-us/blog/announcing-the-gpt-4-1-model-series-for-azure-ai-foundry-developers/",
        "https://learn.microsoft.com/ja-jp/azure/ai-services/openai/concepts/models",
        "https://openai.com/index/gpt-4-1-technical-report/",
        "https://openai.com/api/gpt-4-turbo/",
        "https://docs.aws.amazon.com/ja_jp/nova/latest/userguide/what-is-nova.html",
        "https://aws.amazon.com/jp/bedrock/llama/",
        "https://openai.com/index/gpt-4-1/",
        "https://docs.anthropic.com/ja/docs/about-claude/models/all-models",
        "https://llama.meta.com/"
    ]
    
    print(f"指定された {len(urls)} 件のWebサイトをスクレイピングします...")
    scraped_data = parallel_scrape_webpages(urls)
    
    print("\nモデル説明文を生成中...")
    # 30文字の説明文を生成
    model_descriptions = generate_model_descriptions(scraped_data)
    
    print("\n===== 生成されたモデル説明文 =====")
    for model, description in model_descriptions.items():
        print(f"・{model}\n  {description}\n")
    print("================================")
    

if __name__ == "__main__":
    main()