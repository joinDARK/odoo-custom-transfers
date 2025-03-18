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

    # Поле для выполнения автоматизации
    execute_automation = fields.Boolean(string="Выполнить автоматизацию")

    def log_transfer_data(self):
        for record in self:
            data = {
                "ID": record.id,
                "Отправитель": record.sender_id.name,
                "Получатель": record.receiver_id.name,
                "Сумма": record.amount,
                "Дата": record.date
            }
            # Вывод в консоль сервера
            print("\n=== Данные перевода ===")
            for key, value in data.items():
                print(f"{key}: {value}")
            print("=======================\n")
            
            # Сбрасываем флаг, чтобы кнопка исчезла
            record.write({'execute_automation': False})
