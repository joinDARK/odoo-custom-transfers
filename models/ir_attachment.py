# -*- coding: utf-8 -*-
import io
import base64
import requests
from io import BytesIO

import pandas as pd
from docx import Document as DocxDocument
from odoo import api, fields, models

# Попытка импорта различных движков для чтения Excel
try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    import xlrd
    XLRD_AVAILABLE = True
except ImportError:
    XLRD_AVAILABLE = False


class IrAttachment(models.Model):
    """Extended Attachment Model for Amanat Sverka Files"""
    _inherit = 'ir.attachment'

    @api.model
    def decode_content(self, attach_id, doc_type):
        """Decode XLSX, XLS, or DOCX File Data.
        This method takes a binary file data from an attachment and decodes
        the content of the file for XLSX, XLS, and DOCX file formats.
        :param int attach_id: id of attachment.
        :param str doc_type: the type of the given attachment either 'xlsx', 'xls', or 'docx'
        :return: return the decoded data."""
        try:
            attachment = self.sudo().browse(attach_id)
            
            # Проверяем, что файл существует
            if not attachment.exists():
                return ("<p style='padding-top:8px;color:red;'>"
                        "Файл не найден</p>")
            
            # Получаем данные файла
            xlsx_data = None
            
            # Способ 1: Пробуем сначала получить binary данные (как chatter_attachment_manager)
            try:
                if attachment.datas:
                    xlsx_data = base64.b64decode(attachment.datas)
                    if xlsx_data:
                        # Успешно получили binary данные
                        pass
            except Exception as e:
                pass
            
            # Способ 2: Если binary данных нет, пробуем загрузить по URL
            if not xlsx_data and hasattr(attachment, 'type') and attachment.type == 'url':
                try:
                    if not attachment.url:
                        return ("<p style='padding-top:8px;color:red;'>"
                                "URL файла не найден</p>")
                    
                    # Загружаем файл с внешнего URL
                    response = requests.get(attachment.url, timeout=30)
                    response.raise_for_status()
                    xlsx_data = response.content
                    
                except requests.exceptions.RequestException as e:
                    return (f"<p style='padding-top:8px;color:red;'>"
                            f"Ошибка при загрузке файла: {str(e)}</p>")
                except Exception as e:
                    return (f"<p style='padding-top:8px;color:red;'>"
                            f"Ошибка при доступе к URL: {str(e)}</p>")
            
            # Проверяем, что данные получены
            if not xlsx_data:
                return ("<p style='padding-top:8px;color:red;'>"
                        "Не удалось получить данные файла</p>")
            
            # Обрабатываем файлы
            if doc_type in ['xlsx', 'xls', 'docx']:
                try:
                    if doc_type == 'xlsx':
                        content = None
                        error_msgs = []
                        
                        # Способ 1: openpyxl с максимально безопасными настройками
                        if OPENPYXL_AVAILABLE:
                            try:
                                # Попробуем с самыми безопасными настройками
                                workbook = openpyxl.load_workbook(
                                    BytesIO(xlsx_data), 
                                    data_only=True,      # Игнорируем формулы
                                    read_only=True,      # Только для чтения
                                    keep_vba=False,      # Не загружаем VBA
                                    keep_links=False     # Не загружаем ссылки
                                )
                                
                                sheet = workbook.active
                                if not sheet:
                                    # Попробуем первый лист по имени
                                    sheet = workbook[workbook.sheetnames[0]]
                                
                                data = []
                                max_rows = 1000  # Ограничиваем количество строк
                                
                                # Читаем данные построчно
                                for row_num, row in enumerate(sheet.iter_rows(values_only=True, max_row=max_rows)):
                                    if row_num > 500:  # Ограничение для превью
                                        break
                                    # Пропускаем полностью пустые строки
                                    if any(cell is not None and str(cell).strip() for cell in row):
                                        # Очищаем данные от сложных объектов
                                        clean_row = []
                                        for cell in row:
                                            if cell is None:
                                                clean_row.append("")
                                            else:
                                                try:
                                                    clean_row.append(str(cell))
                                                except:
                                                    clean_row.append("")
                                        data.append(clean_row)
                                
                                workbook.close()
                                
                                if data:
                                    # Создаем DataFrame с очищенными данными
                                    if len(data) > 1:
                                        # Первая строка как заголовки
                                        headers = []
                                        for i, header in enumerate(data[0]):
                                            if header and str(header).strip():
                                                headers.append(str(header).strip())
                                            else:
                                                headers.append(f"Column_{i+1}")
                                        
                                        content = pd.DataFrame(data[1:], columns=headers)
                                    else:
                                        content = pd.DataFrame(data)
                                        
                            except Exception as e1:
                                error_msgs.append(f"openpyxl улучшенный: {str(e1)}")
                        
                        # Способ 2: pandas с openpyxl engine
                        if content is None:
                            try:
                                content = pd.read_excel(
                                    BytesIO(xlsx_data),
                                    engine='openpyxl',
                                    nrows=500  # Ограничиваем количество строк
                                )
                            except Exception as e2:
                                error_msgs.append(f"pandas+openpyxl: {str(e2)}")
                        
                        # Способ 3: calamine engine (быстрый и надежный)
                        if content is None:
                            try:
                                content = pd.read_excel(
                                    BytesIO(xlsx_data),
                                    engine='calamine',
                                    nrows=500
                                )
                            except Exception as e3:
                                error_msgs.append(f"calamine: {str(e3)}")
                        
                        # Способ 4: xlrd engine (для старых файлов)
                        if content is None and XLRD_AVAILABLE:
                            try:
                                content = pd.read_excel(
                                    BytesIO(xlsx_data),
                                    engine='xlrd',
                                    nrows=500
                                )
                            except Exception as e4:
                                error_msgs.append(f"xlrd: {str(e4)}")
                        
                        # Способ 5: Простое чтение без pandas (последняя попытка)
                        if content is None and OPENPYXL_AVAILABLE:
                            try:
                                from openpyxl import load_workbook
                                wb = load_workbook(BytesIO(xlsx_data), data_only=True, read_only=True)
                                ws = wb.active
                                
                                # Читаем как простые значения
                                simple_data = []
                                if ws:  # Проверяем что worksheet не None
                                    for row in ws.iter_rows(values_only=True, max_row=100):
                                        if any(cell for cell in row):
                                            simple_data.append([str(cell) if cell is not None else "" for cell in row])
                                
                                wb.close()
                                
                                if simple_data:
                                    content = pd.DataFrame(simple_data[1:], columns=simple_data[0] if simple_data else [])
                                    
                            except Exception as e5:
                                error_msgs.append(f"openpyxl простой: {str(e5)}")
                        
                        # Если все способы не сработали
                        if content is None:
                            return (f"<p style='padding-top:8px;color:red;'>"
                                    f"<strong>{attachment.name}</strong><br/>"
                                    f"Не удалось прочитать xlsx файл.<br/>"
                                    f"Ошибки: {' | '.join(error_msgs)}<br/><br/>"
                                    f"<strong>Возможные решения:</strong><br/>"
                                    f"1. Файл содержит сложное форматирование или поврежден<br/>"
                                    f"2. Пересохраните файл в Excel как 'Книга Excel (.xlsx)' без макросов<br/>"
                                    f"3. Экспортируйте в CSV формат<br/>"
                                    f"4. Уберите все стили, формулы и защиту из файла<br/>"
                                    f"5. Попробуйте открыть файл в другой программе для проверки целостности</p>")
                        
                    elif doc_type == 'xls':
                        # Для старых .xls файлов используем xlrd
                        content = pd.read_excel(
                            BytesIO(xlsx_data), 
                            engine='xlrd',
                            nrows=500
                        )
                    elif doc_type == 'docx':
                        doc = DocxDocument(io.BytesIO(xlsx_data))
                        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                        if not paragraphs:
                            return ("<p style='padding-top:8px;color:orange;'>"
                                    "Документ пуст или не содержит текста</p>")
                        return paragraphs
                    
                    # Для Excel файлов возвращаем HTML таблицу
                    if doc_type in ['xlsx', 'xls'] and content is not None:
                        if content.empty:
                            return ("<p style='padding-top:8px;color:orange;'>"
                                    "Файл не содержит данных</p>")
                        
                        # Ограничиваем для превью
                        preview_note = ""
                        if len(content) > 100:
                            content = content.head(100)
                            preview_note = "<p style='color:blue;'>Показаны первые 100 строк</p>"
                        
                        if len(content.columns) > 20:
                            content = content.iloc[:, :20]
                            preview_note += "<p style='color:blue;'>Показаны первые 20 колонок</p>"
                        
                        html_table = content.to_html(index=False, escape=False)
                        return preview_note + html_table
                        
                except Exception as e:
                    return (f"<p style='padding-top:8px;color:red;'>"
                            f"Ошибка при обработке файла {doc_type}: {str(e)}<br/><br/>"
                            f"<strong>Рекомендации:</strong><br/>"
                            f"1. Откройте файл в Excel и пересохраните без форматирования<br/>"
                            f"2. Экспортируйте в CSV для гарантированной совместимости<br/>"
                            f"3. Убедитесь, что файл не защищен паролем</p>")
            
        except Exception as e:
            return (f"<p style='padding-top:8px;color:red;'>"
                    f"Общая ошибка обработки файла: {str(e)}</p>")
        
        return ("<p style='padding-top:8px;color:red;'>"
                "Формат файла не поддерживается</p>") 