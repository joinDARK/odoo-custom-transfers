/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";

// Проверяем, что модуль загружается
console.log('📌 Amanat: pin_field_handler.js loaded!');

// Функция для поиска полей с классом pin и применения базовых стилей
function findPinFields() {
    console.log('📌 Searching for pin fields...');
    
    // Ищем таблицы с pin элементами
    const tables = document.querySelectorAll('table');
    console.log('📌 Found tables:', tables.length);
    
    tables.forEach((table, tableIndex) => {
        console.log('📌 Table:', table);
        
        // Ищем ячейки с классом pin в теле таблицы (класс может быть на td или внутри td)
        const pinCellsDirectly = table.querySelectorAll('tbody td.pin');
        const pinCellsInside = table.querySelectorAll('tbody td .pin');
        
        // Объединяем результаты и получаем родительские td элементы
        const allPinCells = new Set();
        
        // Добавляем td с прямым классом pin
        pinCellsDirectly.forEach(cell => allPinCells.add(cell));
        
        // Добавляем td, которые содержат элементы с классом pin
        pinCellsInside.forEach(element => {
            const parentTd = element.closest('td');
            if (parentTd) allPinCells.add(parentTd);
        });
        
        const pinCells = Array.from(allPinCells);
        console.log(`📌 Found pin cells: direct=${pinCellsDirectly.length}, inside=${pinCellsInside.length}, total unique=${pinCells.length}`);
        
        if (pinCells.length === 0) return;
        
        console.log(`📌 Table ${tableIndex} has ${pinCells.length} pin cells`);
        
        // Получаем все заголовки для определения индексов
        const allHeaders = table.querySelectorAll('thead th');
        const pinHeadersInfo = [];
        
        // Собираем уникальные имена полей из pin ячеек
        const pinFieldNames = new Set();
        pinCells.forEach((cell, index) => {
            // Пробуем получить имя поля из самой ячейки или из вложенного элемента
            let fieldName = cell.getAttribute('name');
            
            if (!fieldName) {
                // Ищем вложенный элемент с атрибутом name
                const nameElement = cell.querySelector('[name]');
                if (nameElement) {
                    fieldName = nameElement.getAttribute('name');
                }
            }
            
            console.log(`📌 Pin cell ${index}:`, {
                element: cell,
                name: fieldName,
                textContent: cell.textContent?.trim(),
                hasDirectName: !!cell.getAttribute('name'),
                hasNestedName: !!cell.querySelector('[name]')
            });
            
            if (fieldName) {
                pinFieldNames.add(fieldName);
            }
        });
        
        console.log('📌 Pin field names:', Array.from(pinFieldNames));
        
        // Для каждого уникального имени поля находим соответствующий заголовок
        pinFieldNames.forEach(fieldName => {
            const header = table.querySelector(`thead th[data-name="${fieldName}"]`);
            if (header) {
                // Определяем индекс колонки
                const columnIndex = Array.from(allHeaders).indexOf(header);
                
                pinHeadersInfo.push({
                    element: header,
                    columnIndex: columnIndex,
                    fieldName: fieldName,
                    width: 0 // будет измерено
                });
                
                console.log(`📌 Found pin header for field "${fieldName}" at column ${columnIndex}:`, header.textContent?.trim());
            }
        });
        
        // Сортируем по индексу колонки (слева направо)
        pinHeadersInfo.sort((a, b) => a.columnIndex - b.columnIndex);
        
        // Рассчитываем позиции и применяем стили
        if (pinHeadersInfo.length > 0) {
            calculateAndApplyPinPositions(table, pinHeadersInfo);
        }
    });
}

