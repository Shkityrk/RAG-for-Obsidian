from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    first_name: str
    last_name: str
    username: str
    email: str
    hashed_password: str
    user_role: str = "client"
    id: Optional[int] = None