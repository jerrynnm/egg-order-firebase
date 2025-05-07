import pyrebase  # 建議使用 pyrebase4，如果 requirements.txt 允許
import json
import streamlit as st
import time
from io import StringIO
import sys

# 把 secrets 中的 FIREBASE_CREDENTIALS 解析成字典
firebase_config = json.loads(st.secrets["FIREBASE_CREDENTIALS"])

# 建立臨時憑證檔案（Streamlit Cloud 專用做法）
with open("temp_credentials.json", "w") as f:
    json.dump(firebase_config, f)

# 1. 正確設定 databaseURL（直接填寫完整網址）
config = {
    "apiKey": firebase_config.get("api_key", ""),
    "authDomain": f"{firebase_config['project_id']}.firebaseapp.com",
    "databaseURL": "https://egg-order-system-default-rtdb.asia-southeast1.firebasedatabase.app/",
    "storageBucket": f"{firebase_config['project_id']}.appspot.com",
    "serviceAccount": StringIO(json.dumps(firebase_config))
}

# 5. pyrebase 版本建議
# 建議在 requirements.txt 使用 pyrebase4 或 firebase-admin
# 例如：pyrebase4==4.5.0

firebase = pyrebase.initialize_app(config)
db = firebase.database()

# 6. 本地端測試錯誤提示
def print_error_and_exit(e):
    print("Firebase 連線或寫入失敗，請檢查下列事項：")
    print("1. databaseURL 是否正確")
    print("2. FIREBASE_CREDENTIALS 格式是否正確")
    print("3. Firebase Database Rules 權限是否允許")
    print("4. pyrebase 版本是否相容")
    print("詳細錯誤訊息：", e)
    sys.exit(1)

# ✅ 寫入新訂單
import time  # ⬅️ 這行請加在最上面 if not already present

def append_order(order_id, content, price, status, note):
    data = {
        "訂單編號": order_id,
        "品項內容": content,
        "金額": price,
        "狀態": status,
        "備註": note,
        "timestamp": time.time()
    }
    print("[DEBUG] 寫入資料：", data)  # ✅ 在 console 顯示寫入內容
    db.child("orders").child(order_id).set(data)

    try:
        db.child("orders").child(order_id).set(data)
    except Exception as e:
        print_error_and_exit(e)

# ✅ 根據狀態抓取訂單
import json
import hashlib

def fetch_orders(status="未完成"):
    try:
        all_data = db.child("orders").get().val()
        if not all_data:
            print("[DEBUG] Firebase 中沒有任何訂單")
            return []

        filtered = [v for v in all_data.values() if v.get("狀態") == status]
        print(f"[DEBUG] 從 Firebase 抓到『{status}』訂單共 {len(filtered)} 筆")
        return filtered

    except Exception as e:
        print("[ERROR] 讀取 Firebase 訂單失敗：", e)
        return []

# ✅ 更新品項內容（部分完成用）
def update_order_content(order_id, new_content):
    try:
        db.child("orders").child(order_id).update({"品項內容": new_content})
    except Exception as e:
        print_error_and_exit(e)

# ✅ 專門修改為「完成」狀態
def mark_order_done(order_id):
    try:
        db.child("orders").child(order_id).update({"狀態": "完成"})
    except Exception as e:
        print_error_and_exit(e)

# ✅ 刪除訂單（可傳入狀態，但目前未用上）
def delete_order_by_id(order_id, status=None):
    try:
        db.child("orders").child(order_id).remove()
    except Exception as e:
        print_error_and_exit(e)
