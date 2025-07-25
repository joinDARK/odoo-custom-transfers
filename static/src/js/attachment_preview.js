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

// Глобальная переменная для отслеживания активного превью
let isPreviewActive = false;

async function handlePreviewOffline(ev) {
    ev.stopPropagation();
    ev.preventDefault();
    
    // Предотвращаем повторные вызовы
    if (isPreviewActive) {
        console.log('Превью уже активно, игнорируем повторный вызов');
        return;
    }
    
    const target = ev.target.closest('.preview-offline-btn') || ev.target;
    const attachmentId = target.dataset.attachmentId;
    const fileType = target.dataset.fileType;
    const fileName = target.dataset.fileName;
    
    console.log(`Начинаем превью файла: ${fileName}, ID: ${attachmentId}, тип: ${fileType}`);
    
    if (!attachmentId || !fileType) {
        console.error('Attachment ID or file type not found');
        return;
    }
    
    isPreviewActive = true;
    
    const modal = document.getElementById('xlsx_preview');
    const fileHead = document.getElementById('FileHead');
    
    if (!modal || !fileHead) {
        console.error('Modal elements not found');
        isPreviewActive = false;
        return;
    }
    
    // Полностью очищаем контейнеры перед добавлением нового содержимого
    const myDocs = document.querySelector('.MyDocs');
    const xlsxTable = document.querySelector('.XlsxTable');
    
    if (myDocs) {
        myDocs.innerHTML = '';
    }
    if (xlsxTable) {
        xlsxTable.innerHTML = '';
    }
    
    fileHead.textContent = fileName || 'Предпросмотр файла';
    
    if (['xls', 'xlsx', 'docx'].includes(fileType)) {
        modal.style.display = "block";
        
        try {
            console.log('Получаем данные файла...');
            // Используем встроенный сервис ORM Odoo
            const data = await odoo.env.services.orm.call(
                "ir.attachment", 
                "decode_content", 
                [parseInt(attachmentId), fileType]
            );
            
            console.log('Данные получены, обрабатываем...');
            
            if (fileType === 'xls' || fileType === 'xlsx') {
                if (xlsxTable) {
                    xlsxTable.innerHTML = data;
                    const frame = xlsxTable.querySelector(".dataframe");
                    if (frame) {
                        frame.id = 'MyTable';
                        frame.classList.add('excel-table');
                        
                        // Преобразуем таблицу в Excel-подобный вид
                        transformToExcelTable(frame);
                        console.log('Таблица успешно преобразована');
                    }
                }
            } else if (fileType === 'docx') {
                if (myDocs) {
                    if (Array.isArray(data)) {
                        data.forEach(para => {
                            const p = document.createElement('p');
                            p.textContent = para;
                            p.style.marginBottom = '10px';
                            myDocs.appendChild(p);
                        });
                    }
                }
            }
        } catch (error) {
            console.error('Error loading file preview:', error);
            if (myDocs) {
                myDocs.innerHTML = '<p style="color: red; padding: 20px; text-align: center; font-size: 16px;">Ошибка при загрузке предпросмотра файла</p>';
            }
        } finally {
            isPreviewActive = false;
        }
    } else {
        isPreviewActive = false;
    }
    
    // Добавляем обработчик закрытия модального окна
    addCloseHandler(modal);
}

// Функция для преобразования таблицы в Excel-подобный вид
function transformToExcelTable(table) {
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

// Функция для получения буквы колонки (A, B, C... Z, AA, AB...)
function getColumnLetter(index) {
    let result = '';
    while (index >= 0) {
        result = String.fromCharCode(65 + (index % 26)) + result;
        index = Math.floor(index / 26) - 1;
    }
    return result;
}

// Функция для добавления обработчика закрытия модального окна
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
            isPreviewActive = false;
        };
    }

    // Закрытие по клику вне модального окна
    const modalClickHandler = (event) => {
        if (event.target === modal) {
            modal.style.display = "none";
            isPreviewActive = false;
            window.removeEventListener('click', modalClickHandler);
        }
    };
    
    window.addEventListener('click', modalClickHandler);
} 