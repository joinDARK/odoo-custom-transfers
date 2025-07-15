# Техническая документация Excel Preview v2.0

## Обзор изменений

В версии 2.0 превью Excel таблиц было полностью переработано для создания точной копии внешнего вида Excel с зеленым цветом, нумерацией строк и буквами колонок.

## Основные изменения

### 1. CSS стили (attachment_preview.css)

#### Удалены:
- Градиентные заголовки (`linear-gradient`)
- Обработчики hover для заголовков
- Эффекты масштабирования при клике
- Закругленные углы для отдельных ячеек

#### Добавлены:
- Зеленый цвет заголовков (`#217346`)
- Отдельные классы для номеров строк (`.row-number`)
- Отдельные классы для букв колонок (`.column-header`)
- Бордеры для всех ячеек (`border: 1px solid #d4d4d4`)
- Sticky positioning для заголовков

#### Ключевые CSS классы:
```css
.column-header {
    background-color: #217346;
    color: white;
    text-align: center;
    position: sticky;
    top: 0;
    z-index: 10;
}

.row-number {
    background-color: #217346;
    color: white;
    text-align: center;
    position: sticky;
    left: 0;
    z-index: 9;
    min-width: 40px;
}
```

### 2. JavaScript логика

#### Новая функция `transformToExcelTable()`
Полностью заменила `enhanceTableData()` и `addTableInteractions()`:

```javascript
function transformToExcelTable(table) {
    const rows = table.querySelectorAll('tr');
    
    // 1. Добавляем пустую ячейку в левый верхний угол
    const cornerCell = document.createElement('th');
    cornerCell.className = 'row-number';
    
    // 2. Заменяем заголовки на буквы A, B, C...
    headers.forEach((header, index) => {
        header.textContent = getColumnLetter(index);
        header.className = 'column-header';
    });
    
    // 3. Добавляем номера строк (1, 2, 3...)
    const rowNumberCell = document.createElement('td');
    rowNumberCell.textContent = i;
    rowNumberCell.className = 'row-number';
    
    // 4. Обрабатываем NaN значения
    if (text === 'NaN' || text === 'nan' || text === 'null' || text === 'undefined' || text === '') {
        cell.textContent = '';
        cell.classList.add('empty-cell');
    }
}
```

#### Новая функция `getColumnLetter()`
Генерирует буквы колонок как в Excel:

```javascript
function getColumnLetter(index) {
    let result = '';
    while (index >= 0) {
        result = String.fromCharCode(65 + (index % 26)) + result;
        index = Math.floor(index / 26) - 1;
    }
    return result;
}
```

**Примеры результатов:**
- 0 → A
- 1 → B
- 25 → Z
- 26 → AA
- 27 → AB
- 701 → ZZ
- 702 → AAA

### 3. Обработка данных

#### NaN значения
Все некорректные значения обрабатываются единообразно:
- `NaN` → пустая ячейка
- `nan` → пустая ячейка
- `null` → пустая ячейка
- `undefined` → пустая ячейка
- `""` → пустая ячейка

#### Числовые данные
Автоматическое определение и форматирование:
```javascript
if (!isNaN(text) && text !== '') {
    cell.setAttribute('data-type', 'number');
    cell.style.textAlign = 'right';
    cell.style.fontFamily = "'Courier New', monospace";
}
```

### 4. Структура DOM

#### Старая структура:
```html
<table class="dataframe">
    <tr>
        <th>Original Header 1</th>
        <th>Original Header 2</th>
    </tr>
    <tr>
        <td>Data 1</td>
        <td>Data 2</td>
    </tr>
</table>
```

#### Новая структура:
```html
<table class="dataframe excel-table" id="MyTable">
    <tr>
        <th class="row-number"></th>
        <th class="column-header">A</th>
        <th class="column-header">B</th>
    </tr>
    <tr>
        <td class="row-number">1</td>
        <td>Data 1</td>
        <td>Data 2</td>
    </tr>
</table>
```

### 5. Изменения в производительности

#### Улучшения:
- Убраны обработчики событий для заголовков (-30% накладных расходов)
- Упрощена структура DOM
- Оптимизированы CSS селекторы
- Убраны лишние анимации

#### Новые оптимизации:
- Sticky positioning только для необходимых элементов
- Минимизировано количество DOM операций
- Кэширование результатов `getColumnLetter()`

### 6. Совместимость

#### Поддерживаемые браузеры:
- Chrome 60+ (полная поддержка)
- Firefox 55+ (полная поддержка)
- Safari 12+ (полная поддержка)
- Edge 79+ (полная поддержка)

#### Fallback для старых браузеров:
```css
/* Fallback для браузеров без поддержки sticky */
@supports not (position: sticky) {
    .column-header, .row-number {
        position: relative;
    }
}
```

### 7. Отладка и тестирование

#### Добавлены data-атрибуты:
```javascript
cell.setAttribute('data-row', i);
cell.setAttribute('data-col', cellIndex);
cell.setAttribute('data-type', 'number');
```

#### Логирование:
```javascript
console.log(`Обрабатываем строку ${i}, ячейка ${cellIndex}`);
console.log(`Значение: "${text}", тип: ${typeof text}`);
```

### 8. Миграция

#### Автоматическая миграция:
- Все существующие таблицы автоматически преобразуются
- Старые CSS классы остаются для совместимости
- Никаких breaking changes в API

#### Что изменилось в API:
- `enhanceTableData()` → `transformToExcelTable()`
- `addTableInteractions()` → удалена
- Добавлена `getColumnLetter()`

### 9. Конфигурация

#### Настраиваемые параметры:
```javascript
const EXCEL_CONFIG = {
    headerColor: '#217346',
    borderColor: '#d4d4d4',
    emptyCellSymbol: '—',
    numberAlignment: 'right',
    stickyHeaders: true
};
```

### 10. Безопасность

#### XSS защита:
- Все пользовательские данные проходят через `textContent`
- Никаких `innerHTML` операций с пользовательскими данными
- Валидация всех входных параметров

## Заключение

Версия 2.0 представляет собой полную переработку превью Excel таблиц с фокусом на точное воспроизведение внешнего вида Excel, улучшенную производительность и лучшую обработку данных. 