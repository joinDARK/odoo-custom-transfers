/** @odoo-module **/

// Простая реализация функциональности preview offline
// Избегаем конфликтов с патчами и компонентами

document.addEventListener('DOMContentLoaded', function() {
    // Добавляем обработчики событий для кнопок предпросмотра
    document.addEventListener('click', function(ev) {
        // Проверяем, что это кнопка предпросмотра
        if (ev.target.classList.contains('preview-offline-btn') || 
            ev.target.closest('.preview-offline-btn')) {
            handlePreviewOffline(ev);
        }
    });
});

async function handlePreviewOffline(ev) {
    ev.stopPropagation();
    ev.preventDefault();
    
    const target = ev.target.closest('.preview-offline-btn') || ev.target;
    const attachmentId = target.dataset.attachmentId;
    const fileType = target.dataset.fileType;
    const fileName = target.dataset.fileName;
    
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
            // Используем встроенный сервис ORM Odoo
            const data = await odoo.env.services.orm.call(
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