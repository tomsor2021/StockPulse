"""Streamlit 表单组件（登录/注册/修改密码 UI）"""
import streamlit as st
from auth.auth import authenticate_user, register_user, change_password, change_nickname, delete_account, is_first_user


def show_login_page():
    """显示登录页面"""
    # Page config is set in app.py

    st.markdown("""
    <style>
    .main > div { max-width: 400px; margin: 0 auto; padding-top: 80px; }
    .stApp header { display: none; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("📊 StockPulse")
        st.caption("个人股票复盘系统")
        st.divider()

        if is_first_user():
            st.info("🔑 首次启动，请创建管理员账号")
            return show_register_page(is_admin_setup=True)

        tab1, tab2 = st.tabs(["登录", "注册"])

        with tab1:
            username_input = st.text_input("用户名", key="login_username")
            password_input = st.text_input("密码", type="password", key="login_password")
            if st.button("登录", type="primary", use_container_width=True):
                if not username_input or not password_input:
                    st.error("请输入用户名和密码")
                    return None
                user = authenticate_user(username_input, password_input)
                if user:
                    st.session_state["user"] = user
                    st.rerun()
                else:
                    st.error("用户名或密码错误")

        with tab2:
            return show_register_page()

    return None


def show_register_page(is_admin_setup=False):
    """显示注册页面"""
    reg_username = st.text_input("用户名", key="reg_username")
    reg_nickname = st.text_input("昵称（选填）", key="reg_nickname")
    reg_password = st.text_input("密码", type="password", key="reg_password")
    reg_confirm = st.text_input("确认密码", type="password", key="reg_confirm")

    btn_label = "创建管理员账号" if is_admin_setup else "注册"
    if st.button(btn_label, type="primary", use_container_width=True):
        if not reg_username or not reg_password:
            st.error("用户名和密码不能为空")
            return None
        if len(reg_username) < 2:
            st.error("用户名至少 2 个字符")
            return None
        if len(reg_password) < 4:
            st.error("密码至少 4 个字符")
            return None
        if reg_password != reg_confirm:
            st.error("两次密码输入不一致")
            return None
        user = register_user(reg_username, reg_password, reg_nickname or None)
        if user:
            st.session_state["user"] = user
            st.success("账号创建成功！")
            st.rerun()
        else:
            st.error("用户名已存在，请换一个")
    return None


def show_account_settings():
    """显示账户设置表单"""
    user = st.session_state.get("user")
    if not user:
        return

    st.subheader("👤 账户设置")

    with st.expander("修改昵称", expanded=False):
        new_nickname = st.text_input("新昵称", value=user.get("nickname", ""), key="edit_nickname")
        if st.button("保存昵称"):
            if new_nickname.strip():
                change_nickname(user["user_id"], new_nickname.strip())
                st.session_state["user"]["nickname"] = new_nickname.strip()
                st.success("昵称已更新")

    with st.expander("修改密码", expanded=False):
        old_pw = st.text_input("当前密码", type="password", key="old_pw")
        new_pw = st.text_input("新密码", type="password", key="new_pw")
        confirm_pw = st.text_input("确认新密码", type="password", key="confirm_pw")
        if st.button("修改密码"):
            if not old_pw or not new_pw or not confirm_pw:
                st.error("请填写所有密码字段")
            elif new_pw != confirm_pw:
                st.error("两次新密码输入不一致")
            elif len(new_pw) < 4:
                st.error("密码至少 4 个字符")
            else:
                if change_password(user["user_id"], old_pw, new_pw):
                    st.success("密码修改成功")
                else:
                    st.error("当前密码错误")

    with st.expander("⚠️ 注销账户", expanded=False):
        st.warning("注销后所有数据将被永久删除，不可恢复！")
        confirm_pw2 = st.text_input("输入密码确认注销", type="password", key="delete_confirm")
        if st.button("确认注销", type="primary", use_container_width=True):
            if confirm_pw2 and delete_account(user["user_id"], confirm_pw2):
                st.session_state.clear()
                st.rerun()
            else:
                st.error("密码错误或注销失败")


def logout():
    """登出"""
    st.session_state.clear()
    st.rerun()
