"""用户认证核心逻辑"""
import logging
import hashlib
import os

logger = logging.getLogger("stockpulse.auth")

# 固定 salt（本地应用，安全需求不高）
_PEPPER = b"StockPulse2024!@#"


def hash_password(password: str) -> str:
    """使用 SHA-256 加盐哈希密码"""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt + _PEPPER, 100000)
    return salt.hex() + ":" + key.hex()


def verify_password(password: str, stored_hash: str) -> bool:
    """验证密码"""
    try:
        salt_hex, key_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        stored_key = bytes.fromhex(key_hex)
        computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt + _PEPPER, 100000)
        return computed == stored_key
    except Exception as e:
        logger.error(f"密码验证失败: {e}")
        return False


def authenticate_user(username: str, password: str) -> dict:
    """验证用户登录，成功返回用户信息字典"""
    from database import models as db
    user = db.get_user_by_username(username)
    if not user:
        logger.warning(f"登录失败：用户不存在 - {username}")
        return None
    if not verify_password(password, user["password_hash"]):
        logger.warning(f"登录失败：密码错误 - {username}")
        return None
    logger.info(f"登录成功：{username}")
    return {"user_id": user["id"], "username": user["username"], "nickname": user["nickname"]}


def register_user(username: str, password: str, nickname: str = None) -> dict:
    """注册新用户"""
    from database import models as db
    existing = db.get_user_by_username(username)
    if existing:
        logger.warning(f"注册失败：用户名已存在 - {username}")
        return None
    pw_hash = hash_password(password)
    user_id = db.create_user(username, pw_hash, nickname)
    logger.info(f"注册成功：{username} (id={user_id})")
    return {"user_id": user_id, "username": username, "nickname": nickname or username}


def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    """修改密码"""
    from database import models as db
    user = db.get_user_by_id(user_id)
    if not user:
        return False
    if not verify_password(old_password, user["password_hash"]):
        return False
    new_hash = hash_password(new_password)
    db.update_user_password(user_id, new_hash)
    logger.info(f"密码修改成功：user_id={user_id}")
    return True


def change_nickname(user_id: int, nickname: str):
    from database import models as db
    db.update_user_nickname(user_id, nickname)
    logger.info(f"昵称修改成功：user_id={user_id}")


def delete_account(user_id: int, password: str) -> bool:
    """注销账户"""
    from database import models as db
    user = db.get_user_by_id(user_id)
    if not user:
        return False
    if not verify_password(password, user["password_hash"]):
        return False
    db.delete_user(user_id)
    logger.info(f"账户注销：user_id={user_id}")
    return True


def is_first_user() -> bool:
    """检查是否为首次启动（无用户）"""
    from database import models as db
    return db.get_user_count() == 0