// Функция для расчета позиций и применения стилей
function calculateAndApplyPinPositions(table, pinHeadersInfo) {
    console.log('📌 Calculating pin positions...');
    
    // Проверяем наличие нумерации строк
    const hasRowNumberHeader = table.querySelector('thead .amanat_row_number_header');
    const hasRowNumberCells = table.querySelector('tbody .amanat_row_number_cell');
    const hasRowNumbers = hasRowNumberHeader || hasRowNumberCells;
    
    const INITIAL_OFFSET = hasRowNumbers ? 50 : 0; // Отступ только если есть нумерация
    console.log(`📌 Row numbers detected: header=${!!hasRowNumberHeader}, cells=${!!hasRowNumberCells}, offset=${INITIAL_OFFSET}px`);
    
    let currentLeft = INITIAL_OFFSET;
    
    pinHeadersInfo.forEach((headerInfo, pinIndex) => {
        const { element, columnIndex, fieldName } = headerInfo;
        
        // Измеряем ширину заголовка
        const rect = element.getBoundingClientRect();
        const width = Math.ceil(rect.width);
        headerInfo.width = width;
        
        // Определяем, является ли это последним pin полем
        const isLastPinField = pinIndex === pinHeadersInfo.length - 1;
        
        console.log(`📌 Pin header ${pinIndex} (field: ${fieldName}, column ${columnIndex}):`, {
            text: element.textContent?.trim(),
            width: width,
            leftPosition: currentLeft,
            isLast: isLastPinField
        });
        
        // Применяем стили к заголовку
        applyPinStyles(element, currentLeft, width, 'header', isLastPinField);
        
        // Применяем стили к соответствующим ячейкам в теле таблицы
        const tbody = table.querySelector('tbody');
        if (tbody) {
            // Ищем все ячейки с данным именем поля
            const pinCells = tbody.querySelectorAll(`td[name="${fieldName}"].pin`);
            pinCells.forEach(cell => {
                applyPinStyles(cell, currentLeft, width, 'cell', isLastPinField);
            });
            
            // Также применяем к ячейкам по индексу колонки (на всякий случай)
            const rows = tbody.querySelectorAll('tr');
            rows.forEach(row => {
                const cell = row.children[columnIndex];
                if (cell && cell.getAttribute('name') === fieldName) {
                    applyPinStyles(cell, currentLeft, width, 'cell', isLastPinField);
                }
            });
        }
        
        // Увеличиваем позицию для следующего pin поля
        currentLeft += width;
    });
    
    console.log('📌 Pin positions calculated and applied!');
}

// Функция для применения pin стилей
function applyPinStyles(element, leftPosition, width, type, isLastPinField = false) {
    element.style.setProperty('position', 'sticky', 'important');
    element.style.setProperty('left', leftPosition + 'px', 'important');
    element.style.setProperty('width', width + 'px', 'important');
    element.style.setProperty('background-color', 'var(--ListRenderer-thead-bg-color)', 'important');
    
    // Для заголовков сохраняем top: 0 и используем правильный z-index
    if (type === 'header') {
        element.style.setProperty('top', '0', 'important');
        element.style.setProperty('z-index', '16', 'important'); // Выше обычных заголовков
    } else {
        element.style.setProperty('z-index', '12', 'important');
    }
    
    // Добавляем CSS класс для синей черты только для последнего pin поля
    if (isLastPinField) {
        element.classList.add('pin-field-indicator');
        console.log(`📌 Added blue line indicator to last pin field`);
    }
    
    console.log(`📌 Applied pin styles to ${type}:`, {
        tagName: element.tagName,
        text: element.textContent?.trim(),
        left: leftPosition + 'px',
        width: width + 'px',
        hasIndicator: isLastPinField,
        zIndex: type === 'header' ? '16' : '12'
    });
}

// Расширяем ListRenderer для поиска pin элементов
patch(ListRenderer.prototype, {
    setup() {
        super.setup();
        console.log('📌 ListRenderer setup');
        
        // Пробуем запустить поиск сразу после setup
        setTimeout(() => {
            console.log('📌 Trying to find pin fields after setup...');
            findPinFields();
        }, 2000);
    },
    
    onRendered() {
        super.onRendered();
        console.log('📌 ListRenderer rendered');
        
        // Пробуем после рендера
        setTimeout(() => {
            findPinFields();
        }, 500);
    }
});
