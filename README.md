## Azure OpenAI Serviceの各モデルをコマンドラインで実行するフォルダ
<img src="https://qiita-user-contents.imgix.net/https%3A%2F%2Fimg.shields.io%2Fbadge%2F-Python-F2C63C.svg%3Flogo%3Dpython%26style%3Dfor-the-badge?ixlib=rb-4.0.0&auto=format&gif-q=60&q=75&s=c17144ccc12f9c19e9dbba2eec5c7980">

## 主要技術

| 言語・フレームワーク | バージョン |
| ---------------- | ---------------- |
| Anaconda         | 24.11.3          |
| Python           | 3.11.11          |
| Brave Search API | 2023-01-01 （APIバージョン）|
 > max_tokens は、o1 シリーズ モデルでは機能しない
## ライブラリ
 > pip　であることに注意</br>
 > Dall E 3（画像生成）を使用する場合は、Imgageモジュールをインストールすること
 ```
    pip install AzureOpenAI,requests,Image,load_dotenv,BeautifulSoup
 ```
## 環境変数
| 変数名 | 役割 |
| ----- | ---- |
| AZURE_OPENAI_API_KEY | Azure Open AI ServiceのAPI Key|
| AZURE_OPENAI_ENDPOINT | Azure Open AI Serviceのエンドポイント |
| BRAVE_API_KEY| Brave Web Search のAPI Key|
| BRAVE_ENDPOINT| Brave Web Search のエンドポイント|
> Brave Web SearchのAPI Key ,エンドポイントを設定することで Deep Research が可能