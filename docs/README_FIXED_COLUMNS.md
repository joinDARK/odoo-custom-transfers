# Фиксация первых 4 колонок в таблицах

## Описание
Добавлена функциональность закрепления первых 4 колонок во всех таблицах (list view) модуля Amanat. При горизонтальном скролле первые 4 колонки остаются видимыми.

## Что было реализовано

### Фиксированные колонки:
1. **Кнопка перехода в форму** - кнопка с иконкой "fa-external-link"
2. **Основное поле** - обычно ID записи или название (name)
3. **Второе важное поле** - статус, дата или другое ключевое поле
4. **Третье важное поле** - дополнительная важная информация

## Технические детали

### Файлы изменений:
- `addons/amanat/static/src/css/style.css` - добавлены CSS стили для фиксации

### CSS особенности:
- Используется `position: sticky` для закрепления колонок
- Z-index управляет наложением элементов
- CSS переменные обеспечивают адаптивность ширин колонок
- Поддержка всех состояний строк (выбранная, новая, при наведении)

### Адаптивность:
- Мобильные устройства (≤ 768px): уменьшенные ширины колонок
- Планшеты (769px - 1024px): средние ширины
- Большие экраны (≥ 1400px): увеличенные ширины

## Применение изменений

### Для применения обновлений выполните:

1. **Обновление через интерфейс Odoo:**
   - Зайдите в Приложения
   - Найдите модуль "Amanat: Переводы"
   - Нажмите "Обновить"

2. **Или через командную строку:**
   ```bash
   ./odoo-bin -u amanat -d your_database_name
   ```

3. **Принудительное обновление ресурсов:**
   - Очистите кэш браузера (Ctrl+F5)
   - Или перезапустите сервер Odoo

## Проверка работы

После применения изменений:
1. Откройте любую таблицу в модуле Amanat
2. Прокрутите таблицу вправо
3. Убедитесь, что первые 4 колонки остаются видимыми

## Совместимость

Стили совместимы с:
- Odoo 17.x
- Всеми существующими темами оформления
- Мобильными и десктопными устройствами
- Режимом редактирования таблиц (editable="top")

## Техническая поддержка

При возникновении проблем проверьте:
1. Загружается ли CSS файл в браузере
2. Нет ли конфликтующих стилей
3. Корректно ли обновился модуль

Дата реализации: 2024
Авторы: IncubeAI команда 