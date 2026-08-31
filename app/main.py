from fastapi import FastAPI, Path, Query, Header, Cookie, HTTPException
from typing import Annotated
from pydantic import BaseModel
from fastapi.responses import RedirectResponse,JSONResponse



app = FastAPI(
    title="我的 API",                    # API 标题
    description="这是一个示例 API，展示文档自定义功能",  # API 描述
    version="1.0.0",                    # API 版本
    terms_of_service="http://example.com/terms/",  # 服务条款 URL
    contact={                           # 联系信息
        "name": "开发者",
        "url": "http://example.com/contact/",
        "email": "dev@example.com",
    },
    license_info={                      # 许可证信息
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)
@app.get("/")
async def read_root():
    return {"message": "Hello, FastAPI!"}

@app.get("/users/", tags=["用户管理"])
async def read_users():
    return [{"username": "Rick"}, {"username": "Morty"}]

@app.get(
    "/items/{item_id}",
    summary="获取商品信息",              # 简短摘要
    description="根据商品 ID 获取商品的详细信息",  # 详细描述
    response_description="商品信息对象",   # 响应描述
    tags=["商品管理"],                   # 分组标签
)
async def read_item(
    item_id: Annotated[int, Path(ge=1, description="商品ID")],
    q: Annotated[str | None, Query(description="搜索关键词")] = None,
):
    """
    获取商品信息：

    - **item_id**: 商品的唯一标识符
    - **q**: 可选的搜索关键词
    """
    if item_id == 42:
        raise HTTPException(status_code=404, detail="Item not found")
    content = {"item_id": item_id}
    headers = {"X-Custom-Header": "custom-header-value"}
    if item_id==43:
        return JSONResponse(content=content, headers=headers)
    return {"item_id": item_id, "q": q}

# 定义请求体数据模型
class Item(BaseModel):
    name: str           # 必填：商品名称
    description: str | None = None  # 可选：商品描述
    price: float        # 必填：商品价格
    tax: float | None = None        # 可选：税费


@app.post("/items/")
async def create_item(item: Item):
    """创建新商品，接收 JSON 请求体"""
    return item


@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item):
    """更新指定商品，同时使用路径参数和请求体"""
    return {"item_id": item_id, "item_name": item.name}


@app.get("/items/")
def read_item(user_agent: str = Header(None), session_token: str = Cookie(None)):
    return {"User-Agent": user_agent, "Session-Token": session_token}

@app.get("/redirect")
def redirect():
    return RedirectResponse(url="/items/")