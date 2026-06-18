import streamlit as st

st.set_page_config(
    page_title="财务数据大屏 - 测试",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("财务数据大屏 - 测试版")

with st.sidebar:
    st.header("侧边栏")
    st.write("这是侧边栏内容")
    if st.button("测试按钮"):
        st.success("按钮点击成功！")

st.header("主内容区")
st.write("这是主内容区域")

col1, col2 = st.columns(2)
with col1:
    st.metric("营收", "1,234.56万", "+12.3%")
with col2:
    st.metric("利润", "456.78万", "-5.2%", delta_color="inverse")
