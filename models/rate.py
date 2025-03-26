# models/rate.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel

class Rates(models.Model, AmanatBaseModel):
    _name = 'amanat.rates'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Курсы к доллару'

    id = fields.Char(
        string='id',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: 'Новый курс'
    )
    euro = fields.Float(string='euro', tracking=True)
    cny = fields.Float(string='cny', tracking=True)
    rub = fields.Float(string='rub', tracking=True)
    aed = fields.Float(string='aed', tracking=True)
    thb = fields.Float(string='thb', tracking=True)
    usd = fields.Float(string='usd', tracking=True)
    usdt = fields.Float(string='usdt', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('id', 'Новый курс') == 'Новый курс':
            vals['id'] = self.env['ir.sequence'].next_by_bycode('amanat.rates.sequence') or 'Новый курс'
        return super(Rates, self).create(vals)
