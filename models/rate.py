# models/rate.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel

class Rates(models.Model, AmanatBaseModel):
    _name = 'amanat.rates'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Курсы к доллару'

    id = fields.Char(
        string='id',
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.rates.sequence'),
        required=True,
        readonly=True,
    )
    euro = fields.Float(string='euro', tracking=True)
    cny = fields.Float(string='cny', tracking=True)
    rub = fields.Float(string='rub', tracking=True)
    aed = fields.Float(string='aed', tracking=True)
    thb = fields.Float(string='thb', tracking=True)
    usd = fields.Float(string='usd', tracking=True)
    usdt = fields.Float(string='usdt', tracking=True)
