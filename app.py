import streamlit as st
import time
import re
import json
import hashlib
import firebase_db as fdb
from datetime import datetime, date

# ====== 1. 在最上方先做 Session State 的初始化 ======
#    這裡把所有之後會用到的 key（temp_order、show_popup、success_message、
#    btn_send_hidden、btn_del_hidden）都先用 setdefault 建立好，
#    避免之後在 widget 渲染階段修改它們而出錯。

st.session_state.setdefault("temp_order", [])
st.session_state.setdefault("show_popup", False)
st.session_state.setdefault("success_message", None)

# 隱藏版按鈕的 key 也預先放進 session_state
# 這樣後面再做 st.button(key="btn_send_hidden")、st.button(key="btn_del_hidden") 時
# 不會因為「在渲染階段修改 session_state」而拋出錯誤。
st.session_state.setdefault("btn_send_hidden", False)
st.session_state.setdefault("btn_del_hidden", False)


# ====== 2. 定義真正要執行的 Callback 函式 ======
def _send_callback():
    """
    每當使用者點擊隱藏版的 btn_send_hidden 按鈕，就會執行此函式：
    將暫存的訂單寫入 Firebase，然後清空暫存列表，顯示成功訊息。
    """
    order_id = str(int(time.time() * 1000))[-8:]
    content_list = [o["text"] for o in st.session_state.temp_order]
    total_price = sum(o["price"] for o in st.session_state.temp_order)
    combined_note = " / ".join([o.get("note", "") for o in st.session_state.temp_order if o.get("note")])
    # 寫進 Firebase
    fdb.append_order(order_id, content_list, total_price, "未完成", combined_note)

    # 清空暫存
    st.session_state.temp_order.clear()
    st.session_state.show_popup = False
    # 顯示綠色成功訊息
    st.session_state.success_message = "✅ 訂單已送出！"

def _del_callback():
    """
    每當使用者點擊隱藏版的 btn_del_hidden 按鈕，就會執行此函式：
    如果暫存有東西，就移除最後一筆。
    """
    if st.session_state.temp_order:
        st.session_state.temp_order.pop()


# ====== 3. 建立「隱藏版」的 st.button，並綁定剛剛定義的 Callback ======
#    這兩顆按鈕在畫面上不顯示文字，但我們會在 HTML 裡用 JavaScript 去觸發它們，
#    從而把訂單真正「送出」或「刪除最後一筆」。
st.button(
    label="", 
    key="btn_send_hidden", 
    on_click=_send_callback
)
st.button(
    label="", 
    key="btn_del_hidden", 
    on_click=_del_callback
)


# ====== 4. 定義其他輔助函式 ======
MENU = {
    "特價綜合雞蛋糕": 70,
    "內餡雞蛋糕": 50,
    "原味雞蛋糕": 60
}
FLAVORS = ["拉絲起司", "奧利奧 Oreo", "黑糖麻糬"]

def estimate_price(item_text: str) -> int:
    """
    根據品項名稱計算金額。例如：原味雞蛋糕 x3 => 60 * 3
    內餡跟特價綜合不限數量，一律算一組價格。
    """
    if item_text.startswith("原味雞蛋糕"):
        m = re.search(r"x(\d+)", item_text)
        return MENU["原味雞蛋糕"] * int(m.group(1)) if m else MENU["原味雞蛋糕"]
    return MENU["內餡雞蛋糕"]


# ====== 5. 全局 CSS（手機優先，並強制「不換行」按鈕） ======
#    這段 CSS 必須在「任何 st.markdown(...button HTML...)」之前載入，
#    才能讓後續的 UI 正確套用樣式。
st.markdown("""
<style>
/* 分頁標籤置中、字體粗體且放大 */
.stTabs [role="tablist"] {
  justify-content: center !important;
}
.stTabs [role="tab"] {
  font-weight: bold;
  font-size: 18px;
}

/* .center：用來包最上方的標題置中 */
.center {
  text-align: center !important;
}

/* 強制按鈕永遠並排、不換行 */
.order-btn-row {
  display: flex;
  flex-wrap: nowrap;     /* 不換行 */
  justify-content: center;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
  margin-bottom: 8px;
}
/* HTML 按鈕的預設樣式（手機優先） */
.order-btn {
  background-color: #ff4b4b;
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
  background-color: #888888;
}
.order-btn:hover {
  opacity: 0.9;
}

/* 大螢幕 (≥600px) 時，把按鈕放大 */
@media (min-width: 600px) {
  .order-btn {
    font-size: 14px !important;
    padding: 8px 20px !important;
    border-radius: 25px !important;
    min-width: 100px !important;
    box-shadow: 1px 2px 8px rgba(0,0,0,0.2) !important;
  }
  .order-btn-row {
    gap: 14px;
    margin: 12px 0;
  }
}

/* 如果在其他地方還有保留原生 st.button，想讓它們撐滿寬度可保留這段 */
.stButton > button {
  width: 100% !important;
  margin-top: 6px;
}
</style>
""", unsafe_allow_html=True)


# ====== 6. 開始建立分頁 ======
tabs = st.tabs(["暫存", "未完成", "完成"])


