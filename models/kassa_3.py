from odoo import models, fields
from .base_model import AmanatBaseModel

class Kassa3(models.Model, AmanatBaseModel):
    _name = 'amanat.kassa_3'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Касса 3'

    name = fields.Char(
        string='Участник Кассы',
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.kassa_3.sequence'),
        copy=False,
        tracking=True
    )

    contragent_id = fields.Many2one(
        'amanat.contragent',
        string='Наименование участника',
        required=True,
        tracking=True
    )