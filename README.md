# FastAPI 工程化示例项目

一个结构清晰、生产就绪的 FastAPI 脚手架，覆盖：

- **FastAPI 最佳实践** — APIRouter 拆分、pydantic-settings 配置、依赖注入
- **SQLAlchemy 2.0 异步 ORM** — MySQL CRUD + 连接池管理
- **Alembic 数据库迁移** — 异步引擎支持，autogenerate 可用
- **JWT 认证（OAuth2 Password Flow）** — 走真实数据库，bcrypt 密码哈希
- **中间件** — CORS / GZip / 请求日志 / 响应计时
- **统一异常处理** — 全局错误格式，敏感信息脱敏
- **结构化日志** — 控制台 + RotatingFileHandler（10MB 轮转）
- **Docker 多阶段构建** — 非 root 用户、HEALTHCHECK
- **Jenkins Pipeline** — 声明式 CI/CD + Allure 报告 + 钉钉通知
- **完整测试** — 100+ 单元测试，SQLite 内存库覆盖，无需真实 MySQL

## 目录结构

```
fast_api/
├── app/
│   ├── core/                    # 横切关注点
│   │   ├── config.py            # pydantic-settings 集中配置
│   │   ├── logging.py           # 日志（控制台 + 文件轮转）
│   │   ├── exceptions.py        # 自定义异常 + 全局处理器
│   │   ├── middleware.py         # CORS / GZip / 请求日志 / 响应计时
│   │   ├── dependencies.py      # 通用依赖（分页/校验 API Key 等）
│   │   └── security.py          # JWT + 密码哈希 + 当前用户依赖
│   ├── api/
│   │   └── routers/             # 按业务拆分的 APIRouter
│   │       ├── items_db.py      # SQLAlchemy 持久化 CRUD
│   │       ├── users.py         # 用户管理（真实数据库）
│   │       ├── auth.py          # OAuth2 密码模式登录
│   │       ├── files.py         # 文件上传（演示）
│   │       ├── forms.py         # 表单提交（演示）
│   │       ├── items.py         # 内存字典演示（演示）
│   │       └── examples.py      # FastAPI 特性教学（演示）
│   ├── models/                  # SQLAlchemy ORM 模型
│   │   ├── item.py              # Item 表
│   │   └── user.py              # UserORM 表
│   ├── schemas/                 # Pydantic 请求/响应模型
│   │   ├── item.py              # 演示用复合模型
│   │   ├── item_db.py           # DB 持久化版 Item schema
│   │   ├── user.py              # 用户输入/输出 schema
│   │   └── auth.py              # Token / User / UserInDB
│   ├── db/                      # 数据访问层
│   │   ├── session.py           # async 引擎 / get_db 依赖 / init_db
│   │   ├── seed.py              # 首次启动种子数据
│   │   └── fake_data.py         # 内存示例数据（演示路由用）
│   └── main.py                  # 应用入口（瘦壳）
├── alembic/                     # 数据库迁移
│   ├── env.py                   # 异步迁移环境
│   ├── script.py.mako           # 迁移模板
│   └── versions/
│       └── 001_initial.py       # 初始表结构
├── tests/                       # pytest 测试
│   ├── conftest.py              # client / db_client fixtures
│   ├── test_main.py             # 冒烟测试
│   ├── test_items.py            # 演示路由测试
│   ├── test_items_db.py         # SQLAlchemy CRUD 测试
│   ├── test_users.py            # 用户路由测试
│   ├── test_auth.py             # 认证测试
│   ├── test_files.py            # 文件上传测试
│   ├── test_forms.py            # 表单测试
│   └── test_examples.py         # FastAPI 特性测试
├── static/ templates/ uploads/
├── alembic.ini
├── Dockerfile                   # 多阶段构建
├── docker-compose.yml
├── Jenkinsfile                  # 跨平台 CI/CD
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── .env.example
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### 2. 配置数据库

复制 `.env.example` 为 `.env`，填入 MySQL 连接信息：

```bash
# 方式一：直接给完整 URL
DB_URL=mysql+aiomysql://root:你的密码@127.0.0.1:3306/fast_api?charset=utf8mb4

# 方式二：按字段拼接（留空 DB_URL 时生效）
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=你的密码
DB_NAME=fast_api

# JWT（生产务必替换！）
JWT_SECRET_KEY=$(openssl rand -hex 32)
```

### 3. 数据库迁移

```bash
# 首次：用 Alembic 建表
alembic upgrade head

# 后续改了 model 后自动生成迁移
alembic revision --autogenerate -m "描述"
alembic upgrade head
```

> 也可以不跑 Alembic，应用启动时会自动 `create_all()` 建表（开发便利，生产建议用 Alembic）。

### 4. 启动服务

```bash
# 开发模式（热重载）
uvicorn app.main:app --reload --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

