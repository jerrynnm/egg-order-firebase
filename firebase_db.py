# firebase_db.py
import pyrebase
import time

# ✅ 根據你提供的憑證內容整合完成
config = {
    "apiKey": "AIzaSyDZldA0JmQ0UvZK9sDbZZIquwlhUBpvJDk",
    "authDomain": "egg-order-system.firebaseapp.com",
    "databaseURL": "https://egg-order-system.firebaseio.com",
    "storageBucket": "egg-order-system.appspot.com",
    "serviceAccount": "credentials.json"
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()

# ✅ 寫入新訂單（未完成）
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

# ✅ 抓取訂單（可指定狀態）
def fetch_orders(status="未完成"):
    result = db.child("orders").order_by_child("狀態").equal_to(status).get()
    return [o.val() for o in result.each()] if result.each() else []

# ✅ 更新訂單內容（部分完成時修改）
def update_order_content(order_id, new_content):
    db.child("orders").child(order_id).update({"品項內容": new_content})

# ✅ 修改狀態（完成訂單）
def mark_order_done(order_id):
    db.child("orders").child(order_id).update({"狀態": "完成"})

# ✅ 刪除訂單
def delete_order_by_id(order_id, status=None):
    db.child("orders").child(order_id).remove()
