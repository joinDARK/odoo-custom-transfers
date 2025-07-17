from odoo import models, fields, api
from .base_model import AmanatBaseModel

class AmanatSverkaFiles(models.Model, AmanatBaseModel):
    _name = 'amanat.sverka_files'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Сверка файлы'

    name = fields.Char(string='Наименование файла', tracking=True)
    contragent_id = fields.Many2one('amanat.contragent', string='Контрагент', tracking=True)

    attachment_ids = fields.One2many('ir.attachment', string='Файлы', compute='_compute_attachments')
    
    # Раздельные поля для разных типов файлов
    sverka1_file_attachments = fields.Many2many(
        'ir.attachment', 
        'amanat_sverka_files_sverka1_attachment_rel',
        'sverka_file_id', 
        'attachment_id',
        string='Сверка',
        help='Файлы сверки 1'
    )
    
    sverka2_file_attachments = fields.Many2many(
        'ir.attachment', 
        'amanat_sverka_files_sverka2_attachment_rel',
        'sverka_file_id', 
        'attachment_id',
        string='Сверка ТДК',
        help='Файлы сверки 2'
    )
    
    file_attachments = fields.Many2many(
        'ir.attachment', 
        'amanat_sverka_files_attachment_rel',
        'sverka_file_id', 
        'attachment_id',
        string='Все документы',
        help='Все файлы сверки'
    )
    
    # Computed поля для подсчета файлов
    sverka1_files_count = fields.Integer(
        string='Файлов сверки 1',
        compute='_compute_files_count',
        store=False
    )
    
    sverka2_files_count = fields.Integer(
        string='Файлов сверки 2',
        compute='_compute_files_count',
        store=False
    )
    
    total_files_count = fields.Integer(
        string='Всего файлов',
        compute='_compute_files_count',
        store=False
    )

    def _compute_attachments(self):
        for record in self:
            record.attachment_ids = record.file_attachments

    @api.depends('sverka1_file_attachments', 'sverka2_file_attachments', 'file_attachments')
    def _compute_files_count(self):
        for record in self:
            record.sverka1_files_count = len(record.sverka1_file_attachments)
            record.sverka2_files_count = len(record.sverka2_file_attachments)
            record.total_files_count = len(record.file_attachments)

    def preview_files(self):
        """Превью файлов"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Превью файлов',
                'message': f'Файлов сверки 1: {self.sverka1_files_count}, Файлов сверки 2: {self.sverka2_files_count}',
                'sticky': False,
                'type': 'success',
            }
        }

    def preview_sverka1_files(self):
        """Превью файлов сверки 1"""
        if not self.sverka1_file_attachments:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Нет файлов',
                    'message': 'Файлы сверки не найдены',
                    'sticky': False,
                    'type': 'warning',
                }
            }
        
        # Прямой вызов JavaScript функции
        return {
            'type': 'ir.actions.client',
            'tag': 'javascript_call',
            'params': {
                'function': 'showSverka1FilesPreview',
                'args': [self.id]
            }
        }

    def preview_sverka2_files(self):
        """Превью файлов сверки ТДК"""
        if not self.sverka2_file_attachments:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Нет файлов',
                    'message': 'Файлы сверки ТДК не найдены',
                    'sticky': False,
                    'type': 'warning',
                }
            }
        
        # Прямой вызов JavaScript функции
        return {
            'type': 'ir.actions.client',
            'tag': 'javascript_call',
            'params': {
                'function': 'showSverka2FilesPreview',
                'args': [self.id]
            }
        }
    
    def action_download_sverka1_files(self):
        """Скачать файлы сверки 1"""
        files = self.sverka1_file_attachments
        if not files or len(files) == 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Нет файлов',
                    'message': 'Файлы сверки 1 не найдены',
                    'sticky': False,
                    'type': 'warning',
                }
            }
        
        if len(files) == 1:
            attachment = files[0]
            return {
                'type': 'ir.actions.act_url',
                'url': attachment.url or f'/web/content/ir.attachment/{attachment.id}/datas',
                'target': 'new',
            }
        
        # Если файлов несколько, возвращаем список
        return {
            'type': 'ir.actions.act_window',
            'name': 'Файлы сверки 1',
            'res_model': 'ir.attachment',
            'domain': [('id', 'in', [f.id for f in files])],
            'view_mode': 'tree,form',
            'target': 'new',
        }
    
    def action_download_sverka2_files(self):
        """Скачать файлы сверки 2"""
        files = self.sverka2_file_attachments
        if not files or len(files) == 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Нет файлов',
                    'message': 'Файлы сверки 2 не найдены',
                    'sticky': False,
                    'type': 'warning',
                }
            }
        
        if len(files) == 1:
            attachment = files[0]
            return {
                'type': 'ir.actions.act_url',
                'url': attachment.url or f'/web/content/ir.attachment/{attachment.id}/datas',
                'target': 'new',
            }
        
        # Если файлов несколько, возвращаем список
        return {
            'type': 'ir.actions.act_window',
            'name': 'Файлы сверки 2',
            'res_model': 'ir.attachment',
            'domain': [('id', 'in', [f.id for f in files])],
            'view_mode': 'tree,form',
            'target': 'new',
        }