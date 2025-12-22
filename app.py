import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="家庭智能账本", layout="wide")

# --- 1. 状态管理 ---
if "members" not in st.session_state:
    st.session_state.members = ["爸爸", "妈妈", "我"]

# --- 2. 侧边栏：成员管理（优化交互） ---
st.sidebar.title("👥 成员管理")

# 添加成员的表单，提交后自动清空
with st.sidebar.form("add_member_form", clear_on_submit=True):
    new_name = st.text_input("添加新成员", placeholder="输入名字...")
    submit_add = st.form_submit_button("➕ 确认添加")
    if submit_add:
        if new_name and new_name not in st.session_state.members:
            st.session_state.members.append(new_name)
            st.toast(f"✅ 已添加成员: {new_name}")
        elif not new_name:
            st.error("请输入名字")

# 删除成员
if len(st.session_state.members) > 0:
    st.sidebar.markdown("---")
    to_delete = st.sidebar.selectbox("移除成员", ["选择成员..."] + st.session_state.members)
    if st.sidebar.button("🗑️ 确认移除"):
        if to_delete != "选择成员...":
            st.session_state.members.remove(to_delete)
            st.toast(f"⚠️ 已移除成员: {to_delete}")
            st.rerun()

# --- 3. 主界面：录入面板 ---
st.title("🍎 家庭费用分摊")

with st.container(border=True):
    st.subheader("📝 录入新消费")
    c1, c2 = st.columns(2)
    
    with c1:
        item = st.text_input("消费项目", placeholder="例如：晚餐、超市买菜...")
        total_amount = st.number_input("总金额", min_value=0.0, step=0.5, format="%.2f")
    
    with c2:
        date = st.date_input("日期")
        payer = st.selectbox("谁付的钱？", st.session_state.members)

    st.markdown("**💡 谁来分摊？**")
    
    # 使用列布局来放置 Checkbox，更直观
    cols = st.columns(len(st.session_state.members))
    checked_status = {}
    for i, member in enumerate(st.session_state.members):
        with cols[i]:
            checked_status[member] = st.checkbox(member, value=True, key=f"check_{member}")

    # 分摊模式切换
    active_participants = [m for m, checked in checked_status.items() if checked]
    
    split_mode = st.radio(
        "选择分摊方式：",
        ["均分费用", "手动输入每人金额"],
        horizontal=True
    )

    final_shares = {}
    if split_mode == "均分费用":
        if active_participants:
            per_person = total_amount / len(active_participants)
            for m in st.session_state.members:
                final_shares[m] = per_person if checked_status[m] else 0.0
            st.info(f"💡 选中的 {len(active_participants)} 人，每人应付: {per_person:.2f}")
        else:
            st.warning("请至少勾选一位参与人")
    else:
        st.write("请填入各人负责的金额：")
        sc1, sc2, sc3 = st.columns(3)
        for i, m in enumerate(st.session_state.members):
            target_col = [sc1, sc2, sc3][i % 3]
            with target_col:
                val = st.number_input(f"{m} 的金额", min_value=0.0, value=0.0, key=f"input_{m}")
                final_shares[m] = val

    # 校验金额
    total_shared = sum(final_shares.values())
    if split_mode == "手动输入每人金额" and abs(total_shared - total_amount) > 0.01:
        st.error(f"❌ 分摊总和 ({total_shared:.2f}) 与总金额 ({total_amount:.2f}) 不符！")
        allow_submit = False
    else:
        allow_submit = True

    if st.button("💾 保存记录", use_container_width=True, type="primary", disabled=not allow_submit):
        if item and total_amount > 0:
            st.balloons()
            st.success("账单已成功录入！")
            # 此处待接入数据库

# --- 4. UI 视觉升级：卡片式分摊详情 ---
st.markdown("### 📊 本单分摊预览")
if any(v > 0 for v in final_shares.values()):
    # 建立精美的卡片展示区
    card_cols = st.columns(len([v for v in final_shares.values() if v > 0]))
    col_idx = 0
    for name, amt in final_shares.items():
        if amt > 0:
            with card_cols[col_idx]:
                st.markdown(
                    f"""
                    <div style="
                        padding: 20px;
                        border-radius: 10px;
                        background-color: #f0f2f6;
                        border-left: 5px solid {'#ff4b4b' if name == payer else '#00cc96'};
                        text-align: center;
                        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
                    ">
                        <p style="margin:0; color: #555; font-size: 14px;">{name}</p>
                        <h2 style="margin:0; color: #31333F;">${amt:.2f}</h2>
                        <p style="margin:0; font-size: 10px; color: #888;">{'付款人' if name == payer else '参与人'}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                col_idx += 1
