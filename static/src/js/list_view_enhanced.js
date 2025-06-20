/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";

// Проверяем, что модуль загружается
console.log('🚀 Amanat: list_view_enhanced.js loaded!');

// Расширяем стандартный ListRenderer для поддержки real-time обновлений
patch(ListRenderer.prototype, {

    setup() {
        super.setup();
        
        console.log('🔧 Amanat: ListRenderer setup called');
        
        // Сохраняем ссылку на renderer в глобальном объекте для доступа из real-time сервиса
        if (!window.amanatListRenderers) {
            window.amanatListRenderers = new Map();
        }
        
        const model = this.props.list.model.config.resModel;
        window.amanatListRenderers.set(model, this);
        
        this.realtimeUpdater = new AmanatListRealtimeUpdater(this);
    },

    onMounted() {
        console.log('🎯 Amanat: ListRenderer onMounted called');
        
        // Устанавливаем фиксированные колонки после рендера
        setTimeout(() => this.setupStickyColumns(), 300);
        
        // Добавляем обработчик ресайза
        this._resizeHandler = () => {
            setTimeout(() => this.setupStickyColumns(), 100);
        };
        window.addEventListener('resize', this._resizeHandler);
    },

    setupStickyColumns() {
        const table = this.tableRef?.el;
        if (!table) {
            console.log('Amanat: Table not found');
            return;
        }
        
        console.log('Amanat: Starting sticky columns setup...');
        console.log('Amanat: Table element:', table);
        
        const thead = table.querySelector('thead');
        const tbody = table.querySelector('tbody');
        if (!thead || !tbody) {
            console.log('Amanat: thead or tbody not found', { thead, tbody });
            return;
        }
        
        // Получаем ВСЕ заголовки для анализа
        const allHeaders = thead.querySelectorAll('th');
        console.log('Amanat: All headers found:', allHeaders.length);
        
        // Логируем информацию о каждом заголовке
        allHeaders.forEach((th, index) => {
            console.log(`Amanat: Header ${index}:`, {
                element: th,
                textContent: th.textContent?.trim(),
                className: th.className,
                offsetWidth: th.offsetWidth,
                clientWidth: th.clientWidth,
                getBoundingClientRect: th.getBoundingClientRect(),
                style: th.style.cssText
            });
        });
        
        if (allHeaders.length < 4) {
            console.log('Amanat: Less than 4 headers found:', allHeaders.length);
            return;
        }
        
        // Получаем первую строку данных для сравнения
        const firstRow = tbody.querySelector('tr');
        if (firstRow) {
            const allCells = firstRow.querySelectorAll('td');
            console.log('Amanat: First row cells:', allCells.length);
            
            allCells.forEach((td, index) => {
                if (index < 6) { // Логируем первые 6 ячеек
                    console.log(`Amanat: Cell ${index}:`, {
                        element: td,
                        textContent: td.textContent?.trim(),
                        className: td.className,
                        offsetWidth: td.offsetWidth,
                        clientWidth: td.clientWidth,
                        getBoundingClientRect: td.getBoundingClientRect()
                    });
                }
            });
        }
        
        // Работаем с первыми 4 заголовками
        const headers = Array.from(allHeaders).slice(0, 4);
        console.log('Amanat: Working with headers:', headers.map(h => h.textContent?.trim()));
        
        // Временно убираем sticky для точного измерения
        console.log('Amanat: Removing sticky temporarily...');
        headers.forEach((th, index) => {
            th.style.position = 'static';
            th.style.left = 'auto';
            
            // Также убираем sticky у ячеек
            const rows = tbody.querySelectorAll('tr');
            rows.forEach(row => {
                const td = row.children[index];
                if (td) {
                    td.style.position = 'static';
                    td.style.left = 'auto';
                }
            });
        });
        
        // Даем браузеру время на перерисовку
        requestAnimationFrame(() => {
            console.log('Amanat: Measuring widths after removing sticky...');
            
            // Измеряем ширины
            const widths = [];
            headers.forEach((th, index) => {
                const measurements = {
                    offsetWidth: th.offsetWidth,
                    clientWidth: th.clientWidth,
                    boundingRect: th.getBoundingClientRect().width,
                    scrollWidth: th.scrollWidth
                };
                
                console.log(`Amanat: Header ${index} measurements:`, measurements);
                widths.push(measurements.boundingRect); // Используем boundingRect как основной
            });
            
            console.log('Amanat: Collected widths:', widths);
            
            // Восстанавливаем sticky и устанавливаем позиции
            let currentLeft = 0;
            headers.forEach((th, index) => {
                console.log(`Amanat: Setting column ${index} - left: ${currentLeft}px, width: ${widths[index]}px`);
                
                // Восстанавливаем sticky для заголовка
                th.style.position = 'sticky';
                th.style.left = currentLeft + 'px';
                
                // Восстанавливаем sticky для ячеек
                const rows = tbody.querySelectorAll('tr');
                rows.forEach(row => {
                    const td = row.children[index];
                    if (td) {
                        td.style.position = 'sticky';
                        td.style.left = currentLeft + 'px';
                    }
                });
                
                currentLeft += widths[index];
            });
            
            console.log('Amanat: Sticky columns setup completed!');
            console.log('Amanat: Final positions:', headers.map((th, i) => ({
                column: i,
                left: th.style.left,
                width: widths[i]
            })));
        });
    },

    willUnmount() {
        // Убираем ссылку при размонтировании
        const model = this.props.list.model.config.resModel;
        if (window.amanatListRenderers) {
            window.amanatListRenderers.delete(model);
        }
        
        // Убираем обработчик ресайза
        if (this._resizeHandler) {
            window.removeEventListener('resize', this._resizeHandler);
        }
        
        super.willUnmount();
    },

    // Метод для получения структуры полей
    getFieldsStructure() {
        const columns = this.props.list.columns || [];
        const fieldsStructure = {};
        
        columns.forEach((column, index) => {
            if (column.name) {
                fieldsStructure[column.name] = {
                    index: index,
                    type: column.type,
                    widget: column.widget,
                    string: column.string,
                    readonly: column.readonly
                };
            }
        });
        
        return fieldsStructure;
    },

    // Получаем DOM элемент строки по ID записи
    getRowElement(recordId) {
        return this.tableRef.el?.querySelector(`tr[data-id="${recordId}"]`);
    },

    // Создаем новую строку для записи
    async createRowForRecord(recordData) {
        return this.realtimeUpdater.createRowElement(recordData);
    },

    // Обновляем существующую строку
    async updateRowForRecord(recordId, recordData, changedFields) {
        return this.realtimeUpdater.updateRowElement(recordId, recordData, changedFields);
    },

    // Удаляем строку
    async removeRowForRecord(recordId) {
        return this.realtimeUpdater.removeRowElement(recordId);
    }
});

