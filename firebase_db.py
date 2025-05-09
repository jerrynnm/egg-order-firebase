import pyrebase
import json
import streamlit as st
import time
from io import StringIO
import sys
import hashlib

firebase_config = json.loads(st.secrets["FIREBASE_CREDENTIALS"])

with open("temp_credentials.json", "w") as f:
    json.dump(firebase_config, f)

config = {
    "apiKey": firebase_config.get("api_key", ""),
    "authDomain": f"{firebase_config['project_id']}.firebaseapp.com",
    "databaseURL": "https://egg-order-system-default-rtdb.asia-southeast1.firebasedatabase.app/",
    "storageBucket": f"{firebase_config['project_id']}.appspot.com",
    "serviceAccount": StringIO(json.dumps(firebase_config))
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()

def print_error_and_exit(e):
    print("Firebase 連線或寫入失敗，請檢查下列事項：")
    print("1. databaseURL 是否正確")
    print("2. FIREBASE_CREDENTIALS 格式是否正確")
    print("3. Firebase Database Rules 權限是否允許")
    print("4. pyrebase 版本是否相容")
    print("詳細錯誤訊息：", e)
    sys.exit(1)

def append_order(order_id, content, price, status, note):
    data = {
        "訂單編號": order_id,
        "品項內容": content,
        "金額": price,
        "狀態": status,
        "備註": note,
        "timestamp": time.time()
    }
    try:
        db.child("orders").child(order_id).set(data)
    except Exception as e:
        print_error_and_exit(e)

def fetch_orders(status="未完成"):
    try:
        all_data = db.child("orders").get().val()
        if not all_data:
            return []
        return [v for v in all_data.values() if v.get("狀態") == status]
    except Exception as e:
        print("[ERROR] 讀取 Firebase 訂單失敗：", e)
        return []

def update_order_content(order_id, new_content):
    try:
        db.child("orders").child(order_id).update({"品項內容": new_content})
    except Exception as e:
        print_error_and_exit(e)

def mark_order_done(order_id):
    try:
        db.child("orders").child(order_id).update({"狀態": "完成"})
    except Exception as e:
        print_error_and_exit(e)

def delete_order_by_id(order_id, status=None):
    try:
        db.child("orders").child(order_id).remove()
    except Exception as e:
        print_error_and_exit(e)

# ✅ 新增：更新已完成品項欄位

def update_completed_items(order_id, completed_items):
    try:
        db.child("orders").child(order_id).update({"completed_items": completed_items})
    except Exception as e:
        print_error_and_exit(e)
