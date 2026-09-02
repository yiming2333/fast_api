import logging
import shutil
import time
from fastapi import FastAPI, Path, Query, Header, Cookie, HTTPException, Depends, Form, status, UploadFile, File, \
    Request
from typing import Annotated
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


# logger = logging.getLogger("uvicorn.access")


async def verify_token(x_token: str = Header()):
    if x_token != "fake-super-secret-token":
        raise HTTPException(status_code=400, detail="X-Token header invalid")


app = FastAPI(
    title="我的 API",  # API 标题
    description="这是一个示例 API，展示文档自定义功能",  # API 描述
    version="1.0.0",  # API 版本
    terms_of_service="http://example.com/terms/",  # 服务条款 URL
    contact={  # 联系信息
        "name": "开发者",
        "url": "http://example.com/contact/",
        "email": "dev@example.com",
    },
    license_info={  # 许可证信息
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    # dependencies=[Depends(verify_token)]
)


@app.get("/")
async def read_root():
    return {"message": "Hello, FastAPI!"}


@app.get("/users/", tags=["用户管理"])
async def read_users():
    return [{"username": "Rick"}, {"username": "Morty"}]


@app.get(
    "/items/{item_id}",
    summary="获取商品信息",  # 简短摘要
    description="根据商品 ID 获取商品的详细信息",  # 详细描述
    response_description="商品信息对象",  # 响应描述
    tags=["商品管理"],  # 分组标签
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
    if item_id == 43:
        return JSONResponse(content=content, headers=headers)
    return {"item_id": item_id, "q": q}


# 子模型：图片
class Image(BaseModel):
    url: HttpUrl  # 自动校验是否为有效的 URL
    name: str


# 定义请求体数据模型
class Item(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="商品名称")  # 必填，1-100字符
    description: str | None = Field(default=None, max_length=300, description="商品描述")  # 可选
    price: float = Field(gt=0, description="商品价格")  # 必填，必须大于 0
    tax: float | None = Field(default=None, ge=0, description="税费")  # 可选，>= 0
    tags: list[str] = []  # 字符串列表，默认为空列表
    tags1: set[str] = set()  # 自动去除重复标签
    image: Image | None = None  # 可选的图片信息
    images: list[Image] | None = None  # 图片列表

    # Pydantic v2 的配置方式
    model_config = ConfigDict(
        json_schema_extra={  # 在 API 文档中显示示例
            "examples": [
                {
                    "name": "Foo",
                    "price": 35.4
                }
            ]
        }
    )


class Offer(BaseModel):
    name: str
    description: str | None = None
    price: float
    items: list[Item]  # Offer 包含多个 Item，Item 又包含多个 Image


# @app.post("/items/")
# async def create_item(item: Item):
#     """创建新商品，接收 JSON 请求体"""
#     return item
@app.post("/offers/")
async def create_offer(offer: Offer):
    return offer


# 请求体直接是一个 Image 列表
@app.post("/images/multiple/")
async def create_multiple_images(images: list[Image]):
    return images


# 接收键为 int、值为 float 的字典
@app.post("/index-weights/")
async def create_index_weights(weights: dict[int, float]):
    return weights


@app.post("/items/", status_code=status.HTTP_201_CREATED)
async def create_item(item: Item):
    # 访问模型属性
    print(item.name)  # 直接访问属性
    print(item.price)  # 编辑器提供自动补全

    # 序列化为字典
    item_dict = item.model_dump()
    print(item_dict)  # {"name": "Foo", "description": None, "price": 45.2, "tax": None}

    # 序列化为 JSON 字符串
    item_json = item.model_dump_json()
    print(item_json)  # '{"name":"Foo","description":null,"price":45.2,"tax":null}'

    return item_dict


items = {
    "foo": {"name": "Foo", "price": 50.2},
    "bar": {"name": "Bar", "description": "The bartenders", "price": 62, "tax": 20.2},
    "baz": {"name": "Baz", "description": None, "price": 50.2, "tax": 10.5, "tags": []},
}


@app.get("/exclude/items/{item_id}", response_model=Item, response_model_exclude_unset=True,
         response_model_include={"name", "description"})
async def read_item(item_id: str):
    return items[item_id]


# 排除 tax
@app.get("/items/{item_id}/no-tax", response_model=Item, response_model_exclude={"tax"})
async def read_item_no_tax(item_id: str):
    return items[item_id]


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


# 基础模型
class UserBase(BaseModel):
    username: str  # 必填
    email: EmailStr  # 必填，自动校验邮箱格式
    full_name: str | None = None  # 可选


# 创建用户时的输入模型（包含密码）
class UserCreate(UserBase):
    password: str  # 必填


# 返回用户信息时的输出模型（不包含密码）
class UserOut(UserBase):
    id: int  # 由服务器生成


# 使用示例
@app.post("/users/", response_model=UserOut)
async def create_user(user: UserCreate):
    # 函数接收 UserCreate（含密码），但响应使用 UserOut（不含密码）
    # 这样密码就不会出现在 API 响应中
    return {"id": 1, **user.model_dump(exclude={"password"})}


# 1. 定义依赖函数
def common_parameters(q: str | None = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}


# 2. 在路由中使用依赖
@app.get("/depend/items/")
async def read_items(commons: dict = Depends(common_parameters)):
    # commons 接收依赖函数的返回值
    return commons


@app.get("/depend/users/")
async def read_users(commons: dict = Depends(common_parameters)):
    # 多个路由可以复用同一个依赖
    return commons


# 用类声明依赖
class CommonQueryParams:
    def __init__(self, q: str | None = None, skip: int = 0, limit: int = 100):
        self.q = q
        self.skip = skip
        self.limit = limit


# 使用类作为依赖
@app.get("/class/depend/items/")
async def read_items(commons: Annotated[CommonQueryParams, Depends()]):
    return {"q": commons.q, "skip": commons.skip, "limit": commons.limit}


# 依赖函数
def query_extractor(q: str | None = None):
    return q


# 子依赖：依赖 query_extractor
def query_checker(q: str = Depends(query_extractor)):
    if q == "admin":
        # 子依赖可以进行校验
        return q + " (checked)"
    return q


# 路由使用子依赖
@app.get("/son/depend/items/")
async def read_items(q: str = Depends(query_checker)):
    return {"q": q}


# 依赖：校验 API Key
async def verify_api_key(x_api_key: str = Header()):
    if x_api_key != "secret-key":
        raise HTTPException(status_code=400, detail="X-API-Key invalid")


# 在装饰器中使用依赖，不需要返回值
@app.get("/decrator/depend/items/", dependencies=[Depends(verify_api_key)])
async def read_items():
    return [{"item": "Foo"}]


# 对整个路由组使用依赖
@app.get("/route/depend/users/", dependencies=[Depends(verify_api_key)])
async def read_users():
    return [{"user": "Bar"}]


# 全局依赖：所有路由都需要通过 token 校验

@app.get("/all/depend/items/")
async def read_items():
    return [{"item": "Foo"}]


@app.get("/all/depend/users/")
async def read_users():
    return [{"user": "Bar"}]


# 使用 yield 的依赖：请求前创建连接，请求后关闭连接
def get_db():
    db = "database_connection"  # 模拟创建数据库连接
    try:
        yield db  # 请求处理期间提供数据库连接
    finally:
        print("关闭数据库连接")  # 请求完成后清理资源


@app.get("/yiled/items/")
async def read_items(db: str = Depends(get_db)):
    return {"db": db}


@app.post("/form/login/")
async def login(
        username: str = Form(),  # 必填表单字段
        password: str = Form(),  # 必填表单字段
):
    return {"username": username, "password": password}


@app.post("/not_must_select/form/items/")
async def create_item(
        name: str = Form(...),  # 必填
        description: str | None = Form(None),  # 可选，默认 None
        price: float = Form(..., gt=0),  # 必填，必须大于 0
):
    return {"name": name, "description": description, "price": price}


# ✅ 直接通过浏览器访问测试页面
@app.get("/test", response_class=HTMLResponse)
async def test_page():
    return """
    <form action="http://localhost:8000/not_must_select/form/items/" method="post">
        <label for="name">Name:</label>
        <input type="text" id="name" name="name" required><br>

        <label for="description">Description:</label>
        <textarea id="description" name="description"></textarea><br>

        <label for="price">Price:</label>
        <input type="number" id="price" name="price" required min="0"><br>

        <button type="submit">Submit</button>
    </form>
    """


# :path 表示该参数可以匹配包含斜杠的路径
@app.get("/files/{file_path:path}")
async def read_file(file_path: str):
    return {"file_path": file_path}


# skip 和 limit 是查询参数，有默认值
fake_items_db = [{"item_name": "Foo"}, {"item_name": "Bar"}, {"item_name": "Baz"}]


@app.get("/query/param/items/")
async def read_item(skip: int = 0, limit: int = 10):
    # 模拟分页查询
    return fake_items_db[skip: skip + limit]


@app.get("/test/items/{item_id}")
async def read_item(item_id: str, q: str | None = None):
    # item_id 是路径参数（必填），q 是查询参数（可选）
    if q:
        return {"item_id": item_id, "q": q}
    return {"item_id": item_id}


@app.get("/test1/items/{item_id}")
async def read_item(item_id: str, short: bool = False):
    # short 参数会被自动转换为布尔值
    if short:
        return {"item_id": item_id}
    return {"item_id": item_id, "description": "这是一段很长的描述"}


@app.get("/test2/items/{item_id}")
async def read_item(item_id: str, needy: str):
    # needy 没有默认值，是必选查询参数
    return {"item_id": item_id, "needy": needy}


@app.get("/max_50/items/")
async def read_items(
        # 使用 Annotated + Query 添加校验
        q: Annotated[str | None, Query(
            title="查询字符串",  # 参数标题
            description="用于筛选商品的查询字符串",  # 参数描述
            min_length=3,
            max_length=50,
            alias="item-query",  # URL 中的参数名别名
            deprecated=True,  # 标记为已弃用
            include_in_schema=False,  # hidden_query 不会出现在 API 文档中，但仍然可以使用
            pattern="^fixedquery$"
        )] = None,
):
    results = {"items": [{"item_id": "Foo"}, {"item_id": "Bar"}]}
    if q:
        results.update({"q": q})
    return results


@app.get("/multi_params/items/")
async def read_items(
        # q 可以在 URL 中出现多次，值会被收集为列表
        q: Annotated[list[str] | None, Query()] = None,
):
    query_items = {"q": q}
    return query_items


@app.get("/path/items/{item_id}")
async def read_items(
        # 为路径参数添加元数据和校验
        item_id: Annotated[int, Path(title="商品ID", description="要获取的商品ID", ge=1)],
        # 查询参数也可以用数值校验
        size: Annotated[float, Query(gt=0, lt=10.5)] = 5.0,
):
    return {"item_id": item_id, "size": size}


@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile | None = None):
    if not file:
        return {"message": "没有上传文件"}
    # UploadFile 提供的属性和方法
    return {
        "filename": file.filename,  # 文件名
        "content_type": file.content_type,  # 文件 MIME 类型
        "size": file.size,  # 文件大小（字节）
    }


@app.post("/uploadfiles/")
async def create_upload_files(files: list[UploadFile]):
    return {"filenames": [file.filename for file in files]}


@app.post("/files/")
async def create_file(file: bytes = File()):
    # file 是文件的原始字节数据
    return {"file_size": len(file)}


@app.post("/form_file/items/")
async def create_item(
        # 表单字段
        name: str = Form(),
        description: str | None = Form(None),
        # 文件上传
        file: UploadFile | None = None,
):
    result = {"name": name, "description": description}
    if file:
        result["filename"] = file.filename
    return result


@app.post("/save/uploadfile/")
async def create_upload_file(file: UploadFile):
    # 将上传的文件保存到指定路径
    with open(f"uploads/{file.filename}", "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename, "message": "文件上传成功"}


@app.get("/user_agent/items/")
async def read_items(
        # 接收 User-Agent 请求头
        user_agent: Annotated[str | None, Header()] = None,
):
    return {"User-Agent": user_agent}


@app.get("/x_token/items/")
async def read_items(
        # Python 变量名用下划线，FastAPI 自动转换为 X-Token 请求头
        x_token: Annotated[list[str] | None, Header()] = None,
):
    return {"X-Token values": x_token}


@app.get("/multi_x_uid/items/")
async def read_items(
        # 接收多个 X-uid 请求头
        x_uid: Annotated[list[str] | None, Header()] = None,
):
    return {"X-Uid values": x_uid}


@app.get("/get_cookie/items/")
async def read_items(
        # 接收名为 session_token 的 Cookie
        session_token: Annotated[str | None, Cookie()] = None,
):
    return {"session_token": session_token}


@app.get("/header_cookie/items/")
async def read_items(
        user_agent: Annotated[str | None, Header()] = None,
        session_token: Annotated[str | None, Cookie()] = None,
        ads_id: Annotated[str | None, Cookie()] = None,
):
    return {
        "User-Agent": user_agent,
        "Session-Token": session_token,
        "Ads-ID": ads_id,
    }


@app.get("/invalid_detail/items/{item_id}")
async def read_item(item_id: str):
    if item_id == "invalid":
        # detail 可以是字典，包含更多错误信息
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_ID",
                "message": "商品ID格式不正确",
                "hint": "请使用字母数字组合的ID"
            }
        )
    return {"item_id": item_id}


