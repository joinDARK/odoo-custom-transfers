# custom_transfers/models/transfer.py
from odoo import models, fields

class Transfer(models.Model):
    _name = 'custom.transfer'
    _description = 'Перевод'

    sender_id = fields.Many2one('custom.contragent', string='Отправитель', required=True)
    sender_payer_id = fields.Many2one('custom.payer', string='Плательщик отправителя', required=True)
    receiver_id = fields.Many2one('custom.contragent', string='Получатель', required=True)
    receiver_payer_id = fields.Many2one('custom.payer', string='Плательщик получателя', required=True)
    amount = fields.Float(string='Сумма', required=True)
    date = fields.Date(string='Дата', default=fields.Date.today)
