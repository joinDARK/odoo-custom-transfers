/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

// Обработчик для тега javascript_call
function javascriptCallHandler(env, action) {
    const params = action.params;
    const functionName = params.function;
    const args = params.args || [];
    
    console.log(`Вызываем JavaScript функцию: ${functionName} с аргументами:`, args);
    
    // Проверяем, что функция существует в глобальном объекте window
    if (typeof window[functionName] === 'function') {
        try {
            window[functionName](...args);
        } catch (error) {
            console.error(`Ошибка при вызове функции ${functionName}:`, error);
        }
    } else {
        console.error(`Функция ${functionName} не найдена в глобальном объекте window`);
    }
}

// Регистрируем обработчик
registry.category("actions").add("javascript_call", javascriptCallHandler);

export class SverkaFilesPreviewButton extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.isPreviewActive = false;
    }

    /**
     * Показать превью файлов используя модальное окно из chatter_attachments_manager
     */
    async showFilePreview(recordIds) {
        const recordId = Array.isArray(recordIds) ? recordIds[0] : recordIds;
        
        // Предотвращаем повторные вызовы
        if (this.isPreviewActive) {
            console.log('Превью уже активно, игнорируем повторный вызов');
            return;
        }
        
        this.isPreviewActive = true;
        
        try {
            console.log(`Начинаем превью файлов для записи: ${recordId}`);
            
            // Получаем все прикрепленные файлы к записи
            const attachments = await this.orm.call(
                "ir.attachment",
                "search_read",
                [[["res_model", "=", "amanat.sverka_files"], ["res_id", "=", recordId]]],
                ["id", "name", "mimetype", "file_size", "datas"]
            );

            if (!attachments || attachments.length === 0) {
                this.notification.add(
                    _t("Нет прикрепленных файлов для превью"),
                    { type: "warning" }
                );
                return;
            }

            // Фильтруем файлы по поддерживаемым типам
            const supportedTypes = ["xls", "xlsx", "docx", "pdf"];
            const previewableFiles = attachments.filter(attachment => {
                const extension = attachment.name.split('.').pop().toLowerCase();
                return supportedTypes.includes(extension);
            });

            if (previewableFiles.length === 0) {
                this.notification.add(
                    _t("Нет файлов поддерживаемых типов (Excel, Word, PDF) для превью"),
                    { type: "warning" }
                );
                return;
            }

            // Показываем первый файл, если есть несколько
            const firstFile = previewableFiles[0];
            const extension = firstFile.name.split('.').pop().toLowerCase();
            
            await this.openPreviewModal(firstFile, extension);
            
        } catch (error) {
            console.error("Ошибка при получении файлов:", error);
            this.notification.add(
                _t("Ошибка при загрузке файлов для превью"),
                { type: "danger" }
            );
        } finally {
            this.isPreviewActive = false;
        }
    }

    /**
     * Открыть модальное окно превью (копия логики из chatter_attachments_manager)
     */
    async openPreviewModal(attachment, type) {
        try {
            // Создаем модальное окно если его еще нет
            this.createPreviewModal();
            
            const modal = document.getElementById('xlsx_preview');
            if (!modal) {
                this.notification.add(
                    _t("Модальное окно не найдено. Убедитесь, что модуль chatter_attachments_manager установлен"),
                    { type: "danger" }
                );
                return;
            }

            // Полностью очищаем контейнеры перед добавлением нового содержимого
            const myDocs = modal.querySelector('.MyDocs');
            const xlsxTable = modal.querySelector('.XlsxTable');
            
            if (myDocs) {
                myDocs.innerHTML = '';
            }
            if (xlsxTable) {
                xlsxTable.innerHTML = '';
            }

            // Устанавливаем заголовок
            const fileHead = modal.querySelector('#FileHead');
            if (fileHead) {
                fileHead.textContent = attachment.name;
            }

            // Показываем модальное окно
            modal.style.display = "block";

            // Получаем контент файла
            if (type === 'xls' || type === 'xlsx' || type === 'docx') {
                console.log(`Получаем контент файла: ${attachment.name}`);
                
                const content = await this.orm.call(
                    "ir.attachment",
                    "decode_content",
                    [attachment.id, type]
                );

                console.log('Контент получен, обрабатываем...');

                if (type === 'xls' || type === 'xlsx') {
                    if (xlsxTable) {
                        xlsxTable.innerHTML = content;
                        // Добавляем ID для стилизации таблицы
                        const dataFrame = xlsxTable.querySelector('.dataframe');
                        if (dataFrame) {
                            dataFrame.setAttribute('id', 'MyTable');
                            dataFrame.classList.add('excel-table');
                            // Преобразуем таблицу в Excel-подобный вид
                            this.transformToExcelTable(dataFrame);
                            console.log('Таблица успешно преобразована');
                        }
                    }
                } else if (type === 'docx') {
                    if (myDocs) {
                        if (Array.isArray(content)) {
                            content.forEach(paragraph => {
                                const p = document.createElement('p');
                                p.textContent = paragraph;
                                myDocs.appendChild(p);
                            });
                        }
                    }
                }
            } else {
                // Для PDF и других типов файлов можно использовать стандартный просмотрщик
                this.notification.add(
                    _t("Превью PDF файлов доступно через чаттер"),
                    { type: "info" }
                );
            }

            // Добавляем обработчик закрытия
            this.addCloseHandler(modal);

        } catch (error) {
            console.error("Ошибка при открытии превью:", error);
            this.notification.add(
                _t("Ошибка при открытии превью файла"),
                { type: "danger" }
            );
        }
    }

    /**
     * Создать модальное окно если его нет
     */
    createPreviewModal() {
        if (document.getElementById('xlsx_preview')) {
            return; // Модальное окно уже существует
        }

        const modalHTML = `
            <div id="xlsx_preview" class="modal" style="display: none; position: fixed; z-index: 10000; padding-top: 100px; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.4);">
                <div class="modal-content" id="MyPreview_content" style="background-color: #fefefe; overflow: hidden; margin: auto; padding: 20px; border: 1px solid #888; width: 80%; max-height: 80vh; overflow-y: auto;">
                    <span class="close" id="stop-preview-button" style="color: #aaaaaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer;">×</span>
                    <h1 id="FileHead"></h1>
                    <div class="XlsxTable" style="overflow: auto; max-height: 70vh;"></div>
                    <div class="MyDocs" style="overflow: auto; text-align: justify; padding: 30px;"></div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    /**
     * Добавить обработчик закрытия модального окна
     */
    addCloseHandler(modal) {
        const closeBtn = modal.querySelector('#stop-preview-button');
        
        // Убираем предыдущие обработчики
        if (closeBtn) {
            // Клонируем элемент для удаления всех обработчиков
            const newCloseBtn = closeBtn.cloneNode(true);
            closeBtn.parentNode.replaceChild(newCloseBtn, closeBtn);
            
            // Добавляем новый обработчик
            newCloseBtn.onclick = () => {
                modal.style.display = "none";
                this.isPreviewActive = false;
            };
        }

        // Закрытие по клику вне модального окна
        const modalClickHandler = (event) => {
            if (event.target === modal) {
                modal.style.display = "none";
                this.isPreviewActive = false;
                window.removeEventListener('click', modalClickHandler);
            }
        };
        
        window.addEventListener('click', modalClickHandler);
    }

    /**
     * Преобразование таблицы в Excel-подобный вид
     */
    transformToExcelTable(table) {
        console.log('Начинаем трансформацию таблицы...');
        
        // Проверяем, не была ли таблица уже обработана
        if (table.classList.contains('excel-transformed')) {
            console.log('Таблица уже была обработана, пропускаем');
            return;
        }
        
        const rows = table.querySelectorAll('tr');
        
        if (rows.length === 0) {
            console.log('Таблица пуста, нечего обрабатывать');
            return;
        }
        
        console.log(`Обрабатываем таблицу с ${rows.length} строками`);
        
        // Обрабатываем заголовки (первая строка)
        const headerRow = rows[0];
        const headers = headerRow.querySelectorAll('th');
        
        if (headers.length > 0) {
            // Проверяем, не добавлена ли уже corner cell
            const existingCornerCell = headerRow.querySelector('.row-number');
            if (!existingCornerCell) {
                // Добавляем пустую ячейку в левый верхний угол
                const cornerCell = document.createElement('th');
                cornerCell.className = 'row-number';
                cornerCell.style.backgroundColor = '#217346';
                headerRow.insertBefore(cornerCell, headers[0]);
            }
            
            // Сохраняем оригинальные заголовки колонок (как в Excel)
            headers.forEach((header, index) => {
                // Не заменяем текст заголовка, оставляем оригинальный
                header.className = 'column-header';
            });
        }
        
        // Обрабатываем строки данных
        for (let i = 1; i < rows.length; i++) {
            const row = rows[i];
            const cells = row.querySelectorAll('td');
            
            if (cells.length > 0) {
                // Проверяем, не добавлена ли уже ячейка с номером строки
                const existingRowNumber = row.querySelector('.row-number');
                if (!existingRowNumber) {
                    // Добавляем номер строки в начало
                    const rowNumberCell = document.createElement('td');
                    rowNumberCell.textContent = i;
                    rowNumberCell.className = 'row-number';
                    row.insertBefore(rowNumberCell, cells[0]);
                }
                
                // Обрабатываем каждую ячейку
                cells.forEach((cell, cellIndex) => {
                    // Обрабатываем NaN, NaT, null, undefined значения
                    const text = cell.textContent.trim();
                    if (text === 'NaN' || text === 'nan' || text === 'NaT' || text === 'null' || text === 'undefined' || text === '') {
                        cell.textContent = '';
                        cell.classList.add('empty-cell');
                    } else {
                        // Проверяем, является ли значение числом
                        if (!isNaN(text) && text !== '') {
                            cell.setAttribute('data-type', 'number');
                            cell.style.textAlign = 'right';
                            cell.style.fontFamily = "'Courier New', monospace";
                        }
                    }
                    
                    // Добавляем атрибуты для навигации
                    cell.setAttribute('data-row', i);
                    cell.setAttribute('data-col', cellIndex);
                });
            }
        }
        
        // Помечаем таблицу как обработанную
        table.classList.add('excel-transformed');
        
        // Добавляем плавную анимацию появления строк
        rows.forEach((row, index) => {
            row.style.animationDelay = `${index * 0.05}s`;
        });
        
        console.log('Трансформация таблицы завершена');
    }

    /**
     * Получение буквы колонки (A, B, C... Z, AA, AB...)
     */
    getColumnLetter(index) {
        let result = '';
        while (index >= 0) {
            result = String.fromCharCode(65 + (index % 26)) + result;
            index = Math.floor(index / 26) - 1;
        }
        return result;
    }
}

// Глобальная переменная для отслеживания активного превью
let isGlobalPreviewActive = false;

// Функции для отдельного превью файлов сверки и сверки ТДК
window.showSverka1FilesPreview = async function(recordId) {
    console.log(`Начинаем превью файлов сверки для записи: ${recordId}`);
    await showSverkaFilesPreviewByType(recordId, 'sverka1');
};

window.showSverka2FilesPreview = async function(recordId) {
    console.log(`Начинаем превью файлов сверки ТДК для записи: ${recordId}`);
    await showSverkaFilesPreviewByType(recordId, 'sverka2');
};

// Общая функция для превью файлов по типу
async function showSverkaFilesPreviewByType(recordId, fileType) {
    // Предотвращаем повторные вызовы
    if (isGlobalPreviewActive) {
        console.log(`Превью уже активно, игнорируем повторный вызов для ${fileType}`);
        return;
    }
    
    isGlobalPreviewActive = true;
    
    try {
        console.log(`Начинаем превью ${fileType} для записи: ${recordId}`);
        
        // Получаем запись sverka_files с нужным полем
        const fieldName = fileType === 'sverka1' ? 'sverka1_file_attachments' : 'sverka2_file_attachments';
        const sverkaRecords = await rpc("/web/dataset/call_kw", {
            model: "amanat.sverka_files",
            method: "read",
            args: [[recordId], [fieldName]],
            kwargs: {}
        });

        let allAttachments = [];

        // Получаем файлы из соответствующего поля
        if (sverkaRecords.length > 0) {
            const sverkaRecord = sverkaRecords[0];
            const attachmentIds = sverkaRecord[fieldName];
            
            console.log(`Поле ${fieldName}:`, attachmentIds);
            
            if (attachmentIds && attachmentIds.length > 0) {
                const fileAttachments = await rpc("/web/dataset/call_kw", {
                    model: "ir.attachment",
                    method: "read",
                    args: [attachmentIds, ["id", "name", "mimetype", "file_size", "datas", "url", "type"]],
                    kwargs: {}
                });
                
                console.log(`Файлы из ${fieldName}:`, fileAttachments);
                allAttachments = fileAttachments;
            }
        }

        console.log(`Найдено файлов ${fileType}: ${allAttachments.length}`);

        if (allAttachments.length === 0) {
            console.log(`Нет файлов ${fileType} для превью`);
            return;
        }

        // Фильтруем файлы по поддерживаемым типам
        const supportedTypes = ["xls", "xlsx", "docx", "pdf"];
        const previewableFiles = allAttachments.filter(attachment => {
            const extension = attachment.name.split('.').pop().toLowerCase();
            return supportedTypes.includes(extension);
        });

        console.log(`Найдено файлов ${fileType} поддерживаемых типов: ${previewableFiles.length}`);

        if (previewableFiles.length === 0) {
            console.log(`Нет файлов ${fileType} поддерживаемых типов для превью`);
            return;
        }

        // Показываем первый файл
        const firstFile = previewableFiles[0];
        const extension = firstFile.name.split('.').pop().toLowerCase();
        
        console.log(`Показываем файл ${fileType}: ${firstFile.name}, расширение: ${extension}`);
        
        await openPreviewModal(firstFile, extension);
        
    } catch (error) {
        console.error(`Ошибка при получении файлов ${fileType}:`, error);
    } finally {
        isGlobalPreviewActive = false;
    }
}

// Глобальная функция для вызова из Python (упрощенная версия)
window.showSverkaFilesPreview = async function(recordId) {
    // Предотвращаем повторные вызовы
    if (isGlobalPreviewActive) {
        console.log('Глобальное превью уже активно, игнорируем повторный вызов');
        return;
    }
    
    isGlobalPreviewActive = true;
    
    try {
        console.log(`Начинаем глобальное превью для записи: ${recordId}`);
        
        // Получаем запись sverka_files с полем file_attachments
        const sverkaRecords = await rpc("/web/dataset/call_kw", {
            model: "amanat.sverka_files",
            method: "read",
            args: [[recordId], ["file_attachments"]],
            kwargs: {}
        });

        let allAttachments = [];

        // 1. Получаем файлы из поля file_attachments (Many2many)
        if (sverkaRecords.length > 0) {
            const sverkaRecord = sverkaRecords[0];
            console.log(`Поле file_attachments:`, sverkaRecord.file_attachments);
            if (sverkaRecord.file_attachments && sverkaRecord.file_attachments.length > 0) {
                            const fileAttachments = await rpc("/web/dataset/call_kw", {
                model: "ir.attachment",
                method: "read",
                args: [sverkaRecord.file_attachments, ["id", "name", "mimetype", "file_size", "datas", "url", "type"]],
                kwargs: {}
            });
                console.log(`Файлы из file_attachments:`, fileAttachments);
                allAttachments = allAttachments.concat(fileAttachments);
            }
        }

        // 2. Получаем файлы через стандартный механизм (res_model/res_id)
        const standardAttachments = await rpc("/web/dataset/call_kw", {
            model: "ir.attachment",
            method: "search_read",
            args: [[["res_model", "=", "amanat.sverka_files"], ["res_id", "=", recordId]]],
            kwargs: {
                fields: ["id", "name", "mimetype", "file_size", "datas", "url", "type"]
            }
        });

        console.log(`Стандартные файлы (res_model/res_id):`, standardAttachments);

        if (standardAttachments && standardAttachments.length > 0) {
            allAttachments = allAttachments.concat(standardAttachments);
        }

        // Убираем дубликаты по ID
        const uniqueAttachments = [];
        const seenIds = new Set();
        for (const attachment of allAttachments) {
            if (!seenIds.has(attachment.id)) {
                seenIds.add(attachment.id);
                uniqueAttachments.push(attachment);
            }
        }

        console.log(`Найдено файлов всего: ${uniqueAttachments.length}`);

        if (uniqueAttachments.length === 0) {
            console.log("Нет прикрепленных файлов для превью");
            return;
        }

        // Фильтруем файлы по поддерживаемым типам
        const supportedTypes = ["xls", "xlsx", "docx", "pdf"];
        const previewableFiles = uniqueAttachments.filter(attachment => {
            const extension = attachment.name.split('.').pop().toLowerCase();
            return supportedTypes.includes(extension);
        });

        console.log(`Найдено файлов поддерживаемых типов: ${previewableFiles.length}`);

        if (previewableFiles.length === 0) {
            console.log("Нет файлов поддерживаемых типов для превью");
            return;
        }

        // Показываем первый файл
        const firstFile = previewableFiles[0];
        const extension = firstFile.name.split('.').pop().toLowerCase();
        
        console.log(`Показываем файл: ${firstFile.name}, расширение: ${extension}`);
        console.log(`Тип файла: ${firstFile.type}, URL: ${firstFile.url}, Данные: ${firstFile.datas ? 'есть' : 'нет'}`);
        
        await openPreviewModal(firstFile, extension);
        
    } catch (error) {
        console.error("Ошибка при получении файлов:", error);
    } finally {
        isGlobalPreviewActive = false;
    }
};

// Функция для открытия модального окна
async function openPreviewModal(attachment, type) {
    try {
        // Создаем модальное окно если его еще нет
        createPreviewModal();
        
        const modal = document.getElementById('xlsx_preview');
        if (!modal) {
            console.error("Модальное окно не найдено");
            return;
        }

        // Полностью очищаем контейнеры перед добавлением нового содержимого
        const myDocs = modal.querySelector('.MyDocs');
        const xlsxTable = modal.querySelector('.XlsxTable');
        
        if (myDocs) {
            myDocs.innerHTML = '';
        }
        if (xlsxTable) {
            xlsxTable.innerHTML = '';
        }

        // Устанавливаем заголовок
        const fileHead = modal.querySelector('#FileHead');
        if (fileHead) {
            fileHead.textContent = attachment.name;
        }

        // Показываем модальное окно
        modal.style.display = "block";

        console.log(`Обрабатываем файл ID: ${attachment.id}, тип: ${attachment.type}, URL: ${attachment.url}`);
        
        // Получаем контент файла через RPC (Odoo автоматически скачает URL файлы)
        if (type === 'xls' || type === 'xlsx' || type === 'docx') {
            try {
                const content = await rpc("/web/dataset/call_kw", {
                    model: "ir.attachment",
                    method: "decode_content",
                    args: [attachment.id, type],
                    kwargs: {}
                });

                console.log("Получен контент:", content);

                if (type === 'xls' || type === 'xlsx') {
                    if (xlsxTable) {
                        xlsxTable.innerHTML = content;
                        // Добавляем ID для стилизации таблицы
                        const dataFrame = xlsxTable.querySelector('.dataframe');
                        if (dataFrame) {
                            dataFrame.setAttribute('id', 'MyTable');
                            dataFrame.classList.add('excel-table');
                            // Преобразуем таблицу в Excel-подобный вид
                            transformToExcelTable(dataFrame);
                            console.log('Таблица успешно преобразована');
                        }
                    }
                } else if (type === 'docx') {
                    if (myDocs) {
                        if (Array.isArray(content)) {
                            content.forEach(paragraph => {
                                const p = document.createElement('p');
                                p.textContent = paragraph;
                                myDocs.appendChild(p);
                            });
                        } else {
                            // Если content не массив, значит это HTML сообщение
                            myDocs.innerHTML = content;
                        }
                    }
                }
            } catch (error) {
                console.error("Ошибка при получении контента файла:", error);
                
                if (myDocs) {
                    myDocs.innerHTML = `
                        <p style="padding-top:8px;color:red;">
                            Ошибка при загрузке файла: ${error.message || 'Неизвестная ошибка'}
                        </p>
                    `;
                }
            }
        }

        // Добавляем обработчик закрытия
        addCloseHandler(modal);

    } catch (error) {
        console.error("Ошибка при открытии превью:", error);
    }
}

// Функция для создания модального окна
function createPreviewModal() {
    if (document.getElementById('xlsx_preview')) {
        return; // Модальное окно уже существует
    }

    const modalHTML = `
        <div id="xlsx_preview" class="modal" style="display: none; position: fixed; z-index: 10000; padding-top: 100px; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.4);">
            <div class="modal-content" id="MyPreview_content" style="background-color: #fefefe; overflow: hidden; margin: auto; padding: 20px; border: 1px solid #888; width: 80%; max-height: 80vh; overflow-y: auto;">
                <span class="close" id="stop-preview-button" style="color: #aaaaaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer;">×</span>
                <h1 id="FileHead"></h1>
                <div class="XlsxTable" style="overflow: auto; max-height: 70vh;"></div>
                <div class="MyDocs" style="overflow: auto; text-align: justify; padding: 30px;"></div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

// Функция для добавления обработчика закрытия
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
            isGlobalPreviewActive = false;
        };
    }

    // Закрытие по клику вне модального окна
    const modalClickHandler = (event) => {
        if (event.target === modal) {
            modal.style.display = "none";
            isGlobalPreviewActive = false;
            window.removeEventListener('click', modalClickHandler);
        }
    };
    
    window.addEventListener('click', modalClickHandler);
}