@app.get("/items-header/{item_id}")
async def read_item_header(item_id: str):
    if item_id == "invalid":
        raise HTTPException(
            status_code=404,
            detail="Item not found",
            headers={"X-Error": "There goes my error"},  # 自定义响应头
        )
    return {"item": item_id}


# 自定义异常类
class UnicornException(Exception):
    def __init__(self, name: str):
        self.name = name


# 注册异常处理器
@app.exception_handler(UnicornException)
async def unicorn_exception_handler(request: Request, exc: UnicornException):
    # 返回自定义格式的错误响应
    return JSONResponse(
        status_code=418,
        content={"message": f"Oops! {exc.name} did something wrong"},
    )


@app.get("/unicorns/{name}")
async def read_unicorn(name: str):
    if name == "yolo":
        # 抛出自定义异常
        raise UnicornException(name=name)
    return {"unicorn_name": name}


# 覆盖 HTTP 异常处理器
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": f"HTTP error: {exc.detail}"},
    )


# 覆盖请求校验异常处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "数据校验失败", "details": exc.errors()},
    )


@app.get("/custom/items/{item_id}")
async def read_item(item_id: int):
    content = {"item_id": item_id}
    headers = {"X-Custom-Header": "custom-header-value"}
    return JSONResponse(content=content, headers=headers)


