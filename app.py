import streamlit as st
import pandas as pd
import os

# --- 配置与数据存储 ---
st.set_page_config(page_title="家庭账本", layout="wide")
DATA_FILE = "expenses.csv"
MEMBERS = ["爸爸", "妈妈", "我", "妹妹"]

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=["日期", "项目", "总金额", "付款人", "参与人"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- 页面标题 ---
st.title("🍎 家庭费用平摊助手")
st.write("随时随地记录，再也不怕忘账。")

# --- 侧边栏：录入新开销 ---
st.sidebar.header("新增记录")
with st.sidebar.form("expense_form", clear_on_submit=True):
    date = st.date_input("日期")
    item = st.text_input("消费项目", placeholder="例如：晚餐、超市")
    amount = st.number_input("总金额", min_value=0.0, step=1.0)
    payer = st.selectbox("谁付的钱？", MEMBERS)
    participants = st.multiselect("谁参与了平摊？", MEMBERS, default=MEMBERS)
    
    submitted = st.form_submit_button("确认提交")
    if submitted and item and amount > 0:
        df = load_data()
        new_record = {
            "日期": date,
            "项目": item,
            "总金额": amount,
            "付款人": payer,
            "参与人": ",".join(participants)
        }
        df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
        save_data(df)
        st.sidebar.success("已记录！")

# --- 主界面：数据展示与结算 ---
df = load_data()

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📊 消费历史")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        if st.button("清空所有记录"):
            if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
            st.rerun()
    else:
        st.info("目前没有记录，请从侧边栏添加。")

with col2:
    st.subheader("💰 结算方案")
    if not df.empty:
        balances = {m: 0.0 for m in MEMBERS}
        for _, row in df.iterrows():
            # 付款人增加
            balances[row["付款人"]] += row["总金额"]
            # 参与者扣除
            p_list = row["参与人"].split(",")
            share = row["总金额"] / len(p_list)
            for p in p_list:
                balances[p] -= share
        
        # 显示欠款逻辑
        st.write("目前余额状态：")
        for m, b in balances.items():
            color = "green" if b >= 0 else "red"
            st.markdown(f"{m}: :{color}[{b:.2f} 元]")
        
        st.divider()
        st.write("**转账建议：**")
        # 简单结算算法
        debtors = [[m, abs(b)] for m, b in balances.items() if b < -0.01]
        creditors = [[m, b] for m, b in balances.items() if b > 0.01]
        
        for d in debtors:
            for c in creditors:
                if d[1] <= 0: break
                if c[1] <= 0: continue
                settle = min(d[1], c[1])
                st.info(f"👉 **{d[0]}** 应给 **{c[0]}** : **{settle:.2f}** 元")
                d[1] -= settle
                c[1] -= settle
