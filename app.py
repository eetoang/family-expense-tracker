import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="家庭智能账本", layout="wide", initial_sidebar_state="collapsed")

# --- 1. 初始化状态 ---
if "members" not in st.session_state:
    st.session_state.members = ["爸爸", "妈妈", "我"]
if "all_records" not in st.session_state:
    st.session_state.all_records = []

# --- 2. 侧边栏 (管理功能) ---
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

# --- 3. 主界面 ---
st.title("🍎 家庭费用分摊")

# 模式选择移到外面以确保实时刷新
split_mode = st.radio("选择分摊方式：", ["均分费用", "手动输入每人金额"], horizontal=True)

with st.form("main_expense_form", clear_on_submit=True):
    st.subheader("📝 录入新消费")
    c1, c2 = st.columns(2)
    with c1:
        item = st.text_input("消费项目", placeholder="例如：晚餐、超市买菜...")
        # 使用 value=None 配合 placeholder 实现“点击即输入”
        total_amount = st.number_input("总金额", min_value=0.0, step=0.1, value=None, placeholder="0.00")
    with c2:
        date = st.date_input("日期", value=datetime.now())
        payer = st.selectbox("谁先付钱？", st.session_state.members)

    st.markdown("**💡 参与人 (谁需要付钱？)**")
    p_cols = st.columns(len(st.session_state.members))
    checked_status = {}
    for i, m in enumerate(st.session_state.members):
        checked_status[m] = p_cols[i].checkbox(m, value=True, key=f"form_check_{m}")

    # 手动输入区域
    manual_shares = {}
    if split_mode == "手动输入每人金额":
        st.markdown("---")
        st.info("请在下方输入各人对应的金额：")
        mc = st.columns(3)
        for i, m in enumerate(st.session_state.members):
            manual_shares[m] = mc[i%3].number_input(f"{m} 的金额", min_value=0.0, value=None, placeholder="0.00", key=f"manual_{m}")

    submit_btn = st.form_submit_button("💾 保存记录", use_container_width=True, type="primary")

    if submit_btn:
        if not item or total_amount is None:
            st.error("请输入项目和金额")
        else:
            final_shares = {}
            active_p = [m for m, checked in checked_status.items() if checked]
            
            if split_mode == "均分费用":
                per_person = total_amount / len(active_p) if active_p else 0
                for m in st.session_state.members:
                    final_shares[m] = per_person if checked_status[m] else 0.0
            else:
                for m in st.session_state.members:
                    val = manual_shares.get(m)
                    final_shares[m] = val if val is not None else 0.0

            if abs(sum(final_shares.values()) - total_amount) > 0.01:
                st.error(f"分摊总和 (${sum(final_shares.values()):.2f}) 不等于总金额 (${total_amount:.2f})")
            else:
                record = {
                    "日期": date.strftime("%Y-%m-%d"),
                    "项目": item,
                    "总金额": total_amount,
                    "付款人": payer,
                    "分摊详情": final_shares
                }
                st.session_state.all_records.insert(0, record)
                st.rerun()

# --- 4. 历史记录 (浅色卡片 UI) ---
st.divider()
st.subheader("📋 历史消费记录")

if not st.session_state.all_records:
    st.info("目前没有记录")
else:
    for idx, rec in enumerate(st.session_state.all_records):
        with st.expander(f"{rec['日期']} - {rec['项目']} (${rec['总金额']:.2f})", expanded=(idx==0)):
            st.markdown(f"**付款人：** <span style='color:#ff4b4b'>{rec['付款人']}</span>", unsafe_allow_html=True)
            
            # 过滤掉金额为 0 的人，只显示有参与的人
            display_shares = {k: v for k, v in rec['分摊详情'].items() if v > 0}
            cols = st.columns(max(len(display_shares), 1))
            
            for i, (name, amt) in enumerate(display_shares.items()):
                with cols[i]:
                    st.markdown(f"""
                        <div style="
                            padding: 12px; 
                            border-radius: 8px; 
                            background-color: #f8f9fa; 
                            border: 1px solid #eee;
                            border-top: 4px solid #00cc96;
                            text-align: center;
                        ">
                            <div style="color: #666; font-size: 0.85rem; margin-bottom: 4px;">{name}</div>
                            <div style="color: #222; font-weight: bold; font-size: 1.1rem;">${amt:.2f}</div>
                        </div>
                    """, unsafe_allow_html=True)

# --- 5. 结算统计 ---
if st.session_state.all_records:
    st.divider()
    st.subheader("⚖️ 最终结算")
    # 此处省略结算逻辑代码（同前一版本）...
