import streamlit as st
import time
import re
import json
import hashlib
import firebase_db as fdb
from datetime import datetime, date

# ====== 1. Session State 初始化 ======
# 一開始就把會用到的 key 全部先做好預設，避免在渲染階段又寫意 session_state 而出錯。
st.session_state.setdefault("temp_order", [])
st.session_state.setdefault("show_popup", False)
st.session_state.setdefault("success_message", None)

# ====== 2. Python 端執行邏輯：送出 / 刪除暫存 ======
def send_temp_order_directly():
    """
    寫入 Firebase，清空暫存，顯示成功訊息。
    """
    order_id = str(int(time.time() * 1000))[-8:]
    content_list = [o["text"] for o in st.session_state.temp_order]
    total_price = sum(o["price"] for o in st.session_state.temp_order)
    combined_note = " / ".join([o.get("note", "") for o in st.session_state.temp_order if o.get("note")])
    fdb.append_order(order_id, content_list, total_price, "未完成", combined_note)

    st.session_state.temp_order.clear()
    st.session_state.show_popup = False
    st.session_state.success_message = "✅ 訂單已送出！"

def del_last_temp_item():
    """
    刪除暫存最後一筆。
    """
    if st.session_state.temp_order:
        st.session_state.temp_order.pop()

# ====== 3. 注入「原生 HTML+CSS」段落，和你貼的範例基本一樣，只是稍微改成 unsafe_allow_html ======
st.markdown("""
<style>
    /* 3.1 如果你已有分頁要置中，直接保留下面這兩行即可 */
    .stTabs [role="tablist"] {
        justify-content: center !important;
    }
    .stTabs [role="tab"] {
        font-weight: bold !important;
        font-size: 18px !important;
    }

    /* 3.2 .center 類別：置中使用 */
    .center {
        text-align: center !important;
    }

    /* 3.3 這裡就是「不換行」或「極窄螢幕容許換行」的關鍵，
       原本範例用 flex-wrap:wrap，但若你要完全不換行，可改成 nowrap。 */
    .btn-row {
        display: flex;
        gap: 12px;
        justify-content: center; /* 水平置中 */
        align-items: center;     /* 垂直置中 */
        margin: 12px 0 18px 0;
        flex-wrap: wrap;         /* 極窄螢幕允許換行 → 要改成 nowrap 就直接寫 flex-wrap:nowrap; */
        padding: 0 10px;         /* 左右邊距，防止按鈕貼邊 */
    }
    /* 3.4 按鈕樣式：背景漸層、圓角、陰影、hover/active 效果 */
    .my-btn {
        font-size: 15px;
        padding: 8px 20px;
        border-radius: 1.2em;
        border: none;
        background: linear-gradient(90deg, #ffe082, #ffd966);
        color: #a76700;
        font-weight: 700;
        cursor: pointer;
        transition: background 0.12s, transform 0.1s;
        box-shadow: 0 2px 8px #ffd96655;
        white-space: nowrap; /* 防止文字換行 */
        flex: 0 1 auto;     /* 確保按鈕大小能靈活適應 */
    }
    .my-btn:hover {
        background: linear-gradient(90deg, #ffeca2, #ffe082);
    }
    .my-btn:active {
        background: #ffd966 !important;
        transform: scale(0.95); /* 點擊縮放效果 */
    }

    /* 3.5 在手機（小於600px）時，縮小按鈕的 font-size / padding / min-width */
    @media (max-width: 600px) {
        .btn-row {
            gap: 8px;
            justify-content: center; /* 手機端保持水平置中 */
        }
        .my-btn {
            font-size: 14px;
            padding: 7px 16px;
            min-width: 100px; /* 最小寬度，適配點餐系統 */
        }
    }
    @media (max-width: 400px) {
        .my-btn {
            font-size: 13px;
            padding: 6px 12px;
            min-width: 90px; /* 超小螢幕再微調 */
        }
    }
</style>
""", unsafe_allow_html=True)

# ====== 4. 三個分頁 ======
tabs = st.tabs(["暫存", "未完成", "完成"])