// Преобразование таблицы в Excel-подобный вид
function transformToExcelTable(table) {
    console.log('Начинаем глобальную трансформацию таблицы...');
    
    // Проверяем, не была ли таблица уже обработана
    if (table.classList.contains('excel-transformed')) {
        console.log('Таблица уже была обработана, пропускаем');
        return;
    }
    
    const rows = table.querySelectorAll('tr');
    
    if (rows.length === 0) {
        console.log('Таблица пуста, нечего обрабатывать');
        return;
    }
    
    console.log(`Обрабатываем таблицу с ${rows.length} строками`);
    
    // Обрабатываем заголовки (первая строка)
    const headerRow = rows[0];
    const headers = headerRow.querySelectorAll('th');
    
    if (headers.length > 0) {
        // Проверяем, не добавлена ли уже corner cell
        const existingCornerCell = headerRow.querySelector('.row-number');
        if (!existingCornerCell) {
            // Добавляем пустую ячейку в левый верхний угол
            const cornerCell = document.createElement('th');
            cornerCell.className = 'row-number';
            cornerCell.style.backgroundColor = '#217346';
            headerRow.insertBefore(cornerCell, headers[0]);
        }
        
        // Сохраняем оригинальные заголовки колонок (как в Excel)
        headers.forEach((header, index) => {
            // Не заменяем текст заголовка, оставляем оригинальный
            header.className = 'column-header';
        });
    }
    
    // Обрабатываем строки данных
    for (let i = 1; i < rows.length; i++) {
        const row = rows[i];
        const cells = row.querySelectorAll('td');
        
        if (cells.length > 0) {
            // Проверяем, не добавлена ли уже ячейка с номером строки
            const existingRowNumber = row.querySelector('.row-number');
            if (!existingRowNumber) {
                // Добавляем номер строки в начало
                const rowNumberCell = document.createElement('td');
                rowNumberCell.textContent = i;
                rowNumberCell.className = 'row-number';
                row.insertBefore(rowNumberCell, cells[0]);
            }
            
            // Обрабатываем каждую ячейку
            cells.forEach((cell, cellIndex) => {
                // Обрабатываем NaN, NaT, null, undefined значения
                const text = cell.textContent.trim();
                if (text === 'NaN' || text === 'nan' || text === 'NaT' || text === 'null' || text === 'undefined' || text === '') {
                    cell.textContent = '';
                    cell.classList.add('empty-cell');
                } else {
                    // Проверяем, является ли значение числом
                    if (!isNaN(text) && text !== '') {
                        cell.setAttribute('data-type', 'number');
                        cell.style.textAlign = 'right';
                        cell.style.fontFamily = "'Courier New', monospace";
                    }
                }
                
                // Добавляем атрибуты для навигации
                cell.setAttribute('data-row', i);
                cell.setAttribute('data-col', cellIndex);
            });
        }
    }
    
    // Помечаем таблицу как обработанную
    table.classList.add('excel-transformed');
    
    // Добавляем плавную анимацию появления строк
    rows.forEach((row, index) => {
        row.style.animationDelay = `${index * 0.05}s`;
    });
    
    console.log('Глобальная трансформация таблицы завершена');
}

// Получение буквы колонки (A, B, C... Z, AA, AB...)
function getColumnLetter(index) {
    let result = '';
    while (index >= 0) {
        result = String.fromCharCode(65 + (index % 26)) + result;
        index = Math.floor(index / 26) - 1;
    }
    return result;
}

// Регистрируем компонент
registry.category("public_components").add("sverka_files_preview_button", SverkaFilesPreviewButton); 