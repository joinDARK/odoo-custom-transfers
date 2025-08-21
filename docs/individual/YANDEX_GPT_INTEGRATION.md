# Интеграция с YandexGPT для переводов

## Описание

Модуль использует YandexGPT API для автоматического перевода названий организаций с русского языка на английский при генерации документа "Индивидуал". Это обеспечивает профессиональный и точный перевод юридических названий компаний.

## Архитектура интеграции

### Компоненты системы

1. **Метод перевода** (`_translate_text_via_yandex_gpt`)
2. **Существующая инфраструктура YandexGPT** (`_send_text_to_yandex_gpt_with_prompt`)
3. **Конфигурация API** (системные параметры)
4. **Обработка ошибок** (fallback механизмы)

## Настройка YandexGPT

### Системные параметры

Для работы модуля необходимо настроить следующие параметры в Odoo:

```python
# Настройки → Общие настройки → YandexGPT API Configuration
amanat.ygpt.api_key = "ваш_api_ключ_yandex_gpt"
amanat.ygpt.folder_id = "ваш_folder_id_yandex_cloud"
```

### Получение API ключей

1. **Регистрация в Yandex Cloud:**
   - Перейдите на https://cloud.yandex.ru/
   - Создайте аккаунт или войдите в существующий

2. **Создание сервисного аккаунта:**
   ```bash
   yc iam service-account create --name amanat-gpt-service
   ```

3. **Получение API ключа:**
   ```bash
   yc iam api-key create --service-account-name amanat-gpt-service
   ```

4. **Получение Folder ID:**
   ```bash
   yc config list
   ```

## Реализация перевода

### Основной метод

```python
def _translate_text_via_yandex_gpt(self, text):
    """Переводит текст с русского на английский через YandexGPT"""
    if not text or not text.strip():
        return ""
    
    try:
        # Промпт для перевода
        translation_prompt = f"""Переведи следующий текст с русского языка на английский язык. 
Это название организации или компании, поэтому перевод должен быть профессиональным и точным.
Если это юридическое лицо (ООО, АО и т.д.), переведи правильно юридическую форму.
Верни только переведенный текст без дополнительных комментариев.

Текст для перевода: {text}"""
        
        # Используем существующую функцию для отправки в YandexGPT
        translated_text = self._send_text_to_yandex_gpt_with_prompt("", translation_prompt)
        
        if translated_text and translated_text.strip():
            result = translated_text.strip()
            _logger.info(f"[ПЕРЕВОД] '{text}' -> '{result}'")
            return result
        else:
            _logger.warning(f"[ПЕРЕВОД] Не удалось перевести '{text}', возвращаем оригинал")
            return text
            
    except Exception as e:
        _logger.error(f"[ПЕРЕВОД] Ошибка при переводе '{text}': {str(e)}")
        return text
```

### Промпт для перевода

Специально разработанный промпт обеспечивает:

1. **Контекст задачи:** Указание на то, что переводится название организации
2. **Требования к качеству:** Профессиональный и точный перевод
3. **Специфика юридических форм:** Правильный перевод ООО, АО, ИП и т.д.
4. **Формат ответа:** Только переведенный текст без комментариев

```
Переведи следующий текст с русского языка на английский язык. 
Это название организации или компании, поэтому перевод должен быть профессиональным и точным.
Если это юридическое лицо (ООО, АО и т.д.), переведи правильно юридическую форму.
Верни только переведенный текст без дополнительных комментариев.

Текст для перевода: {text}
```

## Примеры переводов

### Юридические формы

| Русский | Английский | Комментарий |
|---------|------------|-------------|
| `ООО "Импекс-Ф"` | `Implex-F LLC` | Limited Liability Company |
| `АО "Сбербанк"` | `Sberbank JSC` | Joint Stock Company |
| `ПАО "Газпром"` | `Gazprom PJSC` | Public Joint Stock Company |
| `ИП Иванов И.И.` | `Ivanov I.I. Individual Entrepreneur` | Individual Entrepreneur |
| `ЗАО "Техносила"` | `Technosila CJSC` | Closed Joint Stock Company |

### Банки и финансовые организации

| Русский | Английский |
|---------|------------|
| `Сбербанк России` | `Sberbank of Russia` |
| `ВТБ Банк` | `VTB Bank` |
| `Альфа-Банк` | `Alfa-Bank` |
| `Банк Открытие` | `Otkritie Bank` |
| `Тинькофф Банк` | `Tinkoff Bank` |

### Агенты и субагенты

| Русский | Английский |
|---------|------------|
| `ТДК` | `TDK` |
| `СТЕЛЛАР` | `STELLAR` |
| `Транзит Деловой Компании` | `Transit Business Company` |

## Обработка ошибок

### Типы ошибок и их обработка

1. **Отсутствие конфигурации YandexGPT:**
   ```python
   if not cfg['api_key'] or not cfg['folder_id']:
       _logger.error("Не настроены API ключ и/или Folder ID")
       return text  # Возвращаем оригинал
   ```

