"""示例路由：演示 FastAPI 各类特性的“教学用”端点。

原本散落在 main.py 中，路径名混乱（如 /test1/items/、/max_50/items/、
/decrator/depend/items/ 等），且大量同名函数造成可读性差。

此模块按特性分组并改用语义化路径：
- /examples/models/*        复合模型（嵌套、列表、字典）
- /examples/params/*        路径与查询参数校验
- /examples/headers/*       请求头与 Cookie
- /examples/responses/*     异常处理器与自定义响应
- /examples/dependencies/*  依赖注入（普通/类/子依赖/yield）
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Path, Query, status
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.dependencies import (
    CommonQueryParams,
    common_parameters,
    get_db,
    query_checker,
    verify_api_key,
)
from app.core.exceptions import UnicornException
from app.schemas.item import Image, Offer

router = APIRouter(prefix="/examples", tags=["示例"])


# ===== 复合模型 =====
@router.post("/models/offers", summary="嵌套模型示例")
async def create_offer(offer: Offer):
    """Offer 包含多个 Item，Item 又包含多个 Image。"""
    return offer


@router.post("/models/images", summary="请求体为模型列表")
async def create_multiple_images(images: list[Image]):
    """请求体直接是一个 Image 列表。"""
    return images


@router.post("/models/index-weights", summary="请求体为字典")
async def create_index_weights(weights: dict[int, float]):
    """接收键为 int、值为 float 的字典。"""
    return weights


# ===== 路径与查询参数 =====
@router.get("/params/path/{item_id}", summary="路径参数校验")
async def read_with_path_validation(
    item_id: Annotated[int, Path(ge=1, description="商品ID")],
    size: Annotated[float, Query(gt=0, lt=10.5)] = 5.0,
):
    """为路径参数与查询参数添加元数据和校验。"""
    return {"item_id": item_id, "size": size}


@router.get("/params/multi-query", summary="多值查询参数")
async def read_multi_query(
    q: Annotated[list[str] | None, Query()] = None,
):
    """q 可在 URL 中出现多次，值会被收集为列表。"""
    return {"q": q}


@router.get("/params/validated-query", summary="查询参数高级校验")
async def read_validated_query(
    q: Annotated[str | None, Query(
        title="查询字符串",
        description="用于筛选商品的查询字符串",
        min_length=3,
        max_length=50,
        alias="item-query",
        deprecated=True,
        include_in_schema=False,
        pattern="^fixedquery$",
    )] = None,
):
    """演示 min/max/alias/deprecated/hidden/pattern 等高级校验。"""
    results = {"items": [{"item_id": "Foo"}, {"item_id": "Bar"}]}
    if q:
        results.update({"q": q})
    return results


@router.get("/params/optional-query/{item_id}", summary="路径参数+可选查询")
async def read_with_optional_query(item_id: str, q: str | None = None):
    """item_id 必填，q 可选。"""
    if q:
        return {"item_id": item_id, "q": q}
    return {"item_id": item_id}


@router.get("/params/bool-query/{item_id}", summary="布尔查询参数")
async def read_with_bool_query(item_id: str, short: bool = False):
    """short 参数会被自动转换为布尔值。"""
    if short:
        return {"item_id": item_id}
    return {"item_id": item_id, "description": "这是一段很长的描述"}


@router.get("/params/required-query/{item_id}", summary="必选查询参数")
async def read_with_required_query(item_id: str, needy: str):
    """needy 没有默认值，是必选查询参数。"""
    return {"item_id": item_id, "needy": needy}


# ===== 请求头与 Cookie =====
@router.get("/headers/user-agent", summary="读取 User-Agent")
async def read_user_agent(
    user_agent: Annotated[str | None, Header()] = None,
):
    return {"User-Agent": user_agent}


@router.get("/headers/x-token", summary="读取 X-Token（多值）")
async def read_x_token(
    x_token: Annotated[list[str] | None, Header()] = None,
):
    """Python 变量名用下划线，FastAPI 自动转换为 X-Token 请求头。"""
    return {"X-Token values": x_token}


@router.get("/headers/x-uid", summary="读取 X-Uid（多值）")
async def read_x_uid(
    x_uid: Annotated[list[str] | None, Header()] = None,
):
    return {"X-Uid values": x_uid}


@router.get("/cookies/session", summary="读取 Cookie")
async def read_session_cookie(
    session_token: Annotated[str | None, Cookie()] = None,
):
    return {"session_token": session_token}


@router.get("/headers-cookies", summary="读取请求头与 Cookie 组合")
async def read_headers_and_cookies(
    user_agent: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Cookie()] = None,
    ads_id: Annotated[str | None, Cookie()] = None,
):
    return {
        "User-Agent": user_agent,
        "Session-Token": session_token,
        "Ads-ID": ads_id,
    }


# ===== 异常处理器与自定义响应 =====
@router.get("/responses/redirect", summary="重定向示例")
async def redirect():
    return RedirectResponse(url="/api/v1/items/")


@router.get("/responses/unicorns/{name}", summary="自定义异常示例")
async def read_unicorn(name: str):
    """name == yolo 时抛出 UnicornException，由全局处理器统一返回。"""
    if name == "yolo":
        raise UnicornException(name=name)
    return {"unicorn_name": name}


@router.get("/responses/http-exception/{item_id}", summary="HTTPException（字典 detail）")
async def raise_http_exception(item_id: str):
    """detail 可以是字典，包含更多错误信息。"""
    if item_id == "invalid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_ID",
                "message": "商品ID格式不正确",
                "hint": "请使用字母数字组合的ID",
            },
        )
    return {"item_id": item_id}


@router.get("/responses/header-error/{item_id}", summary="带自定义响应头的异常")
async def raise_with_headers(item_id: str):
    if item_id == "invalid":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
            headers={"X-Error": "There goes my error"},
        )
    return {"item": item_id}


@router.get("/responses/custom/{item_id}", summary="自定义 JSONResponse")
async def custom_response(item_id: int):
    """直接返回 JSONResponse 并附加自定义响应头。"""
    content = {"item_id": item_id}
    headers = {"X-Custom-Header": "custom-header-value"}
    return JSONResponse(content=content, headers=headers)


# ===== 依赖注入 =====
@router.get("/dependencies/common/items", summary="普通依赖（items）")
async def read_with_common_dep(commons: Annotated[dict, Depends(common_parameters)]):
    """复用 common_parameters 依赖。"""
    return commons


@router.get("/dependencies/common/users", summary="普通依赖（users）")
async def read_users_with_common_dep(commons: Annotated[dict, Depends(common_parameters)]):
    return commons


@router.get("/dependencies/class", summary="类形式依赖")
async def read_with_class_dep(commons: Annotated[CommonQueryParams, Depends()]):
    """使用类作为依赖。"""
    return {"q": commons.q, "skip": commons.skip, "limit": commons.limit}


@router.get("/dependencies/sub", summary="子依赖链")
async def read_with_sub_dep(q: Annotated[str, Depends(query_checker)]):
    """query_checker 内部又依赖 query_extractor，形成子依赖链。"""
    return {"q": q}


@router.get(
    "/dependencies/api-key-protected",
    dependencies=[Depends(verify_api_key)],
    summary="装饰器级依赖（无返回值）",
)
async def read_with_api_key_dep():
    """在装饰器中使用依赖，不需要返回值。"""
    return [{"item": "Foo"}]


@router.get(
    "/dependencies/route-protected",
    dependencies=[Depends(verify_api_key)],
    summary="路由级依赖",
)
async def read_users_with_route_dep():
    return [{"user": "Bar"}]


@router.get("/dependencies/yield-db", summary="yield 依赖（资源管理）")
async def read_with_yield_dep(db: Annotated[str, Depends(get_db)]):
    """使用 yield 的依赖：请求前创建连接，请求后关闭连接。"""
    return {"db": db}
