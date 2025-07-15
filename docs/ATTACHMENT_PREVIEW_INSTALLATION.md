# Инструкция по установке функционала Preview Offline

## Предварительные требования

### Системные требования
- Odoo 18.0+
- Python 3.8+
- Ubuntu 20.04+ / CentOS 8+ / Windows 10+

### Права доступа
- Права администратора системы
- Доступ к файлам модуля Odoo
- Возможность перезапуска сервера Odoo

## Пошаговая установка

### Шаг 1: Установка Python зависимостей

```bash
# Для Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3-pip

# Установка необходимых пакетов
pip3 install pandas python-docx openpyxl xlrd requests

# Для CentOS/RHEL
sudo yum install python3-pip
pip3 install pandas python-docx openpyxl xlrd requests

# Для Windows
pip install pandas python-docx openpyxl xlrd requests
```

### Шаг 2: Проверка установки зависимостей

```bash
python3 -c "import pandas; print('pandas:', pandas.__version__)"
python3 -c "import docx; print('python-docx: OK')"
python3 -c "import openpyxl; print('openpyxl:', openpyxl.__version__)"
python3 -c "import xlrd; print('xlrd:', xlrd.__version__)"
```

Ожидаемый вывод:
```
pandas: 1.3.0+
python-docx: OK
openpyxl: 3.0.0+
xlrd: 2.0.0+
```

### Шаг 3: Проверка модуля chatter_attachments_manager

```bash
# Убедитесь, что модуль установлен
ls -la addons/chatter_attachments_manager/

# Проверьте статус в Odoo
# Apps → Installed → Search: "Chatter Attachment Manager"
```

### Шаг 4: Проверка файлов модуля amanat

Убедитесь, что следующие файлы присутствуют:

```bash
# Backend файлы
ls -la addons/amanat/models/ir_attachment.py
ls -la addons/amanat/models/sverka_files.py

# Frontend файлы
ls -la addons/amanat/static/src/js/attachment_preview.js
ls -la addons/amanat/static/src/js/attachment_preview_modal.js
ls -la addons/amanat/static/src/css/attachment_preview.css
ls -la addons/amanat/static/src/xml/attachment_preview.xml

# Конфигурация
ls -la addons/amanat/__manifest__.py
```

### Шаг 5: Обновление модуля

```bash
# Остановите сервер Odoo
sudo systemctl stop odoo

# Или через процесс
sudo killall odoo-bin

# Обновите модуль
./odoo-bin -c /etc/odoo/odoo.conf -u amanat -d your_database_name

# Или через интерфейс после запуска
# Apps → Installed → Search: "Amanat" → Upgrade
```

### Шаг 6: Перезапуск сервера

```bash
# Запустите сервер
sudo systemctl start odoo

# Или в режиме разработки
./odoo-bin -c /etc/odoo/odoo.conf --dev=all

# Проверьте статус
sudo systemctl status odoo
```

## Проверка работоспособности

### Тест 1: Проверка модального окна

1. Откройте любую запись с вложениями
2. Откройте консоль браузера (F12)
3. Выполните:
```javascript
console.log(document.getElementById('xlsx_preview'));
```
4. Результат должен показать элемент, а не `null`

### Тест 2: Проверка backend метода

1. Загрузите Excel файл в любую запись
2. Откройте консоль браузера
3. Выполните:
```javascript
odoo.env.services.orm.call(
    "ir.attachment", 
    "decode_content", 
    [1, "xlsx"]  // Замените 1 на ID вашего файла
).then(data => console.log(data));
```

### Тест 3: Проверка в Sverka Files

1. Перейдите в модуль Сверка файлы
2. Создайте новую запись
3. Загрузите Excel или Word файл
4. Проверьте появление кнопки предпросмотра

## Устранение проблем

### Проблема: Модуль не загружается

**Решение:**
```bash
# Проверьте логи
tail -f /var/log/odoo/odoo.log

# Проверьте синтаксис Python
python3 -m py_compile addons/amanat/models/ir_attachment.py

# Проверьте права доступа
sudo chown -R odoo:odoo addons/amanat/
```

### Проблема: JavaScript ошибки

**Решение:**
1. Очистите кэш браузера (Ctrl+Shift+Delete)
2. Проверьте консоль браузера на ошибки
3. Перезапустите сервер с флагом `--dev=all`

