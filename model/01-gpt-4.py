# gpt-4oの場合 Max_token 4096 以下
# o1-mini, gpt-4o, gpt-4o-mini

from openai import AzureOpenAI
import os
import requests
from PIL import Image
import json
from dotenv import load_dotenv

# 環境変数の読み込み　.envが使える
load_dotenv() 


client = AzureOpenAI(
    api_version="2024-02-01",  
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

response = client.chat.completions.create(
    model="gpt-4o", # replace with the model deployment name of your o1-preview, or o1-mini model
    messages=[
        {
            "role": "user", 
            "content": "o1 miniモデルについて教えて"},
    ],
    max_completion_tokens = 4096

)

# contentのみを表示
content = response.choices[0].message.content
print(content)