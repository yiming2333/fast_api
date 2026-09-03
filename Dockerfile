# syntax=docker/dockerfile:1.7
# ===== 多阶段构建 =====
# Stage 1: builder —— 安装依赖到独立虚拟环境，便于最终镜像只复制产物
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# 先单独复制依赖清单，最大化利用 layer cache
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt


# Stage 2: runtime —— 最终镜像只含运行所需内容，体积更小、攻击面更小
FROM python:3.10-slim AS runtime

LABEL org.opencontainers.image.title="fast_api" \
      org.opencontainers.image.description="FastAPI 示例应用" \
      org.opencontainers.image.source="https://github.com/example/fast_api"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app

# 创建非 root 用户运行应用，遵循最小权限原则
RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --create-home --home-dir /home/app app

WORKDIR /app

# 从 builder 复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 复制应用代码与静态资源
COPY --chown=app:app app/ ./app/
COPY --chown=app:app static/ ./static/
COPY --chown=app:app templates/ ./templates/

# 创建上传目录（非 root 用户可写）
RUN mkdir -p uploads && chown -R app:app uploads

USER app

EXPOSE 8000

# 健康检查：调用根路径，确认服务可用
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8000/').status==200 else sys.exit(1)"

# 生产使用多 worker；本地调试可去掉 --workers
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
