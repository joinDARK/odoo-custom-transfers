from odoo import models, fields
from .base_model import AmanatBaseModel


class AmanatPayment(models.Model, AmanatBaseModel):
    _name = 'amanat.payment'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Платеж'

    # Поля модели (id создаётся автоматически)
    date = fields.Datetime(string="Дата")
    currency = fields.Selection([
        ('usd', 'USD'),
        ('eur', 'EUR'),
        ('rub', 'RUB'),
    ], string="Валюта", required=True)
    
    wallet = fields.Char(string="Кошелек", tracking=True)
    sender = fields.Char(string="Отправитель", tracking=True)
    sender_payer = fields.Char(string="Плательщик отправителя", tracking=True)
    recipient = fields.Char(string="Получатель")
    recipient_payer = fields.Char(string="Плательщик получателя", tracking=True)

    # wallet = fields.Many2one('amanat.wallet', string="Кошелек") # done
    # sender = fields.Many2one('amanat.contragent', string="Отправитель", tracking=True) # done
    # sender_payer = fields.Many2one('amanat.payer', string="Плательщик отправителя", tracking=True) # done
    # recipient = fields.Many2one('amanat.contragent', string="Получатель") # done
    # recipient_payer = fields.Many2one('amanat.payer', string="Плательщик получателя", tracking=True) # done
    
    amount = fields.Char(string="Сумма", tracking=True)
    purpose = fields.Char(string="Назначение", tracking=True)
    execute = fields.Boolean(string="Выполнить", tracking=True)
    status = fields.Selection([
        ('new', 'Новый'),
        ('in_progress', 'В процессе'),
        ('done', 'Выполнен'),
        ('cancelled', 'Отменен'),
    ], string="Статус")
    actual_date = fields.Datetime(string="Дата фактического приземления денег", tracking=True)
    payment_status = fields.Selection([
        ('pending', 'Ожидается'),
        ('completed', 'Завершен'),
        ('failed', 'Неудачный'),
    ], string="Статус платежа")
    money = fields.Char(string="Деньги", tracking=True)
    deal = fields.Char(string="Сделка", tracking=True)
    minus = fields.Char(string="Минус", tracking=True)
    plus = fields.Char(string="Плюс", tracking=True)
