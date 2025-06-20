/** @odoo-module **/

import { Component, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";

class FixedColumnsCalculator {
    constructor() {
        this.observer = null;
        this.routeObserver = null;
        this.initialized = false;
        this.debounceTimer = null;
        this.isProcessing = false;
        this.lastTableHTML = '';
    }

    init() {
        if (this.initialized) return;
        
        console.log('🔧 Инициализация калькулятора фиксированных колонок');
        this.setupMutationObserver();
        this.setupRouteObserver();
        this.calculateAndApplyPositions();
        this.initialized = true;
    }

    debounce(func, delay) {
        return (...args) => {
            clearTimeout(this.debounceTimer);
            this.debounceTimer = setTimeout(() => func.apply(this, args), delay);
        };
    }

    setupMutationObserver() {
        // Дебаунсированная функция для пересчета
        const debouncedRecalculate = this.debounce(() => {
            if (!this.isProcessing) {
                console.log('🔄 Обнаружены изменения в таблице, пересчитываем позиции');
                this.calculateAndApplyPositions();
            }
        }, 200);

        // Наблюдаем за изменениями в DOM
        this.observer = new MutationObserver((mutations) => {
            let shouldRecalculate = false;
            
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList' || mutation.type === 'attributes') {
                    const target = mutation.target;
                    if (target.classList && (
                        target.classList.contains('o_list_view') ||
                        target.classList.contains('o_list_table') ||
                        target.closest('.o_list_view')
                    )) {
                        shouldRecalculate = true;
                    }
                }
            });

            if (shouldRecalculate) {
                debouncedRecalculate();
            }
        });

        this.observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['class', 'style']
        });
    }

    setupRouteObserver() {
        // Отдельный наблюдатель для смены страниц
        const debouncedRouteRecalculate = this.debounce(() => {
            console.log('🔄 Обнаружена новая страница со списками, переинициализируем');
            this.calculateAndApplyPositions();
        }, 500);

        this.routeObserver = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    const addedNodes = Array.from(mutation.addedNodes);
                    const hasListView = addedNodes.some(node => 
                        node.nodeType === 1 && (
                            node.classList?.contains('o_action_manager') ||
                            node.classList?.contains('o_content') ||
                            node.querySelector?.('.o_list_view')
                        )
                    );
                    
                    if (hasListView) {
                        debouncedRouteRecalculate();
                    }
                }
            });
        });
        
        const targetElement = document.querySelector('.o_action_manager') || document.body;
        this.routeObserver.observe(targetElement, {
            childList: true,
            subtree: true
        });
    }

    calculateAndApplyPositions() {
        if (this.isProcessing) return;
        this.isProcessing = true;

        const tables = document.querySelectorAll('.o_list_view:not(.o_field_many2many) .o_list_table');
        
        // Проверяем изменения в таблицах
        const currentTableHTML = Array.from(tables).map(t => t.outerHTML).join('');
        if (currentTableHTML === this.lastTableHTML) {
            this.isProcessing = false;
            return;
        }
        this.lastTableHTML = currentTableHTML;
        
        console.log(`📊 Найдено ${tables.length} таблиц для обработки`);

        tables.forEach((table, tableIndex) => {
            console.log(`\n📋 Обрабатываем таблицу ${tableIndex + 1}:`);
            this.processTable(table, tableIndex);
        });

        this.isProcessing = false;
    }

    processTable(table, tableIndex) {
        // Получаем первую строку для расчета ширин
        const firstRow = table.querySelector('thead tr') || table.querySelector('tbody tr');
        if (!firstRow) {
            console.log('⚠️ Не найдена первая строка таблицы');
            return;
        }

        const cells = firstRow.querySelectorAll('th, td');
        if (cells.length < 4) {
            console.log(`⚠️ В таблице меньше 4 колонок (${cells.length})`);
            return;
        }

        // Очищаем старые классы границ
        this.clearOldBorderClasses(table);

        // Рассчитываем позиции первых 4 колонок
        const positions = this.calculatePositions(cells);
        console.log('📏 Рассчитанные позиции:', positions);

        // Применяем позиции к заголовкам
        this.applyPositionsToHeaders(table, positions);
        
        // Применяем позиции к строкам данных
        this.applyPositionsToRows(table, positions);
    }

    clearOldBorderClasses(table) {
        // Убираем старые классы границ со всех ячеек
        const allCells = table.querySelectorAll('th, td');
        allCells.forEach(cell => {
            cell.classList.remove('fixed-column-with-border');
        });
        console.log('🧹 Очищены старые классы границ');
    }

    isManyToManyCell(cell) {
        // Проверяем различные признаки many2many полей
        const classNames = cell.className || '';
        const cellContent = cell.innerHTML || '';
        
        // Проверяем классы ячейки
        if (classNames.includes('o_field_many2many') || 
            classNames.includes('o_many2many') ||
            classNames.includes('o_field_widget_many2many')) {
            return true;
        }
        
        // Проверяем содержимое ячейки на наличие many2many виджетов
        if (cellContent.includes('o_field_many2many') ||
            cellContent.includes('o_many2many_tags') ||
            cellContent.includes('o_field_widget_many2many')) {
            return true;
        }
        
        // Проверяем родительские элементы
        const fieldWidget = cell.querySelector('.o_field_widget');
        if (fieldWidget && fieldWidget.classList.contains('o_field_many2many')) {
            return true;
        }
        
        // Проверяем атрибут name для many2many полей
        const nameAttr = cell.getAttribute('name') || '';
        if (nameAttr && cell.closest('.o_field_many2many')) {
            return true;
        }
        
        return false;
    }

    calculatePositions(cells) {
        const positions = [0]; // Первая колонка всегда в позиции 0
        let cumulativeWidth = 0;
        const borderWidth = 2; // Ширина границы в пикселях (border-right: 2px)

        for (let i = 0; i < Math.min(4, cells.length - 1); i++) {
            const cell = cells[i];
            const width = cell.offsetWidth;
            
            console.log(`  Колонка ${i + 1}: ширина = ${width}px`);
            
            cumulativeWidth += width;
            
            // Вычитаем ширину границы из позиции, чтобы избежать пустого пространства
            // Для всех колонок кроме первой (у первой нет левой границы для вычитания)
            const adjustedPosition = i === 0 ? cumulativeWidth : cumulativeWidth - (borderWidth * (i + 1));
            
            console.log(`    - Исходная позиция: ${cumulativeWidth}px`);
            console.log(`    - Скорректированная позиция: ${adjustedPosition}px (вычтено ${borderWidth * (i + 1)}px границ)`);
            
            positions.push(adjustedPosition);
        }

        return positions.slice(0, 4); // Возвращаем только первые 4 позиции
    }

    applyPositionsToHeaders(table, positions) {
        const headerCells = table.querySelectorAll('thead th:nth-child(-n+4)');
        
        headerCells.forEach((cell, index) => {
            if (index < positions.length) {
                // Проверяем, не является ли это many2many полем
                if (this.isManyToManyCell(cell)) {
                    console.log(`  ⏭️ Пропускаем заголовок ${index + 1}: many2many поле`);
                    return;
                }
                
                // Устанавливаем позицию через inline стиль
                cell.style.setProperty('left', `${positions[index]}px`, 'important');
                
                // Добавляем CSS класс для границ
                cell.classList.add('fixed-column-with-border');
                
                console.log(`  ✅ Заголовок ${index + 1}: установлен left = ${positions[index]}px, добавлен класс границы`);
                console.log(`    - Классы: ${cell.className}`);
            }
        });
    }

    applyPositionsToRows(table, positions) {
        const rows = table.querySelectorAll('tbody tr');
        
        rows.forEach((row, rowIndex) => {
            const cells = row.querySelectorAll('td:nth-child(-n+4)');
            
            cells.forEach((cell, cellIndex) => {
                if (cellIndex < positions.length) {
                    // Проверяем, не является ли это many2many полем
                    // if (this.isManyToManyCell(cell)) {
                    //     if (rowIndex === 0) {
                    //         console.log(`  ⏭️ Пропускаем ячейку ${cellIndex + 1}: many2many поле`);
                    //     }
                    //     return;
                    // }
                    
                    // Устанавливаем позицию через inline стиль
                    cell.style.setProperty('left', `${positions[cellIndex]}px`, 'important');
                    
                    // Добавляем CSS класс для границ
                    cell.classList.add('fixed-column-with-border');
                    
                    // Выводим отладку только для первой строки, чтобы не засорять консоль
                    if (rowIndex === 0) {
                        console.log(`  ✅ Ячейка ${cellIndex + 1}: установлен left = ${positions[cellIndex]}px, добавлен класс границы`);
                        console.log(`    - Классы: ${cell.className}`);
                    }
                }
            });
        });
    }

    destroy() {
        if (this.observer) {
            this.observer.disconnect();
            this.observer = null;
        }
        if (this.routeObserver) {
            this.routeObserver.disconnect();
            this.routeObserver = null;
        }
        clearTimeout(this.debounceTimer);
        this.initialized = false;
        console.log('🗑️ Калькулятор фиксированных колонок отключен');
    }
}

