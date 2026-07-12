import os
import sys

os.environ["TENCENT_CLOUDBASE"] = "true"

try:
    import app
except Exception as e:
    import streamlit as st
    st.error(f"应用启动失败: {str(e)}")
    st.exception(e)
    sys.exit(1)