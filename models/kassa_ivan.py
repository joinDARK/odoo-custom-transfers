from odoo import models, fields
from .base_model import AmanatBaseModel

class KassaIvan(models.Model, AmanatBaseModel):
    _name = 'amanat.kassa_ivan'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Касса Иван'

    name = fields.Char(
        string='Участник Кассы',
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.kassa_ivan.sequence'),
        copy=False,
        tracking=True
    )

    contragent_id = fields.Many2one(
        'amanat.contragent',
        string='Наименование участника',
        required=True,
        tracking=True
    )