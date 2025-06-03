import streamlit as st
import time
import datetime
import re
import firebase_db as fdb
import json
import hashlib
from dateutil import parser

# -------- CSS --------
import streamlit as st
import time
import datetime
import re
import firebase_db as fdb
import json
import hashlib
from dateutil import parser

# -------- 全局 CSS（包含你之前的 .center 以及隱藏按鈕樣式）--------
st.markdown("""
<style>
  .center {text-align: center !important;}

  /* 調整 Streamlit 原生按鈕讓它寬度撐滿，保留在製作/完成分頁可用 */
  .stButton>button {
    width: 100%;
    margin-top: 10px;
  }

  /* 分頁列置中、字型加粗加大 */
  .stTabs [role="tablist"] {
    justify-content: center;
  }
  .stTabs [role="tab"] {
    font-weight: bold;
    font-size: 18px;
  }

  /* 自訂「送出/刪除暫存」HTML 按鈕樣式 */
  .order-btn-row {
    display: flex;
    justify-content: center;
    margin-top: 12px;
    margin-bottom: 12px;
    gap: 14px;
  }
  .order-btn {
    background: #ff4b4b;
    color: #fff;
    border: none;
    border-radius: 25px;
    font-size: 14px;
    font-weight: bold;
    padding: 8px 20px;
    min-width: 100px;
    box-shadow: 1px 2px 8px #ccc;
    cursor: pointer;
    transition: opacity 0.2s;
  }
  .order-btn.delete {
    background: #888;
  }
  .order-btn:hover {
    opacity: 0.9;
  }

  @media (max-width: 600px) {
    .order-btn-row {
      gap: 10px;
    }
    .order-btn {
      font-size: 12px;
      padding: 6px 12px;
      min-width: 80px;
    }
  }
</style>
""", unsafe_allow_html=True)


# -------- MENU 資料（你原本的）--------
MENU = {
    "特價綜合雞蛋糕": 70,
    "內餡雞蛋糕": 50,
    "原味雞蛋糕": 60
}
FLAVORS = ["拉絲起司", "奧利奧 Oreo", "黑糖麻糬"]

# -------- 初始化 --------
if 'temp_order' not in st.session_state:
    st.session_state.temp_order = []
if 'show_popup' not in st.session_state:
    st.session_state.show_popup = False
if 'success_message' not in st.session_state:
    st.session_state.success_message = None

def estimate_price(item_text):
    if item_text.startswith("原味雞蛋糕"):
        match = re.search(r"x(\d+)", item_text)
        return MENU["原味雞蛋糕"] * int(match.group(1)) if match else MENU["原味雞蛋糕"]
    return MENU["內餡雞蛋糕"]

def send_temp_order_directly():
    # 實務上你會把暫存訂單寫入 Firebase，這裡只示範「清空 + 顯示成功訊息」
    order_id = str(int(time.time() * 1000))[-8:]
    content_list = [o['text'] for o in st.session_state.temp_order]
    total_price = sum(o['price'] for o in st.session_state.temp_order)
    combined_note = ' / '.join([o.get('note', '') for o in st.session_state.temp_order if o.get('note')])
    fdb.append_order(order_id, content_list, total_price, "未完成", combined_note)

    st.session_state.temp_order.clear()
    st.session_state.success_message = "✅ 訂單已送出！"
    st.session_state.show_popup = False


# -------- 分頁 --------
tabs = st.tabs(["暫存", "未完成", "完成"])

