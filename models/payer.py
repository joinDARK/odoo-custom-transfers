# custom_transfers/models/payer.py
from odoo import models, fields

class Payer(models.Model):
    _name = 'custom.payer'
    _description = 'Плательщик'

    name = fields.Char(string='Имя', required=True)
    bank_account = fields.Char(string='Банковский счёт')
