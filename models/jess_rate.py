from odoo import models, fields
from .base_model import AmanatBaseModel

class JessRate(models.Model, AmanatBaseModel):
    _name = 'amanat.jess_rate'
    _description = 'Курс Джесс'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Название', compute='_compute_name')
    date = fields.Date(string='Дата фиксация курса', required=True, tracking=True)
    currency = fields.Selection(
        [
            ('rub', 'RUB'), ('rub_cashe', 'RUB КЭШ'),
            ('usd', 'USD'), ('usd_cashe', 'USD КЭШ'),
            ('usdt', 'USDT'),
            ('euro', 'EURO'), ('euro_cashe', 'EURO КЭШ'),
            ('cny', 'CNY'), ('cny_cashe', 'CNY КЭШ'),
            ('aed', 'AED'), ('aed_cashe', 'AED КЭШ'),
            ('thb', 'THB'), ('thb_cashe', 'THB КЭШ'),
            ('idr', 'IDR'), ('idr_cashe', 'IDR КЭШ'),
            ('inr', 'INR'), ('inr_cashe', 'INR КЭШ'),
        ],
        string='Валюта',
        default='usd',
        tracking=True
    )
    rate = fields.Float(string='Курс', tracking=True, digits=(16, 6))

    def _compute_name(self):
        for record in self:
            record.name = f"{record.rate} {str.upper(record.currency)}"