"""HTTP клиент для работы с Data Service"""
import os
import requests
from typing import Optional
from src.domain.models.user import User


class DataServiceClient:
    """Клиент для обращения к Data Service API"""
    
    def __init__(self):
        self.base_url = os.getenv("DATA_SERVICE_URL", "http://data:8004")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def _request(self, method: str, endpoint: str, **kwargs):
        """Выполняет HTTP запрос к Data Service"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            if response.status_code == 204:
                return None
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Data Service request failed: {e}")
    
    # User methods
    def create_user(self, user_data: dict) -> dict:
        """Создает пользователя"""
        return self._request("POST", "/api/users", json=user_data)
    
    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """Получает пользователя по ID"""
        try:
            return self._request("GET", f"/api/users/{user_id}")
        except Exception:
            return None
    
    def get_user_by_username(self, username: str) -> Optional[dict]:
        """Получает пользователя по username"""
        try:
            return self._request("GET", f"/api/users/username/{username}")
        except Exception:
            return None
    
    def get_user_by_email(self, email: str) -> Optional[dict]:
        """Получает пользователя по email"""
        try:
            return self._request("GET", f"/api/users/email/{email}")
        except Exception:
            return None
    
    def list_users(self, **filters) -> list:
        """Получает список пользователей с фильтрацией"""
        return self._request("GET", "/api/users", params=filters)
    
    def update_user(self, user_id: int, user_data: dict) -> dict:
        """Обновляет пользователя"""
        return self._request("PUT", f"/api/users/{user_id}", json=user_data)
    
    def delete_user(self, user_id: int) -> None:
        """Удаляет пользователя"""
        self._request("DELETE", f"/api/users/{user_id}")
    
    def check_user_exists(self, username: str = None, email: str = None) -> bool:
        """Проверяет существование пользователя"""
        payload = {}
        if username:
            payload["username"] = username
        if email:
            payload["email"] = email
        
        result = self._request("POST", "/api/users/exists", json=payload)
        return result.get("exists", False)

