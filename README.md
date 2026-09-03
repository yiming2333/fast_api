# FastAPI 示例项目

一个结构清晰、工程化完整的 FastAPI 示例应用，覆盖：

- FastAPI 最佳实践（APIRouter 拆分、pydantic-settings 配置、依赖注入）
- SQLAlchemy 2.0 异步 ORM + MySQL CRUD
- JWT 认证（OAuth2 Password Flow）
- 中间件（CORS / GZip / 请求日志 / 响应计时）
- 异常处理器统一响应格式
- Dockerfile（多阶段 + 非 root 用户）+ docker-compose.yml
- Jenkinsfile（声明式 Pipeline）
- 100+ 单元测试（SQLite 内存库覆盖 CRUD）
- Allure 测试报告

---

## 目录结构

```
fast_api/
├── app/
│   ├── core/              # 横切关注点
│   │   ├── config.py      # pydantic-settings 集中配置
│   │   ├── logging.py     # 日志
│   │   ├── exceptions.py  # 自定义异常 + 全局处理器
│   │   ├── middleware.py  # CORS / GZip / 请求日志 / 响应计时
│   │   ├── dependencies.py# 通用依赖（分页/校验 API Key 等）
│   │   └── security.py    # JWT + 密码哈希 + 当前用户依赖
│   ├── api/
│   │   └── routers/       # 按业务拆分的 APIRouter
│   │       ├── items.py       # 内存字典演示版商品路由
│   │       ├── items_db.py    # SQLAlchemy 持久化 CRUD
│   │       ├── users.py       # 用户列表 / 创建 / /me
│   │       ├── auth.py        # OAuth2 密码模式登录
│   │       ├── files.py       # 文件上传
│   │       ├── forms.py       # 表单提交
│   │       └── examples.py    # FastAPI 特性教学演示
│   ├── models/            # SQLAlchemy ORM 模型
│   │   ├── item.py        # Item 表
│   │   └── user.py        # UserORM 表
│   ├── schemas/           # Pydantic 请求/响应模型
│   │   ├── item.py        # 演示用复合模型
│   │   ├── item_db.py     # DB 持久化版 Item schema
│   │   ├── user.py
│   │   └── auth.py
│   ├── db/                # 数据访问层
│   │   ├── session.py     # async 引擎 / get_db 依赖 / init_db
│   │   └── fake_data.py   # 内存示例数据（不依赖 DB 的演示路由用）
│   └── main.py            # 应用入口（瘦壳）
├── tests/                 # pytest 测试
│   ├── conftest.py        # client / db_client fixtures
│   ├── test_main.py
│   ├── test_items.py
│   ├── test_items_db.py   # SQLite 覆盖的 CRUD 测试
│   ├── test_users.py
│   ├── test_auth.py
│   ├── test_files.py
│   ├── test_forms.py
│   └── test_examples.py
├── static/  templates/  uploads/
├── Dockerfile
├── docker-compose.yml
├── Jenkinsfile
├── requirements.txt   requirements-dev.txt
├── pytest.ini         .env.example
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
# 推荐用虚拟环境
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

### 2. 配置数据库

复制 `.env.example` 为 `.env`，填入 MySQL 连接信息：

```env
# 方式一：直接给完整 URL
DB_URL=mysql+aiomysql://root:你的密码@127.0.0.1:3306/fast_api?charset=utf8mb4

# 方式二：按字段拼接（留空 DB_URL 时生效）
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=你的密码
DB_NAME=fast_api
```

首次启动会自动执行 `CREATE DATABASE IF NOT EXISTS fast_api` 对应的 `create_all`，
所以 **先在 MySQL 里建库**，或者让应用用有权限的账号自动建库。

### 3. 启动服务

```bash
# 开发模式（热重载）
uvicorn app.main:app --reload --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

打开 <http://localhost:8000/docs> 查看 Swagger UI。

### 4. 运行测试

```bash
# 全部测试（100 个）
pytest tests/ -v

# 指定分组
pytest tests/ -m db        # 只跑 SQLAlchemy CRUD
pytest tests/ -m auth      # 只跑认证相关
```

