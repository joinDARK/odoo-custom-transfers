from odoo import api, fields, models
import base64
import io
import json
import logging
import subprocess
import tempfile
import os
try:
    import pymupdf
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

_logger = logging.getLogger(__name__)


class AmanatZayavkaDocuments(models.Model):
    _inherit = 'amanat.zayavka'

    # Поля для подписанных документов
    signed_zayavka_attachments = fields.Many2many(
        'ir.attachment', 
        'signed_zayavka_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Подписанная заявка',
        readonly=True
    )
    
    signed_invoice_attachments = fields.Many2many(
        'ir.attachment', 
        'signed_invoice_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Подписанный инвойс',
        readonly=True
    )
    
    signed_assignment_attachments = fields.Many2many(
        'ir.attachment', 
        'signed_assignment_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Подписанное поручение',
        readonly=True
    )
    
    signed_swift_attachments = fields.Many2many(
        'ir.attachment', 
        'signed_swift_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Подписанный SWIFT',
        readonly=True
    )
    
    signed_swift103_attachments = fields.Many2many(
        'ir.attachment', 
        'signed_swift103_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Подписанный SWIFT 103',
        readonly=True
    )
    
    signed_swift199_attachments = fields.Many2many(
        'ir.attachment', 
        'signed_swift199_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Подписанный SWIFT 199',
        readonly=True
    )
    
    signed_report_attachments = fields.Many2many(
        'ir.attachment', 
        'signed_report_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Подписанный акт-отчет',
        readonly=True
    )

    signed_zayavka_start_attachments = fields.Many2many(
        'ir.attachment', 
        'signed_zayavka_start_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Подписанная заявка Вход',
    )

    signed_zayavka_end_attachments = fields.Many2many(
        'ir.attachment', 
        'signed_zayavka_end_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Подписанная заявка Выход',
    )

    signed_assignment_start_attachments = fields.Many2many(
        'ir.attachment', 
        'signed_assignment_start_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Подписанное поручение Вход',
    )

    signed_assignment_end_attachments = fields.Many2many(
        'ir.attachment', 
        'signed_assignment_end_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Подписанное поручение Выход',
    )

    signed_screen_sber_attachments = fields.Many2many(
        'ir.attachment', 
        'signed_screen_sber_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Подписанный скрин сбер',
    )

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

    zayavka_start_signature_state = fields.Selection([
        ('draft', 'Загружен PDF'),
        ('ready', 'Готов к подписанию'),
        ('signed', 'Подписан'),
    ], string='Статус подписания заявки Вход', default='draft')

    zayavka_end_signature_state = fields.Selection([
        ('draft', 'Загружен PDF'),
        ('ready', 'Готов к подписанию'),
        ('signed', 'Подписан'),
    ], string='Статус подписания заявки Выход', default='draft')

    assignment_start_signature_state = fields.Selection([
        ('draft', 'Загружен PDF'),
        ('ready', 'Готов к подписанию'),
        ('signed', 'Подписан'),
    ], string='Статус подписания поручения Вход', default='draft')

    assignment_end_signature_state = fields.Selection([
        ('draft', 'Загружен PDF'),
        ('ready', 'Готов к подписанию'),
        ('signed', 'Подписан'),
    ], string='Статус подписания поручения Выход', default='draft')

    screen_sber_signature_state = fields.Selection([
        ('draft', 'Загружен PDF'),
        ('ready', 'Готов к подписанию'),
        ('signed', 'Подписан'),
    ], string='Статус подписания скрина сбер', default='draft')

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

    zayavka_start_signature_position_ids = fields.One2many(
        'amanat.zayavka.signature.position', 
        'zayavka_id', 
        string='Позиции подписей заявки Вход',
        domain=[('document_type', '=', 'zayavka_start')]
    )

    zayavka_start_signature_assignment_ids = fields.One2many(
        'amanat.zayavka.signature.assignment', 
        'zayavka_id', 
        string='Назначенные подписи заявки Вход',
        domain=[('document_type', '=', 'zayavka_start')]
    )

    zayavka_end_signature_position_ids = fields.One2many(
        'amanat.zayavka.signature.position', 
        'zayavka_id', 
        string='Позиции подписей заявки Выход',
        domain=[('document_type', '=', 'zayavka_end')]
    )

    zayavka_end_signature_assignment_ids = fields.One2many(
        'amanat.zayavka.signature.assignment', 
        'zayavka_id', 
        string='Назначенные подписи заявки Выход',
        domain=[('document_type', '=', 'zayavka_end')]
    )

    assignment_start_signature_position_ids = fields.One2many(
        'amanat.zayavka.signature.position', 
        'zayavka_id', 
        string='Позиции подписей поручения Вход',
        domain=[('document_type', '=', 'assignment_start')]
    )

    assignment_start_signature_assignment_ids = fields.One2many(
        'amanat.zayavka.signature.assignment', 
        'zayavka_id', 
        string='Назначенные подписи поручения Вход',
        domain=[('document_type', '=', 'assignment_start')]
    )

    assignment_end_signature_position_ids = fields.One2many(
        'amanat.zayavka.signature.position', 
        'zayavka_id', 
        string='Позиции подписей поручения Выход',
        domain=[('document_type', '=', 'assignment_end')]
    )

    assignment_end_signature_assignment_ids = fields.One2many(
        'amanat.zayavka.signature.assignment', 
        'zayavka_id', 
        string='Назначенные подписи поручения Выход',
        domain=[('document_type', '=', 'assignment_end')]
    )
    
    screen_sber_signature_position_ids = fields.One2many(
        'amanat.zayavka.signature.position', 
        'zayavka_id', 
        string='Позиции подписей скрина сбер',
        domain=[('document_type', '=', 'screen_sber')]
    )

    screen_sber_signature_assignment_ids = fields.One2many(
        'amanat.zayavka.signature.assignment', 
        'zayavka_id', 
        string='Назначенные подписи скрина сбер',
        domain=[('document_type', '=', 'screen_sber')]
    )

    # Методы для определения подписей в каждом типе документа (поддерживает DOCX и PDF)
    def action_detect_signatures_zayavka(self):
        """Определить позиции подписей в заявке (DOCX/PDF)"""
        return self._detect_signatures_for_document('zayavka', self.zayavka_attachments, 'zayavka_signature_state')

    def action_detect_signatures_invoice(self):
        """Определить позиции подписей в инвойсе (DOCX/PDF)"""
        return self._detect_signatures_for_document('invoice', self.invoice_attachments, 'invoice_signature_state')

    def action_detect_signatures_assignment(self):
        """Определить позиции подписей в поручении (DOCX/PDF)"""
        return self._detect_signatures_for_document('assignment', self.assignment_attachments, 'assignment_signature_state')

    def action_detect_signatures_swift(self):
        """Определить позиции подписей в SWIFT (DOCX/PDF)"""
        return self._detect_signatures_for_document('swift', self.swift_attachments, 'swift_signature_state')

    def action_detect_signatures_swift103(self):
        """Определить позиции подписей в SWIFT 103 (DOCX/PDF)"""
        return self._detect_signatures_for_document('swift103', self.swift103_attachments, 'swift103_signature_state')

    def action_detect_signatures_swift199(self):
        """Определить позиции подписей в SWIFT 199 (DOCX/PDF)"""
        return self._detect_signatures_for_document('swift199', self.swift199_attachments, 'swift199_signature_state')

    def action_detect_signatures_report(self):
        """Определить позиции подписей в акт-отчете (DOCX/PDF)"""
        return self._detect_signatures_for_document('report', self.report_attachments, 'report_signature_state')

    def action_detect_signatures_zayavka_start(self):
        """Определить позиции подписей в заявке Вход (DOCX/PDF)"""
        return self._detect_signatures_for_document('zayavka_start', self.zayavka_start_attachments, 'zayavka_start_signature_state')

    def action_detect_signatures_zayavka_end(self):
        """Определить позиции подписей в заявке Выход (DOCX/PDF)"""
        return self._detect_signatures_for_document('zayavka_end', self.zayavka_end_attachments, 'zayavka_end_signature_state')
    
    def action_detect_signatures_assignment_start(self):
        """Определить позиции подписей в поручении Вход (DOCX/PDF)"""
        return self._detect_signatures_for_document('assignment_start', self.assignment_start_attachments, 'assignment_start_signature_state')

    def action_detect_signatures_assignment_end(self):
        """Определить позиции подписей в поручении Выход (DOCX/PDF)"""
        return self._detect_signatures_for_document('assignment_end', self.assignment_end_attachments, 'assignment_end_signature_state')

    def action_detect_signatures_screen_sber(self):
        """Определить позиции подписей в скрине сбер (DOCX/PDF)"""
        return self._detect_signatures_for_document('screen_sber', self.screen_sber_attachments, 'screen_sber_signature_state')

    # Методы для подписания каждого типа документа (DOCX→PDF с подписями)
    def action_sign_zayavka(self):
        """Подписать заявку (DOCX→PDF с подписями)"""
        return self._sign_document('zayavka', self.zayavka_attachments, 'signed_zayavka_attachments', 'zayavka_signature_state')

    def action_sign_invoice(self):
        """Подписать инвойс"""
        return self._sign_document('invoice', self.invoice_attachments, 'signed_invoice_attachments', 'invoice_signature_state')

    def action_sign_assignment(self):
        """Подписать поручение"""
        return self._sign_document('assignment', self.assignment_attachments, 'signed_assignment_attachments', 'assignment_signature_state')

    def action_sign_swift(self):
        """Подписать SWIFT"""
        return self._sign_document('swift', self.swift_attachments, 'signed_swift_attachments', 'swift_signature_state')

    def action_sign_swift103(self):
        """Подписать SWIFT 103"""
        return self._sign_document('swift103', self.swift103_attachments, 'signed_swift103_attachments', 'swift103_signature_state')

    def action_sign_swift199(self):
        """Подписать SWIFT 199"""
        return self._sign_document('swift199', self.swift199_attachments, 'signed_swift199_attachments', 'swift199_signature_state')

    def action_sign_report(self):
        """Подписать акт-отчет"""
        return self._sign_document('report', self.report_attachments, 'signed_report_attachments', 'report_signature_state')

    def action_sign_zayavka_start(self):
        """Подписать заявку Вход"""
        return self._sign_document('zayavka_start', self.zayavka_start_attachments, 'signed_zayavka_start_attachments', 'zayavka_start_signature_state')

    def action_sign_zayavka_end(self):
        """Подписать заявку Выход"""
        return self._sign_document('zayavka_end', self.zayavka_end_attachments, 'signed_zayavka_end_attachments', 'zayavka_end_signature_state')

    def action_sign_assignment_start(self):
        """Подписать поручение Вход"""
        return self._sign_document('assignment_start', self.assignment_start_attachments, 'signed_assignment_start_attachments', 'assignment_start_signature_state')

    def action_sign_assignment_end(self):
        """Подписать поручение Выход"""
        return self._sign_document('assignment_end', self.assignment_end_attachments, 'signed_assignment_end_attachments', 'assignment_end_signature_state')

    def action_sign_screen_sber(self):
        """Подписать скрин сбер"""
        return self._sign_document('screen_sber', self.screen_sber_attachments, 'signed_screen_sber_attachments', 'screen_sber_signature_state')

    # Методы сброса документов
    def action_reset_zayavka_document(self):
        """Сбросить все данные заявки"""
        return self._reset_document('zayavka', 'zayavka_attachments', 'signed_zayavka_attachments', 'zayavka_signature_state')

    def action_reset_invoice_document(self):
        """Сбросить все данные инвойса"""
        return self._reset_document('invoice', 'invoice_attachments', 'signed_invoice_attachments', 'invoice_signature_state')

    def action_reset_assignment_document(self):
        """Сбросить все данные поручения"""
        return self._reset_document('assignment', 'assignment_attachments', 'signed_assignment_attachments', 'assignment_signature_state')

    def action_reset_swift_document(self):
        """Сбросить все данные SWIFT"""
        return self._reset_document('swift', 'swift_attachments', 'signed_swift_attachments', 'swift_signature_state')

    def action_reset_swift103_document(self):
        """Сбросить все данные SWIFT 103"""
        return self._reset_document('swift103', 'swift103_attachments', 'signed_swift103_attachments', 'swift103_signature_state')

    def action_reset_swift199_document(self):
        """Сбросить все данные SWIFT 199"""
        return self._reset_document('swift199', 'swift199_attachments', 'signed_swift199_attachments', 'swift199_signature_state')

    def action_reset_report_document(self):
        """Сбросить все данные акт-отчета"""
        return self._reset_document('report', 'report_attachments', 'signed_report_attachments', 'report_signature_state')

    def action_reset_zayavka_start_document(self):
        """Сбросить все данные заявки Вход"""
        return self._reset_document('zayavka_start', 'zayavka_start_attachments', 'signed_zayavka_start_attachments', 'zayavka_start_signature_state')

    def action_reset_zayavka_end_document(self):
        """Сбросить все данные заявки Выход"""
        return self._reset_document('zayavka_end', 'zayavka_end_attachments', 'signed_zayavka_end_attachments', 'zayavka_end_signature_state')

    def action_reset_assignment_start_document(self):
        """Сбросить все данные поручения Вход"""
        return self._reset_document('assignment_start', 'assignment_start_attachments', 'signed_assignment_start_attachments', 'assignment_start_signature_state')

    def action_reset_assignment_end_document(self):
        """Сбросить все данные поручения Выход"""
        return self._reset_document('assignment_end', 'assignment_end_attachments', 'signed_assignment_end_attachments', 'assignment_end_signature_state')

    def action_reset_screen_sber_document(self):
        """Сбросить все данные скрина сбер"""
        return self._reset_document('screen_sber', 'screen_sber_attachments', 'signed_screen_sber_attachments', 'screen_sber_signature_state')

    def _detect_signatures_for_document(self, document_type, attachments, state_field):
        """Универсальный метод для определения подписей в документе (поддерживает DOCX и PDF)"""
        if not attachments:
            from odoo.exceptions import UserError
            raise UserError(f'Сначала загрузите DOCX или PDF файл для {document_type}')
        
        # Берем первое вложение для анализа
        attachment = attachments[0] if attachments else None
        if not attachment:
            from odoo.exceptions import UserError
            raise UserError(f'Нет вложений для анализа в {document_type}')
        
        # Определяем тип файла
        _logger.info(f"Определяем тип файла для {document_type}, имя файла: {attachment.name}, размер: {len(attachment.datas) if attachment.datas else 'None'}")
        file_type = self._detect_file_type(attachment.datas)
        _logger.info(f"Определенный тип файла для {document_type}: {file_type}")
        
        if file_type == 'docx':
            # Конвертируем DOCX в PDF для анализа (не изменяем исходное вложение)
            pdf_data = self._convert_docx_to_pdf(attachment.datas)
        elif file_type == 'pdf':
            pdf_data = attachment.datas
        else:
            from odoo.exceptions import UserError
            raise UserError(f'Неподдерживаемый тип файла для {document_type}. Поддерживаются только DOCX и PDF.')
        
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
        found_positions = self._auto_find_signatures(document_type, pdf_data)
        
        # Создаем назначения подписей
        if found_positions:
            self._create_signature_assignments(document_type, found_positions)
        
        # Меняем статус на готов к подписанию
        setattr(self, state_field, 'ready')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _detect_file_type(self, file_data):
        """Определить тип файла по заголовку"""
        if not file_data:
            _logger.warning("_detect_file_type: file_data пустой")
            return None
            
        try:
            # Если данные в base64, декодируем их
            _logger.info(f"_detect_file_type: тип данных: {type(file_data)}")
            if isinstance(file_data, str):
                decoded_data = base64.b64decode(file_data)
                _logger.info(f"_detect_file_type: декодировали base64, размер: {len(decoded_data)}, первые 10 байт: {decoded_data[:10]}")
            else:
                # Если уже байты, используем как есть
                decoded_data = file_data
                _logger.info(f"_detect_file_type: получили байты, размер: {len(decoded_data)}, первые 10 байт: {decoded_data[:10]}")
            
            # PDF файлы начинаются с %PDF
            if decoded_data[:4] == b'%PDF':
                _logger.info("_detect_file_type: определен как PDF")
                return 'pdf'
            
            # DOCX файлы начинаются с PK (ZIP архив)
            if decoded_data[:2] == b'PK':
                _logger.info("_detect_file_type: найден ZIP архив, проверяем на DOCX")
                # Дополнительная проверка на DOCX
                if b'word/' in decoded_data[:2000] or b'[Content_Types].xml' in decoded_data[:2000]:
                    _logger.info("_detect_file_type: определен как DOCX")
                    return 'docx'
                else:
                    _logger.info("_detect_file_type: найден ZIP, но не DOCX")
            
            # Проверяем, может быть это base64-кодированные данные, которые нужно декодировать еще раз
            if decoded_data.startswith(b'UEs'):
                _logger.info("_detect_file_type: возможно, это base64-кодированный ZIP, пробуем декодировать")
                try:
                    # Пробуем декодировать как base64
                    double_decoded = base64.b64decode(decoded_data)
                    if double_decoded[:2] == b'PK':
                        if b'word/' in double_decoded[:2000] or b'[Content_Types].xml' in double_decoded[:2000]:
                            _logger.info("_detect_file_type: после двойного декодирования определен как DOCX")
                            return 'docx'
                except:
                    pass
                
            _logger.warning(f"_detect_file_type: неизвестный тип файла, первые 10 байт: {decoded_data[:10]}")
            return 'unknown'
            
        except Exception as e:
            _logger.error(f"Ошибка при определении типа файла: {str(e)}")
            return 'unknown'

    def _convert_docx_to_pdf(self, docx_data):
        """Конвертировать DOCX в PDF используя LibreOffice"""
        if not docx_data:
            raise ValueError("Отсутствуют данные DOCX файла")
        
        _logger.info(f"Начинаем конвертацию DOCX в PDF, размер входных данных: {len(docx_data)}")
            
        try:
            # Создаем временные файлы
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as docx_temp:
                docx_temp.write(base64.b64decode(docx_data))
                docx_temp_path = docx_temp.name
            
            # Создаем временную директорию для вывода
            temp_dir = tempfile.mkdtemp()
            
            try:
                # Конвертируем с помощью LibreOffice
                cmd = [
                    'libreoffice', 
                    '--headless', 
                    '--convert-to', 'pdf',
                    '--outdir', temp_dir,
                    docx_temp_path
                ]
                
                _logger.info(f"Запускаем LibreOffice: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                _logger.info(f"LibreOffice завершился с кодом: {result.returncode}")
                if result.stdout:
                    _logger.info(f"LibreOffice stdout: {result.stdout}")
                if result.stderr:
                    _logger.info(f"LibreOffice stderr: {result.stderr}")
                
                if result.returncode != 0:
                    raise RuntimeError(f"LibreOffice завершился с ошибкой: {result.stderr}")
                
                # Находим созданный PDF файл
                pdf_filename = os.path.splitext(os.path.basename(docx_temp_path))[0] + '.pdf'
                pdf_path = os.path.join(temp_dir, pdf_filename)
                
                _logger.info(f"Ищем созданный PDF файл: {pdf_path}")
                
                if not os.path.exists(pdf_path):
                    # Проверим, какие файлы создались в директории
                    files_in_dir = os.listdir(temp_dir)
                    _logger.error(f"PDF файл не был создан. Файлы в директории: {files_in_dir}")
                    raise FileNotFoundError("PDF файл не был создан")
                
                # Читаем PDF и кодируем в base64
                with open(pdf_path, 'rb') as pdf_file:
                    pdf_data = pdf_file.read()
                    _logger.info(f"PDF файл успешно создан, размер: {len(pdf_data)} байт")
                    return base64.b64encode(pdf_data)
                    
            finally:
                # Очищаем временные файлы
                try:
                    os.unlink(docx_temp_path)
                    pdf_filename = os.path.splitext(os.path.basename(docx_temp_path))[0] + '.pdf'
                    pdf_path_cleanup = os.path.join(temp_dir, pdf_filename)
                    if os.path.exists(pdf_path_cleanup):
                        os.unlink(pdf_path_cleanup)
                    os.rmdir(temp_dir)
                except:
                    pass  # Игнорируем ошибки очистки
                    
        except subprocess.TimeoutExpired:
            raise RuntimeError("Превышено время ожидания конвертации DOCX в PDF. Проверьте, что LibreOffice установлен и доступен.")
        except FileNotFoundError:
            raise RuntimeError("LibreOffice не найден. Установите LibreOffice для конвертации DOCX файлов.")
        except Exception as e:
            _logger.error(f"Ошибка при конвертации DOCX в PDF: {str(e)}")
            raise RuntimeError(f"Не удалось конвертировать DOCX в PDF: {str(e)}")

    def _auto_find_signatures(self, document_type, pdf_file):
        """Автоматический поиск белого текста 'Подпись' и 'Печать' в PDF (PDF может быть сконвертирован из DOCX)"""
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

    def _sign_document(self, document_type, source_attachments, signed_attachments_field, state_field):
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
        
        # Берем первое вложение для подписания
        source_attachment = source_attachments[0] if source_attachments else None
        if not source_attachment:
            from odoo.exceptions import UserError
            raise UserError(f'Нет исходного документа для подписания в {document_type}')
        
        # Генерируем подписанный документ
        signed_file_data, signed_filename = self._generate_signed_document(document_type, source_attachment.datas)
        
        # Создаем новое вложение для подписанного документа
        signed_attachment = self.env['ir.attachment'].create({
            'name': signed_filename,
            'datas': signed_file_data,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        
        # Очищаем старые подписанные вложения и добавляем новое
        signed_attachments = getattr(self, signed_attachments_field)
        signed_attachments.unlink()
        setattr(self, signed_attachments_field, [(4, signed_attachment.id)])
        
        # Обновляем статус
        setattr(self, state_field, 'signed')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _generate_signed_document(self, document_type, source_file):
        """Генерируем подписанный PDF документ из DOCX или PDF исходника"""
        if not PYMUPDF_AVAILABLE:
            # Fallback: просто копируем оригинальный файл
            _logger.warning("PyMuPDF не установлен. Возвращаем оригинальный файл.")
            return source_file, f"signed_{document_type}.pdf"
        
        if not source_file:
            from odoo.exceptions import UserError
            raise UserError(f'Отсутствует исходный файл для {document_type}')
            
        try:
            # Определяем тип исходного файла
            _logger.info(f"Определяем тип файла для {document_type}, размер данных: {len(source_file) if source_file else 'None'}")
            file_type = self._detect_file_type(source_file)
            _logger.info(f"Определенный тип файла для {document_type}: {file_type}")
            
            if file_type == 'docx':
                # Конвертируем DOCX в PDF
                pdf_data_b64 = self._convert_docx_to_pdf(source_file)
                pdf_data = base64.b64decode(pdf_data_b64)
            elif file_type == 'pdf':
                # Декодируем оригинальный PDF
                pdf_data = base64.b64decode(source_file)
            else:
                from odoo.exceptions import UserError
                raise UserError(f'Неподдерживаемый тип файла для {document_type}. Поддерживаются только DOCX и PDF.')
            
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

    def _reset_document(self, document_type, source_attachments_field, signed_attachments_field, state_field):
        """Универсальный метод для сброса документа и всех связанных данных"""
        from odoo.exceptions import UserError
        
        # Проверяем есть ли что сбрасывать
        source_attachments = getattr(self, source_attachments_field, None)
        signed_attachments = getattr(self, signed_attachments_field, None)
        
        if not source_attachments and not signed_attachments:
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
        
        # Удаляем вложения
        if source_attachments:
            source_attachments.unlink()
        if signed_attachments:
            signed_attachments.unlink()
        
        # Сбрасываем статус
        setattr(self, state_field, 'draft')
        
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

    def _analyze_and_log_document_text(self):
        """
        Извлекает ВЕСЬ текст из документов, формирует JSON и выводит в логер
        """
        if not PYMUPDF_AVAILABLE:
            _logger.warning("PyMuPDF не установлен. Невозможно анализировать документы.")
            return
        
        analysis_results = []
        
        # Анализируем файлы из zayavka_attachments
        for attachment in self.zayavka_attachments:
            try:
                pages_text = self._extract_all_text_from_attachment(attachment)
                if pages_text:
                    analysis_results.append({
                        'attachment_name': attachment.name,
                        'extracted_text': pages_text
                    })
            except Exception as e:
                _logger.error(f"Ошибка при анализе файла {attachment.name}: {str(e)}")
        
        # Формируем и выводим JSON в логгер
        if analysis_results:
            self._format_and_log_json(analysis_results)

    def _extract_all_text_from_attachment(self, attachment):
        """
        Извлекает ВЕСЬ текст из вложения
        """
        if not attachment.datas:
            _logger.warning(f"Файл {attachment.name} не содержит данных")
            return None
        
        file_data = base64.b64decode(attachment.datas)
        file_type = self._detect_file_type(file_data)
        
        _logger.info(f"Анализируем файл {attachment.name}, определенный тип: {file_type}, размер: {len(file_data)} байт")
        
        # Конвертируем DOCX в PDF если необходимо
        if file_type == 'docx':
            try:
                pdf_data_b64 = self._convert_docx_to_pdf(attachment.datas)  # Передаем base64 строку
                if not pdf_data_b64:
                    _logger.warning(f"Файл {attachment.name} не содержит текста после конвертации")
                    return None
                # Декодируем base64 в байты для анализа
                pdf_data = base64.b64decode(pdf_data_b64)
                _logger.info(f"DOCX файл {attachment.name} успешно конвертирован в PDF, размер: {len(pdf_data)} байт")
            except Exception as e:
                _logger.warning(f"Не удалось обработать DOCX файл {attachment.name}: {str(e)}. Возможно, файл поврежден или пустой")
                return None
        elif file_type == 'pdf':
            pdf_data = file_data
        else:
            _logger.warning(f"Неподдерживаемый тип файла {attachment.name}: {file_type}")
            return None
        
        # Извлекаем весь текст из PDF
        try:
            extracted_text = self._extract_all_text_from_pdf(pdf_data)
            if not extracted_text:
                _logger.warning(f"Файл {attachment.name} не содержит извлекаемого текста")
                return None
            return extracted_text
        except Exception as e:
            _logger.warning(f"Не удалось извлечь текст из файла {attachment.name}: {str(e)}. Возможно, файл поврежден или содержит только изображения")
            return None

    def _extract_all_text_from_pdf(self, pdf_data):
        """
        Извлекает ВЕСЬ текст из PDF, возвращает словарь по страницам
        """
        if not PYMUPDF_AVAILABLE:
            raise ImportError("PyMuPDF не доступен")
        
        if not pdf_data:
            return None
            
        try:
            doc = pymupdf.open(stream=pdf_data, filetype="pdf")  # type: ignore
        except Exception as e:
            raise Exception(f"Не удалось открыть PDF: {str(e)}")
            
        pages_text = {}
        
        try:
            if len(doc) == 0:
                return None
                
            for page_num in range(len(doc)):
                page = doc[page_num]
                # Получаем весь текст со страницы
                page_text = page.get_text()  # type: ignore
                if page_text and page_text.strip():
                    pages_text[f"page{page_num + 1}"] = page_text.strip()
        finally:
            doc.close()
        
        return pages_text if pages_text else None

    def _format_and_log_json(self, analysis_results):
        """
        Форматирует результаты анализа в JSON и выводит в логгер
        Затем отправляет JSON на анализ в YandexGPT
        """
        # Создаем простую структуру {text: {page1: ..., page2: ...}}
        for result in analysis_results:
            if result.get('extracted_text'):
                json_result = {
                    'text': result['extracted_text']
                }
                
                # Форматируем JSON с отступами для читаемости
                formatted_json = json.dumps(json_result, ensure_ascii=False, indent=2)
                
                # Выводим JSON в логгер для каждого файла
                _logger.info(f"АНАЛИЗ ДОКУМЕНТА {result['attachment_name']} - JSON РЕЗУЛЬТАТ:\n{formatted_json}")
                
                # Отправляем JSON на анализ в YandexGPT
                try:
                    self.analyze_document_with_yandex_gpt(formatted_json)
                except Exception as e:
                    _logger.error(f"Ошибка при отправке документа {result['attachment_name']} на анализ YandexGPT: {str(e)}")
        
        return True