### Проблема: Python зависимости не найдены

**Решение:**
```bash
# Проверьте виртуальное окружение
which python3
which pip3

# Установите в правильное окружение
/path/to/odoo/venv/bin/pip install pandas python-docx openpyxl xlrd

# Или для system-wide установки
sudo pip3 install pandas python-docx openpyxl xlrd
```

### Проблема: Файлы не читаются

**Решение:**
1. Проверьте права доступа к файлам
2. Убедитесь, что файлы не повреждены
3. Пересохраните файлы в совместимом формате

## Настройка производительности

### Ограничения памяти

В `ir_attachment.py` настройте ограничения:
```python
# Максимальное количество строк для предпросмотра
MAX_PREVIEW_ROWS = 100

# Максимальное количество колонок
MAX_PREVIEW_COLS = 20

# Таймаут для загрузки файлов
REQUEST_TIMEOUT = 30
```

### Кэширование

Добавьте кэширование для часто используемых файлов:
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def decode_content_cached(self, attach_id, doc_type):
    # Кэшированная версия метода
    pass
```

## Мониторинг и логирование

### Включение отладки

В `ir_attachment.py`:
```python
import logging
_logger = logging.getLogger(__name__)

def decode_content(self, attach_id, doc_type):
    _logger.info("Processing file: %s, type: %s", attach_id, doc_type)
    # ... код метода
```

### Мониторинг производительности

```python
import time

def decode_content(self, attach_id, doc_type):
    start_time = time.time()
    try:
        # ... код метода
        result = process_file()
        return result
    finally:
        process_time = time.time() - start_time
        _logger.info("File processing took: %.2f seconds", process_time)
```

## Резервное копирование

### Создание бэкапа

```bash
# Создайте резервную копию модуля
tar -czf amanat_backup_$(date +%Y%m%d).tar.gz addons/amanat/

# Создайте резервную копию базы данных
pg_dump -h localhost -U odoo -d your_database > backup_$(date +%Y%m%d).sql
```

### Восстановление

```bash
# Восстановите модуль
tar -xzf amanat_backup_YYYYMMDD.tar.gz -C addons/

# Восстановите базу данных
psql -h localhost -U odoo -d your_database < backup_YYYYMMDD.sql
```

## Автоматизация

### Скрипт проверки

```bash
#!/bin/bash
# check_preview_functionality.sh

echo "Проверка функционала Preview Offline..."

# Проверка Python зависимостей
python3 -c "import pandas, docx, openpyxl, xlrd" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ Python зависимости: OK"
else
    echo "✗ Python зависимости: FAIL"
    exit 1
fi

# Проверка файлов
if [ -f "addons/amanat/models/ir_attachment.py" ]; then
    echo "✓ Backend файлы: OK"
else
    echo "✗ Backend файлы: FAIL"
    exit 1
fi

# Проверка JavaScript файлов
if [ -f "addons/amanat/static/src/js/attachment_preview.js" ]; then
    echo "✓ Frontend файлы: OK"
else
    echo "✗ Frontend файлы: FAIL"
    exit 1
fi

echo "Все проверки пройдены успешно!"
```

### Cron задача для мониторинга

```bash
# Добавьте в crontab
0 */6 * * * /path/to/check_preview_functionality.sh >> /var/log/odoo/preview_check.log 2>&1
```

## Обновления и миграции

### Обновление зависимостей

```bash
# Обновите Python пакеты
pip3 install --upgrade pandas python-docx openpyxl xlrd

# Проверьте совместимость
python3 -c "import pandas; print('pandas:', pandas.__version__)"
```

### Миграция данных

При обновлении модуля может потребоваться миграция:
```python
# migration.py
def migrate(cr, version):
    # Код миграции для новой версии
    pass
```

## Заключение

После выполнения всех шагов функционал Preview Offline должен работать корректно. Для поддержки обращайтесь к документации или в техническую поддержку.

### Контакты поддержки

- **Документация**: `addons/amanat/docs/`
- **Логи**: `/var/log/odoo/odoo.log`
- **Тестирование**: Используйте тестовую базу данных

### Полезные ссылки

- [Документация Odoo](https://www.odoo.com/documentation/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [Python-docx Documentation](https://python-docx.readthedocs.io/)
- [Openpyxl Documentation](https://openpyxl.readthedocs.io/) 