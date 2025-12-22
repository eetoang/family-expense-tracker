import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import ast  # 用于处理存储在表格里的字典字符串

st.set_page_config(page_title="家庭智能账本", layout="wide")

# --- 1. 连接 Google Sheets ---
# 请确保已在 Streamlit Cloud 的 Secrets 中配置了 spreadsheet 链接
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # ttl="0" 确保每次都读取最新数据，不使用缓存
        return conn.read(ttl="0")
    except:
        return pd.DataFrame(columns=["日期", "项目", "总金额", "付款人", "分摊详情"])

# --- 2. 初始化成员列表 ---
# 建议：如果成员固定，可以直接写死；如果需动态，可从另一个工作表读取
if "members" not in st.session_state:
    st.session_state.members = ["爸爸", "妈妈", "我", "妹妹"]

# --- 3. 录入面板 ---
st.title("🍎 家庭云账本")

split_mode = st.radio("选择分摊方式：", ["均分费用", "手动输入每人金额"], horizontal=True)

with st.form("main_form", clear_on_submit=True):
    st.subheader("📝 录入新消费")
    c1, c2 = st.columns(2)
    with c1:
        item = st.text_input("消费项目", placeholder="例如：晚餐")
        total_amount = st.number_input("总金额", min_value=0.0, step=0.1, value=None, placeholder="0.00")
    with c2:
        date = st.date_input("日期", value=datetime.now())
        payer = st.selectbox("谁先付钱？", st.session_state.members)

    st.markdown("**💡 参与人**")
    p_cols = st.columns(len(st.session_state.members))
    checked_status = {m: p_cols[i].checkbox(m, value=True) for i, m in enumerate(st.session_state.members)}

    manual_shares = {}
    if split_mode == "手动输入每人金额":
        st.markdown("---")
        mc = st.columns(3)
        for i, m in enumerate(st.session_state.members):
            manual_shares[m] = mc[i%3].number_input(f"{m} 的部分", min_value=0.0, value=None, placeholder="0.00")

    if st.form_submit_button("💾 保存并同步到云端", use_container_width=True, type="primary"):
        if item and total_amount:
            # 计算分摊
            final_shares = {}
            active_p = [m for m, checked in checked_status.items() if checked]
            if split_mode == "均分费用":
                per_person = total_amount / len(active_p) if active_p else 0
                final_shares = {m: (per_person if checked_status[m] else 0.0) for m in st.session_state.members}
            else:
                final_shares = {m: (manual_shares.get(m) if manual_shares.get(m) else 0.0) for m in st.session_state.members}

            if abs(sum(final_shares.values()) - total_amount) < 0.1:
                # 写入云端
                existing_df = load_data()
                new_row = pd.DataFrame([{
                    "日期": date.strftime("%Y-%m-%d"),
                    "项目": item,
                    "总金额": total_amount,
                    "付款人": payer,
                    "分摊详情": str(final_shares) # 字典转为字符串保存
                }])
                updated_df = pd.concat([existing_df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.success("云端同步成功！")
                st.rerun()
            else:
                st.error("金额总数对不上，请检查。")

# --- 4. 历史记录与结算逻辑 ---
df = load_data()

if not df.empty:
    st.divider()
    st.subheader("📋 历史消费记录")
    
    # 初始化清算余额
    balances = {m: 0.0 for m in st.session_state.members}

    # 反转顺序显示，最新的在上面
    for idx, row in df[::-1].iterrows():
        try:
            # 解析存储的字符串字典
            shares = ast.literal_eval(row["分摊详情"])
            
            # 计算清算余额
            balances[row["付款人"]] += row["总金额"]
            for name, amt in shares.items():
                balances[name] -= amt

            # UI 显示
            with st.expander(f"{row['日期']} - {row['项目']} (${row['总金额']:.2f})"):
                st.write(f"付款人: {row['付款人']}")
                cols = st.columns(len([v for v in shares.values() if v > 0]))
                c_idx = 0
                for n, a in shares.items():
                    if a > 0:
                        with cols[c_idx]:
                            st.markdown(f"""<div style="padding:10px; border-radius:8px; background-color:#f8f9fa; border:1px solid #eee; border-top:4px solid #00cc96; text-align:center;">
                                <div style="color:#666; font-size:0.8rem;">{n}</div><div style="color:#222; font-weight:bold;">${a:.2f}</div></div>""", unsafe_allow_html=True)
                        c_idx += 1
        except:
            continue

    # --- 5. 核心：最终结算方案 ---
    st.divider()
    st.subheader("⚖️ 最终结算")
    
    # 找出欠钱的人和应收钱的人
    debtors = [[m, abs(b)] for m, b in balances.items() if b < -0.01]
    creditors = [[m, b] for m, b in balances.items() if b > 0.01]

    if not debtors and not creditors:
        st.info("所有账目已结清。")
    else:
        # 计算最简转账路径
        for d in debtors:
            for c in creditors:
                if d[1] <= 0: break
                if c[1] <= 0: continue
                settle = min(d[1], c[1])
                st.warning(f"👉 **{d[0]}** 应转账给 **{c[0]}** : **${settle:.2f}**")
                d[1] -= settle
                c[1] -= settle
else:
    st.info("云端尚无记录。")
