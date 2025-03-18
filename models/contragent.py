# custom_transfers/models/contragent.py
from odoo import models, fields

class Contragent(models.Model):
    _name = 'custom.contragent'
    _description = 'Контрагент'

    name = fields.Char(string='Имя', required=True)
    address = fields.Char(string='Адрес')
    phone = fields.Char(string='Телефон')
