# Исправление проблемы с повторной отрисовкой Excel таблиц

## Проблема

При открытии превью Excel файлов таблицы отрисовывались несколько раз, что приводило к:
- Дублированию контента
- Появлению разных версий одной таблицы
- Неправильному отображению данных
- Производительным проблемам

## Причины проблемы

1. **Повторные вызовы функции трансформации** - `transformToExcelTable()` вызывалась несколько раз для одной таблицы
2. **Отсутствие очистки контейнера** - новый контент добавлялся к существующему
3. **Дублирование обработчиков событий** - модальное окно создавалось несколько раз
4. **Отсутствие защиты от параллельных вызовов** - функции могли вызываться одновременно

## Решение

### 1. Добавлена защита от повторных вызовов

#### В `attachment_preview.js`:
```javascript
// Глобальная переменная для отслеживания активного превью
let isPreviewActive = false;

async function handlePreviewOffline(ev) {
    // Предотвращаем повторные вызовы
    if (isPreviewActive) {
        console.log('Превью уже активно, игнорируем повторный вызов');
        return;
    }
    isPreviewActive = true;
    // ... код ...
    isPreviewActive = false;
}
```

#### В `sverka_files_preview.js`:
```javascript
export class SverkaFilesPreviewButton extends Component {
    setup() {
        this.isPreviewActive = false;
    }
    
    async showFilePreview(recordIds) {
        if (this.isPreviewActive) {
            return;
        }
        this.isPreviewActive = true;
        // ... код ...
        this.isPreviewActive = false;
    }
}
```

### 2. Добавлена полная очистка контейнеров

```javascript
// Полностью очищаем контейнеры перед добавлением нового содержимого
const myDocs = document.querySelector('.MyDocs');
const xlsxTable = document.querySelector('.XlsxTable');

if (myDocs) {
    myDocs.innerHTML = '';
}
if (xlsxTable) {
    xlsxTable.innerHTML = '';
}
```

### 3. Добавлена защита от повторной трансформации

```javascript
function transformToExcelTable(table) {
    // Проверяем, не была ли таблица уже обработана
    if (table.classList.contains('excel-transformed')) {
        console.log('Таблица уже была обработана, пропускаем');
        return;
    }
    
    // ... трансформация ...
    
    // Помечаем таблицу как обработанную
    table.classList.add('excel-transformed');
}
```

### 4. Добавлены проверки на существующие элементы

```javascript
// Проверяем, не добавлена ли уже corner cell
const existingCornerCell = headerRow.querySelector('.row-number');
if (!existingCornerCell) {
    // Добавляем пустую ячейку в левый верхний угол
    const cornerCell = document.createElement('th');
    cornerCell.className = 'row-number';
    // ...
}

// Проверяем, не добавлена ли уже ячейка с номером строки
const existingRowNumber = row.querySelector('.row-number');
if (!existingRowNumber) {
    // Добавляем номер строки в начало
    const rowNumberCell = document.createElement('td');
    // ...
}
```

### 5. Улучшена обработка событий

```javascript
function addCloseHandler(modal) {
    const closeBtn = modal.querySelector('#stop-preview-button');
    
    // Убираем предыдущие обработчики
    if (closeBtn) {
        // Клонируем элемент для удаления всех обработчиков
        const newCloseBtn = closeBtn.cloneNode(true);
        closeBtn.parentNode.replaceChild(newCloseBtn, closeBtn);
        
        // Добавляем новый обработчик
        newCloseBtn.onclick = () => {
            modal.style.display = "none";
            isPreviewActive = false;
        };
    }
    
    // Правильная обработка закрытия по клику вне модального окна
    const modalClickHandler = (event) => {
        if (event.target === modal) {
            modal.style.display = "none";
            isPreviewActive = false;
            window.removeEventListener('click', modalClickHandler);
        }
    };
    
    window.addEventListener('click', modalClickHandler);
}
```

### 6. Добавлено логирование для отладки

```javascript
console.log('Начинаем трансформацию таблицы...');
console.log(`Обрабатываем таблицу с ${rows.length} строками`);
console.log('Трансформация таблицы завершена');
```

### 7. Исправлены CSS анимации

```css
/* Анимация для строк таблицы - только для новых таблиц */
#MyTable tr:not(.excel-transformed *),
.dataframe tr:not(.excel-transformed *) {
    animation: fadeInRow 0.3s ease-out forwards;
    opacity: 0;
    transform: translateX(-10px);
}

/* Для уже обработанных таблиц убираем анимацию */
#MyTable.excel-transformed tr,
.dataframe.excel-transformed tr {
    animation: none;
    opacity: 1;
    transform: translateX(0);
}
```

## Результат

После исправления:
- ✅ Таблицы отрисовываются только один раз
- ✅ Нет дублирования контента
- ✅ Улучшена производительность
- ✅ Стабильная работа при многократных открытиях
- ✅ Корректное отображение данных

## Файлы изменены

- `static/src/js/attachment_preview.js` - основные исправления
- `static/src/js/sverka_files_preview.js` - аналогичные исправления
- `static/src/css/attachment_preview.css` - исправления анимаций

## Тестирование

Для тестирования исправлений:
1. Откройте превью Excel файла
2. Закройте и откройте снова несколько раз
3. Убедитесь, что таблица отображается корректно
4. Проверьте консоль браузера на наличие логов

Все исправления полностью обратно совместимы и не влияют на существующую функциональность. 