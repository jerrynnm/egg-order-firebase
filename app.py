import streamlit as st
import time
import datetime
import re
import firebase_db as fdb
import json
import hashlib
from dateutil import parser

# -------- CSS --------
st.markdown(
    """
    <style>
    .center {
        text-align: center !important;
    }
    .stButton>button {
        margin-top: 10px;
        width: 100%; /* 預設按鈕寬度 100% */
    }
    .stTabs [role="tablist"] {
        justify-content: center;
    }
    .stTabs [role="tab"] {
        font-weight: bold;
        font-size: 18px;
    }

    /* 在寬度大於 600px 的螢幕上，調整彈出視窗和主畫面的按鈕並排 */
    @media (min-width: 601px) {
        /* 彈出視窗的按鈕 */
        .st-emotion-cache-10pwrl8 > div > div > div:nth-child(2) > div:first-child .stButton>button { /* 針對彈出視窗的 "確認新增" */
            width: calc(50% - 5px);
            float: left;
        }
        .st-emotion-cache-10pwrl8 > div > div > div:nth-child(2) > div:last-child .stButton>button { /* 針對彈出視窗的 "直接送出" */
            width: calc(50% - 5px);
            float: right;
        }
        .st-emotion-cache-10pwrl8 > div > div > div:nth-child(2)::after { /* 清除彈出視窗按鈕的浮動 */
            content: "";
            display: table;
            clear: both;
        }

        /* 主畫面的 "刪除暫存" 和 "送出" 按鈕 */
        .st-emotion-cache-10pwrl8 > div > div > div:last-child > div:first-child .stButton>button { /* 針對 "刪除暫存" */
            width: calc(50% - 5px);
            float: left;
        }
        .st-emotion-cache-10pwrl8 > div > div > div:last-child > div:last-child .stButton>button { /* 針對 "送出" */
            width: calc(50% - 5px);
            float: right;
        }
        .st-emotion-cache-10pwrl8 > div > div > div:last-child::after { /* 清除主畫面按鈕的浮動 */
            content: "";
            display: table;
            clear: both;
        }
    }

    /* 在寬度小於等於 600px 的螢幕上，按鈕恢復佔滿欄位 */
    @media (max-width: 600px) {
        .stButton>button {
            width: 100%;
            float: none; /* 移除浮動 */
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)
# -------- MENU 資料 --------
MENU = {
    "特價綜合雞蛋糕": 70,
    "內餡雞蛋糕": 50,
    "原味雞蛋糕": 60,
}
FLAVORS = ["拉絲起司", "奧利奧 Oreo", "黑糖麻糬"]
# -------- 初始化 --------
if "temp_order" not in st.session_state:
    st.session_state.temp_order = []


def expand_order_items(order_items):
    return [item["text"] for item in order_items]


def estimate_price(item_text):
    if item_text.startswith("原味雞蛋糕"):
        match = re.search(r"x(\d+)", item_text)
        return MENU["原味雞蛋糕"] * int(match.group(1)) if match else MENU["原味雞蛋糕"]
    return MENU["內餡雞蛋糕"]


# -------- 分頁 --------
tabs = st.tabs(["暫存", "未完成", "完成"])

# -------- 暫存頁 --------
with tabs[0]:
    st.markdown('<div class="center">', unsafe_allow_html=True)
    st.title("選擇餐點")

    def send_temp_order_directly():
        order_id = str(int(time.time() * 1000))[-8:]
        content_list = [o["text"] for o in st.session_state.temp_order]
        total_price = sum(o["price"] for o in st.session_state.temp_order)
        combined_note = " / ".join(
            [o.get("note", "") for o in st.session_state.temp_order if o.get("note")]
        )
        fdb.append_order(order_id, content_list, total_price, "未完成", combined_note)
        st.session_state.temp_order.clear()
        st.session_state.show_popup = True  # ✅ 保持在彈出畫面
        st.session_state.success_message = "✅ 訂單已送出！"

    if st.session_state.get("success_message"):
        st.success(st.session_state.success_message)
        st.session_state.success_message = None

    for item in MENU:
        if st.button(item, key=f"menu_button_{item}"):
            st.session_state.selected_item = item
            st.session_state.show_popup = True

    if st.session_state.get("show_popup", False):
        item = st.session_state["selected_item"]
        st.subheader(f"新增: {item}")

        if item == "原味雞蛋糕":
            qty = st.number_input(
                "份數", min_value=1, max_value=20, value=1, step=1, key="qty"
            )
            note = st.text_input("輸入備註（可空白）", key="note_plain")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("確認新增", key="confirm_plain"):
                    txt = f"{item} x{qty}"
                    if note:
                        txt += f" - 備註: {note}"
                    st.session_state.temp_order.append(
                        {"text": txt, "price": MENU[item] * qty, "note": note}
                    )
                    st.session_state.show_popup = False

            with col2:
                if st.button("直接送出", key="send_plain"):
                    txt = f"{item} x{qty}"
                    if note:
                        txt += f" - 備註: {note}"
                    st.session_state.temp_order.append(
                        {"text": txt, "price": MENU[item] * qty, "note": note}
                    )
                    send_temp_order_directly()

        else:
            flavor_counts = {}
            current_values = {
                flavor: st.session_state.get(f"flavor_{flavor}", 0) for flavor in FLAVORS
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
                    key=f"flavor_{flavor}",
                )

            total_after = sum(flavor_counts.values())
            st.markdown(f"\U0001F7A1 已選擇：**{total_after} 顆**（最多 3 顆）")
            note = st.text_input("輸入備註（可空白）", key="note_filled")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("確認新增", key="confirm_filled"):
                    if total_after != 3:
                        st.warning("必須選滿3顆！")
                    else:
                        flavor_txt = ", ".join(
                            [f"{k}x{v}" for k, v in flavor_counts.items() if v > 0]
                        )
                        if item == "特價綜合雞蛋糕":
                            flavor_txt += ", 原味x3"
                        txt = f"{item} {flavor_txt}"
                        if note:
                            txt += f" - 備註: {note}"
                        st.session_state.temp_order.append(
                            {"text": txt, "price": MENU[item], "note": note}
                        )

                        for flavor in FLAVORS:
                            st.session_state.pop(f"flavor_{flavor}", None)

                        st.session_state.show_popup = True
                        st.rerun()

            with col2:
                if st.button("直接送出", key="send_filled"):
                    if total_after != 3:
                        st.warning("必須選滿3顆！")
                    else:
                        flavor_txt = ", ".join(
                            [f"{k}x{v}" for k, v in flavor_counts.items() if v > 0]
                        )
                        if item == "特價綜合雞蛋糕":
                            flavor_txt += ", 原味x3"
                        txt = f"{item} {flavor_txt}"
                        if note:
                            txt += f" - 備註: {note}"
                        st.session_state.temp_order.append(
                            {"text": txt, "price": MENU[item], "note": note}
                        )
                        send_temp_order_directly()

    st.subheader("暫存訂單顯示區")
    for i, o in enumerate(st.session_state.temp_order):
        st.write(f"{i+1}. {o['text']} (${o['price']})")

    col_del, col_send = st.columns([1, 1])
    with col_del:
        if st.button("刪除暫存", key="delete_temp"):
            if st.session_state.temp_order:
                st.session_state.temp_order.pop()

    with col_send:
        if st.button("送出", key="send_temp_order"):
            if st.session_state.temp_order:
                send_temp_order_directly()

    st.markdown("</div>", unsafe_allow_html=True)

# -------- 未完成訂單頁 --------
...

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
                    if not all(key in order for key in ["訂單編號", "金額", "品項內容"]):
                        st.error(f"訂單資料不完整: {order['訂單編號']}")
                        continue

                    st.subheader(f"訂單 {order['訂單編號']}（金額: ${order['金額']}）")

                    item_list = (
                        order["品項內容"]
                        if isinstance(order["品項內容"], list)
                        else order["品項內容"].split("\n")
                    )
                    completed_items = order.get("completed_items", [])
                    remaining_items = [item for item in item_list if item not in completed_items]

                    checkbox_key_prefix = f"checked_{order['訂單編號']}"
                    if checkbox_key_prefix not in st.session_state:
                        st.session_state[checkbox_key_prefix] = []

                    checked = []
                    for i, item in enumerate(remaining_items):
                        checkbox_key = f"{order['訂單編號']}_{i}"
                        if st.checkbox(f"🟠 {item}", key=checkbox_key):
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
                                    fdb.update_completed_items(order["訂單編號"], checked, completed_price)

                                    new_remaining = [item for item in remaining_items if item not in checked]
                                    if new_remaining:
                                        fdb.update_order_content(order["訂單編號"], new_remaining, order["金額"])
                                    else:
                                        fdb.mark_order_done(order["訂單編號"])
                                else:
                                    fdb.mark_order_done(order["訂單編號"])

                                st.success("訂單更新成功！")
                                st.rerun()
                            except Exception as e:
                                st.error(f"更新訂單時發生錯誤: {str(e)}")

                    with col2:
                        if st.button("🗑️ 刪除", key=f"del_{order['訂單編號']}"):
                            try:
                                fdb.delete_order_by_id(order["訂單編號"])
                                st.success("訂單已刪除！")
                                st.rerun()
                            except Exception as e:
                                st.error(f"刪除訂單時發生錯誤: {str(e)}")
                except Exception as e:
                    st.error(f"處理訂單 {order.get('訂單編號', '未知')} 時發生錯誤: {str(e)}")
        else:
            st.info("目前沒有未完成訂單。")
    except Exception as e:
        st.error(f"載入訂單時發生錯誤: {str(e)}")

# -------- 完成訂單頁 --------
with tabs[2]:
    st.title("完成訂單")

    all_finished = fdb.fetch_orders("完成")
    today_str = date.today().isoformat()
    for order in all_finished:
        ts = order.get("timestamp")
        if ts:
            order_date = datetime.fromtimestamp(ts).date().isoformat()
            if order_date != today_str:
                fdb.delete_order_by_id(order["訂單編號"])

    finished_orders = fdb.fetch_orders("完成")
    finished_orders = sorted(finished_orders, key=lambda x: x.get("timestamp", 0))
    total = sum(o.get("金額", 0) for o in finished_orders)
    st.subheader(f"總營業額：${total}")

    if finished_orders:
        for order in finished_orders:
            st.markdown(f"#### 訂單 {order.get('訂單編號', '未知')}（金額: ${order.get('金額', 0)}）")

            content = order.get("品項內容") or order.get("completed_items") or []
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
