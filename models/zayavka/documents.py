from odoo import api, fields, models
import base64
import io
import logging
try:
    import pymupdf
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

_logger = logging.getLogger(__name__)


class AmanatZayavkaDocuments(models.Model):
    _inherit = 'amanat.zayavka'

    # Поля для подписанных документов
    signed_zayavka_file = fields.Binary(string='Подписанная заявка', readonly=True)
    signed_zayavka_filename = fields.Char(string='Имя подписанной заявки', readonly=True)
    
    signed_invoice_file = fields.Binary(string='Подписанный инвойс', readonly=True)
    signed_invoice_filename = fields.Char(string='Имя подписанного инвойса', readonly=True)
    
    signed_assignment_file = fields.Binary(string='Подписанное поручение', readonly=True)
    signed_assignment_filename = fields.Char(string='Имя подписанного поручения', readonly=True)
    
    signed_swift_file = fields.Binary(string='Подписанный SWIFT', readonly=True)
    signed_swift_filename = fields.Char(string='Имя подписанного SWIFT', readonly=True)
    
    signed_swift103_file = fields.Binary(string='Подписанный SWIFT 103', readonly=True)
    signed_swift103_filename = fields.Char(string='Имя подписанного SWIFT 103', readonly=True)
    
    signed_swift199_file = fields.Binary(string='Подписанный SWIFT 199', readonly=True)
    signed_swift199_filename = fields.Char(string='Имя подписанного SWIFT 199', readonly=True)
    
    signed_report_file = fields.Binary(string='Подписанный акт-отчет', readonly=True)
    signed_report_filename = fields.Char(string='Имя подписанного акт-отчета', readonly=True)

    # Поля для статуса подписания каждого документа
    zayavka_signature_state = fields.Selection([
        ('draft', 'Загружен PDF'),
        ('ready', 'Готов к подписанию'),
        ('signed', 'Подписан'),
    ], string='Статус подписания заявки', default='draft')
    
    invoice_signature_state = fields.Selection([
        ('draft', 'Загружен PDF'),
        ('ready', 'Готов к подписанию'),
        ('signed', 'Подписан'),
    ], string='Статус подписания инвойса', default='draft')
    
    assignment_signature_state = fields.Selection([
        ('draft', 'Загружен PDF'),
        ('ready', 'Готов к подписанию'),
        ('signed', 'Подписан'),
    ], string='Статус подписания поручения', default='draft')
    
    swift_signature_state = fields.Selection([
        ('draft', 'Загружен PDF'),
        ('ready', 'Готов к подписанию'),
        ('signed', 'Подписан'),
    ], string='Статус подписания SWIFT', default='draft')
    
    swift103_signature_state = fields.Selection([
        ('draft', 'Загружен PDF'),
        ('ready', 'Готов к подписанию'),
        ('signed', 'Подписан'),
    ], string='Статус подписания SWIFT 103', default='draft')
    
    swift199_signature_state = fields.Selection([
        ('draft', 'Загружен PDF'),
        ('ready', 'Готов к подписанию'),
        ('signed', 'Подписан'),
    ], string='Статус подписания SWIFT 199', default='draft')
    
    report_signature_state = fields.Selection([
        ('draft', 'Загружен PDF'),
        ('ready', 'Готов к подписанию'),
        ('signed', 'Подписан'),
    ], string='Статус подписания акт-отчета', default='draft')

    # Связи с позициями и назначениями подписей для каждого типа документа
    zayavka_signature_position_ids = fields.One2many(
        'amanat.zayavka.signature.position', 
        'zayavka_id', 
        string='Позиции подписей заявки',
        domain=[('document_type', '=', 'zayavka')]
    )
    
    zayavka_signature_assignment_ids = fields.One2many(
        'amanat.zayavka.signature.assignment', 
        'zayavka_id', 
        string='Назначенные подписи заявки',
        domain=[('document_type', '=', 'zayavka')]
    )

    invoice_signature_position_ids = fields.One2many(
        'amanat.zayavka.signature.position', 
        'zayavka_id', 
        string='Позиции подписей инвойса',
        domain=[('document_type', '=', 'invoice')]
    )
    
    invoice_signature_assignment_ids = fields.One2many(
        'amanat.zayavka.signature.assignment', 
        'zayavka_id', 
        string='Назначенные подписи инвойса',
        domain=[('document_type', '=', 'invoice')]
    )

    assignment_signature_position_ids = fields.One2many(
        'amanat.zayavka.signature.position', 
        'zayavka_id', 
        string='Позиции подписей поручения',
        domain=[('document_type', '=', 'assignment')]
    )
    
    assignment_signature_assignment_ids = fields.One2many(
        'amanat.zayavka.signature.assignment', 
        'zayavka_id', 
        string='Назначенные подписи поручения',
        domain=[('document_type', '=', 'assignment')]
    )

    swift_signature_position_ids = fields.One2many(
        'amanat.zayavka.signature.position', 
        'zayavka_id', 
        string='Позиции подписей SWIFT',
        domain=[('document_type', '=', 'swift')]
    )
    
    swift_signature_assignment_ids = fields.One2many(
        'amanat.zayavka.signature.assignment', 
        'zayavka_id', 
        string='Назначенные подписи SWIFT',
        domain=[('document_type', '=', 'swift')]
    )

    swift103_signature_position_ids = fields.One2many(
        'amanat.zayavka.signature.position', 
        'zayavka_id', 
        string='Позиции подписей SWIFT 103',
        domain=[('document_type', '=', 'swift103')]
    )
    
    swift103_signature_assignment_ids = fields.One2many(
        'amanat.zayavka.signature.assignment', 
        'zayavka_id', 
        string='Назначенные подписи SWIFT 103',
        domain=[('document_type', '=', 'swift103')]
    )

    swift199_signature_position_ids = fields.One2many(
        'amanat.zayavka.signature.position', 
        'zayavka_id', 
        string='Позиции подписей SWIFT 199',
        domain=[('document_type', '=', 'swift199')]
    )
    
    swift199_signature_assignment_ids = fields.One2many(
        'amanat.zayavka.signature.assignment', 
        'zayavka_id', 
        string='Назначенные подписи SWIFT 199',
        domain=[('document_type', '=', 'swift199')]
    )

    report_signature_position_ids = fields.One2many(
        'amanat.zayavka.signature.position', 
        'zayavka_id', 
        string='Позиции подписей акт-отчета',
        domain=[('document_type', '=', 'report')]
    )
    
    report_signature_assignment_ids = fields.One2many(
        'amanat.zayavka.signature.assignment', 
        'zayavka_id', 
        string='Назначенные подписи акт-отчета',
        domain=[('document_type', '=', 'report')]
    )

    # Методы для определения подписей в каждом типе документа
    def action_detect_signatures_zayavka(self):
        """Определить позиции подписей в заявке"""
        return self._detect_signatures_for_document('zayavka', self.zayavka_file, 'zayavka_signature_state')

    def action_detect_signatures_invoice(self):
        """Определить позиции подписей в инвойсе"""
        return self._detect_signatures_for_document('invoice', self.invoice_file, 'invoice_signature_state')

    def action_detect_signatures_assignment(self):
        """Определить позиции подписей в поручении"""
        return self._detect_signatures_for_document('assignment', self.assignment_file, 'assignment_signature_state')

    def action_detect_signatures_swift(self):
        """Определить позиции подписей в SWIFT"""
        return self._detect_signatures_for_document('swift', self.swift_file, 'swift_signature_state')

    def action_detect_signatures_swift103(self):
        """Определить позиции подписей в SWIFT 103"""
        return self._detect_signatures_for_document('swift103', self.swift103_file, 'swift103_signature_state')

    def action_detect_signatures_swift199(self):
        """Определить позиции подписей в SWIFT 199"""
        return self._detect_signatures_for_document('swift199', self.swift199_file, 'swift199_signature_state')

    def action_detect_signatures_report(self):
        """Определить позиции подписей в акт-отчете"""
        return self._detect_signatures_for_document('report', self.report_file, 'report_signature_state')

    # Методы для подписания каждого типа документа
    def action_sign_zayavka(self):
        """Подписать заявку"""
        return self._sign_document('zayavka', self.zayavka_file, 'signed_zayavka_file', 'signed_zayavka_filename', 'zayavka_signature_state')

    def action_sign_invoice(self):
        """Подписать инвойс"""
        return self._sign_document('invoice', self.invoice_file, 'signed_invoice_file', 'signed_invoice_filename', 'invoice_signature_state')

    def action_sign_assignment(self):
        """Подписать поручение"""
        return self._sign_document('assignment', self.assignment_file, 'signed_assignment_file', 'signed_assignment_filename', 'assignment_signature_state')

    def action_sign_swift(self):
        """Подписать SWIFT"""
        return self._sign_document('swift', self.swift_file, 'signed_swift_file', 'signed_swift_filename', 'swift_signature_state')

    def action_sign_swift103(self):
        """Подписать SWIFT 103"""
        return self._sign_document('swift103', self.swift103_file, 'signed_swift103_file', 'signed_swift103_filename', 'swift103_signature_state')

    def action_sign_swift199(self):
        """Подписать SWIFT 199"""
        return self._sign_document('swift199', self.swift199_file, 'signed_swift199_file', 'signed_swift199_filename', 'swift199_signature_state')

    def action_sign_report(self):
        """Подписать акт-отчет"""
        return self._sign_document('report', self.report_file, 'signed_report_file', 'signed_report_filename', 'report_signature_state')

    # Методы сброса документов
    def action_reset_zayavka_document(self):
        """Сбросить все данные заявки"""
        return self._reset_document('zayavka', 'zayavka_file', 'signed_zayavka_file', 'signed_zayavka_filename', 'zayavka_signature_state')

    def action_reset_invoice_document(self):
        """Сбросить все данные инвойса"""
        return self._reset_document('invoice', 'invoice_file', 'signed_invoice_file', 'signed_invoice_filename', 'invoice_signature_state')

    def action_reset_assignment_document(self):
        """Сбросить все данные поручения"""
        return self._reset_document('assignment', 'assignment_file', 'signed_assignment_file', 'signed_assignment_filename', 'assignment_signature_state')

    def action_reset_swift_document(self):
        """Сбросить все данные SWIFT"""
        return self._reset_document('swift', 'swift_file', 'signed_swift_file', 'signed_swift_filename', 'swift_signature_state')

    def action_reset_swift103_document(self):
        """Сбросить все данные SWIFT 103"""
        return self._reset_document('swift103', 'swift103_file', 'signed_swift103_file', 'signed_swift103_filename', 'swift103_signature_state')

    def action_reset_swift199_document(self):
        """Сбросить все данные SWIFT 199"""
        return self._reset_document('swift199', 'swift199_file', 'signed_swift199_file', 'signed_swift199_filename', 'swift199_signature_state')

    def action_reset_report_document(self):
        """Сбросить все данные акт-отчета"""
        return self._reset_document('report', 'report_file', 'signed_report_file', 'signed_report_filename', 'report_signature_state')

    def _detect_signatures_for_document(self, document_type, pdf_file, state_field):
        """Универсальный метод для определения подписей в документе"""
        if not pdf_file:
            from odoo.exceptions import UserError
            raise UserError(f'Сначала загрузите PDF файл для {document_type}')
        
        # Удаляем существующие позиции и назначения для данного типа документа
        position_model = self.env['amanat.zayavka.signature.position']
        assignment_model = self.env['amanat.zayavka.signature.assignment']
        
        existing_positions = position_model.search([
            ('zayavka_id', '=', self.id),
            ('document_type', '=', document_type)
        ])
        existing_assignments = assignment_model.search([
            ('zayavka_id', '=', self.id),
            ('document_type', '=', document_type)
        ])
        
        existing_positions.unlink()
        existing_assignments.unlink()
        
        # Автоматически находим позиции
        found_positions = self._auto_find_signatures(document_type, pdf_file)
        
        # Создаем назначения подписей
        if found_positions:
            self._create_signature_assignments(document_type, found_positions)
        
        # Меняем статус на готов к подписанию
        setattr(self, state_field, 'ready')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _auto_find_signatures(self, document_type, pdf_file):
        """Автоматический поиск белого текста 'Подпись' и 'Печать' в PDF"""
        if not PYMUPDF_AVAILABLE:
            _logger.warning("PyMuPDF не установлен. Автоматический поиск недоступен.")
            return []
            
        if not pdf_file:
            return []
            
        try:
            # Декодируем PDF из base64
            pdf_data = base64.b64decode(pdf_file)
            
            # Открываем PDF с помощью PyMuPDF
            doc = pymupdf.open(stream=pdf_data, filetype="pdf")
            
            found_signatures = []
            signature_count = 0
            stamp_count = 0
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Получаем детальную информацию о тексте
                text_dict = page.get_text("dict")
                
                for block in text_dict["blocks"]:
                    if "lines" in block:  # Текстовый блок
                        for line in block["lines"]:
                            for span in line["spans"]:
                                text = span["text"].strip()
                                
                                # Проверяем цвет текста (белый или близкий к белому)
                                color_int = span["color"]
                                color_rgb = pymupdf.sRGB_to_rgb(color_int)
                                
                                # Белый цвет: RGB близко к (1.0, 1.0, 1.0)
                                is_white = all(c > 0.9 for c in color_rgb)
                                
                                if is_white and text.lower() in ['подпись', 'печать']:
                                    bbox = span["bbox"]
                                    
                                    # Размеры области найденного текста
                                    text_width = bbox[2] - bbox[0]
                                    text_height = bbox[3] - bbox[1]
                                    
                                    if text.lower() == 'подпись':
                                        signature_count += 1
                                        sig_type = 'signature'
                                        name = f'Подпись {signature_count}'
                                    else:  # 'печать'
                                        stamp_count += 1
                                        sig_type = 'stamp'
                                        name = f'Печать {stamp_count}'
                                    
                                    found_signatures.append({
                                        'name': name,
                                        'zayavka_id': self.id,
                                        'document_type': document_type,
                                        'page_number': page_num + 1,
                                        'x_position': bbox[0],
                                        'y_position': bbox[1],
                                        'width': text_width,
                                        'height': text_height,
                                        'signature_type': sig_type,
                                        'required': True,
                                    })
                                    
                                    _logger.info(f"Найден белый текст '{text}' на странице {page_num + 1}, RGB: {color_rgb}")
            
            doc.close()
            
            # Создаем записи позиций подписей
            if found_signatures:
                self.env['amanat.zayavka.signature.position'].create(found_signatures)
                _logger.info(f'Найдено сигнатур в {document_type}: {len(found_signatures)} (подписей: {signature_count}, печатей: {stamp_count})')
            else:
                _logger.warning(f'Белый текст "Подпись" или "Печать" не найден в документе {document_type}')
            
            return found_signatures
            
        except Exception as e:
            _logger.error(f"Ошибка при поиске белых подписей в {document_type}: {str(e)}")
            from odoo.exceptions import UserError
            raise UserError(f'Ошибка при поиске позиций белых подписей в {document_type}: {str(e)}')

    def _create_signature_assignments(self, document_type, found_positions):
        """Создаем назначения подписей на основе найденных позиций"""
        position_model = self.env['amanat.zayavka.signature.position']
        assignment_model = self.env['amanat.zayavka.signature.assignment']
        
        # Получаем созданные позиции
        positions = position_model.search([
            ('zayavka_id', '=', self.id),
            ('document_type', '=', document_type)
        ])
        
        # Создаем новые назначения для каждой позиции
        for position in positions:
            assignment_model.create({
                'zayavka_id': self.id,
                'position_id': position.id,
                'document_type': document_type,
                'name': position.name,
            })

    def _sign_document(self, document_type, source_file, signed_file_field, signed_filename_field, state_field):
        """Универсальный метод для подписания документа"""
        # Получаем назначения подписей для данного типа документа
        assignments = self.env['amanat.zayavka.signature.assignment'].search([
            ('zayavka_id', '=', self.id),
            ('document_type', '=', document_type)
        ])
        
        # Проверяем, что все обязательные подписи назначены
        missing_signatures = assignments.filtered(
            lambda x: x.position_id.required and not x.signature_id
        )
        
        if missing_signatures:
            from odoo.exceptions import UserError
            raise UserError(
                f'Не назначены обязательные подписи для позиций в {document_type}: '
                f'{", ".join(missing_signatures.mapped("name"))}'
            )
        
        # Генерируем подписанный документ
        signed_file_data, signed_filename = self._generate_signed_document(document_type, source_file)
        
        # Сохраняем подписанный файл
        setattr(self, signed_file_field, signed_file_data)
        setattr(self, signed_filename_field, signed_filename)
        
        # Обновляем статус
        setattr(self, state_field, 'signed')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _generate_signed_document(self, document_type, source_file):
        """Генерируем подписанный PDF документ"""
        if not PYMUPDF_AVAILABLE:
            # Fallback: просто копируем оригинальный файл
            _logger.warning("PyMuPDF не установлен. Возвращаем оригинальный файл.")
            return source_file, f"signed_{document_type}.pdf"
        
        if not source_file:
            from odoo.exceptions import UserError
            raise UserError(f'Отсутствует исходный файл для {document_type}')
            
        try:
            # Декодируем оригинальный PDF
            pdf_data = base64.b64decode(source_file)
            doc = pymupdf.open(stream=pdf_data, filetype="pdf")
            
            # Получаем назначения подписей с изображениями для данного типа документа
            assignments_with_signatures = self.env['amanat.zayavka.signature.assignment'].search([
                ('zayavka_id', '=', self.id),
                ('document_type', '=', document_type),
                ('signature_id', '!=', False)
            ])
            
            for assignment in assignments_with_signatures:
                if not assignment.signature_id.image:
                    continue
                
                # Декодируем изображение подписи
                signature_image_data = base64.b64decode(assignment.signature_id.image)
                
                # Получаем страницу
                page_num = assignment.page_number - 1  # PyMuPDF использует 0-based индексы
                if page_num >= len(doc):
                    continue
                    
                page = doc[page_num]
                
                # Создаем прямоугольник для вставки изображения по центру найденного текста
                # Получаем центр найденного текста
                text_center_x = assignment.x_position + (assignment.width / 2)
                text_center_y = assignment.y_position + (assignment.height / 2)
                
                # Используем размеры подписи из библиотеки или расширяем область текста
                if assignment.signature_id.default_width and assignment.signature_id.default_height:
                    signature_width = assignment.signature_id.default_width
                    signature_height = assignment.signature_id.default_height
                else:
                    # Если размеры не заданы, используем область текста с небольшим увеличением
                    signature_width = max(assignment.width * 1.5, 100)  # минимум 100px
                    signature_height = max(assignment.height * 1.5, 30)  # минимум 30px
                
                # Вычисляем координаты для центрирования изображения подписи
                signature_x = text_center_x - (signature_width / 2)
                signature_y = text_center_y - (signature_height / 2)
                
                rect = pymupdf.Rect(
                    signature_x,
                    signature_y,
                    signature_x + signature_width,
                    signature_y + signature_height
                )
                
                # Вставляем изображение подписи
                page.insert_image(rect, stream=signature_image_data)
            
            # Сохраняем подписанный PDF
            pdf_bytes = doc.tobytes()
            doc.close()
            
            # Кодируем в base64 и возвращаем
            signed_file_data = base64.b64encode(pdf_bytes)
            signed_filename = f"signed_{document_type}_{self.zayavka_id or self.id}.pdf"
            
            return signed_file_data, signed_filename
            
        except Exception as e:
            from odoo.exceptions import UserError
            raise UserError(f'Ошибка при генерации подписанного документа {document_type}: {str(e)}')

    def _reset_document(self, document_type, source_file_field, signed_file_field, signed_filename_field, state_field):
        """Универсальный метод для сброса документа и всех связанных данных"""
        from odoo.exceptions import UserError
        
        # Проверяем есть ли что сбрасывать
        source_file = getattr(self, source_file_field, None)
        signed_file = getattr(self, signed_file_field, None)
        
        if not source_file and not signed_file:
            raise UserError(f'Нет данных для сброса в {document_type}')
        
        # Сначала удаляем все назначения подписей для данного типа документа
        assignment_model = self.env['amanat.zayavka.signature.assignment']
        existing_assignments = assignment_model.search([
            ('zayavka_id', '=', self.id),
            ('document_type', '=', document_type)
        ])
        existing_assignments.unlink()
        
        # Затем удаляем все позиции подписей для данного типа документа
        position_model = self.env['amanat.zayavka.signature.position']
        existing_positions = position_model.search([
            ('zayavka_id', '=', self.id),
            ('document_type', '=', document_type)
        ])
        existing_positions.unlink()
        
        # Очищаем файлы и сбрасываем статус
        update_vals = {
            source_file_field: False,
            signed_file_field: False,
            signed_filename_field: False,
            state_field: 'draft'
        }
        
        self.write(update_vals)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Успешно',
                'message': f'Все данные {document_type} сброшены',
                'type': 'success',
                'sticky': False,
            }
        }