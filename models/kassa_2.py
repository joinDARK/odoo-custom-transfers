from odoo import models, fields
from .base_model import AmanatBaseModel

class Kassa2(models.Model, AmanatBaseModel):
    _name = 'amanat.kassa_2'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Касса 2'

    name = fields.Char(
        string='Участник Кассы',
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.kassa_2.sequence'),
        copy=False,
        tracking=True
    )

    contragent_id = fields.Many2one(
        'amanat.contragent',
        string='Наименование участника',
        required=True,
        tracking=True
    )

    manual_sort = fields.Char(
        string='Manual Sort',
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.kassa_2.manual_sort.sequence'),
        copy=False,
        tracking=True
    )

    percent = fields.Float(
        string='Процент',
        default=0.0,
        digits=(16, 2),
        tracking=True
    )