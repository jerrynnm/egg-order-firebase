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

# ✅ 更新完成品項並累加金額
def update_completed_items(order_id, new_items, new_amount):
    try:
        order_ref = db.child("orders").child(order_id)
        existing = order_ref.get().val()

        old_items = existing.get("品項內容", [])
        if not isinstance(old_items, list):
            old_items = [old_items]

        old_amount = existing.get("金額", 0)
        updated_items = old_items + new_items
        updated_amount = old_amount + new_amount

        order_ref.update({
            "品項內容": updated_items,
            "金額": updated_amount
            # ⛔ 不自動改為完成，由 app.py 視剩餘品項決定
        })
    except Exception as e:
        print_error_and_exit(e)


# ✅ 更新未完成的剩餘品項

def update_completed_items(order_id, new_items, new_amount):
    try:
        order_ref = db.child("orders").child(order_id)
        existing = order_ref.get().val()

        # 原本完成品項 + 新增品項
        old_completed = existing.get("completed_items", [])
        updated_completed = old_completed + new_items

        # 原本金額 + 新增金額
        old_amount = existing.get("金額", 0)
        updated_amount = old_amount + new_amount

        # 更新品項、金額、完成清單與狀態
        order_ref.update({
            "completed_items": updated_completed,
            "金額": updated_amount,
            "狀態": "完成"
        })
    except Exception as e:
        print_error_and_exit(e)


