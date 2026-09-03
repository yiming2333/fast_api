"""路由聚合：将各业务路由统一挂载到 api_router。

main.py 只需 `app.include_router(api_router, prefix=settings.api_v1_prefix)`，
即可完成所有业务路由的注册，避免在主入口维护一长串 include。
"""

from fastapi import APIRouter

from . import auth, examples, files, forms, items, users

api_router = APIRouter()
api_router.include_router(items.router)
api_router.include_router(users.router)
api_router.include_router(auth.router)
api_router.include_router(files.router)
api_router.include_router(forms.router)
api_router.include_router(examples.router)

__all__ = ["api_router"]
