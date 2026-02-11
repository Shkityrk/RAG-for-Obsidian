-- Миграция: добавление колонки user_id в таблицу llm_tokens
-- Дата: 2024-01-XX
-- Описание: Добавляет колонку user_id для связи таблицы llm_tokens с users

-- Проверяем существование таблицы и колонки
DO $$
BEGIN
    -- Проверяем существование таблицы
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'llm_tokens') THEN
        -- Проверяем наличие колонки user_id
        IF NOT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'llm_tokens' AND column_name = 'user_id'
        ) THEN
            -- Добавляем колонку user_id
            ALTER TABLE llm_tokens ADD COLUMN user_id INTEGER;
            
            -- Удаляем записи без user_id (они бесполезны без связи с пользователем)
            DELETE FROM llm_tokens WHERE user_id IS NULL;
            
            -- Делаем колонку NOT NULL
            ALTER TABLE llm_tokens ALTER COLUMN user_id SET NOT NULL;
            
            -- Создаем индекс
            CREATE INDEX IF NOT EXISTS ix_llm_tokens_user_id ON llm_tokens(user_id);
            
            -- Добавляем внешний ключ
            ALTER TABLE llm_tokens 
            ADD CONSTRAINT fk_llm_tokens_user_id_users_id 
            FOREIGN KEY (user_id) REFERENCES users(id);
            
            RAISE NOTICE 'Колонка user_id успешно добавлена в таблицу llm_tokens';
        ELSE
            RAISE NOTICE 'Колонка user_id уже существует в таблице llm_tokens';
        END IF;
    ELSE
        RAISE NOTICE 'Таблица llm_tokens не существует, миграция не требуется';
    END IF;
END $$;

