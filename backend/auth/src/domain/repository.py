from src.domain.models import User
from src.infrastructure.db.models.user_model import UserORM


def map_user_orm_to_domain(orm_user: UserORM) -> User:
    return User(
        id=orm_user.id,
        first_name=orm_user.first_name,
        last_name=orm_user.last_name,
        username=orm_user.username,
        email=orm_user.email,
        hashed_password=orm_user.hashed_password,
        user_role=orm_user.user_role,
    )