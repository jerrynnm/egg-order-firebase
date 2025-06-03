import streamlit as st
import time
import re
import firebase_db as fdb
from datetime import datetime, date

# ====== 全局 CSS（手機優先） ======
st.markdown("""
<style>
/* 1. 通用：讓分頁置中、字體醒目 */
.stTabs [role="tablist"] {
  justify-content: center !important;
}
.stTabs [role="tab"] {
  font-weight: bold;
  font-size: 18px;
}

/* 2. .center 類別：置中 */
.center {
  text-align: center !important;
}

/* 3. 自訂按鈕：mobile-first 設計，預設使用小尺寸 */
.order-btn-row {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin: 8px 0;
}
.order-btn {
  background: #ff4b4b;
  color: white;
  border: none;
  border-radius: 20px;
  font-size: 12px;
  font-weight: bold;
  padding: 6px 16px;
  min-width: 80px;
  box-shadow: 1px 2px 6px rgba(0,0,0,0.2);
  cursor: pointer;
  transition: opacity 0.2s ease-in-out;
}
.order-btn.delete {
  background: #888888;
}
.order-btn:hover {
  opacity: 0.9;
}

/* 4. 大於 600px（桌機／平板）時，按鈕放大 */
@media (min-width: 600px) {
  .order-btn {
    font-size: 14px;
    padding: 8px 20px;
    min-width: 100px;
    border-radius: 25px;
    box-shadow: 1px 2px 8px rgba(0,0,0,0.2);
  }
  .order-btn-row {
    gap: 14px;
    margin: 12px 0;
  }
}

/* 5. 確保所有原生 stButton 都撐滿容器（如果需要保留其他原生按鈕） */
.stButton>button {
  width: 100% !important;
  margin-top: 6px;
}
</style>
""", unsafe_allow_html=True)


# ====== MENU 資料（不變） ======
MENU = {
    "特價綜合雞蛋糕": 70,
    "內餡雞蛋糕": 50,
    "原味雞蛋糕": 60
}
FLAVORS = ["拉絲起司", "奧利奧 Oreo", "黑糖麻糬"]

# ====== 初始化 Session State ======
if 'temp_order' not in st.session_state:
    st.session_state.temp_order = []
if 'show_popup' not in st.session_state:
    st.session_state.show_popup = False
if 'success_message' not in st.session_state:
    st.session_state.success_message = None


# ====== 幫助函式 ======
def estimate_price(item_text):
    if item_text.startswith("原味雞蛋糕"):
        match = re.search(r"x(\d+)", item_text)
        return MENU["原味雞蛋糕"] * int(match.group(1)) if match else MENU["原味雞蛋糕"]
    return MENU["內餡雞蛋糕"]

def send_temp_order_directly():
    """
    真正送出整筆暫存：寫入 Firebase、清空暫存、顯示成功訊息
    """
    order_id = str(int(time.time() * 1000))[-8:]
    content_list = [o['text'] for o in st.session_state.temp_order]
    total_price = sum(o['price'] for o in st.session_state.temp_order)
    combined_note = ' / '.join([o.get('note', '') for o in st.session_state.temp_order if o.get('note')])
    fdb.append_order(order_id, content_list, total_price, "未完成", combined_note)

    st.session_state.temp_order.clear()
    st.session_state.show_popup = False
    st.session_state.success_message = "✅ 訂單已送出！"


# ====== 建立三分頁 ======
tabs = st.tabs(["暫存", "未完成", "完成"])


# ====== 第一頁：「暫存」 ======
with tabs[0]:
    st.markdown('<div class="center">', unsafe_allow_html=True)
    st.title("選擇餐點")

    # 如果剛剛有送出成功訊息，就顯示
    if st.session_state.get("success_message"):
        st.success(st.session_state.success_message)
        st.session_state.success_message = None

    # 1. 點選菜單按鈕 → 顯示要新增項目的彈窗
    for item in MENU:
        if st.button(item, key=f"menu_button_{item}"):
            st.session_state.selected_item = item
            st.session_state.show_popup = True

    # 2. 彈出「新增」視窗
    if st.session_state.get("show_popup", False):
        item = st.session_state['selected_item']
        st.subheader(f"新增: {item}")

        if item == "原味雞蛋糕":
            qty = st.number_input("份數", min_value=1, max_value=20, value=1, step=1, key="qty")
            note = st.text_input("輸入備註（可空白）", key="note_plain")

            col1, col2 = st.columns(2, gap="small")
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

            col1, col2 = st.columns(2, gap="small")
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

                        # 清空每個 flavor 的 state，避免下次重複
                        for flavor in FLAVORS:
                            st.session_state.pop(f"flavor_{flavor}", None)

                        st.session_state.show_popup = True
                        st.rerun()

    # 3. 列出暫存訂單內容
    st.subheader("暫存訂單顯示區")
    if st.session_state.temp_order:
        for i, o in enumerate(st.session_state.temp_order):
            st.write(f"{i+1}. {o['text']} (${o['price']})")
    else:
        st.info("目前沒有暫存訂單。")
    st.markdown("</div>", unsafe_allow_html=True)

    # 4. 隱藏版的 st.button → 真正負責執行 send / delete 動作
    if 'btn_send_hidden' not in st.session_state:
        st.session_state.btn_send_hidden = False
    if 'btn_del_hidden' not in st.session_state:
        st.session_state.btn_del_hidden = False

    # 隱藏按鈕：按下就觸發真正的函式
    st.button(
        "", 
        key="btn_send_hidden", 
        help="", 
        on_click=send_temp_order_directly
    )
    st.button(
        "", 
        key="btn_del_hidden", 
        help="", 
        on_click=lambda: st.session_state.temp_order.pop() if st.session_state.temp_order else None
    )

    # 5. 真正顯示給使用者看的「紅色送出／灰色刪除暫存」HTML 按鈕
    st.markdown("""
    <div class="order-btn-row">
      <button class="order-btn" 
        onclick="document.querySelector('[data-baseweb=\\"button\\"][data-key=\\"btn_send_hidden\\"]').click();">
        🚀 送出
      </button>
      <button class="order-btn delete" 
        onclick="document.querySelector('[data-baseweb=\\"button\\"][data-key=\\"btn_del_hidden\\"]').click();">
        🗑️ 刪除暫存
      </button>
    </div>
    """, unsafe_allow_html=True)


