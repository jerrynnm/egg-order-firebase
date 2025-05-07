# app.py
import streamlit as st
import time
import datetime
import re
import firebase_db as fdb
import json
from streamlit_autorefresh import st_autorefresh
from dateutil import parser
import hashlib

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
            current_values = {}
            for flavor in FLAVORS:
                current_values[flavor] = st.session_state.get(f"flavor_{flavor}", 0)

            total = sum(current_values.values())
            cols = st.columns(len(FLAVORS))
            for i, flavor in enumerate(FLAVORS):
                remaining = 3 - (total - current_values[flavor])
                flavor_counts[flavor] = cols[i].number_input(
                    flavor,
                    min_value=0,
                    max_value=remaining,
                    value=current_values[flavor],
                    step=1,
                    key=f"flavor_{flavor}"
                )

            total = sum(flavor_counts.values())
            st.write(f"已選 {total} 顆 / 限制 3 顆")
            note = st.text_input("輸入備註（可空白）", key="note")

            if st.button("確認新增"):
                if total != 3:
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
                content_all = '\n'.join([o['text'] for o in st.session_state.temp_order])
                total_price = sum([o['price'] for o in st.session_state.temp_order])
                combined_note = ' / '.join([o.get('note', '') for o in st.session_state.temp_order if o.get('note')])

                fdb.append_order(
                    order_id=order_id,
                    content=content_all,
                    price=total_price,
                    status="未完成",
                    note=combined_note
                )

                st.session_state.temp_order.clear()
                st.session_state.force_unfinished_refresh = True
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# -------- 未完成頁 --------
with tabs[1]:
    st.markdown('<div class="center">', unsafe_allow_html=True)
    st.title("未完成訂單")

    st_autorefresh(interval=10000, key="refresh_unfinished_check", limit=None)
    unfinished_orders = fdb.fetch_orders(status="未完成")

    raw_data = json.dumps(unfinished_orders, sort_keys=True, ensure_ascii=False)
    current_hash = hashlib.md5(raw_data.encode("utf-8")).hexdigest()

    if "last_unfinished_hash" not in st.session_state:
        st.session_state.last_unfinished_hash = None
    if "unfinished_viewed_once" not in st.session_state:
        st.session_state.unfinished_viewed_once = False
    if "force_unfinished_refresh" not in st.session_state:
        st.session_state.force_unfinished_refresh = True

    if (
        not st.session_state.unfinished_viewed_once
        or current_hash != st.session_state.last_unfinished_hash
        or st.session_state.force_unfinished_refresh
    ):
        st.session_state.unfinished_viewed_once = True
        st.session_state.last_unfinished_hash = current_hash

        if unfinished_orders:
            for order in unfinished_orders:
                st.subheader(f"訂單 {order['訂單編號']} (金額: ${order['金額']})")
                items = order['品項內容'].split('\n')
                selected_items = []

                for i, item_text in enumerate(items):
                    selected = st.checkbox(f"🔸 {item_text}", key=f"{order['訂單編號']}_check_{i}")
                    if selected:
                        selected_items.append(i)

                if order.get('備註'):
                    st.caption(f"備註：{order['備註']}")

                col1, col2 = st.columns(2)

                if col1.button("✅ 完成", key=f"finish_btn_{order['訂單編號']}"):
                    if selected_items:
                        for i in sorted(selected_items, reverse=True):
                            fdb.append_order(
                                order_id=order['訂單編號'] + f"_{i}",
                                content=items[i],
                                price=0,
                                status="完成",
                                note=order.get('備註', '')
                            )
                            items.pop(i)
                        if items:
                            fdb.update_order_content(order['訂單編號'], '\n'.join(items))
                        else:
                            fdb.delete_order_by_id(order['訂單編號'])
                    else:
                        fdb.append_order(
                            order_id=order['訂單編號'],
                            content=order['品項內容'],
                            price=order['金額'],
                            status="完成",
                            note=order.get('備註', '')
                        )
                        fdb.delete_order_by_id(order['訂單編號'])

                    st.session_state.force_unfinished_refresh = True
                    st.rerun()

                if col2.button("🗑️ 刪除", key=f"delete_btn_{order['訂單編號']}"):
                    if selected_items:
                        for i in sorted(selected_items, reverse=True):
                            items.pop(i)
                        if items:
                            fdb.update_order_content(order['訂單編號'], '\n'.join(items))
                        else:
                            fdb.delete_order_by_id(order['訂單編號'])
                    else:
                        fdb.delete_order_by_id(order['訂單編號'])

                    st.session_state.force_unfinished_refresh = True
                    st.rerun()
        else:
            st.info("目前沒有未完成訂單。")

        if "force_unfinished_refresh" in st.session_state:
            del st.session_state["force_unfinished_refresh"]

    else:
        st.caption("⏳ 訂單內容無變更，暫不更新畫面")

    st.markdown('</div>', unsafe_allow_html=True)

# -------- 完成頁 --------
with tabs[2]:
    st.markdown('<div class="center">', unsafe_allow_html=True)
    st.title("完成訂單")

    finished_orders = fdb.fetch_orders(status="完成")
    total = sum(int(o['金額']) for o in finished_orders)
    count = len(finished_orders)
    st.subheader(f"總營業額: ${total}")
    st.subheader(f"總出單數: {count}")

    for order in finished_orders:
        st.subheader(f"訂單 {order['訂單編號']}")
        st.write(order['品項內容'])
        if order.get('備註'):
            st.caption(f"備註：{order['備註']}")

    st.markdown('</div>', unsafe_allow_html=True)