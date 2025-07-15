# Исправление проблемы с наложением Excel превью на Word файлы

## Описание проблемы

При открытии Word файла в модальном окне превью Excel таблица могла оставаться видимой сверху, создавая наложение контента и путаницу для пользователя.

## Причина проблемы

1. **Недостаточная очистка контейнеров** - при переключении между типами файлов контейнеры не полностью очищались
2. **Отсутствие явного контроля видимости** - контейнеры `.XlsxTable` и `.MyDocs` не имели явного управления видимостью
3. **Остатки DOM элементов** - Excel таблицы могли оставаться в DOM после закрытия

## Реализованные исправления

### 1. Улучшенная функция очистки контейнеров

Добавлена функция `cleanupAllContainers()` которая:
- Очищает содержимое обоих контейнеров
- Явно скрывает контейнеры через `display: none`
- Удаляет все остатки Excel таблиц из DOM
- Добавляет подробное логирование

```javascript
function cleanupAllContainers() {
    const myDocs = document.querySelector('.MyDocs');
    const xlsxTable = document.querySelector('.XlsxTable');
    
    console.log('Очищаем контейнеры...');
    
    if (myDocs) {
        myDocs.innerHTML = '';
        myDocs.style.display = 'none';
        console.log('MyDocs контейнер очищен и скрыт');
    }
    
    if (xlsxTable) {
        xlsxTable.innerHTML = '';
        xlsxTable.style.display = 'none';
        console.log('XlsxTable контейнер очищен и скрыт');
    }
    
    // Удаляем все остатки Excel таблиц
    const existingTables = document.querySelectorAll('.excel-table, .dataframe, #MyTable');
    existingTables.forEach(table => {
        if (table.parentNode) {
            table.parentNode.removeChild(table);
        }
    });
    
    console.log('Очистка завершена');
}
```

### 2. Явное управление видимостью контейнеров

При обработке Excel файлов:
```javascript
// Убеждаемся, что Word контейнер скрыт
if (myDocs) {
    myDocs.style.display = 'none';
    myDocs.innerHTML = '';
}

if (xlsxTable) {
    xlsxTable.style.display = 'block';
    xlsxTable.innerHTML = data;
    // ...
}
```

При обработке Word файлов:
```javascript
// Убеждаемся, что Excel контейнер скрыт
if (xlsxTable) {
    xlsxTable.style.display = 'none';
    xlsxTable.innerHTML = '';
}

if (myDocs) {
    myDocs.style.display = 'block';
    myDocs.innerHTML = '';
    // ...
}
```

### 3. Улучшенная обработка ошибок

При возникновении ошибки загрузки:
```javascript
} catch (error) {
    console.error('Error loading file preview:', error);
    const myDocs = document.querySelector('.MyDocs');
    const xlsxTable = document.querySelector('.XlsxTable');
    
    // Скрываем Excel контейнер при ошибке
    if (xlsxTable) {
        xlsxTable.style.display = 'none';
        xlsxTable.innerHTML = '';
    }
    
    if (myDocs) {
        myDocs.style.display = 'block';
        myDocs.innerHTML = '<p style="color: red;">Ошибка при загрузке предпросмотра файла</p>';
    }
}
```

### 4. Очистка при закрытии модального окна

Обновлена функция `addCloseHandler()`:
```javascript
newCloseBtn.onclick = () => {
    console.log('Закрываем модальное окно...');
    modal.style.display = "none";
    cleanupAllContainers(); // Очищаем контейнеры при закрытии
    isPreviewActive = false;
};
```

### 5. Улучшенные CSS стили

Добавлены CSS правила для контейнеров:
```css
/* Контейнеры для разных типов файлов */
.XlsxTable {
    display: none; /* Скрыто по умолчанию */
    width: 100%;
    overflow: auto;
    max-height: 500px;
    position: relative;
    z-index: 1;
}

.MyDocs {
    display: none; /* Скрыто по умолчанию */
    width: 100%;
    overflow: auto;
    text-align: justify;
    padding: 30px;
    position: relative;
    z-index: 1;
}
```

## Измененные файлы

1. **`addons/amanat/static/src/js/attachment_preview.js`**
   - Добавлена функция `cleanupAllContainers()`
   - Улучшена логика обработки файлов
   - Добавлено явное управление видимостью
   - Улучшена обработка ошибок

2. **`addons/amanat/static/src/js/sverka_files_preview.js`**
   - Аналогичные изменения для модуля sverka_files

3. **`addons/amanat/static/src/css/attachment_preview.css`**
   - Добавлены CSS правила для контейнеров
   - Улучшено позиционирование элементов

## Результат

После внесения изменений:
- ✅ Word файлы открываются без наложения Excel превью
- ✅ Excel файлы открываются без отображения Word контента
- ✅ Корректное переключение между типами файлов
- ✅ Полная очистка при закрытии модального окна
- ✅ Подробное логирование для отладки

## Тестирование

Для проверки исправления:
1. Откройте Excel файл в превью
2. Закройте превью
3. Откройте Word файл в превью
4. Убедитесь, что Excel таблица не отображается
5. Повторите в обратном порядке

Все переходы должны происходить без наложения контента. 