# crm_amanat/models/payer.py
from odoo import models, fields
from .base_model import CustomBaseModel

class Payer(models.Model, CustomBaseModel):
    _name = 'custom.payer'
    _description = 'Плательщик'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Имя', required=True, tracking=True)
    bank_account = fields.Char(string='Банковский счёт', tracking=True)
