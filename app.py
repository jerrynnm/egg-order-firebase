import streamlit as st
import time
import datetime
import re
import firebase_db as fdb
import json
import hashlib
from dateutil import parser

# -------- CSS 美化 --------
st.markdown("""
    <style>
    .center {text-align: center !important;}
    .stButton>button {
        width: 100%;
        margin-top: 10px;
    }
    .stTabs [role="tablist"] {
        justify-content: center;
    }
    .stTabs [role="tab"] {
        font-weight: bold;
        font-size: 18px;
    }
    </style>
""", unsafe_allow_html=True)

# -------- 資料與初始化 --------
MENU = {
    "特價綜合雞蛋糕": 70,
    "內餡雞蛋糕": 50,
    "原味雞蛋糕": 60
}
FLAVORS = ["拉絲起司", "奧利奧 Oreo", "黑糖麻糬"]

if 'temp_order' not in st.session_state:
    st.session_state.temp_order = []

# -------- 分頁 --------
tabs = st.tabs(["暫存", "未完成", "完成"])

# -------- 暫存頁 --------
with tabs[0]:
    st.markdown('<div class="center">', unsafe_allow_html=True)
    st.title("選擇餐點")

    for item in MENU:
        if st.button(item):
            st.session_state.selected_item = item
            st.session_state.show_popup = True

    if st.session_state.get('show_popup', False):
        item = st.session_state['selected_item']
        st.subheader(f"新增: {item}")

        if item == "原味雞蛋糕":
            qty = st.number_input("份數", min_value=1, max_value=20, value=1, step=1, key="qty")
            note = st.text_input("輸入備註（可空白）", key="note")
            if st.button("確認新增"):
                txt = f"{item} x{qty}"
                if note:
                    txt += f" - 備註: {note}"
                st.session_state.temp_order.append({"text": txt, "price": MENU[item] * qty, "note": note})
                st.session_state.show_popup = False

        else:
            flavor_counts = {}
            current_values = {flavor: st.session_state.get(f"flavor_{flavor}", 0) for flavor in FLAVORS}
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
            st.markdown(f"🟡 已選擇：**{total_after} 顆**（最多 3 顆）")
            note = st.text_input("輸入備註（可空白）", key="note")

            if st.button("確認新增"):
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

                    for flavor in FLAVORS:
                        flavor_key = f"flavor_{flavor}"
                        if flavor_key in st.session_state:
                            del st.session_state[flavor_key]

                    st.session_state.show_popup = True
                    st.rerun()

    st.subheader("暫存訂單顯示區")
    for i, o in enumerate(st.session_state.temp_order):
        st.write(f"{i+1}. {o['text']} (${o['price']})")

    col_del, col_send = st.columns([1, 1])
    with col_del:
        if st.button("刪除暫存"):
            if st.session_state.temp_order:
                st.session_state.temp_order.pop()

        with col_send:
        if st.button("送出"):
            if st.session_state.temp_order:
                order_id = str(int(time.time() * 1000))[-8:]
                content_list = [o['text'] for o in st.session_state.temp_order]  # ✅ 改為清單
                total_price = sum([o['price'] for o in st.session_state.temp_order])
                combined_note = ' / '.join([o.get('note', '') for o in st.session_state.temp_order if o.get('note')])

                fdb.append_order(
                    order_id=order_id,
                    content=content_list,  # ✅ 清單格式儲存
                    price=total_price,
                    status="未完成",
                    note=combined_note
                )

                st.session_state.temp_order.clear()
                st.session_state.force_unfinished_refresh = True
                st.rerun()

    if st.session_state.get("order_submitted"):
        st.success("✅ 已送出訂單！")
        del st.session_state["order_submitted"]

    st.markdown('</div>', unsafe_allow_html=True)

# -------- 未完成頁 --------
with tabs[1]:
    st.title("未完成訂單")

    unfinished_orders = fdb.fetch_orders(status="未完成")

    # 判斷資料變化：若有變化才刷新
    raw_data = json.dumps(unfinished_orders, sort_keys=True, ensure_ascii=False)
    current_hash = hashlib.md5(raw_data.encode("utf-8")).hexdigest()
    if "last_unfinished_hash" not in st.session_state:
        st.session_state.last_unfinished_hash = None
    if current_hash != st.session_state.last_unfinished_hash:
        st.session_state.last_unfinished_hash = current_hash
        st.rerun()

    if unfinished_orders:
        for order in unfinished_orders:
            st.subheader(f"訂單 {order['訂單編號']}（金額: ${order['金額']}）")

            item_list = order["品項內容"] if isinstance(order["品項內容"], list) else order["品項內容"].split("\n")

            checked_indices = []
            for i, item in enumerate(item_list):
                if st.checkbox(f"🟠 {item}", key=f"{order['訂單編號']}_{i}"):
                    checked_indices.append(i)

            st.markdown("---")
            col1, col2 = st.columns(2)

            with col1:
                if st.button("✅ 完成", key=f"done_{order['訂單編號']}"):
                    if checked_indices:
                        new_list = [item for i, item in enumerate(item_list) if i not in checked_indices]
                        if new_list:
                            fdb.update_order_content(order['訂單編號'], new_list)
                        else:
                            fdb.mark_order_done(order['訂單編號'])
                    else:
                        fdb.mark_order_done(order['訂單編號'])
                    st.rerun()

            with col2:
                if st.button("🗑️ 刪除", key=f"del_{order['訂單編號']}"):
                    if checked_indices:
                        new_list = [item for i, item in enumerate(item_list) if i not in checked_indices]
                        if new_list:
                            fdb.update_order_content(order['訂單編號'], new_list)
                        else:
                            fdb.delete_order_by_id(order['訂單編號'])
                    else:
                        fdb.delete_order_by_id(order['訂單編號'])
                    st.rerun()
    else:
        st.info("目前沒有未完成訂單。")

# -------- 完成頁 --------
with tabs[2]:
    st.title("完成訂單")
    finished_orders = fdb.fetch_orders(status="完成")
    total = sum(o['金額'] for o in finished_orders) if finished_orders else 0
    st.subheader(f"總營業額：${total}")
    if finished_orders:
        for order in finished_orders:
            st.markdown(f"#### 訂單 {order['訂單編號']}")
            st.text(order['品項內容'])
            if order.get("備註"):
                st.caption(f"備註：{order['備註']}")
    else:
        st.info("尚無完成訂單。")

    st.markdown('</div>', unsafe_allow_html=True)
