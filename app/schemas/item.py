"""商品相关的 Pydantic 模型（请求/响应 schema）。"""

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Image(BaseModel):
    """子模型：图片。"""

    url: HttpUrl  # 自动校验是否为有效的 URL
    name: str


class Item(BaseModel):
    """商品 schema。"""

    name: str = Field(min_length=1, max_length=100, description="商品名称")
    description: str | None = Field(default=None, max_length=300, description="商品描述")
    price: float = Field(gt=0, description="商品价格")
    tax: float | None = Field(default=None, ge=0, description="税费")
    tags: list[str] = Field(default_factory=list)  # 字符串列表，默认为空列表
    tags1: set[str] = Field(default_factory=set)  # 自动去除重复标签
    image: Image | None = None
    images: list[Image] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Foo",
                    "price": 35.4,
                }
            ]
        }
    )


class Offer(BaseModel):
    """套餐 schema：包含多个 Item。"""

    name: str
    description: str | None = None
    price: float
    items: list[Item]
