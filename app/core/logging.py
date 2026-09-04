"""日志配置。

独立的 logger 避免继承 uvicorn 的特殊 formatter，
统一日志格式便于后续接入 ELK / Loki 等日志系统。

生产环境自动写入 logs/app.log（按 10MB 轮转，保留 5 个备份）。
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")


def setup_logger(name: str = "my_app", level: int = logging.INFO) -> logging.Logger:
    """创建并配置一个带 StreamHandler + RotatingFileHandler 的 logger。

    幂等：重复调用不会重复添加 handler。
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # 避免向 root logger 重复传播

    if not logger.handlers:
        # 控制台输出
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(stream_handler)

        # 文件输出（轮转日志，创建 logs 目录时忽略已存在）
        os.makedirs(LOG_DIR, exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(file_handler)

    return logger


# 全局共享 logger
logger = setup_logger()
