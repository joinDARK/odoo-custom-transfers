# Настройка API сервера для модуля Amanat

## Текущая конфигурация

API сервер настроен в файле `addons/amanat/models/reconciliation.py`:

```python
# Конфигурация API сервера
API_SERVER_BASE_URL = "http://localhost:8085"
API_OPERATIONS_ENDPOINT = f"{API_SERVER_BASE_URL}/api/operations"
```

## Изменение адреса сервера

### Для локального развертывания
```python
API_SERVER_BASE_URL = "http://localhost:8085"
```

### Для продакшн сервера
```python
API_SERVER_BASE_URL = "http://92.255.207.48:8085"
```

### Для тестового сервера
```python
API_SERVER_BASE_URL = "http://test-server:8085"
```

## Проверка доступности сервера

### Health Check
```bash
curl -X GET http://localhost:8085/api/health
```

Ожидаемый ответ:
```json
{
  "status": "healthy",
  "timestamp": "2025-07-16T11:43:17.047Z",
  "uptime": 1380.851980888
}
```

### Проверка портов
```bash
netstat -tuln | grep 8085
```

Ожидаемый результат:
```
tcp        0      0 127.0.0.1:8085          0.0.0.0:*               LISTEN
```

## Тестирование API

### Тест операций
```bash
curl -X POST http://localhost:8085/api/operations \
  -H "Content-Type: application/json" \
  -d '{
    "fileName": "test_sverka",
    "data": [
      {
        "№": 1,
        "Дата": "2025-07-16",
        "Отправитель": [{"name": "Тест отправитель"}],
        "Получатель": [{"name": "Тест получатель"}],
        "Валюта": {"name": "RUB"},
        "Сумма": 10000,
        "Кошелек": "Тест кошелек",
        "Комментарий (from Ордер)": "Тестовая операция",
        "Наш процент": 0,
        "РКО": 0,
        "К выдаче": 10000
      }
    ]
  }'
```

### Список файлов в облаке
```bash
curl -X GET http://localhost:8085/api/cloud/files
```

### Статистика облачного хранилища
```bash
curl -X GET http://localhost:8085/api/cloud/stats
```

## Переменные окружения (рекомендуется для продакшн)

Создайте файл `.env` в корне проекта:

```bash
# API Server Configuration
AMANAT_API_SERVER_HOST=localhost
AMANAT_API_SERVER_PORT=8085
AMANAT_API_SERVER_PROTOCOL=http
```

Затем измените код в `reconciliation.py`:

```python
import os
from odoo.tools.config import config

# Конфигурация API сервера
API_SERVER_HOST = os.getenv('AMANAT_API_SERVER_HOST', 'localhost')
API_SERVER_PORT = os.getenv('AMANAT_API_SERVER_PORT', '8085')
API_SERVER_PROTOCOL = os.getenv('AMANAT_API_SERVER_PROTOCOL', 'http')
API_SERVER_BASE_URL = f"{API_SERVER_PROTOCOL}://{API_SERVER_HOST}:{API_SERVER_PORT}"
API_OPERATIONS_ENDPOINT = f"{API_SERVER_BASE_URL}/api/operations"
```

## Устранение неполадок

### Проблема: Connection refused
```
[Errno 111] В соединении отказано
```

**Решения:**
1. Проверьте, что сервер запущен: `netstat -tuln | grep 8085`
2. Проверьте правильность IP адреса в конфигурации
3. Убедитесь, что файрвол не блокирует порт 8085

### Проблема: Timeout
```
HTTPConnectionPool: Read timed out
```

**Решения:**
1. Увеличьте таймаут в коде: `timeout=120`
2. Проверьте производительность сервера
3. Проверьте размер данных в запросе

### Проблема: Invalid JSON response
```
Expecting value: line 1 column 1 (char 0)
```

**Решения:**
1. Проверьте логи сервера
2. Убедитесь, что сервер возвращает корректный JSON
3. Проверьте Content-Type заголовки

## Логирование

Добавьте больше логов для диагностики:

```python
_logger.info(f"Отправка запроса на {endpoint}")
_logger.debug(f"Данные запроса: {payload}")
_logger.info(f"Ответ сервера: {resp.status_code}")
_logger.debug(f"Тело ответа: {resp.text}")
```

## Мониторинг

Рекомендуется настроить мониторинг:
- Доступность сервера (ping)
- Время отклика API
- Количество успешных/неуспешных запросов
- Размер генерируемых файлов

## Контакты

При проблемах с настройкой API обращайтесь к:
- Администратору сервера
- Разработчикам модуля
- Команде DevOps 