"""日志配置"""
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from config.settings import LOG_DIR, LOG_LEVEL, LOG_RETENTION_DAYS


def setup_logging():
    """配置全局日志"""
    logger = logging.getLogger("stockpulse")
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    logger.handlers.clear()

    # 文件日志（按天轮转）
    log_file = LOG_DIR / "stockpulse.log"
    handler = TimedRotatingFileHandler(
        log_file, when="midnight", interval=1, backupCount=LOG_RETENTION_DAYS,
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # 控制台输出
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger("stockpulse")


def get_recent_log_lines(n: int = 100) -> str:
    """读取最近 n 行日志"""
    log_file = LOG_DIR / "stockpulse.log"
    if not log_file.exists():
        return "暂无日志"
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return "".join(lines[-n:])
    except Exception:
        return "读取日志失败"
