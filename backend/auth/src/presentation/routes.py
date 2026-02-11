# from fastapi import APIRouter, Depends, HTTPException, Response, Request
# from sqlalchemy.orm import Session
# from datetime import timedelta
#
# from src.infrastructure.db.repositories.user import UserRepository
# from src.infrastructure.db.session import get_db
# from src.schemas import schemas
#
# from src.application.services.auth_service import AuthService
#
# auth_router = APIRouter(prefix="/auth")
#
#
#
# # def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
# #     return AuthService(UserRepository(db))
#
# #
# # @auth_router.post("/register", response_model=schemas.UserOut)
# # def register(
# #     user_create: schemas.UserCreate,
# #     response: Response,
# #     auth_service: AuthService = Depends(get_auth_service)
# # ):
# #     user = auth_service.register_user(user_create)
# #     access_token = auth_service.create_access_token(data={"sub": user.username})
# #     response.set_cookie(
# #         key="access_token", value=f"Bearer {access_token}", httponly=True
# #     )
# #     return user
#
#
# @auth_router.post("/login")
# def login(
#     response: Response,
#     user_login: schemas.UserLogin,
#     auth_service: AuthService = Depends(get_auth_service)
# ):
#     user = auth_service.authenticate_user(user_login)
#     if not user:
#         raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")
#     access_token = auth_service.create_access_token(data={"sub": user.username})
#     response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
#     return {"message": "Успешный вход"}
#
#
# @auth_router.post("/logout")
# def logout(response: Response):
#     response.delete_cookie(key="access_token")
#     return {"message": "Успешный выход"}
#
#
# @auth_router.get("/protected-route")
# def protected_route(
#     request: Request,
#     auth_service: AuthService = Depends(get_auth_service)
# ):
#     token = auth_service.get_token_from_cookie(request)
#     user = auth_service.get_current_user(token)
#     return {"message": f"Привет, {user.username}!"}
#
#
# @auth_router.get("/info", response_model=schemas.UserOut)
# def verify_token(
#     request: Request,
#     auth_service: AuthService = Depends(get_auth_service)
# ):
#     token = auth_service.get_token_from_cookie(request)
#     user = auth_service.get_current_user(token)
#     return user
