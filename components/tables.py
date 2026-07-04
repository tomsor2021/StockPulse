"""表格和弹窗组件"""
import streamlit as st


def sortable_table(df, column_config=None, height=400, width="stretch"):
    """可排序表格"""
    if df is None or df.empty:
        st.caption("暂无数据")
        return
    st.dataframe(
        df,
        column_config=column_config,
        height=height,
        width=width,
        hide_index=True,
    )


def confirm_dialog(title, message, confirm_text="确认", cancel_text="取消", key="confirm"):
    """确认对话框"""
    if key not in st.session_state:
        st.session_state[key] = False
    result = st.session_state.get(f"{key}_result", False)
    if st.session_state[key]:
        with st.container():
            st.warning(message)
            cols = st.columns(2)
            with cols[0]:
                if st.button(confirm_text, key=f"{key}_yes"):
                    st.session_state[f"{key}_result"] = True
                    st.session_state[key] = False
                    st.rerun()
            with cols[1]:
                if st.button(cancel_text, key=f"{key}_no"):
                    st.session_state[key] = False
                    st.session_state[f"{key}_result"] = False
                    st.rerun()
    return result


def show_confirm(key="confirm"):
    st.session_state[key] = True
