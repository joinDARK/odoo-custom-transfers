from odoo import models, fields
from .base_model import AmanatBaseModel

class AmanatSverkaFiles(models.Model, AmanatBaseModel):
    _name = 'amanat.sverka_files'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Сверка файлы'

    name = fields.Char(string='Наименование файла', tracking=True)
    contragent_id = fields.Many2one('amanat.contragent', string='Контрагент', tracking=True)

    attachment_ids = fields.One2many('ir.attachment', string='Файлы', compute='_compute_attachments')
    file_attachments = fields.Many2many('ir.attachment', string='Документы')  # Добавленное поле

    def _compute_attachments(self):
        for record in self:
            record.attachment_ids = self.env['ir.attachment'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', record.id)
            ])
    
    def preview_files(self):
        """Метод для превью файлов с вызовом модального окна"""
        # Простая проверка наличия файлов
        has_file_attachments = bool(self.file_attachments)
        
        # Проверяем стандартные вложения
        std_attachments_count = self.env['ir.attachment'].search_count([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id)
        ])
        
        total_files = len(self.file_attachments or []) + std_attachments_count
        
        if total_files == 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Превью файлов',
                    'message': 'Нет прикрепленных файлов для превью',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Возвращаем действие для вызова JavaScript функции
        return {
            'type': 'ir.actions.client',
            'tag': 'call_js_function',
            'params': {
                'function_name': 'showSverkaFilesPreview',
                'args': [self.id],
            }
        }