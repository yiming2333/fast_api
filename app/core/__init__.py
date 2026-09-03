"""核心层：跨业务的横切关注点（配置、日志、异常、中间件、依赖）。"""

from .config import settings
from .logging import logger

__all__ = ["settings", "logger"]
