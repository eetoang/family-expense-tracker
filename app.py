import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import ast

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="家庭智能云账本",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. 连接 Google Sheets ---
# 请确保 Secrets 中已配置 [connections.gsheets]
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # ttl=0 保证实时性
        return conn.read(ttl=0)
    except Exception as e:
        # 即使连接失败也返回空表，防止程序崩溃
        return pd.DataFrame(columns=["日期", "项目", "总金额", "付款人", "分摊详情"])

# --- 3. 成员管理状态 ---
if "members" not in st.session_state:
    st.session_state.members = ["爸爸", "妈妈", "我", "妹妹"]

# --- 4. 侧边栏：成员管理 (修复 Log 中的报错) ---
st.sidebar.title("👥 成员管理")

# 修正：在 st.sidebar.form 块内，直接使用 st.text_input 而不是 st.sidebar.text_input
with st.sidebar.form("add_member_form", clear_on_submit=True):
    new_name = st.text_input("添加新成员姓名") 
    submit_add = st.form_submit_button("➕ 确认添加")
    
    if submit_add:
        if new_name and new_name not in st.session_state.members:
            st.session_state.members.append(new_name)
            st.toast(f"✅ 已添加: {new_name}")
            st.rerun()

# --- 5. 主界面：录入面板 ---
st.title("🍎 家庭费用分摊助手")

split_mode = st.radio(
    "选择分摊方式：", 
    ["均分费用", "手动输入每人金额"], 
    horizontal=True
)

with st.form("main_expense_form", clear_on_submit=True):
    st.subheader("📝 录入新消费")
    col1, col2 = st.columns(2)
    
    with col1:
        item = st.text_input("消费项目", placeholder="例如：晚餐")
        total_amount = st.number_input("总金额", min_value=0.0, step=0.1, value=None, placeholder="请输入总金额")
    
    with col2:
        date = st.date_input("日期", value=datetime.now())
        payer = st.selectbox("谁先付钱？", st.session_state.members)

    st.markdown("**💡 参与人 (谁需要平摊？)**")
    p_cols = st.columns(len(st.session_state.members))
    checked_status = {}
    for i, m in enumerate(st.session_state.members):
        checked_status[m] = p_cols[i].checkbox(m, value=True, key=f"check_{m}")

    manual_shares = {}
    if split_mode == "手动输入每人金额":
        st.markdown("---")
        m_cols = st.columns(3)
        for i, m in enumerate(st.session_state.members):
            manual_shares[m] = m_cols[i % 3].number_input(
                f"{m} 的金额", min_value=0.0, value=None, placeholder="0.00", key=f"input_{m}"
            )

    submit_btn = st.form_submit_button("💾 保存并同步到云端", use_container_width=True, type="primary")

    if submit_btn:
        if not item or total_amount is None:
            st.error("⚠️ 请输入项目和金额")
        else:
            final_shares = {}
            active_p = [m for m, v in checked_status.items() if v]
            
            if split_mode == "均分费用":
                if active_p:
                    amt = total_amount / len(active_p)
                    final_shares = {m: (amt if checked_status[m] else 0.0) for m in st.session_state.members}
            else:
                final_shares = {m: (manual_shares.get(m) or 0.0) for m in st.session_state.members}

            if abs(sum(final_shares.values()) - total_amount) > 0.1:
                st.error("❌ 金额总数不匹配")
            else:
                # 写入云端
                df_existing = load_data()
                new_row = pd.DataFrame([{
                    "日期": date.strftime("%Y-%m-%d"),
                    "项目": item,
                    "总金额": total_amount,
                    "付款人": payer,
                    "分摊详情": str(final_shares)
                }])
                updated_df = pd.concat([df_existing, new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.balloons()
                st.rerun()

# --- 6. 历史记录与结算 ---
df = load_data()
if not df.empty:
    st.divider()
    st.subheader("📋 历史消费记录")
    
    balances = {m: 0.0 for m in st.session_state.members}
    
    for idx, row in df[::-1].iterrows():
        try:
            shares = ast.literal_eval(row["分摊详情"])
            balances[row["付款人"]] += row["总金额"]
            for n, a in shares.items():
                if n in balances: balances[n] -= a

            with st.expander(f"{row['日期']} - {row['项目']} (${row['总金额']:.2f})"):
                st.markdown(f"**付款人：** <span style='color:#ff4b4b'>{row['付款人']}</span>", unsafe_allow_html=True)
                disp_shares = {k: v for k, v in shares.items() if v > 0}
                cols = st.columns(len(disp_shares) if disp_shares else 1)
                for i, (n, a) in enumerate(disp_shares.items()):
                    with cols[i]:
                        st.markdown(f"""<div style="padding:10px; border-radius:8px; background-color:#f8f9fa; border:1px solid #eee; border-top:4px solid #00cc96; text-align:center;">
                            <div style="color:#666; font-size:0.8rem;">{n}</div><div style="color:#222; font-weight:bold;">${a:.2f}</div></div>""", unsafe_allow_html=True)
        except: continue

    st.divider()
    st.subheader("⚖️ 最终结算")
    debtors = [[m, abs(b)] for m, b in balances.items() if b < -0.01]
    creditors = [[m, b] for m, b in balances.items() if b > 0.01]
    
    if not debtors and not creditors:
        st.info("🎉 账目已结清")
    else:
        for d in debtors:
            for c in creditors:
                if d[1] <= 0: break
                if c[1] <= 0: continue
                s = min(d[1], c[1])
                st.warning(f"👉 **{d[0]}** 应支付给 **{c[0]}** : **${s:.2f}**")
                d[1] -= s
                c[1] -= s
