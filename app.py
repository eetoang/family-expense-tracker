import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="家庭智能账本", layout="wide")

# --- 1. 初始化状态 (防止刷新后记录消失) ---
if "members" not in st.session_state:
    st.session_state.members = ["爸爸", "妈妈", "我"]
if "all_records" not in st.session_state:
    st.session_state.all_records = []

# --- 2. 侧边栏：成员管理 ---
st.sidebar.title("👥 成员管理")
with st.sidebar.form("add_member", clear_on_submit=True):
    new_name = st.text_input("添加新成员")
    if st.form_submit_button("➕ 添加"):
        if new_name and new_name not in st.session_state.members:
            st.session_state.members.append(new_name)
            st.rerun()

if st.sidebar.button("🗑️ 清空所有账目"):
    st.session_state.all_records = []
    st.rerun()

# --- 3. 主界面：录入面板 ---
st.title("🍎 家庭费用分摊")

# 使用表单并开启提交后自动清空功能
with st.form("main_expense_form", clear_on_submit=True):
    st.subheader("📝 录入新消费")
    c1, c2 = st.columns(2)
    with c1:
        item = st.text_input("消费项目", placeholder="例如：晚餐、超市买菜...")
        total_amount = st.number_input("总金额", min_value=0.0, step=0.1, value=0.0)
    with c2:
        date = st.date_input("日期", value=datetime.now())
        payer = st.selectbox("谁先付钱？", st.session_state.members)

    st.markdown("**💡 参与人 (勾选参与者)**")
    p_cols = st.columns(len(st.session_state.members))
    checked_status = {}
    for i, m in enumerate(st.session_state.members):
        checked_status[m] = p_cols[i].checkbox(m, value=True, key=f"form_check_{m}")

    split_mode = st.radio("分摊方式：", ["均分费用", "手动输入每人金额"], horizontal=True)
    
    # 临时存储手动输入的金额
    manual_shares = {}
    if split_mode == "手动输入每人金额":
        st.info("提示：直接点击框内输入数字即可")
        mc = st.columns(3)
        for i, m in enumerate(st.session_state.members):
            # 将 value 设为 None，这样输入框会显示 0 并在点击时更易覆盖
            manual_shares[m] = mc[i%3].number_input(f"{m} 的部分", min_value=0.0, step=0.1, key=f"manual_{m}")

    # 提交按钮
    submit_btn = st.form_submit_button("💾 保存记录", use_container_width=True, type="primary")

    if submit_btn:
        if not item or total_amount <= 0:
            st.error("请输入完整的项目名称和金额！")
        else:
            # 计算最终分摊
            final_shares = {}
            active_p = [m for m, checked in checked_status.items() if checked]
            
            if split_mode == "均分费用":
                per_person = total_amount / len(active_p) if active_p else 0
                for m in st.session_state.members:
                    final_shares[m] = per_person if checked_status[m] else 0.0
            else:
                final_shares = manual_shares

            # 验证金额是否匹配
            if abs(sum(final_shares.values()) - total_amount) > 0.01:
                st.error("分摊总额与总金额不符，保存失败！")
            else:
                # 存入 Session State
                record = {
                    "日期": date.strftime("%Y-%m-%d"),
                    "项目": item,
                    "总金额": total_amount,
                    "付款人": payer,
                    "分摊详情": final_shares
                }
                st.session_state.all_records.insert(0, record) # 新记录排在前面
                st.balloons()
                st.rerun() # 强制刷新以清空表单并显示新数据

# --- 4. 历史记录展示 (持续显示) ---
st.divider()
st.subheader("📋 历史消费记录")

if not st.session_state.all_records:
    st.info("尚无记录")
else:
    for idx, rec in enumerate(st.session_state.all_records):
        with st.expander(f"{rec['日期']} - {rec['项目']} (${rec['总金额']})", expanded=(idx==0)):
            st.write(f"**付款人:** {rec['付款人']}")
            # 卡片式 UI
            shares = rec['分摊详情']
            cols = st.columns(len([v for v in shares.values() if v > 0]))
            c_idx = 0
            for name, amt in shares.items():
                if amt > 0:
                    with cols[c_idx]:
                        st.markdown(f"""
                            <div style="padding:10px; border-radius:5px; background-color:#f0f2f6; border-left:4px solid #00cc96; text-align:center;">
                                <small>{name}</small><br><b>${amt:.2f}</b>
                            </div>
                        """, unsafe_allow_html=True)
                    c_idx += 1

# --- 5. 最终结算汇总 ---
st.divider()
st.subheader("⚖️ 最终清算 (谁该给谁钱)")
if st.session_state.all_records:
    balances = {m: 0.0 for m in st.session_state.members}
    for rec in st.session_state.all_records:
        balances[rec['付款人']] += rec['总金额']
        for name, amt in rec['分摊详情'].items():
            balances[name] -= amt
    
    # 简易显示
    debtors = [[m, abs(b)] for m, b in balances.items() if b < -0.01]
    creditors = [[m, b] for m, b in balances.items() if b > 0.01]
    
    for d in debtors:
        for c in creditors:
            if d[1] <= 0: break
            if c[1] <= 0: continue
            settle = min(d[1], c[1])
            st.warning(f"👉 **{d[0]}** 应支付给 **{c[0]}**: **${settle:.2f}**")
            d[1] -= settle
            c[1] -= settle
