"""
OJ System - Authentication Router
"""
from fastapi import APIRouter, Request, HTTPException, Depends

from app.services import auth_service
from app.utils.dependencies import get_current_user
from app.models.schemas import UserRegister, UserLogin

router = APIRouter(tags=["auth"])


@router.post("/auth/register", status_code=201)
async def register(body: UserRegister, request: Request):
    """注册新用户。默认角色为 student，不允许客户端指定其他角色。"""
    result = auth_service.register(
        username=body.username,
        password=body.password,
    )
    return {"code": 201, "message": "user registered", "data": result}


@router.post("/auth/login")
async def login(body: UserLogin, request: Request):
    """用户登录。失败统一返回 401。"""
    result = auth_service.login(
        request=request,
        username=body.username,
        password=body.password,
    )
    return {"code": 200, "message": "login successful", "data": result}


@router.post("/auth/logout")
async def logout(request: Request):
    """登出当前用户，清除 Session。"""
    auth_service.logout(request)
    return {"code": 200, "message": "logged out", "data": None}


@router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    """获取当前登录用户信息。"""
    from app.services.auth_service import _sanitize_user
    return {"code": 200, "message": "ok", "data": _sanitize_user(user)}

