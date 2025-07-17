/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FileUploadProgressCard } from "@web/views/fields/file_handler";

// Патч для добавления кнопки preview offline к виджетам вложений
const originalAttachmentPatch = {
    setup() {
        super.setup();
        // Добавляем модальное окно при инициализации
        this.initPreviewModal();
    },
    
    initPreviewModal() {
        // Добавляем модальное окно в DOM если его еще нет
        if (!document.getElementById('xlsx_preview')) {
            const modalHtml = `
                <div id="xlsx_preview" class="modal" style="display: none; position: fixed; z-index: 10000; padding-top: 100px; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.4);">
                    <div class="modal-content" id="MyPreview_content" style="background-color: #fefefe; overflow: hidden; margin: auto; padding: 20px; border: 1px solid #888; width: 80%; max-height: 80vh; overflow-y: auto;">
                        <span class="close" id="stop-preview-button" style="color: #aaaaaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer;">×</span>
                        <h1 id="FileHead" style="font-size: 24px; font-weight: bold; margin-bottom: 20px; color: #333;"></h1>
                        <div class="XlsxTable" style="overflow: auto; max-height: 70vh;"></div>
                        <div class="MyDocs" style="overflow: auto; text-align: justify; padding: 30px; line-height: 1.6;"></div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            // Добавляем обработчик для кнопки закрытия
            const closeBtn = document.getElementById('stop-preview-button');
            if (closeBtn) {
                closeBtn.addEventListener('click', this.stopPreviewButton.bind(this));
            }
            
            // Добавляем обработчик для закрытия по клику на фон
            const modal = document.getElementById('xlsx_preview');
            if (modal) {
                modal.addEventListener('click', (event) => {
                    if (event.target === modal) {
                        this.stopPreviewButton(event);
                    }
                });
            }
        }
    },
    
    async onClickPreviewOffline(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        
        const attachmentId = ev.target.dataset.attachmentId;
        const fileType = ev.target.dataset.fileType;
        const fileName = ev.target.dataset.fileName;
        
        if (!attachmentId || !fileType) {
            console.error('Attachment ID or file type not found');
            return;
        }
        
        const modal = document.getElementById('xlsx_preview');
        const fileHead = document.getElementById('FileHead');
        
        if (!modal || !fileHead) {
            console.error('Modal elements not found');
            return;
        }
        
        fileHead.textContent = fileName || 'Предпросмотр файла';
        
        if (['xls', 'xlsx', 'docx'].includes(fileType)) {
            modal.style.display = "block";
            
            try {
                const data = await this.orm.call(
                    "ir.attachment", 
                    "decode_content", 
                    [parseInt(attachmentId), fileType]
                );
                
                const myDocs = document.querySelector('.MyDocs');
                const xlsxTable = document.querySelector('.XlsxTable');
                
                if (fileType === 'xls' || fileType === 'xlsx') {
                    if (myDocs) myDocs.innerHTML = '';
                    if (xlsxTable) {
                        xlsxTable.innerHTML = data;
                        const frame = xlsxTable.querySelector(".dataframe");
                        if (frame) {
                            frame.id = 'MyTable';
                            frame.style.cssText = 'font-family: Arial, Helvetica, sans-serif; border-collapse: collapse; width: 100%; margin-top: 20px;';
                        }
                    }
                } else if (fileType === 'docx') {
                    if (myDocs) {
                        myDocs.innerHTML = '';
                        if (Array.isArray(data)) {
                            data.forEach(para => {
                                const p = document.createElement('p');
                                p.textContent = para;
                                p.style.marginBottom = '10px';
                                myDocs.appendChild(p);
                            });
                        }
                    }
                    if (xlsxTable) xlsxTable.innerHTML = '';
                }
            } catch (error) {
                console.error('Error loading file preview:', error);
                const errorDiv = document.createElement('div');
                errorDiv.innerHTML = '<p style="color: red; padding: 20px;">Ошибка при загрузке предпросмотра файла</p>';
                document.querySelector('.MyDocs').appendChild(errorDiv);
            }
        }
    },
    
    stopPreviewButton(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        const modal = document.getElementById('xlsx_preview');
        if (modal) {
            modal.style.display = "none";
        }
    }
};

// Добавляем функциональность к различным компонентам вложений
document.addEventListener('DOMContentLoaded', function() {
    // Инициализируем модальное окно
    const initModal = () => {
        if (!document.getElementById('xlsx_preview')) {
            const modalHtml = `
                <div id="xlsx_preview" class="modal" style="display: none; position: fixed; z-index: 10000; padding-top: 100px; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.4);">
                    <div class="modal-content" id="MyPreview_content" style="background-color: #fefefe; overflow: hidden; margin: auto; padding: 20px; border: 1px solid #888; width: 80%; max-height: 80vh; overflow-y: auto;">
                        <span class="close" id="stop-preview-button" style="color: #aaaaaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer;">×</span>
                        <h1 id="FileHead" style="font-size: 24px; font-weight: bold; margin-bottom: 20px; color: #333;"></h1>
                        <div class="XlsxTable" style="overflow: auto; max-height: 70vh;"></div>
                        <div class="MyDocs" style="overflow: auto; text-align: justify; padding: 30px; line-height: 1.6;"></div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            // Добавляем обработчик для кнопки закрытия
            const closeBtn = document.getElementById('stop-preview-button');
            if (closeBtn) {
                closeBtn.addEventListener('click', (ev) => {
                    ev.stopPropagation();
                    ev.preventDefault();
                    const modal = document.getElementById('xlsx_preview');
                    if (modal) {
                        modal.style.display = "none";
                    }
                });
            }
            
            // Добавляем обработчик для закрытия по клику на фон
            const modal = document.getElementById('xlsx_preview');
            if (modal) {
                modal.addEventListener('click', (event) => {
                    if (event.target === modal) {
                        modal.style.display = "none";
                    }
                });
            }
        }
    };
    
    // Инициализируем модальное окно
    initModal();
    
    // Добавляем обработчики для кнопок предпросмотра
    document.addEventListener('click', async function(ev) {
        if (ev.target.classList.contains('preview-offline-btn')) {
            await handlePreviewOffline(ev);
        }
    });
});