// Класс для управления real-time обновлениями в list view
class AmanatListRealtimeUpdater {
    constructor(renderer) {
        this.renderer = renderer;
    }

    async createRowElement(recordData) {
        try {
            const fieldsStructure = this.renderer.getFieldsStructure();
            const tbody = this.renderer.tableRef.el?.querySelector('tbody.o_list_table_ungrouped');
            
            if (!tbody) {
                console.error("Table body not found");
                return null;
            }

            // Создаем новую строку
            const row = document.createElement('tr');
            row.className = 'o_data_row';
            row.setAttribute('data-id', recordData.id);
            
            // Добавляем cell selector если есть
            if (tbody.querySelector('tr .o_list_record_selector')) {
                const selectorCell = document.createElement('td');
                selectorCell.className = 'o_list_record_selector user-select-none';
                selectorCell.innerHTML = `
                    <div class="o_checkbox d-flex justify-content-center">
                        <input type="checkbox" class="form-check-input" disabled="">
                    </div>
                `;
                row.appendChild(selectorCell);
            }

            // Создаем ячейки для каждого поля
            Object.entries(fieldsStructure).forEach(([fieldName, fieldInfo]) => {
                const cell = this.createCellForField(fieldName, fieldInfo, recordData);
                row.appendChild(cell);
            });

            // Добавляем в таблицу с анимацией
            row.style.opacity = '0';
            row.style.transform = 'translateY(-20px)';
            tbody.insertBefore(row, tbody.firstChild);

            // Анимация появления
            requestAnimationFrame(() => {
                row.style.transition = 'all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
                row.style.opacity = '1';
                row.style.transform = 'translateY(0)';
            });

            // Подсветка
            this.highlightRow(row, 'success');

            return row;

        } catch (error) {
            console.error("Error creating row element:", error);
            return null;
        }
    }