# ====== 第一頁：「暫存」 ======
with tabs[0]:
    st.markdown('<div class="center">', unsafe_allow_html=True)
    st.title("選擇餐點")

    # 4.1 如果有「送出成功」訊息就顯示
    if st.session_state.get("success_message"):
        st.success(st.session_state.success_message)
        st.session_state.success_message = None

    # 4.2 菜單按鈕：按一下會打開 popup
    MENU = {
        "特價綜合雞蛋糕": 70,
        "內餡雞蛋糕": 50,
        "原味雞蛋糕": 60
    }
    FLAVORS = ["拉絲起司", "奧利奧 Oreo", "黑糖麻糬"]

    for item in MENU:
        if st.button(item, key=f"menu_button_{item}"):
            st.session_state.selected_item = item
            st.session_state.show_popup = True

    # 4.3 如果 show_popup 為 True，就顯示「新增」邏輯
    if st.session_state.get("show_popup", False):
        food = st.session_state["selected_item"]
        st.subheader(f"新增: {food}")

        if food == "原味雞蛋糕":
            qty = st.number_input("份數", min_value=1, max_value=20, value=1, step=1, key="qty")
            note = st.text_input("輸入備註（可空白）", key="note_plain")

            col1, col2 = st.columns(2, gap="small")
            with col1:
                if st.button("直接送出", key="send_plain"):
                    txt = f"{food} x{qty}"
                    if note:
                        txt += f" - 備註: {note}"
                    st.session_state.temp_order.append({"text": txt, "price": MENU[food] * qty, "note": note})
                    send_temp_order_directly()
            with col2:
                if st.button("確認新增", key="confirm_plain"):
                    txt = f"{food} x{qty}"
                    if note:
                        txt += f" - 備註: {note}"
                    st.session_state.temp_order.append({"text": txt, "price": MENU[food] * qty, "note": note})
                    st.session_state.show_popup = False

        else:
            flavor_counts = {}
            current_vals = {flav: st.session_state.get(f"flavor_{flav}", 0) for flav in FLAVORS}
            total_selected = sum(current_vals.values())
            remaining_total = 3 - total_selected

            cols = st.columns(len(FLAVORS))
            for i, flav in enumerate(FLAVORS):
                curr = current_vals[flav]
                remain_for_this = 3 - (total_selected - curr)
                adjusted = min(curr, remain_for_this)
                flavor_counts[flav] = cols[i].number_input(
                    label=flav,
                    min_value=0,
                    max_value=remain_for_this,
                    value=adjusted,
                    step=1,
                    key=f"flavor_{flav}"
                )

            total_after = sum(flavor_counts.values())
            st.markdown(f"\U0001F7A1 已選擇：**{total_after} 顆**（最多 3 顆）")
            note = st.text_input("輸入備註（可空白）", key="note_filled")

            col1, col2 = st.columns(2, gap="small")
            with col1:
                if st.button("直接送出", key="send_filled"):
                    if total_after != 3:
                        st.warning("必須選滿3顆！")
                    else:
                        flavor_txt = ", ".join(f"{k}x{v}" for k,v in flavor_counts.items() if v>0)
                        if food == "特價綜合雞蛋糕":
                            flavor_txt += ", 原味x3"
                        txt = f"{food} {flavor_txt}"
                        if note:
                            txt += f" - 備註: {note}"
                        st.session_state.temp_order.append({"text": txt, "price": MENU[food], "note": note})
                        send_temp_order_directly()
            with col2:
                if st.button("確認新增", key="confirm_filled"):
                    if total_after != 3:
                        st.warning("必須選滿3顆！")
                    else:
                        flavor_txt = ", ".join(f"{k}x{v}" for k,v in flavor_counts.items() if v>0)
                        if food == "特價綜合雞蛋糕":
                            flavor_txt += ", 原味x3"
                        txt = f"{food} {flavor_txt}"
                        if note:
                            txt += f" - 備註: {note}"
                        st.session_state.temp_order.append({"text": txt, "price": MENU[food], "note": note})
                        for f in FLAVORS:
                            st.session_state.pop(f"flavor_{f}", None)
                        st.session_state.show_popup = True
                        st.rerun()

    # 4.4 顯示暫存訂單
    st.subheader("暫存訂單顯示區")
    if st.session_state.temp_order:
        for idx, o in enumerate(st.session_state.temp_order):
            st.write(f"{idx+1}. {o['text']} (${o['price']})")
    else:
        st.info("目前沒有暫存訂單。")
    st.markdown("</div>", unsafe_allow_html=True)

    # 4.5 最關鍵：兩顆按鈕並排 (st.columns(2)) + CSS 確保手機不換行
    col1, col2 = st.columns(2, gap="small")
    with col1:
        send_click = st.button("🚀 送出", key="send_temp", help="將所有暫存訂單送出")
    with col2:
        del_click = st.button("🗑️ 刪除暫存", key="del_temp", help="刪除最後一筆暫存")

    if send_click:
        send_temp_order_directly()
    if del_click:
        del_last_temp_item()


