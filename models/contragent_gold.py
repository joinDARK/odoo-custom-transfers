# models/contragent_gold.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel

class ContragentGold(models.Model, AmanatBaseModel):
    _name = 'amanat.contragent.gold'
    _description = 'Контрагент Золото'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]  

    name = fields.Char(string='Название', compute='_compute_name', store=True, tracking=True)
    contragent_id = fields.Many2one('amanat.contragent', string='Контрагент', tracking=True)
    gold_deal_ids = fields.One2many('amanat.gold_deal', 'bank', string='Сделки', tracking=True)

    @api.depends('contragent_id.name')
    def _compute_name(self):
        for record in self:
            if record.contragent_id:
                record.name = record.contragent_id.name
            else:
                record.name = 'Новая запись'