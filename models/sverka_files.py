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
