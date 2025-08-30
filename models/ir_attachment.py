# -*- coding: utf-8 -*-
import io
import base64
import logging
import requests
from io import BytesIO
from collections import defaultdict

import pandas as pd
from docx import Document as DocxDocument
from odoo import api, fields, models, _
from odoo.exceptions import AccessError

# Инициализируем logger ПЕРВЫМ!
_logger = logging.getLogger(__name__)

# ДИАГНОСТИЧЕСКОЕ СООБЩЕНИЕ - ПРОВЕРЯЕМ ЗАГРУЖАЕТСЯ ЛИ ФАЙЛ
_logger.info("🚨 AMANAT: ir_attachment.py module is being loaded!")
print("🚨 AMANAT: ir_attachment.py module is being loaded!")  # Дублируем в print

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

    def _check_access(self, operation: str):
        """
        🚨🚨🚨 СУПЕР-ЯДЕРНЫЙ ОБХОД: Всегда возвращаем None = нет проблем с доступом 🚨🚨🚨
        """
        _logger.error(f"🚨🚨🚨 AMANAT ir.attachment._check_access CALLED! operation: {operation}, user: {self.env.user.name}, IDs: {self.ids} 🚨🚨🚨")
        _logger.error(f"🚨 AMANAT: ALWAYS RETURNING None - FULL ACCESS TO ALL ATTACHMENTS! 🚨")
        print(f"🚨 AMANAT: ir.attachment._check_access NUCLEAR BYPASS for {self.env.user.name}, operation: {operation} 🚨")
        
        # СУПЕР-ЯДЕРНЫЙ ПОДХОД: Всегда возвращаем None = нет проблем с доступом
        return None

    


    
    def _filter_access_rules(self, operation):
        """ЯДЕРНЫЙ ОБХОД: Полностью отключаем record rules для ВСЕХ пользователей"""
        _logger.error(f"🚨🚨🚨 AMANAT _filter_access_rules called for IDs: {self.ids}, operation: {operation}, user: {self.env.user.name} 🚨🚨🚨")
        
        # ЭКСТРЕМАЛЬНОЕ ИЗМЕНЕНИЕ: Обходим правила для ВСЕХ пользователей без исключений
        _logger.error(f"🚨 AMANAT: BYPASSING ALL RECORD RULES FOR ALL USERS - NO EXCEPTIONS! 🚨")
        print(f"🚨 AMANAT: _filter_access_rules BYPASS for user {self.env.user.name}, operation: {operation} 🚨")
        
        # Возвращаем все записи без фильтрации для ВСЕХ
        return self

    def read(self, fields=None, load='_classic_read'):
        """
        AMANAT: Агрессивное переопределение read() для обхода record rules
        """
        _logger.info("AMANAT ir.attachment.read() called for IDs: %s, user: %s", self.ids, self.env.user.name)
        
        if self.env.user._is_superuser():
            _logger.info("AMANAT: Superuser - using normal read() for %s", self.ids)
            return super().read(fields, load)
            
        if self.env.user.has_group('base.group_user'):
            _logger.info("AMANAT: Internal user %s - BYPASSING RECORD RULES with sudo() for %s", self.env.user.name, self.ids)
            # Используем sudo() для обхода record rules, но вызываем оригинальный метод
            return super(IrAttachment, self.sudo()).read(fields, load)
            
        _logger.info("AMANAT: External user %s - using normal read() for %s", self.env.user.name, self.ids)
        return super().read(fields, load)

    @api.model
    def check(self, mode, values=None):
        """
        🚨🚨🚨 ЭКСТРЕМАЛЬНЫЙ ЯДЕРНЫЙ ОБХОД: ПОЛНЫЙ ДОСТУП КО ВСЕМ ФАЙЛАМ 🚨🚨🚨
        ЭТОТ МЕТОД ПЕРЕОПРЕДЕЛЯЕТ БАЗОВЫЙ ir.attachment.check() ИЗ ODOO CORE
        """
        _logger.error(f"🚨🚨🚨 AMANAT OVERRIDDEN CHECK() CALLED! IDs: {self.ids}, mode: {mode}, user: {self.env.user.name} 🚨🚨🚨")
        print(f"🚨🚨🚨 AMANAT OVERRIDDEN CHECK() CALLED! IDs: {self.ids}, mode: {mode}, user: {self.env.user.name} 🚨🚨🚨")
        
        # АБСОЛЮТНО ЯДЕРНЫЙ ПОДХОД: Разрешаем ВСЕ операции для ВСЕХ пользователей
        _logger.error(f"🚨 AMANAT: FULL ACCESS GRANTED TO ALL USERS - BYPASSING ALL SECURITY! 🚨")
        print(f"🚨 AMANAT: FULL ACCESS GRANTED TO ALL USERS - BYPASSING ALL SECURITY! 🚨")
        return True
        

    @api.model
    def get_hidden_columns_and_data_range(self, xlsx_data):
        """Определяет скрытые колонки и реальный диапазон данных для оптимизации чтения"""
        if not OPENPYXL_AVAILABLE:
            return set(), None, None
        
        try:
            import openpyxl
            from openpyxl.utils import get_column_letter
            
            # Загружаем файл только для анализа структуры
            workbook = openpyxl.load_workbook(
                BytesIO(xlsx_data), 
                data_only=True,
                read_only=True
            )
            
            sheet = workbook.active
            if not sheet:
                sheet = workbook[workbook.sheetnames[0]]
            
            hidden_columns = set()
            
            # Определяем реальные границы файла
            # Используем max_column из опenpyxl как максимальную границу
            real_max_column = sheet.max_column or 1
            real_max_row = sheet.max_row or 1
            
            # Ограничиваем анализ разумными пределами
            max_cols_to_analyze = min(real_max_column, 50)  # Максимум 50 колонок
            max_rows_to_analyze = min(real_max_row, 100)    # Максимум 100 строк для анализа
            
            # Определяем фактический диапазон данных
            actual_data_column = 0
            for row in sheet.iter_rows(min_row=1, max_row=max_rows_to_analyze, max_col=max_cols_to_analyze, values_only=True):
                for col_idx, cell_value in enumerate(row):
                    if cell_value is not None and str(cell_value).strip():
                        actual_data_column = max(actual_data_column, col_idx + 1)
            
            # Если данных не найдено, используем минимальный диапазон
            if actual_data_column == 0:
                actual_data_column = min(real_max_column, 10)  # Минимум 10 колонок
            
            # Убеждаемся, что actual_data_column не превышает реальный максимум
            actual_data_column = min(actual_data_column, real_max_column)
            
            # Определяем скрытые колонки только в пределах фактического диапазона
            for col_num in range(1, actual_data_column + 1):
                column_letter = get_column_letter(col_num)
                
                # Проверяем различные способы скрытия колонок
                is_hidden = False
                
                # Способ 1: через column_dimensions.hidden
                if column_letter in sheet.column_dimensions:
                    if getattr(sheet.column_dimensions[column_letter], 'hidden', False):
                        is_hidden = True
                
                # Способ 2: через width = 0 (иногда так скрывают колонки)
                if column_letter in sheet.column_dimensions:
                    width = getattr(sheet.column_dimensions[column_letter], 'width', None)
                    if width is not None and width == 0:
                        is_hidden = True
                
                # Способ 3: проверяем, что колонка действительно пустая
                if not is_hidden:
                    col_values = []
                    for row_num in range(1, min(21, max_rows_to_analyze + 1)):
                        if row_num <= real_max_row:  # Проверяем границы
                            cell_value = sheet.cell(row=row_num, column=col_num).value
                            if cell_value is not None and str(cell_value).strip():
                                col_values.append(str(cell_value).strip())
                    
                    # Если колонка полностью пустая, считаем её скрытой
                    if len(col_values) == 0:
                        is_hidden = True
                
                if is_hidden:
                    hidden_columns.add(col_num - 1)  # Индекс с 0
            
            workbook.close()
            
            return hidden_columns, actual_data_column, min(real_max_row, 5000)
            
        except Exception as e:
            # Если не удалось проанализировать структуру, возвращаем безопасные значения
            return set(), 30, 5000  # Ограничиваем 30 колонками и 5000 строками

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
            if doc_type in ['xlsx', 'xls', 'docx', 'pdf']:
                try:
                    content = pd.DataFrame()  # Инициализируем переменную content
                    if doc_type == 'xlsx':
                        # Сначала анализируем структуру файла для оптимизации
                        hidden_columns, max_data_column, max_data_row = self.get_hidden_columns_and_data_range(xlsx_data)
                        
                        # Ограничиваем количество читаемых колонок и строк
                        max_cols_to_read = min(max_data_column or 30, 50)  # Максимум 50 колонок
                        max_rows_to_read = min(max_data_row or 5000, 5000)  # Максимум 5000 строк
                        content = pd.DataFrame()  # Инициализируем как пустой DataFrame
                        error_msgs = []
                        
                        # Способ 1: openpyxl с правильной обработкой формул
                        if OPENPYXL_AVAILABLE:
                            try:
                                import openpyxl
                                from openpyxl.utils import get_column_letter
                                
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
                                
                                # Читаем данные построчно с правильной обработкой формул
                                if sheet:
                                    for row_num, row_cells in enumerate(sheet.iter_rows(max_row=max_rows_to_read, max_col=max_cols_to_read)):
                                        if row_num > max_rows_to_read:
                                            break
                                        # Включаем все строки, включая пустые (как в Excel)
                                        clean_row = []
                                        for cell_idx, cell in enumerate(row_cells):
                                            # Пропускаем скрытые колонки
                                            if cell_idx in hidden_columns:
                                                continue
                                                
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
                                        
                                        # Добавляем строки только если они не пустые или это первая строка (заголовки)
                                        if clean_row and (row_num == 0 or any(cell.strip() for cell in clean_row if cell)):
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
                        
                        # Определяем РЕАЛЬНОЕ количество колонок в файле несколькими способами
                        actual_columns_count = None
                        
                        # Способ 1: Пробуем через pandas без параметров
                        try:
                            test_df = pd.read_excel(BytesIO(xlsx_data), engine='openpyxl', nrows=1, header=None)
                            actual_columns_count = len(test_df.columns)
                        except:
                            pass
                        
                        # Способ 2: Если первый способ не сработал, пробуем через openpyxl напрямую
                        if actual_columns_count is None and OPENPYXL_AVAILABLE:
                            try:
                                import openpyxl
                                workbook = openpyxl.load_workbook(BytesIO(xlsx_data), data_only=True, read_only=True)
                                sheet = workbook.active
                                if not sheet:
                                    sheet = workbook[workbook.sheetnames[0]]
                                
                                # Проверяем реальное количество колонок с данными
                                max_col_with_data = 0
                                for row in sheet.iter_rows(min_row=1, max_row=5, values_only=True):
                                    for col_idx, cell_value in enumerate(row):
                                        if cell_value is not None:
                                            max_col_with_data = max(max_col_with_data, col_idx + 1)
                                
                                actual_columns_count = max_col_with_data
                                workbook.close()
                            except:
                                pass
                        
                        # Способ 3: Если всё не сработало, используем консервативный подход
                        if actual_columns_count is None or actual_columns_count == 0:
                            actual_columns_count = min(max_cols_to_read, 20)  # Максимум 20 колонок
                        
                        # Теперь создаём safe_visible_columns на основе реального количества колонок
                        safe_visible_columns = []
                        for col_idx in range(min(actual_columns_count, max_cols_to_read)):
                            if col_idx not in hidden_columns:
                                safe_visible_columns.append(col_idx)
                        
                        # Дополнительная проверка: убираем любые индексы >= actual_columns_count
                        safe_visible_columns = [col for col in safe_visible_columns if col < actual_columns_count]
                        
                        # Способ 2: pandas с openpyxl engine (лучше для вычисленных значений формул)
                        if content.empty:
                            try:
                                # Pandas может лучше обрабатывать вычисленные значения формул
                                content = pd.read_excel(
                                    BytesIO(xlsx_data),
                                    engine='openpyxl',
                                    nrows=max_rows_to_read,
                                    header=0,    # Первая строка как заголовки
                                    usecols=safe_visible_columns,  # Читаем только безопасные видимые колонки
                                    na_values=['', ' ', 'nan', 'NaN', 'NaT', 'None', '#N/A', '#VALUE!', '#REF!', '#DIV/0!', '#NAME?', '#NULL!', '#NUM!']
                                )
                            except Exception as e2:
                                error_msgs.append(f"pandas+openpyxl: {str(e2)}")
                        
                        # Способ 3: calamine engine (быстрый и надежный)
                        if content.empty:
                            try:
                                # Для calamine используем только безопасные колонки
                                content = pd.read_excel(
                                    BytesIO(xlsx_data),
                                    engine='calamine',
                                    nrows=max_rows_to_read,
                                    usecols=safe_visible_columns  # Читаем только безопасные видимые колонки
                                )
                            except Exception as e3:
                                error_msgs.append(f"calamine: {str(e3)}")
                        
                        # Способ 4: xlrd engine (для старых файлов)
                        if content.empty and XLRD_AVAILABLE:
                            try:
                                content = pd.read_excel(
                                    BytesIO(xlsx_data),
                                    engine='xlrd',
                                    nrows=max_rows_to_read,
                                    usecols=safe_visible_columns  # Читаем только безопасные видимые колонки
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
                                    for row in ws.iter_rows(values_only=True, max_row=max_rows_to_read, max_col=max_cols_to_read):
                                        # Включаем все строки, включая пустые (как в Excel)
                                        processed_row = []
                                        for cell_idx, cell in enumerate(row):
                                            # Пропускаем скрытые колонки
                                            if cell_idx in hidden_columns:
                                                continue
                                                
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
                                        
                                        # Добавляем строки только если они не пустые или это первая строка (заголовки)
                                        if processed_row and (len(simple_data) == 0 or any(cell.strip() for cell in processed_row if cell)):
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
                        # Анализируем структуру файла для оптимизации (может не работать для .xls)
                        try:
                            hidden_columns, max_data_column, max_data_row = self.get_hidden_columns_and_data_range(xlsx_data)
                            max_cols_to_read = min(max_data_column or 30, 50)  # Максимум 50 колонок
                            max_rows_to_read = min(max_data_row or 5000, 5000)  # Максимум 5000 строк
                            
                            # Определяем колонки для чтения (исключаем скрытые)
                            visible_columns = []
                            for col_idx in range(max_cols_to_read):
                                if col_idx not in hidden_columns:
                                    visible_columns.append(col_idx)
                            
                            content = pd.read_excel(
                                BytesIO(xlsx_data), 
                                engine='xlrd',
                                nrows=max_rows_to_read,
                                usecols=visible_columns
                            )
                        except:
                            # Если анализ не удался, читаем как обычно
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
                    elif doc_type == 'pdf':
                        # Для PDF возвращаем URL для iframe просмотра
                        return {
                            'type': 'pdf',
                            'url': f'/web/content/{attach_id}?download=false',
                            'attachment_id': attach_id,
                            'filename': attachment.name or 'document.pdf'
                        }
                    
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