# ====== 第二頁：「未完成」 ======
with tabs[1]:
    st.title("未完成訂單")
    try:
        unfinished_orders = fdb.fetch_orders("未完成")
        # 計算 hash 看是否要 rerun
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
                        st.error(f"訂單資料不完整: {order.get('訂單編號', '未知')}")
                        continue

                    st.subheader(f"訂單 {order['訂單編號']}（金額: ${order['金額']}）")
                    item_list = order["品項內容"] if isinstance(order["品項內容"], list) else order["品項內容"].split("\n")
                    completed_items = order.get("completed_items", [])
                    remaining_items = [it for it in item_list if it not in completed_items]

                    # 每筆未完成品項用 checkbox
                    for i, it in enumerate(remaining_items):
                        key_cb = f"{order['訂單編號']}_cb_{i}"
                        if key_cb not in st.session_state:
                            st.session_state[key_cb] = False
                        checked = st.checkbox(f"\U0001F7E0 {it}", key=key_cb)
                        if checked:
                            # 把它暫時標記到一個暫存 list，待按下「完成」才一併處理
                            if 'to_complete' not in st.session_state:
                                st.session_state.to_complete = {}
                            if order['訂單編號'] not in st.session_state.to_complete:
                                st.session_state.to_complete[order['訂單編號']] = []
                            if it not in st.session_state.to_complete[order['訂單編號']]:
                                st.session_state.to_complete[order['訂單編號']].append(it)

                    st.markdown("---")
                    col1, col2 = st.columns(2, gap="small")
                    with col1:
                        if st.button("✅ 完成", key=f"done_{order['訂單編號']}"):
                            try:
                                checked = st.session_state.to_complete.get(order['訂單編號'], [])
                                if checked:
                                    # 計算該訂單裡面勾選品項的價格
                                    completed_price = sum(estimate_price(i) for i in checked)
                                    fdb.update_completed_items(order['訂單編號'], checked, completed_price)

                                    # 如果還有剩下未完成的，更新內容；否則標記整筆訂單完成
                                    new_remaining = [it for it in remaining_items if it not in checked]
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
                                st.error(f"刪除訂單時出錯: {str(e)}")
                except Exception as e:
                    st.error(f"處理訂單 {order.get('訂單編號','未知')} 時出錯: {str(e)}")
                    continue
        else:
            st.info("目前沒有未完成訂單。")
    except Exception as e:
        st.error(f"載入未完成訂單失敗: {str(e)}")


# ====== 第三頁：「完成」 ======
with tabs[2]:
    st.title("完成訂單")

    # 自動刪除非今天（只留今日完成訂單）
    all_finished = fdb.fetch_orders("完成")
    today_str = date.today().isoformat()
    for order in all_finished:
        ts = order.get("timestamp")
        if ts:
            order_date = datetime.fromtimestamp(ts).date().isoformat()
            if order_date != today_str:
                fdb.delete_order_by_id(order['訂單編號'])

    # 重新讀取並顯示
    finished_orders = fdb.fetch_orders("完成")
    finished_orders = sorted(finished_orders, key=lambda x: x.get("timestamp", 0))
    total = sum(o.get('金額', 0) for o in finished_orders)
    st.subheader(f"總營業額：${total}")

    if finished_orders:
        for order in finished_orders:
            st.markdown(f"#### 訂單 {order.get('訂單編號','未知')}（金額: ${order.get('金額',0)}）")
            content = order.get('品項內容') or order.get('completed_items') or []
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
