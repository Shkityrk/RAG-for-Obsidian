from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.config import app_config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет пароль против хеша"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Хеширует пароль"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создает JWT токен"""
    import logging
    logger = logging.getLogger(__name__)
    to_encode = data.copy()
    # Гарантируем, что sub всегда строка (требование JWT спецификации)
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=app_config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # #region agent log
    logger.info(f"Creating token: data={to_encode}, exp={expire}, SECRET_KEY_preview={app_config.SECRET_KEY[:10]}, ALGORITHM={app_config.ALGORITHM}")
    # #endregion
    encoded_jwt = jwt.encode(to_encode, app_config.SECRET_KEY, algorithm=app_config.ALGORITHM)
    # #region agent log
    logger.info(f"Token created: preview={encoded_jwt[:30]}...")
    # #endregion
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Проверяет и декодирует JWT токен"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        # #region agent log
        logger.info(f"Verifying token: preview={token[:30]}, SECRET_KEY_preview={app_config.SECRET_KEY[:10]}, ALGORITHM={app_config.ALGORITHM}")
        # #endregion
        # Отключаем строгую проверку sub для совместимости со старыми токенами
        # и преобразуем sub в строку после декодирования
        payload = jwt.decode(
            token, 
            app_config.SECRET_KEY, 
            algorithms=[app_config.ALGORITHM],
            options={"verify_sub": False}
        )
        # Преобразуем sub в строку, если он не строка (для совместимости)
        if "sub" in payload and not isinstance(payload["sub"], str):
            payload["sub"] = str(payload["sub"])
        # #region agent log
        logger.info(f"Token verified successfully: payload={payload}")
        # #endregion
        return payload
    except JWTError as e:
        # #region agent log
        logger.error(f"JWT verification failed: {type(e).__name__}: {str(e)}")
        # #endregion
        return None
    except Exception as e:
        # #region agent log
        logger.error(f"Unexpected error during token verification: {type(e).__name__}: {str(e)}")
        # #endregion
        return None