    createCellForField(fieldName, fieldInfo, recordData) {
        const cell = document.createElement('td');
        cell.className = 'o_data_cell cursor-pointer';
        cell.setAttribute('data-field', fieldName);

        const value = recordData[fieldName];
        
        // Обрабатываем разные типы полей
        switch (fieldInfo.type) {
            case 'many2one':
                if (value && typeof value === 'object' && value.display_name) {
                    cell.textContent = value.display_name;
                } else if (Array.isArray(value) && value.length >= 2) {
                    cell.textContent = value[1];
                } else {
                    cell.textContent = value || '';
                }
                break;

            case 'selection':
                cell.textContent = this.getSelectionLabel(fieldName, value) || value || '';
                break;

            case 'boolean':
                cell.innerHTML = value ? 
                    '<i class="fa fa-check text-success"></i>' : 
                    '<i class="fa fa-times text-danger"></i>';
                break;

            case 'date':
            case 'datetime':
                if (value) {
                    const date = new Date(value);
                    cell.textContent = date.toLocaleDateString();
                } else {
                    cell.textContent = '';
                }
                break;

            case 'monetary':
            case 'float':
                if (value !== null && value !== undefined) {
                    cell.textContent = Number(value).toFixed(2);
                } else {
                    cell.textContent = '0.00';
                }
                break;

            case 'integer':
                cell.textContent = value || '0';
                break;

            default:
                cell.textContent = value || '';
        }

        return cell;
    }

    async updateRowElement(recordId, recordData, changedFields) {
        try {
            const row = this.renderer.getRowElement(recordId);
            if (!row) {
                console.log(`Row for record ${recordId} not found`);
                return false;
            }

            // Проверяем, не редактируется ли строка
            if (this.isRowBeingEdited(row)) {
                return this.handleEditingConflict(row, recordData, changedFields);
            }

            const fieldsStructure = this.renderer.getFieldsStructure();
            let hasUpdates = false;

            // Обновляем только измененные поля или все если changedFields не указаны
            const fieldsToUpdate = changedFields && changedFields.length > 0 ? 
                changedFields : Object.keys(fieldsStructure);

            fieldsToUpdate.forEach(fieldName => {
                if (fieldsStructure[fieldName]) {
                    const cell = row.querySelector(`td[data-field="${fieldName}"]`);
                    if (cell) {
                        const oldValue = cell.textContent;
                        this.updateCellContent(cell, fieldName, fieldsStructure[fieldName], recordData);
                        
                        if (cell.textContent !== oldValue) {
                            hasUpdates = true;
                            this.highlightCell(cell);
                        }
                    }
                }
            });

            if (hasUpdates) {
                this.highlightRow(row, 'info');
            }

            return true;

        } catch (error) {
            console.error("Error updating row element:", error);
            return false;
        }
    }

