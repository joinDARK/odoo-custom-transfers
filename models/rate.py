# models/rate.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel

class Rates(models.Model, AmanatBaseModel):
    _name = 'amanat.rates'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Курсы к доллару'

    id = fields.Char(
        string='id',
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.rates.sequence'),
        required=True,
        readonly=True,
    )
    euro = fields.Float(string='euro', tracking=True, digits=(16,4))
    cny = fields.Float(string='cny', tracking=True, digits=(16,4))
    rub = fields.Float(string='rub', tracking=True, digits=(16,4))
    aed = fields.Float(string='aed', tracking=True, digits=(16,4))
    thb = fields.Float(string='thb', tracking=True, digits=(16,4))
    usd = fields.Float(string='usd', tracking=True, digits=(16,4))
    usdt = fields.Float(string='usdt', tracking=True, digits=(16,4))
