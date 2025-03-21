# crm_amanat/models/contragent.py
from odoo import models, fields
from .base_model import AmanatBaseModel

class Contragent(models.Model, AmanatBaseModel):
    _name = 'amanat.contragent'
    _description = 'Контрагент'
    _inherit = ["mail.thread", "mail.activity.mixin"]  

    name = fields.Char(string='Имя', required=True, tracking=True)
    address = fields.Char(string='Адрес', tracking=True)
    phone = fields.Char(string='Телефон', tracking=True)
    payer_id = fields.Many2one(
        'amanat.payer',
        string='Плательщик',
        required=True,  # Обязательное поле
        ondelete='restrict',
        tracking=True
    )
