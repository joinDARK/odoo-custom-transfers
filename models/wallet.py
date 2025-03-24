# models/wallet.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel

class Wallet(models.Model, AmanatBaseModel):
    _name = 'amanat.wallet'
    _description = 'Кошелек плательщика'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Наименование', required=True, tracking=True)
    sum = fields.Float(string='Баланс деняг', default=0.0, tracking=True)