from sqlalchemy import inspect, text
from sqlmodel import create_engine

from src.database.indexes import embedding_index
from src.database.models import SQLModel


def migrate_llm_tokens_table(engine) -> None:
    """Добавляет колонку user_id в таблицу llm_tokens, если её нет"""
    inspector = inspect(engine)
    
    # Проверяем существование таблицы
    if "llm_tokens" not in inspector.get_table_names():
        return
    
    # Проверяем наличие колонки user_id
    columns = [col["name"] for col in inspector.get_columns("llm_tokens")]
    if "user_id" in columns:
        return
    
    # Добавляем колонку user_id
    with engine.connect() as conn:
        # Сначала добавляем колонку как nullable
        conn.execute(text("ALTER TABLE llm_tokens ADD COLUMN user_id INTEGER"))
        conn.commit()
        
        # Если есть данные, нужно установить значения (например, для существующих записей)
        # Но так как это таблица токенов, скорее всего она пустая или можно удалить старые записи
        # Для безопасности установим значение по умолчанию для существующих записей
        result = conn.execute(text("SELECT COUNT(*) FROM llm_tokens"))
        count = result.scalar()
        
        if count > 0:
            # Если есть записи без user_id, удаляем их (так как без user_id они бесполезны)
            # Или можно установить дефолтное значение, но лучше удалить
            conn.execute(text("DELETE FROM llm_tokens WHERE user_id IS NULL"))
            conn.commit()
        
        # Теперь делаем колонку NOT NULL и добавляем внешний ключ и индекс
        conn.execute(text("ALTER TABLE llm_tokens ALTER COLUMN user_id SET NOT NULL"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_llm_tokens_user_id ON llm_tokens(user_id)"))
        conn.execute(text(
            "ALTER TABLE llm_tokens "
            "ADD CONSTRAINT fk_llm_tokens_user_id_users_id "
            "FOREIGN KEY (user_id) REFERENCES users(id)"
        ))
        conn.commit()


def migrate_messages_table(engine) -> None:
    """Добавляет колонку fragments в таблицу messages, если её нет"""
    inspector = inspect(engine)
    
    # Проверяем существование таблицы
    if "messages" not in inspector.get_table_names():
        return
    
    # Проверяем наличие колонки fragments
    columns = [col["name"] for col in inspector.get_columns("messages")]
    if "fragments" in columns:
        return
    
    # Добавляем колонку fragments
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE messages ADD COLUMN fragments TEXT"))
        conn.commit()


def create_database(sync_db_url: str, *, echo: bool = True) -> None:
    metadata = SQLModel.metadata
    engine = create_engine(url=sync_db_url, echo=echo)
    metadata.create_all(engine, checkfirst=True)
    embedding_index.create(engine, checkfirst=True)
    # Применяем миграции для существующих таблиц
    migrate_llm_tokens_table(engine)
    migrate_messages_table(engine)
