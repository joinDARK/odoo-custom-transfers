# models/payer.py
from odoo import models, fields
from .base_model import AmanatBaseModel

class Payer(models.Model, AmanatBaseModel):
    _name = 'amanat.payer'
    _description = 'Плательщик'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Наименование', required=True, tracking=True)
    inn = fields.Char(string='ИНН', tracking=True)
    
    # Связь многие ко многим с Контрагентами
    contragents_ids = fields.Many2many(
        'amanat.contragent',
        'amanat_payer_contragent_rel',  # Имя таблицы-связи
        'payer_id',  # Поле-ссылка на эту модель
        'contragent_id',  # Поле-ссылка на модель Контрагент
        string='Контрагенты',
        tracking=True,
        ondelete='cascade',
    )
    order_ids = fields.One2many(
        'amanat.order',
        string='Ордеры (участие)',
        compute='_compute_order_ids',
        store=False  # Не сохраняем в БД, просто отображаем
    )
    reconciliation = fields.Many2many(
        'amanat.reconciliation',
        'amanat_reconciliation_payer_rel',
        'payer_id',
        'reconciliation_id',
        string='Сверка',
        tracking=True,
    )
    transfer = fields.Char(string='Перевод', tracking=True)
    currency_reserve = fields.Char(string='Валютный резерв', tracking=True) # Исправить связь
    conversion = fields.Char(string='Конвертация', tracking=True) # Исправить связь
    investment = fields.Char(string='Инвестиция', tracking=True) # Исправить связь
    gold_partners = fields.Many2many(
        'res.partner',
        string='Партнеры золото',
        tracking=True
    ) # Исправить связь
    deductions = fields.Char(string='Списания', tracking=True) # Исправить связь
    applications = fields.Char(string='Заявки', tracking=True) # Исправить связь
    # pricelist_conduct = fields.Char(string='Прайс лист Плательщика За проведение', tracking=True) # Исправить связь
    pricelist_partners = fields.One2many(
        'amanat.price_list_partners',
        'payer_partner',
        string='Прайс лист Партнеры',
        tracking=True
    )

    price_list_carrying_out_ids = fields.Many2many(
        'amanat.price_list_payer_carrying_out',
        'amanat_price_list_payer_carrying_out_rel',
        'payer_id',
        'price_list_id',
        string='Прайс листы За проведение',
        tracking=True
    )

    price_list_profit_ids = fields.Many2many(
        'amanat.price_list_payer_profit',
        'amanat_payer_pricelist_profit_rel',
        'payer_id',
        'pricelist_profit_id',
        string='Прайс лист Плательщика Прибыль',
        tracking=True
    ) # Исправить связь

    partner_card_ids = fields.Many2many(
        'ir.attachment',
        'amanat_payer_attachment_rel',
        'payer_id',
        'attachment_id',
        string='Карточки партнеров',
        tracking=True
    )


    def action_download_files(self):
        """Скачать файлы карточки партнера"""
        files = self.partner_card_ids
        if not files or len(files) == 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Нет файлов',
                    'message': 'Файлы карточки партнера не найдены',
                    'sticky': False,
                    'type': 'warning',
                }
            }
        
        if len(files) == 1:
            attachment = files[0]
            return {
                'type': 'ir.actions.act_url',
                'url': attachment.url or f'/web/content/ir.attachment/{attachment.id}/datas',
                'target': 'new',
            }
        
        # Если файлов несколько, возвращаем список
        return {
            'type': 'ir.actions.act_window',
            'name': 'Файлы карточки партнера',
            'res_model': 'ir.attachment',
            'domain': [('id', 'in', [f.id for f in files])],
            'view_mode': 'tree,form',
            'target': 'new',
        }

    def _compute_order_ids(self):
        for payer in self:
            payer.order_ids = self.env['amanat.order'].search([
                '|',
                ('payer_1_id', '=', payer.id),
                ('payer_2_id', '=', payer.id)
            ])