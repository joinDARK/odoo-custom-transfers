/** @odoo-module **/

import { registry } from "@web/core/registry";

// Вспомогательный сервис для тестирования real-time обновлений
const realtimeTestHelperService = {
    dependencies: [],
    
    start(env) {
        console.log("🧪 Realtime Test Helper starting...");
        
        // Глобальные функции для тестирования
        window.realtimeTest = {
            
            // Тест обновления ячеек в таблице
            testTableCellUpdate: () => {
                console.log("🧪 Testing table cell update...");
                
                const cells = document.querySelectorAll('.o_list_table td[name]');
                if (cells.length > 0) {
                    const cell = cells[0];
                    const originalText = cell.textContent;
                    
                    // Симулируем обновление
                    cell.textContent = `Обновлено в ${new Date().toLocaleTimeString()}`;
                    cell.classList.add('field-updated');
                    
                    console.log(`🧪 Updated cell from "${originalText}" to "${cell.textContent}"`);
                    
                    setTimeout(() => {
                        cell.classList.remove('field-updated');
                        console.log("🧪 Removed highlight from cell");
                    }, 3000);
                } else {
                    console.log("🧪 No table cells found");
                }
            },
            
            // Тест подсветки строки в таблице
            testTableRowHighlight: () => {
                console.log("🧪 Testing table row highlight...");
                
                const rows = document.querySelectorAll('.o_list_table tbody tr');
                if (rows.length > 0) {
                    const row = rows[0];
                    
                    row.classList.add('realtime-updated');
                    console.log("🧪 Added highlight to row");
                    
                    setTimeout(() => {
                        row.classList.remove('realtime-updated');
                        console.log("🧪 Removed highlight from row");
                    }, 3000);
                } else {
                    console.log("🧪 No table rows found");
                }
            },
            
            // Тест обновления полей в форме
            testFormFieldUpdate: () => {
                console.log("🧪 Testing form field update...");
                
                const fields = document.querySelectorAll('.o_form_view [name]');
                if (fields.length > 0) {
                    const field = fields[0];
                    
                    field.classList.add('field-updated');
                    console.log(`🧪 Added highlight to field: ${field.getAttribute('name')}`);
                    
                    setTimeout(() => {
                        field.classList.remove('field-updated');
                        console.log("🧪 Removed highlight from field");
                    }, 3000);
                } else {
                    console.log("🧪 No form fields found");
                }
            },
            
            // Тест кастомного уведомления
            testCustomNotification: () => {
                console.log("🧪 Testing custom notification...");
                
                const notification = document.createElement('div');
                notification.className = 'realtime-notification';
                notification.textContent = 'Тестовое real-time уведомление!';
                
                document.body.appendChild(notification);
                
                setTimeout(() => {
                    notification.remove();
                    console.log("🧪 Removed custom notification");
                }, 3000);
            },
            
            // Симуляция полного real-time обновления
            simulateRealtimeUpdate: () => {
                console.log("🧪 Simulating full realtime update...");
                
                // Обновляем таблицу если есть
                const tableRows = document.querySelectorAll('.o_list_table tbody tr');
                if (tableRows.length > 0) {
                    const row = tableRows[0];
                    const cells = row.querySelectorAll('td[name]');
                    
                    // Обновляем случайную ячейку
                    if (cells.length > 0) {
                        const randomCell = cells[Math.floor(Math.random() * cells.length)];
                        const fieldName = randomCell.getAttribute('name');
                        
                        randomCell.textContent = `Обновлено ${new Date().toLocaleTimeString()}`;
                        randomCell.classList.add('field-updated');
                        
                        // Подсвечиваем всю строку
                        row.classList.add('realtime-updated');
                        
                        console.log(`🧪 Simulated update for field: ${fieldName}`);
                        
                        // Показываем уведомление
                        window.realtimeTest.testCustomNotification();
                        
                        // Убираем подсветку
                        setTimeout(() => {
                            randomCell.classList.remove('field-updated');
                            row.classList.remove('realtime-updated');
                        }, 3000);
                    }
                }
                
                // Обновляем форму если есть
                const formFields = document.querySelectorAll('.o_form_view [name]');
                if (formFields.length > 0) {
                    const randomField = formFields[Math.floor(Math.random() * formFields.length)];
                    randomField.classList.add('field-updated');
                    
                    setTimeout(() => {
                        randomField.classList.remove('field-updated');
                    }, 3000);
                }
            },
            
            // Проверка CSS стилей
            checkCssStyles: () => {
                console.log("🧪 Checking CSS styles...");
                
                // Проверяем, загружены ли CSS стили
                const styleSheets = Array.from(document.styleSheets);
                const realtimeStyles = styleSheets.find(sheet => {
                    try {
                        return sheet.href && sheet.href.includes('realtime_highlight.css');
                    } catch (e) {
                        return false;
                    }
                });
                
                if (realtimeStyles) {
                    console.log("✅ Real-time CSS styles are loaded");
                } else {
                    console.log("❌ Real-time CSS styles not found");
                }
                
                // Проверяем наличие CSS правил
                const testElement = document.createElement('div');
                testElement.className = 'field-updated';
                testElement.style.visibility = 'hidden';
                document.body.appendChild(testElement);
                
                const computedStyle = window.getComputedStyle(testElement);
                const backgroundColor = computedStyle.backgroundColor;
                
                document.body.removeChild(testElement);
                
                if (backgroundColor !== 'rgba(0, 0, 0, 0)' && backgroundColor !== 'transparent') {
                    console.log(`✅ CSS styles are working: ${backgroundColor}`);
                } else {
                    console.log("❌ CSS styles not applied");
                }
            }
        };
        
        console.log("🧪 Realtime Test Helper functions available:");
        console.log("🧪 - window.realtimeTest.testTableCellUpdate()");
        console.log("🧪 - window.realtimeTest.testTableRowHighlight()");
        console.log("🧪 - window.realtimeTest.testFormFieldUpdate()");
        console.log("🧪 - window.realtimeTest.testCustomNotification()");
        console.log("🧪 - window.realtimeTest.simulateRealtimeUpdate()");
        console.log("🧪 - window.realtimeTest.checkCssStyles()");
        
        return {};
    }
};

// Регистрируем сервис
registry.category("services").add("realtime_test_helper", realtimeTestHelperService);

console.log("🧪 Realtime Test Helper Service registered"); 