# ====== 第一頁：「暫存」 ======
with tabs[0]:
    # 先把標題包成 center div
    st.markdown('<div class="center">', unsafe_allow_html=True)
    st.title("選擇餐點")

    # 如果剛剛有成功送出的訊息，就顯示出來
    if st.session_state.get("success_message"):
        st.success(st.session_state.success_message)
        # 顯示完後立即清空，避免重複顯示
        st.session_state.success_message = None

    # 1. 菜單部分：列出三種雞蛋糕，按下去就開彈窗
    for item in MENU:
        if st.button(item, key=f"menu_button_{item}"):
            st.session_state.selected_item = item
            st.session_state.show_popup = True

    # 2. 彈窗邏輯：原味 vs 內餡／綜合
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
                    _send_callback()
            with col2:
                if st.button("確認新增", key="confirm_plain"):
                    txt = f"{item} x{qty}"
                    if note:
                        txt += f" - 備註: {note}"
                    st.session_state.temp_order.append({"text": txt, "price": MENU[item] * qty, "note": note})
                    st.session_state.show_popup = False

        else:
            # 內餡或綜合雞蛋糕：一組 3 顆，每種口味可選 0~3，但總和 =3
            flavor_counts = {}
            current_vals = {flavor: st.session_state.get(f"flavor_{flavor}", 0) for flavor in FLAVORS}
            total_selected = sum(current_vals.values())
            remaining_total = 3 - total_selected

            cols = st.columns(len(FLAVORS))
            for i, flavor in enumerate(FLAVORS):
                curr = current_vals[flavor]
                remain_for_this = 3 - (total_selected - curr)
                adjusted = min(curr, remain_for_this)
                flavor_counts[flavor] = cols[i].number_input(
                    label=flavor,
                    min_value=0,
                    max_value=remain_for_this,
                    value=adjusted,
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
                        flavor_txt = ", ".join(f"{k}x{v}" for k, v in flavor_counts.items() if v > 0)
                        if item == "特價綜合雞蛋糕":
                            # 特價綜合雞蛋糕本身包含原味 3 顆
                            flavor_txt += ", 原味x3"
                        txt = f"{item} {flavor_txt}"
                        if note:
                            txt += f" - 備註: {note}"
                        st.session_state.temp_order.append({"text": txt, "price": MENU[item], "note": note})
                        _send_callback()
            with col2:
                if st.button("確認新增", key="confirm_filled"):
                    if total_after != 3:
                        st.warning("必須選滿3顆！")
                    else:
                        flavor_txt = ", ".join(f"{k}x{v}" for k, v in flavor_counts.items() if v > 0)
                        if item == "特價綜合雞蛋糕":
                            flavor_txt += ", 原味x3"
                        txt = f"{item} {flavor_txt}"
                        if note:
                            txt += f" - 備註: {note}"
                        st.session_state.temp_order.append({"text": txt, "price": MENU[item], "note": note})
                        # 新增完畢後，清除各 flavor session state
                        for f in FLAVORS:
                            st.session_state.pop(f"flavor_{f}", None)
                        st.session_state.show_popup = True
                        st.rerun()

    # 3. 列出「暫存訂單」內容
    st.subheader("暫存訂單顯示區")
    if st.session_state.temp_order:
        for idx, o in enumerate(st.session_state.temp_order):
            st.write(f"{idx+1}. {o['text']} (${o['price']})")
    else:
        st.info("目前沒有暫存訂單。")
    st.markdown("</div>", unsafe_allow_html=True)

    # 4. 正式顯示給使用者看的「紅色送出」和「灰色刪除暫存」按鈕
    #    透過 onclick 去觸發最上方的隱藏版 st.button (key="btn_send_hidden" 或 "btn_del_hidden")
    st.markdown("""
    <div class="order-btn-row">
      <!-- 紅色：送出 -->
      <button
        onclick="document.querySelector('[data-baseweb=\\"button\\"][data-key=\\"btn_send_hidden\\"]').click();"
        class="order-btn">
        🚀 送出
      </button>

      <!-- 灰色：刪除暫存 -->
      <button
        onclick="document.querySelector('[data-baseweb=\\"button\\"][data-key=\\"btn_del_hidden\\"]').click();"
        class="order-btn delete">
        🗑️ 刪除暫存
      </button>
    </div>
    """, unsafe_allow_html=True)


# ====== 第二頁：「未完成訂單」 ======
with tabs[1]:
    st.title("未完成訂單")
    try:
        unfinished_orders = fdb.fetch_orders("未完成")
        # 計算 hash，若資料有改變就 rerun 一次
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

                    # 勾選尚未完成的品項
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
                    col1, col2 = st.columns(2, gap="small")
                    with col1:
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
                    with col2:
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

    # 自動刪除非今天的完成訂單，只保留今天的
    all_finished = fdb.fetch_orders("完成")
    today_str = date.today().isoformat()
    for order in all_finished:
        ts = order.get("timestamp")
        if ts:
            order_date = datetime.fromtimestamp(ts).date().isoformat()
            if order_date != today_str:
                fdb.delete_order_by_id(order["訂單編號"])

    # 重新抓取並顯示
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

