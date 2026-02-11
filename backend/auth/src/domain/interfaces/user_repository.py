from abc import ABC, abstractmethod
from src.domain.models import User

class AbstractUserRepository(ABC):

    @abstractmethod
    def get_by_username(self, username: str) -> User | None:
        pass

    @abstractmethod
    def save(self, user: User) -> User:
        pass

    @abstractmethod
    def get_by_username_or_email(self, username, email):
        pass