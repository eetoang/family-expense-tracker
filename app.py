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
# 请确保已在 Streamlit Secrets 中配置连接信息
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # ttl=0 确保每次刷新都从云端抓取最新数据
        return conn.read(ttl=0)
    except:
        return pd.DataFrame(columns=["日期", "项目", "总金额", "付款人", "分摊详情"])

# --- 3. 成员管理 (Session State) ---
if "members" not in st.session_state:
    st.session_state.members = ["爸爸", "妈妈", "我", "妹妹"]

# --- 4. 侧边栏：成员与设置 ---
st.sidebar.title("👥 成员管理")
with st.sidebar.form("add_member_form", clear_on_submit=True):
    new_name = st.sidebar.text_input("添加新成员")
    if st.sidebar.form_submit_button("➕ 确认添加"):
        if new_name and new_name not in st.session_state.members:
            st.session_state.members.append(new_name)
            st.toast(f"已添加: {new_name}")
            st.rerun()

if st.sidebar.button("🗑️ 清空账目 (慎用)"):
    # 这会清空本地显示，如需删除云端请手动操作表格
    st.warning("如需彻底清空，请直接在 Google Sheets 表格中删除行。")

# --- 5. 主界面：录入面板 ---
st.title("🍎 家庭费用分摊助手")

# 模式切换放在表单外以确保 UI 实时响应
split_mode = st.radio(
    "选择分摊方式：", 
    ["均分费用", "手动输入每人金额"], 
    horizontal=True
)

with st.form("main_expense_form", clear_on_submit=True):
    st.subheader("📝 录入新消费")
    col1, col2 = st.columns(2)
    
    with col1:
        item = st.text_input("消费项目", placeholder="例如：晚餐、超市、电影...")
        # value=None 配合 placeholder 实现“点击即可输入数字”，无需删除 0.00
        total_amount = st.number_input("总金额", min_value=0.0, step=0.1, value=None, placeholder="请输入总金额")
    
    with col2:
        date = st.date_input("日期", value=datetime.now())
        payer = st.selectbox("谁先付钱？", st.session_state.members)

    st.markdown("**💡 谁参与了这次消费？**")
    p_cols = st.columns(len(st.session_state.members))
    checked_status = {}
    for i, m in enumerate(st.session_state.members):
        checked_status[m] = p_cols[i].checkbox(m, value=True, key=f"check_{m}")

    # 手动输入金额逻辑
    manual_shares = {}
    if split_mode == "手动输入每人金额":
        st.markdown("---")
        st.info("请在下方输入各人对应的金额：")
        m_cols = st.columns(3)
        for i, m in enumerate(st.session_state.members):
            manual_shares[m] = m_cols[i % 3].number_input(
                f"{m} 的金额", 
                min_value=0.0, 
                value=None, 
                placeholder="0.00", 
                key=f"input_{m}"
            )

    submit_btn = st.form_submit_button("💾 保存并同步到云端", use_container_width=True, type="primary")

    if submit_btn:
        if not item or total_amount is None:
            st.error("⚠️ 请确保已填写‘消费项目’和‘总金额’！")
        else:
            final_shares = {}
            active_p = [m for m, checked in checked_status.items() if checked]
            
            if split_mode == "均分费用":
                per_person = total_amount / len(active_p) if active_p else 0
                final_shares = {m: (per_person if checked_status[m] else 0.0) for m in st.session_state.members}
            else:
                final_shares = {m: (manual_shares.get(m) if manual_shares.get(m) is not None else 0.0) for m in st.session_state.members}

            # 金额校验
            if abs(sum(final_shares.values()) - total_amount) > 0.01:
                st.error(f"❌ 错误：分摊总和 (${sum(final_shares.values()):.2f}) 与总金额 (${total_amount:.2f}) 不符！")
            else:
                # 同步到 Google Sheets
                existing_df = load_data()
                new_data = pd.DataFrame([{
                    "日期": date.strftime("%Y-%m-%d"),
                    "项目": item,
                    "总金额": total_amount,
                    "付款人": payer,
                    "分摊详情": str(final_shares)
                }])
                updated_df = pd.concat([existing_df, new_data], ignore_index=True)
                conn.update(data=updated_df)
                st.balloons()
                st.success("✅ 账单已同步至云端！")
                st.rerun()

# --- 6. 历史记录与结算展示 ---
df = load_data()

if not df.empty:
    st.divider()
    st.subheader("📋 历史消费记录")
    
    # 核心计算逻辑：结算余额
    balances = {m: 0.0 for m in st.session_state.members}

    # 从后往前显示（最新的在最上面）
    for idx, row in df[::-1].iterrows():
        try:
            # 将存储的字符串解析回字典
            shares = ast.literal_eval(row["分摊详情"])
            
            # 累加结算数据
            balances[row["付款人"]] += row["总金额"]
            for name, amt in shares.items():
                balances[name] -= amt

            # UI 卡片展示
            with st.expander(f"{row['日期']} - {row['项目']} (${row['总金额']:.2f})", expanded=(idx == len(df)-1)):
                st.markdown(f"**付款人：** <span style='color:#ff4b4b'>{row['付款人']}</span>", unsafe_allow_html=True)
                
                # 只显示金额 > 0 的参与者
                active_shares = {k: v for k, v in shares.items() if v > 0}
                cols = st.columns(len(active_shares) if active_shares else 1)
                for i, (n, a) in enumerate(active_shares.items()):
                    with cols[i]:
                        st.markdown(f"""
                            <div style="padding:10px; border-radius:8px; background-color:#f8f9fa; border:1px solid #eee; border-top:4px solid #00cc96; text-align:center;">
                                <div style="color:#666; font-size:0.8rem;">{n}</div>
                                <div style="color:#222; font-weight:bold; font-size:1.1rem;">${a:.2f}</div>
                            </div>
                        """, unsafe_allow_html=True)
        except Exception as e:
            continue

    # --- 7. 最终结算方案 ---
    st.divider()
    st.subheader("⚖️ 最终结算 (谁该给谁钱)")
    
    debtors = [[m, abs(b)] for m, b in balances.items() if b < -0.01]
    creditors = [[m, b] for m, b in balances.items() if b > 0.01]

    if not debtors and not creditors:
        st.info("🎉 账目已全部结清！")
    else:
        # 贪心算法计算最简转账
        for d in debtors:
            for c in creditors:
                if d[1] <= 0: break
                if c[1] <= 0: continue
                settle_amt = min(d[1], c[1])
                st.warning(f"👉 **{d[0]}** 应支付给 **{c[0]}** ： **${settle_amt:.2f}**")
                d[1] -= settle_amt
                c[1] -= settle_amt
else:
    st.info("💡 目前云端没有记录，请在上方录入第一笔消费。")
