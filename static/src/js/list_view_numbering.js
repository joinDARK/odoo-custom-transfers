/** @odoo-module **/

// Оптимизированное решение для добавления нумерации в таблицы Odoo
// Исправлены проблемы с производительностью и зависанием

class ListViewNumbering {
    constructor() {
        this.observer = null;
        this.processedTables = new WeakSet();
        this.tableObservers = new WeakMap();
        this.isUpdating = false; // Флаг для предотвращения циклов
        this.debounceTimeout = null;
        this.init();
    }

    init() {
        // Ждем загрузки DOM
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.start());
        } else {
            setTimeout(() => this.start(), 100); // Небольшая задержка для стабильности
        }
    }

    start() {
        // Добавляем стили
        this.addStyles();
        
        // Обрабатываем существующие таблицы с задержкой
        setTimeout(() => {
            this.processExistingTables();
            this.startObserver();
        }, 500);
    }

    addStyles() {
        if (document.getElementById('amanat_list_numbering_styles')) {
            return;
        }

        const style = document.createElement('style');
        style.id = 'amanat_list_numbering_styles';
        style.textContent = `
            /* Стили для нумерации таблиц */
            .amanat_row_number_header,
            .amanat_row_number_cell {
                width: 50px !important;
                min-width: 50px !important;
                max-width: 50px !important;
                text-align: center !important;
                font-weight: bold !important;
                user-select: none !important;
                padding: 8px 4px !important;
            }
            
            .amanat_row_number_header {
                background-color: #e9ecef !important;
                color: #495057 !important;
                border-right: 1px solid #dee2e6 !important;
                position: sticky;
                left: 0;
                z-index: 10;
            }
            
            .amanat_row_number_cell {
                background-color: #f8f9fa !important;
                color: #6c757d !important;
                border-right: 1px solid #dee2e6 !important;
                position: sticky;
                left: 0;
                z-index: 9;
                vertical-align: middle !important;
            }
            
            /* Для темной темы */
            body.o_dark .amanat_row_number_header {
                background-color: #2f3349 !important;
                color: #adb5bd !important;
                border-color: #495057 !important;
            }
            
            body.o_dark .amanat_row_number_cell {
                background-color: #363b4d !important;
                color: #adb5bd !important;
                border-color: #495057 !important;
            }
            
            /* Убираем возможность сортировки */
            .amanat_row_number_header {
                cursor: default !important;
            }
            
            .amanat_row_number_header:hover {
                background-color: #e9ecef !important;
            }
        `;
        
        document.head.appendChild(style);
    }

    processExistingTables() {
        const tables = document.querySelectorAll('.o_list_table:not([data-amanat-numbered]), table.o_list_view:not([data-amanat-numbered])');
        tables.forEach(table => this.addNumberingToTable(table));
    }

    startObserver() {
        // Используем более щадящий наблюдатель
        this.observer = new MutationObserver((mutations) => {
            if (this.isUpdating) return; // Игнорируем наши собственные изменения
            
            // Дебаунсинг для предотвращения частых вызовов
            clearTimeout(this.debounceTimeout);
            this.debounceTimeout = setTimeout(() => {
                this.processMutations(mutations);
            }, 100);
        });

        this.observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: false, // Не отслеживаем изменения атрибутов
            characterData: false // Не отслеживаем изменения текста
        });
    }

    processMutations(mutations) {
        const tablesToProcess = new Set();
        
        mutations.forEach(mutation => {
            mutation.addedNodes.forEach(node => {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    // Ищем только новые таблицы
                    if (node.matches && node.matches('.o_list_table:not([data-amanat-numbered]), table.o_list_view:not([data-amanat-numbered])')) {
                        tablesToProcess.add(node);
                    }
                    
                    const tables = node.querySelectorAll ? 
                        node.querySelectorAll('.o_list_table:not([data-amanat-numbered]), table.o_list_view:not([data-amanat-numbered])') : [];
                    
                    tables.forEach(table => tablesToProcess.add(table));
                }
            });
        });

        // Обрабатываем только новые таблицы
        tablesToProcess.forEach(table => {
            if (!this.processedTables.has(table)) {
                this.addNumberingToTable(table);
            }
        });
    }

    addNumberingToTable(table) {
        // Защита от повторной обработки
        if (this.processedTables.has(table) || table.hasAttribute('data-amanat-numbered')) {
            return;
        }

        const thead = table.querySelector('thead');
        const tbody = table.querySelector('tbody');
        
        if (!thead || !tbody) {
            return;
        }

        this.isUpdating = true; // Устанавливаем флаг

        try {
            // Добавляем заголовок
            this.addHeaderColumn(thead);
            
            // Добавляем нумерацию строк
            this.addRowNumbers(tbody);
            
            // Отмечаем таблицу как обработанную
            table.setAttribute('data-amanat-numbered', 'true');
            this.processedTables.add(table);
            
            // Настраиваем наблюдение за изменениями только содержимого tbody
            this.setupTableObserver(table, tbody);
            
        } finally {
            this.isUpdating = false; // Сбрасываем флаг
        }
    }

    addHeaderColumn(thead) {
        const headerRow = thead.querySelector('tr');
        if (!headerRow || headerRow.querySelector('.amanat_row_number_header')) {
            return;
        }

        const numberTh = document.createElement('th');
        numberTh.className = 'amanat_row_number_header';
        numberTh.textContent = '№';
        
        headerRow.insertBefore(numberTh, headerRow.firstChild);
    }

    addRowNumbers(tbody) {
        const rows = tbody.querySelectorAll('tr:not([data-amanat-row-numbered])');
        
        rows.forEach((row, index) => {
            const numberTd = document.createElement('td');
            numberTd.className = 'amanat_row_number_cell';
            numberTd.textContent = (index + 1).toString();
            
            row.insertBefore(numberTd, row.firstChild);
            row.setAttribute('data-amanat-row-numbered', 'true');
        });
    }

    setupTableObserver(table, tbody) {
        // Отключаем предыдущий наблюдатель для этой таблицы
        if (this.tableObservers.has(table)) {
            this.tableObservers.get(table).disconnect();
        }

        // Создаем новый наблюдатель только для tbody
        const tableObserver = new MutationObserver((mutations) => {
            if (this.isUpdating) return;
            
            // Проверяем, добавились ли новые строки
            let hasNewRows = false;
            mutations.forEach(mutation => {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === Node.ELEMENT_NODE && 
                        node.tagName === 'TR' && 
                        !node.hasAttribute('data-amanat-row-numbered')) {
                        hasNewRows = true;
                    }
                });
            });

            if (hasNewRows) {
                this.updateTableNumbers(tbody);
            }
        });

        tableObserver.observe(tbody, {
            childList: true,
            subtree: false // Не наблюдаем за вложенными элементами
        });

        this.tableObservers.set(table, tableObserver);
    }

    updateTableNumbers(tbody) {
        this.isUpdating = true;
        
        try {
            const rows = tbody.querySelectorAll('tr');
            
            rows.forEach((row, index) => {
                let numberCell = row.querySelector('.amanat_row_number_cell');
                
                if (!numberCell) {
                    // Создаем новую ячейку для новой строки
                    numberCell = document.createElement('td');
                    numberCell.className = 'amanat_row_number_cell';
                    row.insertBefore(numberCell, row.firstChild);
                    row.setAttribute('data-amanat-row-numbered', 'true');
                }
                
                // Обновляем номер
                numberCell.textContent = (index + 1).toString();
            });
        } finally {
            this.isUpdating = false;
        }
    }

    destroy() {
        if (this.observer) {
            this.observer.disconnect();
        }
        
        // Отключаем все наблюдатели таблиц
        this.tableObservers.forEach(observer => observer.disconnect());
        this.tableObservers.clear();
        
        clearTimeout(this.debounceTimeout);
    }
}

// Инициализируем нумерацию при загрузке модуля
const listNumbering = new ListViewNumbering();

// Экспортируем для возможности управления извне
window.amanatListNumbering = listNumbering; 