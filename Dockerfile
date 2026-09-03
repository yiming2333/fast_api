# syntax=docker/dockerfile:1.7
# ===== 多阶段构建 =====

# Stage 1: builder —— 安装依赖到独立虚拟环境
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt


# Stage 2: runtime —— 生产镜像（不含测试文件）
FROM python:3.10-slim AS runtime

LABEL org.opencontainers.image.title="fast_api" \
      org.opencontainers.image.description="FastAPI 示例应用" \
      org.opencontainers.image.source="https://github.com/example/fast_api"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app

RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --create-home --home-dir /home/app app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

COPY --chown=app:app app/ ./app/
COPY --chown=app:app static/ ./static/
COPY --chown=app:app templates/ ./templates/

RUN mkdir -p uploads && chown -R app:app uploads

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8000/').status==200 else sys.exit(1)" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]


# Stage 3: test-runtime —— 自包含测试镜像（CI/任何环境可直接运行）
FROM runtime AS test-runtime

USER root

# 将测试代码与配置打入镜像
COPY --chown=app:app tests/ ./tests/
COPY --chown=app:app pytest.ini ./pytest.ini

# 预创建可写缓存目录，消除 Permission denied 警告
RUN mkdir -p /app/.pytest_cache && chown -R app:app /app/.pytest_cache

USER app

# 禁用 cacheprovider 避免运行时写入问题；静默 httpx 弃用警告
ENV PYTHONWARNINGS="ignore::DeprecationWarning:starlette.testclient"

CMD ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "-q", "-p", "no:cacheprovider"]