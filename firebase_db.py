import pyrebase
import json
import streamlit as st
import time

# 把 secrets 中的 FIREBASE_CREDENTIALS 解析成字典
firebase_config = json.loads(st.secrets["FIREBASE_CREDENTIALS"])

# 建立臨時憑證檔案（Streamlit Cloud 專用做法）
with open("temp_credentials.json", "w") as f:
    json.dump(firebase_config, f)

config = {
    "apiKey": firebase_config.get("api_key", ""),
    "authDomain": f"{firebase_config['project_id']}.firebaseapp.com",
    "databaseURL": "https://egg-order-system-default-rtdb.asia-southeast1.firebasedatabase.app/",
    "storageBucket": f"{firebase_config['project_id']}.appspot.com",
    "serviceAccount": "temp_credentials.json"
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()

# ✅ 寫入新訂單
def append_order(order_id, content, price, status, note=""):
    data = {
        "訂單編號": order_id,
        "品項內容": content,
        "金額": price,
        "備註": note,
        "狀態": status,
        "timestamp": time.time()
    }
    db.child("orders").child(order_id).set(data)

# ✅ 根據狀態抓取訂單
def fetch_orders(status="未完成"):
    try:
        result = db.child("orders").order_by_child("狀態").equal_to(status).get()
        return [o.val() for o in result.each()] if result.each() else []
    except:
        # 防止 order_by_child 抱錯，改為先抓全部再篩選
        all_data = db.child("orders").get().val()
        return [v for v in all_data.values() if v.get("狀態") == status] if all_data else []

# ✅ 更新品項內容（部分完成用）
def update_order_content(order_id, new_content):
    db.child("orders").child(order_id).update({"品項內容": new_content})

# ✅ 專門修改為「完成」狀態
def mark_order_done(order_id):
    db.child("orders").child(order_id).update({"狀態": "完成"})

# ✅ 刪除訂單（可傳入狀態，但目前未用上）
def delete_order_by_id(order_id, status=None):
    db.child("orders").child(order_id).remove()