打开 http://localhost:8000/docs 查看 Swagger UI。

首次启动会自动创建默认用户 `alice`（密码: `secret`），用于快速体验认证流程。

### 5. 运行测试

```bash
# 全部测试（不需要真实 MySQL）
pytest tests/ -v

# 指定分组
pytest tests/ -m db      # 只跑 SQLAlchemy CRUD
pytest tests/ -m auth    # 只跑认证相关

# 并行执行
pytest tests/ -n auto
```

测试通过 `db_client` fixture 把 `get_db` 依赖替换为 SQLite 内存库，无需外部数据库。

### 6. 生成 Allure 报告

```bash
pytest tests/  # 默认生成 allure-results
allure generate allure-results -o allure-report --clean
allure open allure-report
```

## API 速览

所有业务路由统一挂 `/api/v1` 前缀。

### 真实数据库路由

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/` | 健康检查 | - |
| POST | `/api/v1/auth/token` | 登录换 JWT | - |
| GET | `/api/v1/users/` | 用户列表 | - |
| POST | `/api/v1/users/` | 创建用户 | - |
| GET | `/api/v1/users/me` | 当前用户 | Bearer |
| GET | `/api/v1/items/db` | 商品列表（分页+过滤） | - |
| POST | `/api/v1/items/db` | 创建商品 | API Key |
| GET | `/api/v1/items/db/{id}` | 获取商品 | - |
| PUT | `/api/v1/items/db/{id}` | 全量更新 | - |
| PATCH | `/api/v1/items/db/{id}` | 部分更新 | - |
| DEL | `/api/v1/items/db/{id}` | 删除商品 | - |

### 演示路由（内存数据，重启丢失）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/demo/items/` | 演示商品列表 |
| GET | `/api/v1/demo/examples/*` | FastAPI 特性教学 |
| POST | `/api/v1/demo/forms/*` | 表单演示 |
| POST | `/api/v1/demo/files/*` | 文件上传演示 |

### 认证说明

```bash
# 1. 登录获取 JWT
curl -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=alice&password=secret"

# 2. 用 JWT 访问受保护路由
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <token>"

# 3. 用 API Key 创建商品
curl -X POST http://localhost:8000/api/v1/items/db \
  -H "X-API-Key: secret-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "Laptop", "price": 999.9}'
```

## Docker

### 本地一键启动

```bash
docker compose up --build
```

容器内监听 8000 端口，映射到宿主机 8000。数据库凭据通过 `.env` 注入。

### 运行测试容器

```bash
docker compose --profile test run --rm test
```

### 多阶段构建说明

| 阶段 | 说明 |
|------|------|
| builder | python:3.10-slim，安装依赖到独立虚拟环境 |
| runtime | 只复制 venv + 应用代码，非 root 用户运行 |
| test-runtime | 复制测试代码，可直接运行 pytest |

## Jenkins

Jenkinsfile 提供跨平台声明式 Pipeline：

1. **Checkout** — 拉取代码
2. **Lint** — ruff 静态检查
3. **Build** — Docker 内构建测试镜像
4. **Test** — Docker 内执行 pytest（支持并行参数化）
5. **Allure** — 生成测试报告
6. **Notify** — 钉钉 + 邮件通知

### 前置配置

- Jenkins 装 Pipeline / Docker Pipeline 插件
- 添加凭据：`dingtalk_webhook`（Secret text 类型，钉钉 Webhook 地址）
- Jenkins agent 能跑 docker（Linux/macOS/Windows 均可）

## 设计决策

| 问题 | 决策 | 理由 |
|------|------|------|
| DB 连接 | SQLAlchemy aiomysql 异步引擎 | 不阻塞事件循环，FastAPI 原生异步 |
| 会话管理 | 单一 `get_db()` 入口，事务由调用侧控制 | 职责清晰，测试替换简单 |
| 测试 DB | SQLite aiosqlite 内存库 | 无外部依赖，每个测试独立干净 |
| 配置 | pydantic-settings + `.env` | 类型安全，环境变量优先 |
| 异常 | 全局处理器统一格式 + 脱敏 | 前端错误结构一致，不泄露内部信息 |
| ORM | SQLAlchemy 2.0 Mapped/mapped_column | 新版声明式风格 |
| 迁移 | Alembic 异步迁移 | 生产安全，支持 autogenerate |
| 认证 | UserORM 真实表 + bcrypt | 数据持久化，重启不丢用户 |
| 日志 | 控制台 + RotatingFileHandler | 开发看控制台，生产看文件 |

## 已知限制

- 上传文件安全校验（文件类型/大小/病毒）未做，生产请补
- CORS 默认允许 `*` 方法和头，生产环境应收紧
- 无 Rate Limiting，生产建议加 `slowapi` 或网关层限流
- 无 Redis/缓存层，高频读场景需自行扩展

## License

MIT
