# models/conversion.py
from odoo import models, fields
from .base_model import AmanatBaseModel

class Conversion(models.Model, AmanatBaseModel):
    _name = 'amanat.conversion'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Конвертация валют'

    name = fields.Char(
        string='Номер сделки',
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.conversion.sequence'),
        required=True,
        readonly=True
    )
    state = fields.Selection(
        [('open', 'Открыта'), ('archive', 'Архив'), ('close', 'Закрыта')],
        string='Статус',
        default='open',
        tracking=True
    )
    date = fields.Date(string='Дата', default=fields.Date.today, tracking=True)
    amount = fields.Float(string='Сумма', required=True, tracking=True)
    currency = fields.Selection(
        [
            ('rub', 'RUB'), ('rub_cashe', 'RUB КЭШ'), ('usd', 'USD'), ('usd_cashe', 'USD КЭШ'), ('usdt', 'USDT'), ('euro', 'EURO'),
            ('euro_cashe', 'EURO КЭШ'), ('cny', 'CNY'), ('cny_cashe', 'CNY КЭШ'), ('aed', 'AED'), ('aed_cashe', 'AED КЭШ'),
            ('thb', 'THB'), ('thb_cashe', 'THB КЭШ'),
        ],
        string='Валюта',
        default='rub',
        tracking=True
    )
    conversion_currency = fields.Selection(
        [
            ('rub', 'RUB'), ('rub_cashe', 'RUB КЭШ'), ('usd', 'USD'), ('usd_cashe', 'USD КЭШ'), ('usdt', 'USDT'), ('euro', 'EURO'),
            ('euro_cashe', 'EURO КЭШ'), ('cny', 'CNY'), ('cny_cashe', 'CNY КЭШ'), ('aed', 'AED'), ('aed_cashe', 'AED КЭШ'),
            ('thb', 'THB'), ('thb_cashe', 'THB КЭШ'),
        ],
        string='В какую валюту',
        default='rub',
        tracking=True
    )
    sender_id = fields.Many2one(
        'amanat.contragent',
        string='Отправитель',
        store=True,
        tracking=True, 
    )
    sender_payer_id = fields.Many2one(
        'amanat.payer',
        string='Плательщик отправителя',
        required=True,  # Делаем обязательным, так как выбор начинается с плательщика
        tracking=True
    )
    rate = fields.Float(string='Курс', tracking=True)
    receiver_id = fields.Many2one(
        'amanat.contragent', 
        string='Получатель',
        store=True,
        tracking=True, 
    )
    receiver_payer_id = fields.Many2one(
        'amanat.payer',
        string='Плательщик получателя',
        required=True,  # Делаем обязательным
        tracking=True
    )
    order_id = fields.Many2one(
        'amanat.order',
        string='Ордеры',
        tracking=True
    )

    create_Conversion1 = fields.Boolean(
        string='Создать',
        default=False,
        tracking=True
    )
    contragent_count = fields.Selection(
        [('1', '1'), ('2', '2')],
        string='Колво КА',
        default='1',
        tracking=True,
    )
    
    create_Conversion = fields.Boolean(string='Провести', default=False, tracking=True)
    update_Conversion = fields.Boolean(string='Изменить', default=False, tracking=True)
    delete_Conversion = fields.Boolean(string='Удалить', default=False, tracking=True)
