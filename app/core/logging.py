"""日志配置。

独立的 logger 避免继承 uvicorn 的特殊 formatter，
统一日志格式便于后续接入 ELK / Loki 等日志系统。
"""

import logging
import sys

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logger(name: str = "my_app", level: int = logging.INFO) -> logging.Logger:
    """创建并配置一个带 StreamHandler 的 logger。

    幂等：重复调用不会重复添加 handler。
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # 避免向 root logger 重复传播

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)

    return logger


# 全局共享 logger
logger = setup_logger()