async function handlePreviewOffline(ev) {
    ev.stopPropagation();
    ev.preventDefault();
    
    const attachmentId = ev.target.dataset.attachmentId;
    const fileType = ev.target.dataset.fileType;
    const fileName = ev.target.dataset.fileName;
    
    if (!attachmentId || !fileType) {
        console.error('Attachment ID or file type not found');
        return;
    }
    
    const modal = document.getElementById('xlsx_preview');
    const fileHead = document.getElementById('FileHead');
    
    if (!modal || !fileHead) {
        console.error('Modal elements not found');
        return;
    }
    
    fileHead.textContent = fileName || 'Предпросмотр файла';
    
    if (['xls', 'xlsx', 'docx'].includes(fileType)) {
        modal.style.display = "block";
        
        try {
            const data = await window.odoo.env.services.orm.call(
                "ir.attachment", 
                "decode_content", 
                [parseInt(attachmentId), fileType]
            );
            
            const myDocs = document.querySelector('.MyDocs');
            const xlsxTable = document.querySelector('.XlsxTable');
            
            if (fileType === 'xls' || fileType === 'xlsx') {
                if (myDocs) myDocs.innerHTML = '';
                if (xlsxTable) {
                    xlsxTable.innerHTML = data;
                    const frame = xlsxTable.querySelector(".dataframe");
                    if (frame) {
                        frame.id = 'MyTable';
                        frame.style.cssText = 'font-family: Arial, Helvetica, sans-serif; border-collapse: collapse; width: 100%; margin-top: 20px;';
                    }
                }
            } else if (fileType === 'docx') {
                if (myDocs) {
                    myDocs.innerHTML = '';
                    if (Array.isArray(data)) {
                        data.forEach(para => {
                            const p = document.createElement('p');
                            p.textContent = para;
                            p.style.marginBottom = '10px';
                            myDocs.appendChild(p);
                        });
                    }
                }
                if (xlsxTable) xlsxTable.innerHTML = '';
            }
        } catch (error) {
            console.error('Error loading file preview:', error);
            const errorDiv = document.createElement('div');
            errorDiv.innerHTML = '<p style="color: red; padding: 20px;">Ошибка при загрузке предпросмотра файла</p>';
            document.querySelector('.MyDocs').appendChild(errorDiv);
        }
    }
} 