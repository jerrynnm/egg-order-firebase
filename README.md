# requirements.txt
streamlit
pyrebase4
streamlit-autorefresh
python-dateutil


# .gitignore
__pycache__/
*.pyc
credentials.json


# README.md
# 雞蛋糕點餐系統 (Firebase 版)

這是一套以 Streamlit 開發的行動版點餐系統，具備即時同步功能，後端採用 Firebase Realtime Database。

## 🔧 使用技術
- Streamlit
- Firebase (透過 pyrebase4)
- Python

## 📦 部署到 Streamlit Cloud
1. 將此 repo 上傳至 GitHub
2. 登入 [streamlit.io/cloud](https://streamlit.io/cloud)
3. 建立新 App，選擇你的 GitHub 專案與 `app.py`
4. 設定 Secrets：

點右上角 ⚙️ → `Secrets`，加入：
```toml
FIREBASE_CREDENTIALS = """
{你的 credentials.json 內容（已轉換成一行）}
"""
```

## 📁 檔案結構
- `app.py`：主畫面與功能邏輯
- `firebase_db.py`：Firebase 資料存取模組（自動從 secrets 載入）
- `requirements.txt`：套件安裝清單


# firebase_db.py
import pyrebase
import json
from io import StringIO
import streamlit as st

firebase_config = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
config = {
    "apiKey": firebase_config.get("api_key", ""),
    "authDomain": f"{firebase_config['project_id']}.firebaseapp.com",
    "databaseURL": f"https://{firebase_config['project_id']}.firebaseio.com",
    "storageBucket": f"{firebase_config['project_id']}.appspot.com",
    "serviceAccount": StringIO(json.dumps(firebase_config))
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()

# 新增訂單
def append_order(order_id, content, price, status, note):
    db.child("orders").child(order_id).set({
        "訂單編號": order_id,
        "品項內容": content,
        "金額": price,
        "狀態": status,
        "備註": note
    })

# 讀取訂單
def fetch_orders(status):
    all_data = db.child("orders").get().val()
    return [v for v in all_data.values() if v["狀態"] == status] if all_data else []

# 更新品項內容
def update_order_content(order_id, new_content):
    db.child("orders").child(order_id).update({"品項內容": new_content})

# 刪除訂單
def delete_order_by_id(order_id):
    db.child("orders").child(order_id).remove()
