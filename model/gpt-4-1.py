# GPT-4-1 モデルを使用した画像説明
# 画像に書かれたモデル

from openai import AzureOpenAI
import os
import base64
from dotenv import load_dotenv

# 環境変数の読み込み　.envが使える
load_dotenv()

# クライアントの作成
client = AzureOpenAI(
    api_version="2024-02-01",
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

# # 画像ファイルのパスを指定
# file_path = '../images/models.png'

# # ファイルをバイナリモードで開いて読み込む
# with open(file_path, 'rb') as image_file:
#     # ファイルの内容を読み込む
#     encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

# # data URIスキームに従ってフォーマットする
# image_url = f"data:image/png;base64,{encoded_string}"

# GPT-4-1でリクエストを送信
response = client.chat.completions.create(
    model="gpt-4.1", # GPT-4-1モデルのデプロイ名を指定
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "GPT 4.1の特異点を教えてください。"
                }
            ]
        }
    ],
    max_tokens=16384
)

# 応答内容を取得して表示
content = response.choices[0].message.content
print(content)