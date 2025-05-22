from odoo import models, fields
from .base_model import AmanatBaseModel

class AmanatExtracts(models.Model, AmanatBaseModel):
    _name = 'amanat.extracts'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'extracts'

    name = fields.Char(string='ID', tracking=True)

    vypiska_ids = fields.Many2many(
        'ir.attachment',
        'amanat_extracts_ir_attach_rel',
        'extracts_id',
        'attachment_id',
        string='Выписка',
        tracking=True
    )

    raznesti = fields.Boolean(string='Разнести', tracking=True)

    bank = fields.Selection(
        [
            ('mti', 'МТИ'),
            ('sberbank', 'Сбербанк'),
            ('sovkombank', 'Совкомбанк'),
            ('morskoy', 'Морской'),
            ('ingosstrah', 'Ингосстрах'),
            ('rosbank', 'Росбанк'),
            ('sdm_bank', 'СДМ банк'),
            ('vtb', 'ВТБ'),
            ('nbs', 'НБС'),
            ('zenit', 'Зенит'),
            ('absolut', 'Абсолют'),
        ],
        string='Банк',
        tracking=True
    )

    extract_delivery_ids = fields.Many2many(
        'amanat.extract_delivery',
        'amanat_extracts_extract_rel',
        'extracts_id',
        'extract_id',
        string='Выписка разнос',
        tracking=True
    )
