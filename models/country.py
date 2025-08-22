# models/country.py

from odoo import models, fields
from .base_model import AmanatBaseModel

class Country(models.Model, AmanatBaseModel):
    _name = 'amanat.country'
    _description = 'Страны'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"] 
    
    name = fields.Char(string='Краткое название', required=True, tracking=True)
    code = fields.Integer(string='Код страны', required=True, tracking=True)
    full_name = fields.Text(string='Полное название', tracking=True)
    zayavka_id = fields.Many2one('amanat.zayavka', string='Заявка', tracking=True)
    eng_country_name = fields.Char(string='Английское название страны', tracking=True)