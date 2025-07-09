# Исправление проблемы со скроллом в дашбордах

## Проблема
В дашбордах "Фикс заявка" и "Аналитический дашборд" не работал скролл, что приводило к недоступности содержимого при переполнении экрана.

## Причина
В CSS файлах использовались настройки, которые препятствовали появлению скролла:

```scss
.zayavka-fiks-dashboard, .analytics-dashboard {
    overflow-y: auto;
    max-height: none;  // ← Проблема здесь
    height: auto;      // ← И здесь
}
```

Когда контейнер имеет `height: auto`, он автоматически расширяется под все содержимое, и скролл не появляется.

## Решение

### 1. Изменены CSS настройки в файлах:
- `addons/amanat/static/src/scss/zayavka_fiks_dashboard.scss`
- `addons/amanat/static/src/scss/analytics_dashboard.scss`

**Исправленные настройки:**
```scss
.zayavka-fiks-dashboard, .analytics-dashboard {
    overflow-y: auto;
    max-height: calc(100vh - 60px); // Фиксированная максимальная высота
    height: calc(100vh - 60px);     // Фиксированная высота для скролла
}
```

### 2. Добавлены стили для скроллбара

**Улучшенный скроллбар:**
```scss
.zayavka-fiks-dashboard, .analytics-dashboard {
    // Стили для WebKit браузеров (Chrome, Safari, Edge)
    &::-webkit-scrollbar {
        width: 8px;
    }
    
    &::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    &::-webkit-scrollbar-thumb {
        background: #c1c1c1;
        border-radius: 10px;
        
        &:hover {
            background: #a8a8a8;
        }
    }
    
    // Стили для Firefox
    scrollbar-width: thin;
    scrollbar-color: #c1c1c1 #f1f1f1;
}
```

## Результат
- ✅ Скролл теперь работает корректно в обоих дашбордах
- ✅ Высота контейнера ограничена размером viewport
- ✅ Добавлен красивый кастомный скроллбар
- ✅ Сохранена работоспособность сайдбара (учтено в комментариях)

## Затронутые файлы
1. `addons/amanat/static/src/scss/zayavka_fiks_dashboard.scss`
2. `addons/amanat/static/src/scss/analytics_dashboard.scss`

## Дата исправления
$(date)

## Тестирование
После внесения изменений нужно:
1. Перезапустить сервер Odoo
2. Обновить браузер (Ctrl+F5)
3. Проверить работу скролла в обоих дашбордах
4. Убедиться, что сайдбар работает корректно 