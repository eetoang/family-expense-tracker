import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import ast

# --- 1. 页面基本配置 ---
st.set_page_config(
    page_title="家庭智能云账本",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. 连接 Google Sheets ---
# 请确保已在 Streamlit Cloud 的 Secrets 中配置了 [connections.gsheets]
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # ttl=0 确保每次刷新页面都从云端抓取最新数据
        return conn.read(ttl=0)
    except:
        # 如果读取失败，返回一个带有正确列名的空表
        return pd.DataFrame(columns=["日期", "项目", "总金额", "付款人", "分摊详情"])

# --- 3. 成员管理 (Session State) ---
if "members" not in st.session_state:
    st.session_state.members = ["爸爸", "妈妈", "我", "妹妹"]

# --- 4. 侧边栏：成员管理 (修复了之前的 Form 错误) ---
st.sidebar.title("👥 成员管理")

# 侧边栏添加成员表单
with st.sidebar.form("add_member_form", clear_on_submit=True):
    new_name = st.text_input("添加新成员姓名")
    submit_add = st.form_submit_button("➕ 确认添加")
    
    if submit_add:
        if new_name and new_name not in st.session_state.members:
            st.session_state.members.append(new_name)
            st.toast(f"✅ 已成功添加成员: {new_name}")
            st.rerun()
        elif not new_name:
            st.warning("⚠️ 请输入姓名后再点击添加")

# 侧边栏清空功能
st.sidebar.markdown("---")
if st.sidebar.button("🗑️ 清空账目预览"):
    # 注意：这只会清空本地显示，不会删除 Google Sheets 里的数据
    st.info("如需永久删除账目，请直接前往 Google Sheets 手动删除行。")

# --- 5. 主界面：消费录入面板 ---
st.title("🍎 家庭费用分摊助手")

# 将模式切换放在表单外，确保手动输入框能实时刷新显示
split_mode = st.radio(
    "选择分摊方式：", 
    ["均分费用", "手动输入每人金额"], 
    horizontal=True
)

# 主录入表单
with st.form("main_expense_form", clear_on_submit=True):
    st.subheader("📝 录入新消费")
    col1, col2 = st.columns(2)
    
    with col1:
        item = st.text_input("消费项目", placeholder="例如：晚餐、超市、电影...")
        # value=None 配合 placeholder 实现在手机上点击即可直接输入
        total_amount = st.number_input("总金额", min_value=0.0, step=0.1, value=None, placeholder="请输入总金额")
    
    with col2:
        date = st.date_input("日期", value=datetime.now())
        payer = st.selectbox("谁先付钱？", st.session_state.members)

    st.markdown("**💡 参与人 (谁需要平摊？)**")
    p_cols = st.columns(len(st.session_state.members))
    checked_status = {}
    for i, m in enumerate(st.session_state.members):
        # 默认全部勾选
        checked_status[m] = p_cols[i].checkbox(m, value=True, key=f"form_check_{m}")

    # 处理手动输入金额的逻辑
    manual_shares = {}
    if split_mode == "手动输入每人金额":
        st.markdown("---")
        st.info("请在下方输入每个人具体负责的金额：")
        m_cols = st.columns(3)
        for i, m in enumerate(st.session_state.members):
            manual_shares[m] = m_cols[i % 3].number_input(
                f"{m} 的部分", 
                min_value=0.0, 
                value=None, 
                placeholder="0.00", 
                key=f"input_{m}"
            )

    # 提交按钮
    submit_btn = st.form_submit_button("💾 保存并同步到云端", use_container_width=True, type="primary")

    if submit_btn:
        if not item or total_amount is None:
            st.error("⚠️ 必须填写‘消费项目’和‘总金额’！")
        else:
            final_shares = {}
            active_p = [m for m, checked in checked_status.items() if checked]
            
            # 计算每个人该付多少
            if split_mode == "均分费用":
                if not active_p:
                    st.error("❌ 请至少勾选一个参与人！")
                    st.stop()
                per_person = total_amount / len(active_p)
                final_shares = {m: (per_person if checked_status[m] else 0.0) for m in st.session_state.members}
            else:
                # 手动模式下，将 None 转换为 0.0
                final_shares = {m: (manual_shares.get(m) if manual_shares.get(m) is not None else 0.0) for m in st.session_state.members}

            # 校验金额是否匹配
            if abs(sum(final_shares.values()) - total_amount) > 0.01:
                st.error(f"❌ 错误：分摊总和 (${sum(final_shares.values()):.2f}) 不等于总金额 (${total_amount:.2f})")
            else:
                # 写入 Google Sheets
                existing_df = load_data()
                new_row = pd.DataFrame([{
                    "日期": date.strftime("%Y-%m-%d"),
                    "项目": item,
                    "总金额": total_amount,
                    "付款人": payer,
                    "分摊详情": str(final_shares) # 转换为字符串保存
                }])
                updated_df = pd.concat([existing_df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                
                st.balloons()
                st.success("✅ 记录已同步至云端！")
                st.rerun()

# --- 6. 历史记录与结算统计 ---
df = load_data()

if not df.empty:
    st.divider()
    st.subheader("📋 历史消费记录")
    
    # 初始化每个人在该家庭里的余额 (总代付金额 - 总应付金额)
    balances = {m: 0.0 for m in st.session_state.members}

    # 从后往前读取历史记录 (让最新的显示在最上面)
    for idx, row in df[::-1].iterrows():
        try:
            # 使用 ast 解析字符串格式的字典
            shares_dict = ast.literal_eval(row["分摊详情"])
            
            # 累加计算每个人的余额
            balances[row["付款人"]] += row["总金额"]
            for name, amt in shares_dict.items():
                if name in balances:
                    balances[name] -= amt

            # 显示详细卡片
            with st.expander(f"{row['日期']} - {row['项目']} (${row['总金额']:.2f})", expanded=(idx == len(df)-1)):
                st.markdown(f"**付款人：** <span style='color:#ff4b4b'>{row['付款人']}</span>", unsafe_allow_html=True)
                
                # 过滤出有分摊金额的人员
                active_shares = {k: v for k, v in shares_dict.items() if v > 0}
                cols = st.columns(max(len(active_shares), 1))
                for i, (n, a) in enumerate(active_shares.items()):
                    with cols[i]:
                        st.markdown(f"""
                            <div style="padding:10px; border-radius:8px; background-color:#f8f9fa; border:1px solid #eee; border-top:4px solid #00cc96; text-align:center;">
                                <div style="color:#666; font-size:0.8rem;">{n}</div>
                                <div style="color:#222; font-weight:bold; font-size:1.1rem;">${a:.2f}</div>
                            </div>
                        """, unsafe_allow_html=True)
        except:
            continue

    # --- 7. 最终结算显示 ---
    st.divider()
    st.subheader("⚖️ 最终结算")
    
    # 欠钱的人 (余额为负) 和 应收钱的人 (余额为正)
    debtors = [[m, abs(b)] for m, b in balances.items() if b < -0.01]
    creditors = [[m, b] for m, b in balances.items() if b > 0.01]

    if not debtors and not creditors:
        st.info("🎉 恭喜！目前账目已结清，大家互不相欠。")
    else:
        # 显示建议转账方案
        for d in debtors:
            for c in creditors:
                if d[1] <= 0: break
                if c[1] <= 0: continue
                settle_amt = min(d[1], c[1])
                st.warning(f"👉 **{d[0]}** 应转账给 **{c[0]}** : **${settle_amt:.2f}**")
                d[1] -= settle_amt
                c[1] -= settle_amt
else:
    st.info("💡 暂时没有发现云端记录，请在上方尝试录入。")
