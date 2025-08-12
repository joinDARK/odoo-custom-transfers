-- 🚀 Скрипт оптимизации индексов для аналитического дашборда
-- Выполните эти команды в PostgreSQL для ускорения запросов

-- 1. Индекс для таблицы amanat_reconciliation по partner_id и date
-- Ускоряет поиск сверок по контрагенту и диапазону дат
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_amanat_reconciliation_partner_date 
ON amanat_reconciliation(partner_id, date);

-- 2. Индекс для таблицы amanat_reconciliation только по partner_id  
-- Ускоряет группировку данных по контрагентам
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_amanat_reconciliation_partner_id
ON amanat_reconciliation(partner_id);

-- 3. Индекс для таблицы amanat_contragent по имени
-- Ускоряет поиск контрагентов по имени в дашборде
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_amanat_contragent_name
ON amanat_contragent(name);

-- 4. Композитный индекс для дат в reconciliation
-- Ускоряет фильтрацию по диапазону дат 
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_amanat_reconciliation_date_range
ON amanat_reconciliation(date DESC);

-- 5. Индекс для активных контрагентов (если есть поле active)
-- Раскомментируйте, если у вас есть поле active в модели контрагентов
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_amanat_contragent_active
-- ON amanat_contragent(active) WHERE active = true;

-- Проверка созданных индексов
SELECT 
    indexname,
    tablename,
    indexdef
FROM pg_indexes 
WHERE tablename IN ('amanat_reconciliation', 'amanat_contragent')
    AND indexname LIKE 'idx_amanat%'
ORDER BY tablename, indexname;

-- Статистика использования индексов (выполните через некоторое время после создания)
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE indexname LIKE 'idx_amanat%'
ORDER BY idx_tup_read DESC; 