# 创建独立 logger，不会继承 uvicorn 的特殊 formatter
logger = logging.getLogger("my_app")
logger.setLevel(logging.INFO)

# 添加标准 handler（如果尚未配置）
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))
    logger.addHandler(handler)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    # 记录请求信息
    logger.info(f"请求: {request.method} {request.url}")

    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # 记录响应信息
    logger.info(
        f"响应: {request.method} {request.url} "
        f"状态码={response.status_code} 耗时={process_time:.3f}s"
    )

    return response


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    # 1. 请求前的处理：记录开始时间
    start_time = time.time()

    # 2. 将请求传递给下一个中间件或路由函数
    response = await call_next(request)

    # 3. 响应后的处理：计算处理时间并添加响应头
    process_time = int((time.time() - start_time) * 1000)
    response.headers["X-Process-Time"] = str(process_time)
    return response


# 当响应大小超过 1000 字节时自动压缩
app.add_middleware(GZipMiddleware, minimum_size=1000)

'''
中间件在请求/响应的处理链中执行通用逻辑
使用 @app.middleware("http") 创建自定义中间件
call_next(request) 将请求传递给下一层
中间件按注册顺序执行（请求正序，响应反序）
FastAPI/Starlette 提供了 CORS、GZip、HTTPS 重定向等内置中间件
'''

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[  # 允许的源（域名列表）
        "http://localhost:8000",  # 前端开发服务器
        "http://localhost:8080",
    ],
    allow_credentials=True,  # 允许携带 Cookie
    allow_methods=["*"],  # 允许的 HTTP 方法
    allow_headers=["*"],  # 允许的请求头
)

# 挂载静态文件目录
# "/static" 是 URL 路径前缀
# directory="static" 是本地目录名
app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja2 模板
templates = Jinja2Templates(
    directory="templates"
)


@app.get("/hello/{name}")
async def hello(request: Request, name: str):
    return templates.TemplateResponse(
        request=request,
        name="hello.html",
        context={
            "name": name
        }
    )
