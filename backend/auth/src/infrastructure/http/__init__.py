"""HTTP инфраструктура для взаимодействия с внешними сервисами"""
from .data_service_client import DataServiceClient
from .user_repository_http import UserRepositoryHTTP

__all__ = ["DataServiceClient", "UserRepositoryHTTP"]

