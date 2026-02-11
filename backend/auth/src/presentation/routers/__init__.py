from fastapi import APIRouter

from .info import info_router
from .login import login_router
from .logout import logout_router
from .register import register_router
from .protected_route import protected_route_router
from .healthcheck import healthcheck_router

__all__ = [
    "root_router"
]

root_router = APIRouter(prefix="/auth")

root_router.include_router(info_router)
root_router.include_router(login_router)
root_router.include_router(logout_router)
root_router.include_router(register_router)
root_router.include_router(protected_route_router)
root_router.include_router(healthcheck_router)