# -------- 暫存頁 (tabs[0]) --------
with tabs[0]:
    st.markdown('<div class="center">', unsafe_allow_html=True)
    st.title("選擇餐點")

    # 1. 點「選擇餐點」按鈕，放到暫存區
    if st.session_state.get("success_message"):
        st.success(st.session_state.success_message)
        st.session_state.success_message = None

    for item in MENU:
        if st.button(item, key=f"menu_button_{item}"):
            st.session_state.selected_item = item
            st.session_state.show_popup = True

    # 2. 彈出框：原味 vs 其他
    if st.session_state.get('show_popup', False):
        item = st.session_state['selected_item']
        st.subheader(f"新增: {item}")

        if item == "原味雞蛋糕":
            qty = st.number_input("份數", min_value=1, max_value=20, value=1, step=1, key="qty")
            note = st.text_input("輸入備註（可空白）", key="note_plain")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("直接送出", key="send_plain"):
                    txt = f"{item} x{qty}"
                    if note:
                        txt += f" - 備註: {note}"
                    st.session_state.temp_order.append({"text": txt, "price": MENU[item] * qty, "note": note})
                    send_temp_order_directly()
            with col2:
                if st.button("確認新增", key="confirm_plain"):
                    txt = f"{item} x{qty}"
                    if note:
                        txt += f" - 備註: {note}"
                    st.session_state.temp_order.append({"text": txt, "price": MENU[item] * qty, "note": note})
                    st.session_state.show_popup = False

        else:
            flavor_counts = {}
            current_values = {
                flavor: st.session_state.get(f"flavor_{flavor}", 0)
                for flavor in FLAVORS
            }
            total_selected = sum(current_values.values())
            remaining_total = 3 - total_selected

            cols = st.columns(len(FLAVORS))
            for i, flavor in enumerate(FLAVORS):
                current = current_values[flavor]
                remaining_for_this = 3 - (total_selected - current)
                adjusted_value = min(current, remaining_for_this)

                flavor_counts[flavor] = cols[i].number_input(
                    label=flavor,
                    min_value=0,
                    max_value=remaining_for_this,
                    value=adjusted_value,
                    step=1,
                    key=f"flavor_{flavor}"
                )

            total_after = sum(flavor_counts.values())
            st.markdown(f"\U0001F7A1 已選擇：**{total_after} 顆**（最多 3 顆）")
            note = st.text_input("輸入備註（可空白）", key="note_filled")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("直接送出", key="send_filled"):
                    if total_after != 3:
                        st.warning("必須選滿3顆！")
                    else:
                        flavor_txt = ', '.join([f"{k}x{v}" for k, v in flavor_counts.items() if v > 0])
                        if item == '特價綜合雞蛋糕':
                            flavor_txt += ', 原味x3'
                        txt = f"{item} {flavor_txt}"
                        if note:
                            txt += f" - 備註: {note}"
                        st.session_state.temp_order.append({"text": txt, "price": MENU[item], "note": note})
                        send_temp_order_directly()
            with col2:
                if st.button("確認新增", key="confirm_filled"):
                    if total_after != 3:
                        st.warning("必須選滿3顆！")
                    else:
                        flavor_txt = ', '.join([f"{k}x{v}" for k, v in flavor_counts.items() if v > 0])
                        if item == '特價綜合雞蛋糕':
                            flavor_txt += ', 原味x3'
                        txt = f"{item} {flavor_txt}"
                        if note:
                            txt += f" - 備註: {note}"
                        st.session_state.temp_order.append({"text": txt, "price": MENU[item], "note": note})

                        # 清除 flavor 狀態，準備下次新增
                        for flavor in FLAVORS:
                            st.session_state.pop(f"flavor_{flavor}", None)

                        st.session_state.show_popup = True
                        st.rerun()

    # 3. 顯示暫存訂單清單
    st.subheader("暫存訂單顯示區")
    if st.session_state.temp_order:
        for i, o in enumerate(st.session_state.temp_order):
            st.write(f"{i+1}. {o['text']} (${o['price']})")
    else:
        st.info("目前沒有暫存訂單。")
    st.markdown('</div>', unsafe_allow_html=True)

    # 4. 隱藏版 Streamlit 按鈕：實際執行 send / delete
    #    這兩個按鈕的文字設為空白，不會顯示在畫面上
    if 'btn_send_hidden' not in st.session_state:
        st.session_state.btn_send_hidden = False
    if 'btn_del_hidden' not in st.session_state:
        st.session_state.btn_del_hidden = False

    # 呼叫隱藏按鈕做實際邏輯
    send_trigger = st.button(
        "", 
        key="btn_send_hidden", 
        help="", 
        on_click=send_temp_order_directly
    )
    del_trigger = st.button(
        "", 
        key="btn_del_hidden", 
        help="刪除最後一筆暫存", 
        on_click=lambda: st.session_state.temp_order.pop() if st.session_state.temp_order else None
    )

    # 5. 真正呈現給使用者的「紅色送出 / 灰色刪除暫存」按鈕 (HTML)
    st.markdown("""
    <div class="order-btn-row">
        <button class="order-btn" onclick="document.querySelector('[data-baseweb=\"button\"][data-key=\"btn_send_hidden\"]').click();">
            🚀 送出
        </button>
        <button class="order-btn delete" onclick="document.querySelector('[data-baseweb=\"button\"][data-key=\"btn_del_hidden\"]').click();">
            🗑️ 刪除暫存
        </button>
    </div>
    """, unsafe_allow_html=True)

