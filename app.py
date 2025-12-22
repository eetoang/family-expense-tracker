import streamlit as st
import pandas as pd

st.set_page_config(page_title="全能家庭账本", layout="wide")

# --- 1. 动态成员管理 ---
if "members" not in st.session_state:
    st.session_state.members = ["爸爸", "妈妈", "我"] # 初始默认值

st.sidebar.title("👥 成员管理")
new_member = st.sidebar.text_input("添加新成员名字")
if st.sidebar.button("添加成员"):
    if new_member and new_member not in st.session_state.members:
        st.session_state.members.append(new_member)
        st.rerun()

removed_member = st.sidebar.selectbox("删除成员", ["选择成员"] + st.session_state.members)
if st.sidebar.button("确认删除"):
    if removed_member in st.session_state.members:
        st.session_state.members.remove(removed_member)
        st.rerun()

# --- 2. 消费录入面板 ---
st.title("💰 灵活费用分摊助手")

with st.expander("📝 录入新消费", expanded=True):
    col_a, col_b = st.columns(2)
    with col_a:
        date = st.date_input("日期")
        item = st.text_input("消费项目", placeholder="例如：屈臣氏买个人用品")
        total_amount = st.number_input("总金额", min_value=0.0, step=0.1)
    
    with col_b:
        payer = st.selectbox("谁先付钱？", st.session_state.members)
        split_mode = st.radio("分摊模式", ["所有人平摊", "指定部分人平摊", "按个人金额（谁买谁付）"])

    # 核心分摊逻辑处理
    shares = {}
    if split_mode == "所有人平摊":
        st.info(f"模式：每个人分担 {total_amount / len(st.session_state.members):.2f} 元")
        for m in st.session_state.members:
            shares[m] = total_amount / len(st.session_state.members)

    elif split_mode == "指定部分人平摊":
        selected_p = st.multiselect("哪些人参与平摊？", st.session_state.members)
        if selected_p:
            st.info(f"模式：选定人每人分担 {total_amount / len(selected_p):.2f} 元")
            for m in selected_p:
                shares[m] = total_amount / len(selected_p)

    elif split_mode == "按个人金额（谁买谁付）":
        st.write("请输入每个人对应的金额：")
        temp_sum = 0
        for m in st.session_state.members:
            val = st.number_input(f"{m} 的部分", min_value=0.0, key=f"split_{m}")
            shares[m] = val
            temp_sum += val
        
        if abs(temp_sum - total_amount) > 0.1:
            st.warning(f"注意：目前各项加起来为 {temp_sum}，与总金额 {total_amount} 不符！")

    if st.button("🚀 提交记录"):
        if item and total_amount > 0:
            # 这里构造存入数据库的格式
            # 为方便计算，我们将参与人及其分摊金额转为字符串存储，或者展开存储
            new_record = {
                "日期": str(date),
                "项目": item,
                "总金额": total_amount,
                "付款人": payer,
                "分摊详情": str(shares) # 存储为字典字符串
            }
            # 这里之后对接保存到 Google Sheets 的逻辑
            st.success("记录成功（逻辑已跑通，待连接数据库）！")
            st.write("本单分摊情况：", shares)

# --- 3. 统计展示（预览） ---
st.divider()
st.subheader("📋 统计预览")
st.write("当前成员列表：", ", ".join(st.session_state.members))
