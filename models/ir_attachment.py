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
                        content = pd.DataFrame()  # Инициализируем как пустой DataFrame
                        error_msgs = []
                        
                        # Способ 1: openpyxl с правильной обработкой формул
                        if OPENPYXL_AVAILABLE:
                            try:
                                import openpyxl
                                # Загружаем файл с полной информацией о ячейках
                                workbook = openpyxl.load_workbook(
                                    BytesIO(xlsx_data), 
                                    data_only=False,     # Получаем формулы и значения
                                    read_only=False      # Нужно для работы с формулами
                                )
                                
                                sheet = workbook.active
                                if not sheet:
                                    sheet = workbook[workbook.sheetnames[0]]
                                
                                data = []
                                max_rows = 10000  # Увеличиваем ограничение для чтения больших файлов
                                
                                # Читаем данные построчно с правильной обработкой формул
                                if sheet:
                                    for row_num, row_cells in enumerate(sheet.iter_rows(max_row=max_rows)):
                                        if row_num > 5000:  # Увеличиваем ограничение для превью
                                            break
                                        # Включаем все строки, включая пустые (как в Excel)
                                        clean_row = []
                                        for cell in row_cells:
                                            try:
                                                # Проверяем тип ячейки и обрабатываем формулы
                                                if cell.value is None:
                                                    clean_row.append("")
                                                elif isinstance(cell.value, str) and cell.value.startswith('='):
                                                    # Это формула - показываем её как есть
                                                    clean_row.append(str(cell.value))
                                                else:
                                                    # Обычное значение
                                                    cell_value = str(cell.value)
                                                    # Убираем артефакты pandas
                                                    if cell_value in ['nan', 'NaN', 'NaT', 'None']:
                                                        clean_row.append("")
                                                    else:
                                                        clean_row.append(cell_value)
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
                        
                        # Способ 2: pandas с openpyxl engine (лучше для вычисленных значений формул)
                        if content.empty:
                            try:
                                # Pandas может лучше обрабатывать вычисленные значения формул
                                content = pd.read_excel(
                                    BytesIO(xlsx_data),
                                    engine='openpyxl',
                                    nrows=5000,  # Увеличиваем ограничение для чтения больших файлов
                                    header=0,    # Первая строка как заголовки
                                    na_values=['', ' ', 'nan', 'NaN', 'NaT', 'None', '#N/A', '#VALUE!', '#REF!', '#DIV/0!', '#NAME?', '#NULL!', '#NUM!']
                                )
                            except Exception as e2:
                                error_msgs.append(f"pandas+openpyxl: {str(e2)}")
                        
                        # Способ 3: calamine engine (быстрый и надежный)
                        if content.empty:
                            try:
                                content = pd.read_excel(
                                    BytesIO(xlsx_data),
                                    engine='calamine',
                                    nrows=5000
                                )
                            except Exception as e3:
                                error_msgs.append(f"calamine: {str(e3)}")
                        
                        # Способ 4: xlrd engine (для старых файлов)
                        if content.empty and XLRD_AVAILABLE:
                            try:
                                content = pd.read_excel(
                                    BytesIO(xlsx_data),
                                    engine='xlrd',
                                    nrows=5000
                                )
                            except Exception as e4:
                                error_msgs.append(f"xlrd: {str(e4)}")
                        
                        # Способ 5: Простое чтение без pandas (последняя попытка)
                        if content.empty and OPENPYXL_AVAILABLE:
                            try:
                                from openpyxl import load_workbook
                                wb = load_workbook(BytesIO(xlsx_data), data_only=True, read_only=True)
                                ws = wb.active
                                
                                # Читаем как простые значения с правильной обработкой формул
                                simple_data = []
                                if ws:  # Проверяем что worksheet не None
                                    for row in ws.iter_rows(values_only=True, max_row=5000):
                                        # Включаем все строки, включая пустые (как в Excel)
                                        processed_row = []
                                        for cell in row:
                                            if cell is None:
                                                processed_row.append("")
                                            else:
                                                # Конвертируем в строку и обрабатываем формулы
                                                cell_value = str(cell)
                                                # Убираем артефакты pandas
                                                if cell_value in ['nan', 'NaN', 'NaT', 'None']:
                                                    processed_row.append("")
                                                else:
                                                    processed_row.append(cell_value)
                                        simple_data.append(processed_row)
                                
                                wb.close()
                                
                                if simple_data:
                                    # Создаем DataFrame с правильными заголовками
                                    if len(simple_data) > 0:
                                        headers = simple_data[0] if simple_data else []
                                        data_rows = simple_data[1:] if len(simple_data) > 1 else []
                                        content = pd.DataFrame(data_rows, columns=headers)
                                    else:
                                        content = pd.DataFrame()
                                    
                            except Exception as e5:
                                error_msgs.append(f"openpyxl простой: {str(e5)}")
                        
                        # Если все способы не сработали
                        if content.empty:
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
                            nrows=5000
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
                        
                        # Показываем все данные в превью (без ограничений)
                        preview_note = ""
                        # Убираем ограничения на количество строк и колонок
                        # if len(content) > 100:
                        #     content = content.head(100)
                        # 
                        # if len(content.columns) > 20:
                        #     content = content.iloc[:, :20]
                        
                        # Очищаем DataFrame от нежелательных элементов только если content найден
                        if content is not None:
                            # 1. Заменяем названия колонок "Unnamed: 0", "Unnamed: 1" на пустые строки
                            new_columns = []
                            for col in content.columns:
                                if str(col).startswith('Unnamed:'):
                                    new_columns.append('')
                                else:
                                    new_columns.append(col)
                            content.columns = new_columns
                            
                            # 2. Заменяем NaT, NaN, null на пустые значения
                            content = content.fillna('')
                            content = content.replace('NaT', '')
                            content = content.replace('NaN', '')
                            content = content.replace('nan', '')
                        
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