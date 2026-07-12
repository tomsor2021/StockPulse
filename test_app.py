import streamlit as st

st.title("📊 StockPulse 测试")
st.write("应用启动成功！")
st.write("Python 版本:", __import__('sys').version)
st.write("Streamlit 版本:", st.__version__)

try:
    import sqlite3
    st.success("SQLite3 可用")
except Exception as e:
    st.error(f"SQLite3 不可用: {e}")

try:
    import pandas as pd
    st.success(f"pandas 可用: {pd.__version__}")
except Exception as e:
    st.error(f"pandas 不可用: {e}")

try:
    import numpy as np
    st.success(f"numpy 可用: {np.__version__}")
except Exception as e:
    st.error(f"numpy 不可用: {e}")

try:
    import akshare as ak
    st.success(f"akshare 可用: {ak.__version__}")
except Exception as e:
    st.error(f"akshare 不可用: {e}")

try:
    import baostock
    st.success(f"baostock 可用: {baostock.__version__}")
except Exception as e:
    st.error(f"baostock 不可用: {e}")