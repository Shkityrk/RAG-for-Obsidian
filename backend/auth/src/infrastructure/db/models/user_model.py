from sqlalchemy import Column, Integer, String
from src.infrastructure.db.base import Base

__all__ = [
    "UserORM"
]

class UserORM(Base):
    __tablename__ = "users"

    id = Column(Integer,
                primary_key=True,
                index=True,
                autoincrement=True)
    first_name = Column(String)
    last_name = Column(String)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    user_role = Column(String, nullable=False, default="client")
