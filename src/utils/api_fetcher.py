import os
import json
import requests

def fetch_data_and_save(api_endpoint: str, file_path: str) -> None:
    """
    從指定的 API 端點抓取資料，並存到 file_path 對應的 JSON 檔案。
    """
    try:
        response = requests.get(api_endpoint)
        response.raise_for_status()
        data = response.json()
       
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"已成功從 {api_endpoint} 抓取資料，並寫入 {file_path}")
       
    except requests.RequestException as e:
        print(f"抓取過程發生錯誤：{e}")
