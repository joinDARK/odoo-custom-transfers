/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

export class SverkaFilesPreviewButton extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
    }

    /**
     * Показать превью файлов используя модальное окно из chatter_attachments_manager
     */
    async showFilePreview(recordIds) {
        const recordId = Array.isArray(recordIds) ? recordIds[0] : recordIds;
        
        try {
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

            // Устанавливаем заголовок
            const fileHead = modal.querySelector('#FileHead');
            if (fileHead) {
                fileHead.textContent = attachment.name;
            }

            // Показываем модальное окно
            modal.style.display = "block";

            // Получаем контент файла
            if (type === 'xls' || type === 'xlsx' || type === 'docx') {
                const content = await this.orm.call(
                    "ir.attachment",
                    "decode_content",
                    [attachment.id, type]
                );

                if (type === 'xls' || type === 'xlsx') {
                    const myDocs = modal.querySelector('.MyDocs');
                    const xlsxTable = modal.querySelector('.XlsxTable');
                    
                    if (myDocs) myDocs.innerHTML = '';
                    if (xlsxTable) {
                        xlsxTable.innerHTML = content;
                        // Добавляем ID для стилизации таблицы
                        const dataFrame = xlsxTable.querySelector('.dataframe');
                        if (dataFrame) {
                            dataFrame.setAttribute('id', 'MyTable');
                        }
                    }
                } else if (type === 'docx') {
                    const myDocs = modal.querySelector('.MyDocs');
                    const xlsxTable = modal.querySelector('.XlsxTable');
                    
                    if (xlsxTable) xlsxTable.innerHTML = '';
                    if (myDocs) {
                        myDocs.innerHTML = '';
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
                <div class="modal-content" id="MyPreview_content" style="background-color: #fefefe; overflow: hidden; margin: auto; padding: 20px; border: 1px solid #888; width: 80%;">
                    <span class="close" id="stop-preview-button" style="color: #aaaaaa; text-align: end; font-size: 28px; font-weight: bold; cursor: pointer;">×</span>
                    <h1 id="FileHead"></h1>
                    <div class="XlsxTable" style="overflow: overlay;"></div>
                    <p class="MyDocs" style="overflow: auto; text-align: justify; padding: 30px;"></p>
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
        if (closeBtn) {
            closeBtn.onclick = () => {
                modal.style.display = "none";
            };
        }

        // Закрытие по клику вне модального окна
        window.onclick = (event) => {
            if (event.target === modal) {
                modal.style.display = "none";
            }
        };
    }
}

// Глобальная функция для вызова из Python (упрощенная версия)
window.showSverkaFilesPreview = async function(recordId) {
    try {
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
                    const myDocs = modal.querySelector('.MyDocs');
                    const xlsxTable = modal.querySelector('.XlsxTable');
                    
                    if (myDocs) myDocs.innerHTML = '';
                    if (xlsxTable) {
                        xlsxTable.innerHTML = content;
                        // Добавляем ID для стилизации таблицы
                        const dataFrame = xlsxTable.querySelector('.dataframe');
                        if (dataFrame) {
                            dataFrame.setAttribute('id', 'MyTable');
                        }
                    }
                } else if (type === 'docx') {
                    const myDocs = modal.querySelector('.MyDocs');
                    const xlsxTable = modal.querySelector('.XlsxTable');
                    
                    if (xlsxTable) xlsxTable.innerHTML = '';
                    if (myDocs) {
                        myDocs.innerHTML = '';
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
                const myDocs = modal.querySelector('.MyDocs');
                const xlsxTable = modal.querySelector('.XlsxTable');
                
                if (xlsxTable) xlsxTable.innerHTML = '';
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
            <div class="modal-content" id="MyPreview_content" style="background-color: #fefefe; overflow: hidden; margin: auto; padding: 20px; border: 1px solid #888; width: 80%;">
                <span class="close" id="stop-preview-button" style="color: #aaaaaa; text-align: end; font-size: 28px; font-weight: bold; cursor: pointer;">×</span>
                <h1 id="FileHead"></h1>
                <div class="XlsxTable" style="overflow: overlay;"></div>
                <p class="MyDocs" style="overflow: auto; text-align: justify; padding: 30px;"></p>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

// Функция для добавления обработчика закрытия
function addCloseHandler(modal) {
    const closeBtn = modal.querySelector('#stop-preview-button');
    if (closeBtn) {
        closeBtn.onclick = () => {
            modal.style.display = "none";
        };
    }

    // Закрытие по клику вне модального окна
    window.onclick = (event) => {
        if (event.target === modal) {
            modal.style.display = "none";
        }
    };
}

// Регистрируем компонент
registry.category("public_components").add("sverka_files_preview_button", SverkaFilesPreviewButton); 