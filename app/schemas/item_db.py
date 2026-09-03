"""DB 持久化版 Item 的 Pydantic schema。

与 app/schemas/item.py 里的“演示用 Item”并存：
- app.schemas.item.Item   —— 演示复合模型/嵌套/字典等 FastAPI 特性
- app.schemas.item_db.*  —— 对应 app.models.item.Item ORM 的输入/输出 schema

遵循 FastAPI 社区约定：用 model_config(from_attributes=True) 让
Pydantic 自动把 ORM 对象转成 schema（否则得手动 .model_validate(obj)）。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ===== 输入 =====
class ItemCreate(BaseModel):
    """创建商品。"""

    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    price: float = Field(gt=0)
    tax: Optional[float] = Field(default=None, ge=0)


class ItemUpdate(BaseModel):
    """更新商品 —— 所有字段可选（PATCH 语义）。"""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    tax: Optional[float] = Field(default=None, ge=0)


# ===== 输出 =====
class ItemOut(BaseModel):
    """商品输出 —— 与 ORM 字段一一对应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ItemListOut(BaseModel):
    """列表分页返回 —— 带 total 方便前端做分页器。"""

    items: list[ItemOut]
    total: int
    skip: int
    limit: int
