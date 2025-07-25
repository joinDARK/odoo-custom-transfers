# Дашборд - Функционал заявок

## Обзор

В дашборд добавлены новые функции для отображения данных по заявкам с поддержкой двух диапазонов дат для сравнения.

## Добавленные функции

### 1. Основные данные по заявкам

**Отображаемые данные:**
- **Количество заявок** - общее количество заявок в рамках выбранного диапазона дат
- **Количество закрытых заявок** - заявки со статусом 'close'
- **Сумма закрытых заявок** - общая сумма всех закрытых заявок

### 2. Дополнительная аналитика

**Заявки по статусам (топ 5):**
- Показывает 5 самых частых статусов заявок
- Данные отсортированы по убыванию

**Заявки по типам сделок:**
- Импорт
- Экспорт
- Не указан

### 3. Сравнение по двум диапазонам дат

**Функционал:**
- Сравнение количества заявок
- Сравнение количества закрытых заявок
- Сравнение суммы закрытых заявок
- Расчет разности между периодами
- Цветовое выделение (зеленый для положительной разности, красный для отрицательной)

## Технические детали

### Backend (Python)

**Файл**: `addons/amanat/models/dashboard.py`

**Добавленные методы:**
1. `get_dashboard_data()` - обновлен для включения данных по заявкам
2. `get_zayavki_comparison_data()` - новый метод для сравнения двух диапазонов

**Возвращаемые данные:**
```python
{
    'zayavki_count': 150,
    'zayavki_closed': 120,
    'zayavki_closed_amount': 2500000.00,
    'zayavki_by_status': {'close': 120, 'waiting_rub': 30},
    'zayavki_by_month': [{'month': '2024-01', 'count': 45}],
    'zayavki_by_currency': {'RUB': 1200000, 'USD': 15000},
    'zayavki_by_deal_type': {'Импорт': 80, 'Экспорт': 70},
    'top_managers_by_zayavki': [{'name': 'Иванов И.И.', 'count': 25}]
}
```

### Frontend (JavaScript)

**Файл**: `addons/amanat/static/src/js/amanat_dashboard.js`

**Обновленное состояние:**
```javascript
zayavki: {
    total: 0,
    closed: 0,
    closedAmount: 0,
    byStatus: {},
    byMonth: [],
    byCurrency: {},
    byDealType: {}
}
```

**Добавленные функции:**
- `openZayavki()` - открытие списка заявок с применением фильтра по датам

### Frontend (XML)

**Файл**: `addons/amanat/static/src/xml/amanat_dashboard.xml`

**Добавленные секции:**
1. **Второй ряд - Заявки** - основные карточки с данными по заявкам
2. **Сравнение заявок по периодам** - секция сравнения данных

## Использование

### 1. Просмотр данных по заявкам

1. Откройте дашборд
2. Во втором ряду появятся карточки с данными по заявкам:
   - Заявки в рамках диапазона
   - Заявки по статусам (топ 5)
   - Заявки по типам сделок

### 2. Фильтрация по датам

1. Установите диапазон дат в поле "Диапазон дат 1"
2. Данные по заявкам будут отфильтрованы по полю `date_placement` (дата размещения)
3. Клик по карточке "Заявки в рамках диапазона" откроет список заявок с применённым фильтром

### 3. Сравнение периодов

1. Установите два диапазона дат
2. Нажмите кнопку "Применить диапазоны"
3. В нижней части дашборда появится секция "Сравнение заявок по периодам"
4. Данные будут показаны в трёх колонках:
   - Период 1
   - Период 2
   - Разница (с цветовым выделением)

## Структура данных

### Поля заявки (amanat.zayavka)

**Основные поля:**
- `date_placement` - дата размещения (используется для фильтрации)
- `status` - статус заявки
- `amount` - сумма заявки
- `currency` - валюта
- `deal_type` - тип сделки (import/export)
- `manager_ids` - менеджеры

**Статусы заявок:**
- `close` - заявка закрыта
- `cancel` - отменено клиентом
- `waiting_rub` - ждем рубли
- И другие рабочие статусы

## Примеры использования

### Пример 1: Анализ месячной активности
```
Диапазон дат 1: 01.12.2024 - 31.12.2024
Результат: 
- Количество заявок: 150
- Закрытые заявки: 120
- Сумма закрытых: 2,500,000 руб
```

### Пример 2: Сравнение двух месяцев
```
Период 1: 01.11.2024 - 30.11.2024
Период 2: 01.12.2024 - 31.12.2024

Результат сравнения:
- Разница количества: +20 заявок
- Разница закрытых: +15 заявок  
- Разница сумм: +500,000 руб
```

## Возможные расширения

1. **Графики по заявкам** - добавление диаграмм для заявок
2. **Конверсия** - расчет процента закрытых заявок
3. **Среднее время обработки** - аналитика по времени между статусами
4. **География заявок** - анализ по регионам/странам
5. **Менеджерская эффективность** - детальная аналитика по менеджерам 