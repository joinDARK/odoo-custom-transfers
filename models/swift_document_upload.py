from odoo import models, fields, api
from .base_model import AmanatBaseModel
import logging

_logger = logging.getLogger(__name__)

class AmanatSwiftDocumentUpload(models.Model, AmanatBaseModel):
    _name = 'amanat.swift_document_upload'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Загрузка SWIFT документов'
    _order = 'create_date desc'

    # Основные поля
    swift_file = fields.Binary(
        string='SWIFT документ',
        required=True
    )
    
    swift_file_name = fields.Char(
        string='Имя файла'
    )
    
    currency = fields.Char(
        string='Валюта',
        required=False,
        tracking=True
    )
    
    amount = fields.Float(
        string='Сумма',
        required=False,
        digits=(16, 2),
        tracking=True
    )
    
    payer_subagent = fields.Char(
        string='Плательщик субагента',
        required=False,
        tracking=True,
        help='Имя плательщика субагента для поиска заявки в поле subagent_payer_ids'
    )
    
    payment_date = fields.Date(
        string='Дата платежа',
        tracking=True,
        help='Дата оплаты валюты поставщику субагенту'
    )
    
    swift_code = fields.Char(
        string='Код SWIFT',
        tracking=True,
        help='Код SWIFT операции'
    )
    
    # Связанная заявка
    zayavka_id = fields.Many2one(
        'amanat.zayavka',
        string='Связанная заявка',
        store=True,
        tracking=True,
        help='Заявка, найденная автоматически по плательщику субагента'
    )
    
    # Статус обработки
    processing_status = fields.Selection([
        ('pending', 'Ожидает обработки'),
        ('processed', 'Обработано'),
        ('error', 'Ошибка обработки'),
        ('no_zayavka', 'Заявка не найдена')
    ], string='Статус обработки', default='pending', tracking=True)
    
    processing_notes = fields.Text(
        string='Примечания к обработке',
        help='Детали обработки документа'
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Переопределяем создание для автоматической обработки"""
        _logger.info("[SWIFT AUTO] === НАЧАЛО СОЗДАНИЯ swift_document_upload ===")
        _logger.info(f"[SWIFT AUTO] Получены данные для создания: {vals_list}")
        
        # Проверяем сколько заявок было ДО создания
        zayavka_count_before = self.env['amanat.zayavka'].search_count([])
        _logger.info(f"[SWIFT AUTO] Количество заявок ДО создания swift_document_upload: {zayavka_count_before}")
        
        records = super().create(vals_list)
        _logger.info(f"[SWIFT AUTO] Создано записей swift_document_upload: {len(records)}")
        
        # Проверяем сколько заявок стало ПОСЛЕ создания (но ДО автоматизации)
        zayavka_count_after_create = self.env['amanat.zayavka'].search_count([])
        _logger.info(f"[SWIFT AUTO] Количество заявок ПОСЛЕ создания swift_document_upload (до автоматизации): {zayavka_count_after_create}")
        
        if zayavka_count_after_create > zayavka_count_before:
            _logger.error(f"[SWIFT AUTO] ⚠️ ВНИМАНИЕ! Заявка была создана ВНЕ нашей автоматизации! Было: {zayavka_count_before}, стало: {zayavka_count_after_create}")
        
        for record in records:
            try:
                _logger.info(f"[SWIFT AUTO] Запускаем автоматизацию для записи {record.id} с плательщиком '{record.payer_subagent}'")
                # Запускаем автоматизацию при создании записи
                record._process_swift_document_automation()
            except Exception as e:
                _logger.error(f"Ошибка при автоматической обработке SWIFT документа {record.id}: {str(e)}")
                record.processing_status = 'error'
                record.processing_notes = f"Ошибка автоматизации: {str(e)}"
        
        # Проверяем финальное количество заявок
        zayavka_count_final = self.env['amanat.zayavka'].search_count([])
        _logger.info(f"[SWIFT AUTO] Итоговое количество заявок ПОСЛЕ автоматизации: {zayavka_count_final}")
        
        if zayavka_count_final > zayavka_count_after_create:
            _logger.error("[SWIFT AUTO] ⚠️ ВНИМАНИЕ! Заявка была создана НАШЕЙ автоматизацией! Это НЕ должно происходить!")
        
        _logger.info("[SWIFT AUTO] === КОНЕЦ СОЗДАНИЯ swift_document_upload ===")
        return records

    def _process_swift_document_automation(self):
        """Основная логика автоматизации SWIFT документов - ТОЛЬКО линковка с существующей заявкой"""
        self.ensure_one()
        
        _logger.info(f"[SWIFT AUTO] Начинаем обработку SWIFT документа {self.id} для плательщика '{self.payer_subagent}'")
        
        # Шаг 1: Найти СУЩЕСТВУЮЩУЮ заявку (НЕ создавать новую!)
        zayavka = self._find_matching_zayavka()
        
        if not zayavka:
            self.processing_status = 'no_zayavka'
            self.processing_notes = f"Заявка не найдена для плательщика субагента '{self.payer_subagent}'. Создание новой заявки НЕ разрешено."
            _logger.warning(f"[SWIFT AUTO] ❌ ЗАЯВКА НЕ НАЙДЕНА для плательщика субагента '{self.payer_subagent}'. Обработка ОСТАНОВЛЕНА.")
            _logger.warning("[SWIFT AUTO] ❌ НОВАЯ ЗАЯВКА НЕ БУДЕТ СОЗДАНА! Это правильное поведение.")
            return
        
        _logger.info(f"[SWIFT AUTO] Найдена существующая заявка {zayavka.id} для плательщика '{self.payer_subagent}'")
        
        # Шаг 2: Линкуем swift_document_upload с найденной заявкой
        self.zayavka_id = zayavka.id
        _logger.info(f"[SWIFT AUTO] Запись swift_document_upload {self.id} связана с заявкой {zayavka.id}")
        
        # Шаг 3: Загружаем SWIFT документ в заявку (в поле swift_attachments)
        attachment = self._upload_document_to_zayavka(zayavka)
        
        if not attachment:
            self.processing_status = 'error'
            self.processing_notes = "Ошибка при загрузке SWIFT документа в заявку"
            _logger.error(f"[SWIFT AUTO] Ошибка загрузки документа в заявку {zayavka.id}")
            return
        
        _logger.info(f"[SWIFT AUTO] SWIFT документ успешно загружен в заявку {zayavka.id}, attachment ID: {attachment.id}")
        
        # Шаг 4: Встроенная автоматизация заявки уже запустилась при добавлении в swift_attachments
        # НЕ запускаем Yandex GPT анализ - только базовая автоматизация по SWIFT
        
        # Шаг 5: Обновляем статус обработки
        self.processing_status = 'processed'
        self.processing_notes = f"Успешно обработано. SWIFT документ загружен в заявку {zayavka.zayavka_num or zayavka.id}. Автоматизация заявки запущена."
        
        _logger.info(f"[SWIFT AUTO] Обработка завершена успешно. Документ {self.id} связан с заявкой {zayavka.id}")

    def _find_matching_zayavka(self):
        """Поиск существующей заявки по плательщику субагента"""
        if not self.payer_subagent:
            return None
        
        # Ищем заявку по плательщику субагента с точным совпадением
        zayavka = self.env['amanat.zayavka'].search([
            ('subagent_payer_ids.name', '=', self.payer_subagent)
        ], limit=1)
        
        if zayavka:
            _logger.info(f"[SWIFT AUTO] Найдена заявка по плательщику субагента с точным совпадением: {zayavka.id}")
            return zayavka
        
        # Ищем заявку по плательщику субагента с нечетким поиском
        zayavka = self.env['amanat.zayavka'].search([
            ('subagent_payer_ids.name', 'ilike', self.payer_subagent)
        ], limit=1)
        
        if zayavka:
            _logger.info(f"[SWIFT AUTO] Найдена заявка по плательщику субагента с нечетким совпадением: {zayavka.id}")
            return zayavka
        
        # Дополнительный поиск по частичному совпадению имени плательщика субагента
        payer_words = self.payer_subagent.split()
        if len(payer_words) > 1:
            # Ищем по первому слову в имени плательщика субагента
            first_word = payer_words[0]
            zayavka = self.env['amanat.zayavka'].search([
                ('subagent_payer_ids.name', 'ilike', f'%{first_word}%')
            ], limit=1)
            
            if zayavka:
                _logger.info(f"[SWIFT AUTO] Найдена заявка по частичному совпадению плательщика субагента: {zayavka.id}")
                return zayavka
        
        _logger.warning(f"[SWIFT AUTO] Заявка не найдена для плательщика субагента '{self.payer_subagent}'")
        return None

    def _upload_document_to_zayavka(self, zayavka):
        """Загрузка SWIFT документа в заявку"""
        try:
            # Создаем attachment
            attachment_vals = {
                'name': self.swift_file_name or f'SWIFT_{self.swift_code or "document"}_{self.id}.pdf',
                'type': 'binary',
                'datas': self.swift_file,
                'res_model': 'amanat.zayavka',
                'res_id': zayavka.id,
                'mimetype': 'application/pdf',
                'description': f'SWIFT документ от {self.create_date}, плательщик: {self.payer_subagent}'
            }
            
            attachment = self.env['ir.attachment'].create(attachment_vals)
            
            # Добавляем attachment к заявке в поле swift_attachments (вкладка SWIFT)
            zayavka.write({
                'swift_attachments': [(4, attachment.id)]  # (4, id) - добавить связь
            })
            
            _logger.info(f"[SWIFT AUTO] Документ успешно загружен в заявку {zayavka.id}, attachment ID: {attachment.id}")
            return attachment
            
        except Exception as e:
            _logger.error(f"[SWIFT AUTO] Ошибка при загрузке документа в заявку: {str(e)}")
            return None



    @api.depends('payer_subagent')
    def _compute_zayavka_id(self):
        """Находим связанную заявку по плательщику субагента"""
        for record in self:
            if record.payer_subagent and not record.zayavka_id:
                # Ищем заявку, где в subagent_payer_ids есть плательщик с таким именем
                zayavka = self.env['amanat.zayavka'].search([
                    ('subagent_payer_ids.name', 'ilike', record.payer_subagent)
                ], limit=1)
                record.zayavka_id = zayavka if zayavka else False
            elif not record.payer_subagent:
                record.zayavka_id = False

    def action_reprocess_document(self):
        """Кнопка для повторной обработки документа"""
        self.ensure_one()
        try:
            self.processing_status = 'pending'
            self.processing_notes = 'Повторная обработка запущена вручную'
            self._process_swift_document_automation()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Документ успешно переобработан',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Ошибка при переобработке: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }