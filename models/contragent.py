# crm_amanat/models/contragent.py
from odoo import models, fields
from .base_model import CustomBaseModel

class Contragent(models.Model, CustomBaseModel):
    _name = 'custom.contragent'
    _description = 'Контрагент'
    _inherit = ["mail.thread", "mail.activity.mixin"]  

    name = fields.Char(string='Имя', required=True, tracking=True)
    address = fields.Char(string='Адрес', tracking=True)
    phone = fields.Char(string='Телефон', tracking=True)
    payer_id = fields.Many2one(
        'custom.payer',
        string='Плательщик',
        required=True,  # Обязательное поле
        ondelete='restrict',
        tracking=True
    )