# -------- 未完成訂單頁 --------
with tabs[1]:
    st.title("未完成訂單")

    try:
        unfinished_orders = fdb.fetch_orders("未完成")

        raw_data = json.dumps(unfinished_orders, sort_keys=True, ensure_ascii=False)
        current_hash = hashlib.md5(raw_data.encode("utf-8")).hexdigest()

        if "last_unfinished_hash" not in st.session_state:
            st.session_state.last_unfinished_hash = None

        if current_hash != st.session_state.last_unfinished_hash:
            st.session_state.last_unfinished_hash = current_hash
            st.rerun()

        if unfinished_orders:
            for order in unfinished_orders:
                try:
                    if not all(key in order for key in ['訂單編號', '金額', '品項內容']):
                        st.error(f"訂單資料不完整: {order['訂單編號']}")
                        continue

                    st.subheader(f"訂單 {order['訂單編號']}（金額: ${order['金額']}）")

                    item_list = order["品項內容"] if isinstance(order["品項內容"], list) else order["品項內容"].split("\n")
                    completed_items = order.get("completed_items", [])
                    remaining_items = [item for item in item_list if item not in completed_items]

                    checkbox_key = f"checked_{order['訂單編號']}"
                    if checkbox_key not in st.session_state:
                        st.session_state[checkbox_key] = []

                    checked = []
                    for i, item in enumerate(remaining_items):
                        checkbox_key = f"{order['訂單編號']}_{i}"
                        if st.checkbox(f"\U0001F7E0 {item}", key=checkbox_key):
                            checked.append(item)

                    st.markdown("---")
                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button("✅ 完成", key=f"done_{order['訂單編號']}"):
                            try:
                                if checked:
                                    def estimate_price(text):
                                        for k in MENU:
                                            if text.startswith(k):
                                                if k == "原味雞蛋糕":
                                                    match = re.search(r"x(\\d+)", text)
                                                    qty = int(match.group(1)) if match else 1
                                                    return MENU[k] * qty
                                                return MENU[k]
                                        return 50

                                    completed_price = sum(estimate_price(i) for i in checked)

                                    fdb.update_completed_items(order['訂單編號'], checked, completed_price)

                                    new_remaining = [item for item in remaining_items if item not in checked]
                                    if new_remaining:
                                        fdb.update_order_content(order['訂單編號'], new_remaining, order['金額'])
                                    else:
                                        fdb.mark_order_done(order['訂單編號'])
                                else:
                                    fdb.mark_order_done(order['訂單編號'])

                                st.success("訂單更新成功！")
                                st.rerun()

                            except Exception as e:
                                st.error(f"更新訂單時發生錯誤: {str(e)}")

                    with col2:
                        if st.button("🗑️ 刪除", key=f"del_{order['訂單編號']}"):
                            try:
                                fdb.delete_order_by_id(order['訂單編號'])
                                st.success("訂單已刪除！")
                                st.rerun()
                            except Exception as e:
                                st.error(f"刪除訂單時發生錯誤: {str(e)}")

                except Exception as e:
                    st.error(f"處理訂單 {order.get('訂單編號', '未知')} 時發生錯誤: {str(e)}")
                    continue

        else:
            st.info("目前沒有未完成訂單。")

    except Exception as e:
        st.error(f"載入訂單時發生錯誤: {str(e)}")

# -------- 完成訂單頁 --------
from datetime import datetime, date

with tabs[2]:
    st.title("完成訂單")

    # ✅ 自動刪除非今天的完成訂單
    all_finished = fdb.fetch_orders("完成")
    today_str = date.today().isoformat()
    for order in all_finished:
        ts = order.get("timestamp")
        if ts:
            order_date = datetime.fromtimestamp(ts).date().isoformat()
            if order_date != today_str:
                fdb.delete_order_by_id(order['訂單編號'])

    # ✅ 重新抓取已過濾後的資料
    finished_orders = fdb.fetch_orders("完成")
    finished_orders = sorted(finished_orders, key=lambda x: x.get("timestamp", 0))

    total = sum(o.get('金額', 0) for o in finished_orders)
    st.subheader(f"總營業額：${total}")

    if finished_orders:
        for order in finished_orders:
            st.markdown(f"#### 訂單 {order.get('訂單編號', '未知')}（金額: ${order.get('金額', 0)}）")

            # ✅ 顯示「品項內容」（原始品項 + 分批完成的品項）
            content = order.get('品項內容') or order.get('completed_items') or []
            if isinstance(content, list):
                for item in content:
                    st.text(item)
            elif isinstance(content, str):
                for item in content.split("\n"):
                    st.text(item)
            else:
                st.caption("⚠️ 無品項內容")

            if order.get("備註"):
                st.caption(f"備註：{order['備註']}")
    else:
        st.info("尚無完成訂單。")