# ====== 第二頁：「未完成訂單」 ======
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
                    if not all(k in order for k in ["訂單編號", "金額", "品項內容"]):
                        st.error(f"訂單資料不完整: {order.get('訂單編號','未知')}")
                        continue

                    st.subheader(f"訂單 {order['訂單編號']}（金額: ${order['金額']}）")
                    item_list = order["品項內容"] if isinstance(order["品項內容"], list) else order["品項內容"].split("\n")
                    completed_items = order.get("completed_items", [])
                    remaining_items = [it for it in item_list if it not in completed_items]

                    for i, it in enumerate(remaining_items):
                        key_cb = f"{order['訂單編號']}_cb_{i}"
                        if key_cb not in st.session_state:
                            st.session_state[key_cb] = False
                        checked = st.checkbox(f"\U0001F7E0 {it}", key=key_cb)
                        if checked:
                            if "to_complete" not in st.session_state:
                                st.session_state.to_complete = {}
                            if order["訂單編號"] not in st.session_state.to_complete:
                                st.session_state.to_complete[order["訂單編號"]] = []
                            if it not in st.session_state.to_complete[order["訂單編號"]]:
                                st.session_state.to_complete[order["訂單編號"]].append(it)

                    st.markdown("---")
                    c1, c2 = st.columns(2, gap="small")
                    with c1:
                        if st.button("✅ 完成", key=f"done_{order['訂單編號']}"):
                            try:
                                checked = st.session_state.to_complete.get(order["訂單編號"], [])
                                if checked:
                                    completed_price = sum(estimate_price(i) for i in checked)
                                    fdb.update_completed_items(order["訂單編號"], checked, completed_price)
                                    new_remaining = [it for it in remaining_items if it not in checked]
                                    if new_remaining:
                                        fdb.update_order_content(order["訂單編號"], new_remaining, order["金額"])
                                    else:
                                        fdb.mark_order_done(order["訂單編號"])
                                else:
                                    fdb.mark_order_done(order["訂單編號"])
                                st.success("訂單更新成功！")
                                st.rerun()
                            except Exception as e:
                                st.error(f"更新訂單時出錯: {str(e)}")
                    with c2:
                        if st.button("🗑️ 刪除", key=f"del_{order['訂單編號']}"):
                            try:
                                fdb.delete_order_by_id(order["訂單編號"])
                                st.success("訂單已刪除！")
                                st.rerun()
                            except Exception as e:
                                st.error(f"刪除訂單時出錯: {str(e)}")
                except Exception as e:
                    st.error(f"處理訂單 {order.get('訂單編號','未知')} 時出錯: {str(e)}")
                    continue
        else:
            st.info("目前沒有未完成訂單。")
    except Exception as e:
        st.error(f"載入未完成訂單失敗: {str(e)}")


# ====== 第三頁：「完成訂單」 ======
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
            st.markdown(f"#### 訂單 {order.get('訂單編號','未知')}（金額: ${order.get('金額',0)}）")
            content = order.get("品項內容") or order.get("completed_items") or []
            if isinstance(content, list):
                for it in content:
                    st.text(it)
            elif isinstance(content, str):
                for it in content.split("\n"):
                    st.text(it)
            else:
                st.caption("⚠️ 無品項內容")
            if order.get("備註"):
                st.caption(f"備註：{order['備註']}")
    else:
        st.info("尚無完成訂單。")

