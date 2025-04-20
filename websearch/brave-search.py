import requests
import os
from dotenv import load_dotenv
import urllib.parse

load_dotenv()

subscription_key = os.getenv("BRAVE_API_KEY")
search_url = os.getenv("BRAVE_ENDPOINT")
search_term = "今日の熊本の天気"

def main():
    print(f"DEBUG: BRAVE_API_KEY: {subscription_key[:5]}..." if subscription_key else "Not found")
    print(f"DEBUG: BRAVE_ENDPOINT: {search_url}")

    headers = {
        "Accept" : "application/json",
        "X-Loc-Country":"JP",
        "X-Subscription-Token": subscription_key,
        "Accept-Encoding": "gzip",
        "Accept-Language": "ja-JP,ja;q=0.9",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Cache-Control": "no-cache"
    }
    params = dict(q=search_term, search_lang="jp", country="jp", count="5")

    encoded_params = urllib.parse.urlencode(params)
    request_url = f"{search_url}?{encoded_params}"
    print(f"DEBUG: Request URL (Pre-send): {request_url}")
    print(f"DEBUG: Request Headers (Defined): {headers}")

    response = requests.get(search_url,headers=headers,params=params)

    print(f"\n--- Actual Request Sent by requests ---")
    print(f"DEBUG: Actual Request URL: {response.request.url}")
    print(f"DEBUG: Actual Request Headers: {response.request.headers}")

    print("\n--- API Response ---")
    print(f"Status Code: {response.status_code}")
    try:
        print(response.json())
    except requests.exceptions.JSONDecodeError:
        print("Response is not JSON")
        print(response.text)

if __name__ == '__main__':
    main()

# headers = {"X-Subscription-Token": subscription_key}
# params = {
#     "q": search_term, 
#     "textDecorations": True, 
#     "ui_lang": "ja-JP",
#     "textFormat": "HTML",
#     }
# response = requests.get(search_url, headers=headers, params=params)
# response.raise_for_status()
# search_results = response.json()

# print(search_results)