> **重点**：CRUD 测试（`test_items_db.py`）通过 `db_client` fixture
> 把 `get_db` 依赖替换为 **SQLite 内存库**，所以 **不需要真实 MySQL** 也能跑通。

### 5. 生成 Allure 报告

```bash
# 先生成原始结果（pytest.ini 已默认带 --alluredir=allure-results）
pytest tests/

# 再生成 HTML 报告（需要本机装 Allure CLI）
allure generate allure-results -o allure-report --clean
allure open allure-report
```

> Allure CLI 安装：<https://allurereport.org/docs/install/>

---

## API 速览

所有业务路由统一挂 `/api/v1` 前缀：

| 方法 | 路径 | 说明 | 需鉴权 |
|------|------|------|--------|
| GET  | `/` | 健康检查 | - |
| GET  | `/api/v1/items/db` | 商品列表（分页 + 过滤） | - |
| POST | `/api/v1/items/db` | 创建商品 | API Key |
| GET  | `/api/v1/items/db/{id}` | 获取商品 | - |
| PUT  | `/api/v1/items/db/{id}` | 全量更新商品 | - |
| PATCH| `/api/v1/items/db/{id}` | 部分更新商品 | - |
| DEL  | `/api/v1/items/db/{id}` | 删除商品 | - |
| POST | `/api/v1/auth/token` | 登录换 JWT | - |
| GET  | `/api/v1/users/me` | 当前用户 | Bearer |
| GET  | `/docs` | Swagger UI | - |

---

## Docker

### 本地一键启动

```bash
docker compose up --build
```

容器内监听 8000 端口，映射到宿主机 8000。MySQL 凭据通过 `.env` 注入。

### 运行测试容器

```bash
docker compose --profile test run --rm test
```

### 多阶段构建说明

- **builder 阶段**：基于 `python:3.10-slim`，安装依赖到独立虚拟环境
- **runtime 阶段**：只复制虚拟环境和应用代码，使用非 root 用户运行，镜像更小、攻击面更小
- **HEALTHCHECK**：每 30s 探测根路径，失败 3 次判定容器不健康

---

## Jenkins

`Jenkinsfile` 提供声明式 Pipeline，包含：

1. **Checkout** — 拉取代码
2. **Lint** — ruff 静态检查
3. **Test** — 在 Docker 容器内执行 pytest
4. **Build Image** — 构建并推送镜像（仅 main/release 分支）
5. **Deploy** — 占位，接入实际部署方式（SSH / Ansible / kubectl）

### 前置配置

- Jenkins 装 Pipeline / Docker Pipeline 插件
- 添加凭据：`docker-registry`（Username/Password 类型，镜像仓库账号）
- Jenkins agent 能跑 docker

---

## 设计决策

| 问题 | 决策 | 理由 |
|------|------|------|
| DB 连接 | SQLAlchemy `aiomysql` 异步引擎 | 不阻塞事件循环，FastAPI 异步友好 |
| 会话管理 | 单一 `get_db()` 入口，事务由调用侧控制 | 职责清晰，测试替换简单（dependency_overrides 一次搞定） |
| 测试 DB | SQLite aiosqlite 内存库 | 无外部依赖，每个测试独立干净 |
| 配置 | pydantic-settings + `.env` | 类型安全，环境变量优先，Docker / CI 友好 |
| 异常 | 全局 `http_exception_handler` 统一格式 | 前端拿到的错误结构一致 |
| ORM 模型 | SQLAlchemy 2.0 Mapped/mapped_column | 新版声明式风格，不与 Pydantic Field 混用 |
| 迁移 | 暂用 `create_all()` | 示例项目不上 Alembic；生产建议补 |

---

## 已知限制

- 没有 SQL 迁移工具（Alembic）；表结构变更靠 `create_all`，生产请补 Alembic
- 用户注册后没有写入 MySQL（`/api/v1/users/` 仍是内存 dict）；如需完整 Auth 请扩展 `UserORM` 路由
- 演示路由（`/api/v1/items/*`、`/api/v1/examples/*`）用内存数据，服务重启会丢
- 上传文件安全校验（文件类型/大小/病毒）未做，生产请补

---

## License

MIT
