/** @odoo-module **/

// Простая инициализация модального окна без компонентов
document.addEventListener('DOMContentLoaded', function() {
    initAttachmentPreviewModal();
});

function initAttachmentPreviewModal() {
    // Добавляем модальное окно в DOM если его еще нет
    if (!document.getElementById('xlsx_preview')) {
        const modalHtml = `
            <div id="xlsx_preview" class="modal" style="display: none; position: fixed; z-index: 10000; padding-top: 100px; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.4);">
                <div class="modal-content" id="MyPreview_content" style="background-color: #fefefe; overflow: hidden; margin: auto; padding: 20px; border: 1px solid #888; width: 80%; max-height: 80vh; overflow-y: auto;">
                    <span class="close" id="stop-preview-button" style="color: #aaaaaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer;">×</span>
                    <h1 id="FileHead" style="font-size: 24px; font-weight: bold; margin-bottom: 20px; color: #333;"></h1>
                    <div class="XlsxTable" style="overflow: auto; max-height: 500px;"></div>
                    <div class="MyDocs" style="overflow: auto; text-align: justify; padding: 30px; line-height: 1.6;"></div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Добавляем обработчик для кнопки закрытия
        const closeBtn = document.getElementById('stop-preview-button');
        if (closeBtn) {
            closeBtn.addEventListener('click', function(ev) {
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
            modal.addEventListener('click', function(event) {
                if (event.target === modal) {
                    modal.style.display = "none";
                }
            });
        }
    }
} 