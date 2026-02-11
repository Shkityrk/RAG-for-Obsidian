-- Миграция: добавление колонки fragments в таблицу messages
-- Дата: 2024-01-XX
-- Описание: Добавляет колонку fragments для хранения JSON массива фрагментов текста

-- Проверяем существование таблицы и колонки
DO $$
BEGIN
    -- Проверяем существование таблицы
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'messages') THEN
        -- Проверяем наличие колонки fragments
        IF NOT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'messages' AND column_name = 'fragments'
        ) THEN
            -- Добавляем колонку fragments
            ALTER TABLE messages ADD COLUMN fragments TEXT;
            
            RAISE NOTICE 'Колонка fragments успешно добавлена в таблицу messages';
        ELSE
            RAISE NOTICE 'Колонка fragments уже существует в таблице messages';
        END IF;
    ELSE
        RAISE NOTICE 'Таблица messages не существует, миграция не требуется';
    END IF;
END $$;

