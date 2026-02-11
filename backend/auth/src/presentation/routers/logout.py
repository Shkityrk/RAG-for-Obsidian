from fastapi import APIRouter, Response

logout_router = APIRouter()


@logout_router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Успешный выход"}