    updateCellContent(cell, fieldName, fieldInfo, recordData) {
        const value = recordData[fieldName];
        
        // Используем ту же логику что и в createCellForField
        switch (fieldInfo.type) {
            case 'many2one':
                if (value && typeof value === 'object' && value.display_name) {
                    cell.textContent = value.display_name;
                } else if (Array.isArray(value) && value.length >= 2) {
                    cell.textContent = value[1];
                } else {
                    cell.textContent = value || '';
                }
                break;

            case 'selection':
                cell.textContent = this.getSelectionLabel(fieldName, value) || value || '';
                break;

            case 'boolean':
                cell.innerHTML = value ? 
                    '<i class="fa fa-check text-success"></i>' : 
                    '<i class="fa fa-times text-danger"></i>';
                break;

            case 'date':
            case 'datetime':
                if (value) {
                    const date = new Date(value);
                    cell.textContent = date.toLocaleDateString();
                } else {
                    cell.textContent = '';
                }
                break;

            case 'monetary':
            case 'float':
                if (value !== null && value !== undefined) {
                    cell.textContent = Number(value).toFixed(2);
                } else {
                    cell.textContent = '0.00';
                }
                break;

            case 'integer':
                cell.textContent = value || '0';
                break;

            default:
                cell.textContent = value || '';
        }
    }

    async removeRowElement(recordId) {
        try {
            const row = this.renderer.getRowElement(recordId);
            if (!row) {
                console.log(`Row for record ${recordId} not found`);
                return false;
            }

            // Анимация удаления
            row.style.transition = 'all 0.4s cubic-bezier(0.55, 0.09, 0.68, 0.53)';
            row.style.opacity = '0';
            row.style.transform = 'translateX(-100%)';
            row.style.backgroundColor = '#f8d7da';

            setTimeout(() => {
                if (row.parentNode) {
                    row.remove();
                }
            }, 400);

            return true;

        } catch (error) {
            console.error("Error removing row element:", error);
            return false;
        }
    }

    isRowBeingEdited(row) {
        return row.classList.contains('o_selected_row') || 
               row.querySelector('.o_field_widget.o_input') ||
               row.querySelector('input:focus, select:focus, textarea:focus');
    }

    handleEditingConflict(row, recordData, changedFields) {
        // Добавляем визуальную индикацию конфликта
        row.style.borderLeft = '4px solid #ffc107';
        
        // Создаем уведомление о конфликте
        const notification = this.renderer.env.services.notification;
        notification.add("Запись изменена другим пользователем во время вашего редактирования", {
            type: 'warning',
            title: 'Конфликт редактирования',
            sticky: true,
            buttons: [
                {
                    name: "Применить изменения",
                    primary: true,
                    onClick: () => {
                        this.updateRowElement(recordData.id, recordData, changedFields);
                        row.style.borderLeft = '';
                    }
                },
                {
                    name: "Игнорировать",
                    onClick: () => {
                        row.style.borderLeft = '';
                    }
                }
            ]
        });

        return false;
    }

    highlightRow(row, type = 'info') {
        const colors = {
            'success': '#d4edda',
            'info': '#cce7ff', 
            'warning': '#fff3cd',
            'danger': '#f8d7da'
        };

        const originalBg = row.style.backgroundColor;
        row.style.backgroundColor = colors[type] || colors.info;
        row.style.transition = 'background-color 0.3s ease';

        setTimeout(() => {
            row.style.backgroundColor = originalBg;
        }, 2500);
    }

    highlightCell(cell) {
        const originalBorder = cell.style.border;
        const originalBg = cell.style.backgroundColor;
        
        cell.style.border = '2px solid #17a2b8';
        cell.style.backgroundColor = '#e6f3ff';
        cell.style.transition = 'all 0.3s ease';

        setTimeout(() => {
            cell.style.border = originalBorder;
            cell.style.backgroundColor = originalBg;
        }, 2000);
    }

    getSelectionLabel(fieldName, value) {
        // Здесь можно добавить логику для получения label'ов selection полей
        // Пока возвращаем значение как есть
        return value;
    }
}

// Функция для получения renderer текущей модели
window.getAmanatListRenderer = function(model) {
    return window.amanatListRenderers?.get(model);
};

// Экспортируем для использования в других модулях
export { AmanatListRealtimeUpdater }; 