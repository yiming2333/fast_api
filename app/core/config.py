"""集中化应用配置。

通过环境变量（或 .env 文件）注入配置，避免在源码中硬编码敏感信息，
也便于在不同环境（本地开发 / Docker / CI）下复用同一份代码。
"""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置项。

    所有字段均可通过同名环境变量（不区分大小写）覆盖，例如::

        APP_NAME="我的 API" JWT_SECRET_KEY=change-me uvicorn app.main:app
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用基础信息
    app_name: str = "我的 API"
    app_description: str = "这是一个示例 API，展示文档自定义功能"
    app_version: str = "1.0.0"
    debug: bool = False

    # API 版本前缀
    api_v1_prefix: str = "/api/v1"

    # CORS
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:8000", "http://localhost:8080"]
    )

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # 上传文件保存目录
    upload_dir: str = "uploads"


@lru_cache
def get_settings() -> Settings:
    """单例缓存 Settings，避免重复解析环境变量。"""
    return Settings()


settings = get_settings()