// Создаем глобальный экземпляр
const fixedColumnsCalculator = new FixedColumnsCalculator();

// Инициализируем при загрузке DOM
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        fixedColumnsCalculator.init();
    });
} else {
    fixedColumnsCalculator.init();
}

export default fixedColumnsCalculator;

// Добавляем глобальную функцию для ручной отладки
window.debugFixedColumns = () => {
    console.log('🔍 РУЧНАЯ ОТЛАДКА ФИКСИРОВАННЫХ КОЛОНОК');
    console.log('=====================================');
    
    const tables = document.querySelectorAll('.o_list_view:not(.o_field_many2many) .o_list_table');
    console.log(`📊 Найдено таблиц: ${tables.length}`);
    
    tables.forEach((table, index) => {
        console.log(`\n📋 ТАБЛИЦА ${index + 1}:`);
        console.log('Element:', table);
        
        const thead = table.querySelector('thead');
        const tbody = table.querySelector('tbody');
        
        console.log(`  - Заголовок: ${thead ? 'найден' : 'НЕ НАЙДЕН'}`);
        console.log(`  - Тело: ${tbody ? 'найден' : 'НЕ НАЙДЕН'}`);
        
        if (thead) {
            const headerCells = thead.querySelectorAll('th');
            console.log(`  - Колонок в заголовке: ${headerCells.length}`);
            
            headerCells.forEach((cell, cellIndex) => {
                if (cellIndex < 4) {
                    console.log(`    Колонка ${cellIndex + 1}:`);
                    console.log(`      - offsetWidth: ${cell.offsetWidth}px`);
                    console.log(`      - clientWidth: ${cell.clientWidth}px`);
                    console.log(`      - scrollWidth: ${cell.scrollWidth}px`);
                    console.log(`      - текущий left: ${cell.style.left || 'не установлен'}`);
                    console.log(`      - CSS классы: ${cell.className || 'нет классов'}`);
                    console.log(`      - Есть класс границы: ${cell.classList.contains('fixed-column-with-border') ? 'ДА' : 'НЕТ'}`);
                    console.log(`      - Many2Many поле: ${fixedColumnsCalculator.isManyToManyCell(cell) ? 'ДА' : 'НЕТ'}`);
                    
                    // Проверяем вычисленные стили
                    const computedStyle = window.getComputedStyle(cell);
                    console.log(`      - Вычисленный border-right: ${computedStyle.borderRight || 'не установлен'}`);
                    console.log(`      - Вычисленный box-shadow: ${computedStyle.boxShadow || 'не установлен'}`);
                }
            });
        }
        
        if (tbody) {
            const firstRow = tbody.querySelector('tr');
            if (firstRow) {
                const dataCells = firstRow.querySelectorAll('td');
                console.log(`  - Колонок в первой строке: ${dataCells.length}`);
            }
        }
    });
    
    console.log('\n🔧 Пересчитываем позиции...');
    fixedColumnsCalculator.calculateAndApplyPositions();
};

console.log('💡 Для отладки выполните в консоли: debugFixedColumns()'); 