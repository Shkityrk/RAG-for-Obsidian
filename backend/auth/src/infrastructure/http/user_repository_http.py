"""HTTP реализация UserRepository через Data Service"""
from src.domain.models.user import User
from src.domain.interfaces.user_repository import AbstractUserRepository
from src.infrastructure.http.data_service_client import DataServiceClient


class UserRepositoryHTTP(AbstractUserRepository):
    """Репозиторий пользователей через Data Service HTTP API"""
    
    def __init__(self, client: DataServiceClient = None):
        self.client = client or DataServiceClient()
    
    def get_by_username(self, username: str) -> User | None:
        """Получить пользователя по username"""
        user_data = self.client.get_user_by_username(username)
        if user_data is None:
            return None
        return self._map_to_domain(user_data)
    
    def save(self, user: User) -> User:
        """Сохранить пользователя"""
        user_data = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "email": user.email,
            "hashed_password": user.hashed_password,
            "user_role": user.user_role,
        }
        
        created_user = self.client.create_user(user_data)
        return self._map_to_domain(created_user)
    
    def get_by_username_or_email(self, username: str, email: str) -> User | None:
        """Получить пользователя по username или email"""
        # Сначала пробуем по username
        user_data = self.client.get_user_by_username(username)
        if user_data:
            return self._map_to_domain(user_data)
        
        # Если не найден, пробуем по email
        user_data = self.client.get_user_by_email(email)
        if user_data:
            return self._map_to_domain(user_data)
        
        return None
    
    def _map_to_domain(self, user_data: dict) -> User:
        """Преобразовать данные из API в доменную модель"""
        return User(
            id=user_data.get("id"),
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            username=user_data.get("username"),
            email=user_data.get("email"),
            hashed_password=user_data.get("hashed_password"),
            user_role=user_data.get("user_role") or "client",
        )