2. **Ошибки сети:**
   ```python
   except requests.exceptions.RequestException as e:
       _logger.error(f"Ошибка сети при обращении к YandexGPT: {e}")
       return text
   ```

3. **Ошибки API:**
   ```python
   if response.status_code != 200:
       _logger.error(f"Ошибка API YandexGPT: {response.status_code}")
       return text
   ```

4. **Пустой ответ:**
   ```python
   if not translated_text or not translated_text.strip():
       _logger.warning("Получен пустой ответ от YandexGPT")
       return text
   ```

### Fallback стратегия

При любой ошибке система возвращает оригинальный текст:

```python
# Принцип "graceful degradation"
try:
    return translate_via_api(text)
except Exception:
    return text  # Всегда возвращаем что-то осмысленное
```

## Логирование и мониторинг

### Уровни логирования

1. **INFO:** Успешные переводы
   ```python
   _logger.info(f"[ПЕРЕВОД] '{text}' -> '{result}'")
   ```

2. **WARNING:** Неудачные переводы с fallback
   ```python
   _logger.warning(f"[ПЕРЕВОД] Не удалось перевести '{text}', возвращаем оригинал")
   ```

3. **ERROR:** Критические ошибки
   ```python
   _logger.error(f"[ПЕРЕВОД] Ошибка при переводе '{text}': {str(e)}")
   ```

### Мониторинг производительности

```python
import time

start_time = time.time()
result = self._translate_text_via_yandex_gpt(text)
duration = time.time() - start_time

_logger.info(f"[ПЕРЕВОД] Время выполнения: {duration:.2f}с")
```

## Оптимизация и производительность

### Стратегии оптимизации

1. **Пропуск пустых значений:**
   ```python
   if not text or not text.strip():
       return ""
   ```

2. **Кэширование (будущее развитие):**
   ```python
   # Потенциальное кэширование переводов
   cache_key = f"translation_{hash(text)}"
   if cache_key in translation_cache:
       return translation_cache[cache_key]
   ```

3. **Batch переводы (будущее развитие):**
   ```python
   # Групповой перевод для множественных полей
   def translate_batch(texts):
       # Отправка нескольких текстов за один запрос
       pass
   ```

### Ограничения API

- **Rate limiting:** YandexGPT имеет ограничения на количество запросов
- **Размер текста:** Максимальная длина текста для перевода
- **Таймауты:** Настройка таймаутов для предотвращения зависания

```python
# Настройки в _send_text_to_yandex_gpt_with_prompt
"completionOptions": {
    "stream": False,
    "temperature": 0.1,  # Низкая температура для точности
    "maxTokens": 1000
}
```

## Безопасность

### Защита API ключей

1. **Хранение в системных параметрах:**
   - API ключи хранятся в зашифрованном виде в базе данных
   - Доступ только через системные параметры Odoo

2. **Логирование без раскрытия секретов:**
   ```python
   # НЕ логируем API ключи
   _logger.info("Отправка запроса в YandexGPT")  # ✅
   _logger.info(f"API Key: {api_key}")           # ❌
   ```

3. **Валидация входных данных:**
   ```python
   # Защита от инъекций в промпт
   text = text.replace('"', '\\"').replace("'", "\\'")
   ```

### Аудит переводов

Все переводы логируются для аудита:

```python
_logger.info(f"[ПЕРЕВОД] Пользователь: {self.env.user.name}")
_logger.info(f"[ПЕРЕВОД] Заявка: {self.id}")
_logger.info(f"[ПЕРЕВОД] Исходный текст: '{text}'")
_logger.info(f"[ПЕРЕВОД] Переведенный текст: '{result}'")
```

## Тестирование

### Модульные тесты

```python
def test_translate_company_name(self):
    """Тест перевода названия компании"""
    original = "ООО \"Импекс-Ф\""
    expected = "Implex-F LLC"
    result = self._translate_text_via_yandex_gpt(original)
    self.assertEqual(result, expected)

def test_translate_empty_text(self):
    """Тест обработки пустого текста"""
    result = self._translate_text_via_yandex_gpt("")
    self.assertEqual(result, "")

def test_translate_api_error(self):
    """Тест обработки ошибки API"""
    # Мокаем ошибку API
    with patch('requests.post') as mock_post:
        mock_post.side_effect = Exception("API Error")
        result = self._translate_text_via_yandex_gpt("Тест")
        self.assertEqual(result, "Тест")  # Должен вернуть оригинал
```

### Интеграционные тесты

```python
def test_full_document_generation_with_translation(self):
    """Тест полной генерации документа с переводом"""
    # Создаем тестовую заявку
    zayavka = self.create_test_zayavka()
    
    # Генерируем документ
    result = zayavka.action_generate_individual_document()
    
    # Проверяем результат
    self.assertEqual(result['type'], 'ir.actions.client')
    self.assertEqual(result['tag'], 'reload')
```
