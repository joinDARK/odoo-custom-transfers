# models/extract_delivery.py
from odoo import models, fields, api
from .base_model import AmanatBaseModel

class Extract_delivery(models.Model, AmanatBaseModel):
    _name = 'amanat.extract_delivery'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Выписка разнос'

    name = fields.Char(string="Номер платежа", tracking=True, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('amanat.extract_delivery.sequence'), copy=False)
    date = fields.Date(string="Дата", tracking=True)
    amount = fields.Float(string="Сумма", tracking=True)

    payer = fields.Many2one('amanat.payer', string="Плательщик", tracking=True)
    payer_inn = fields.Char(
        string="ИНН Плательщика",
        related='payer.inn',
        store=True,
        readonly=True,
        tracking=True
    )

    recipient = fields.Many2one('amanat.payer', string="Получатель", tracking=True)
    recipient_inn = fields.Char(
        string="ИНН Получателя",
        related='recipient.inn',
        store=True,
        readonly=True,
        tracking=True
    )

    payment_purpose = fields.Char(string="Назначение платежа", tracking=True)
    document_id = fields.Many2many('amanat.extracts', string="ID Документа", tracking=True)
    assign_bulinan = fields.Boolean(string="Разнести булинан", tracking=True)
    create_transfer_bulinan = fields.Boolean(string="Создать перевод булинан", tracking=True)
    dds_article = fields.Selection([
        ('operational', 'Операционные потоки'),
        ('investment', 'Инвестиционные потоки'),
        ('financial', 'Финансовые потоки'),
        ('not_applicable', 'Не относится')
    ], string="Статья ДДС", tracking=True)
    direction_choice = fields.Selection([
        ('currency_reserve', 'Валютный резерв'),
        ('transfer', 'Перевод'),
        ('conversion', 'Конвертация'),
        ('investment', 'Инвестиция'),
        ('gold_deal', 'Золото сделка'),
        ('no_matches', 'Нет совпадений'),
        ('applications', 'Заявки')
    ], string="Выбор направления", tracking=True)

    applications = fields.Many2many('amanat.zayavka', string="Заявки", tracking=True)
    currency_reserve = fields.Many2many('amanat.reserve', string="Валютный резерв", tracking=True)
    transfer_ids = fields.Many2many('amanat.transfer', string="Перевод", tracking=True)
    conversion = fields.Many2many(
        'amanat.conversion',
        'amanat_conversion_extract_delivery_rel',
        'extract_delivery',
        'conversion_id',
        string="Конвертация", 
        tracking=True
    )
    investment = fields.Many2many('amanat.investment', string="Инвестиция", tracking=True)
    gold_deal = fields.Many2many('amanat.gold_deal', string="Золото сделка", tracking=True)

    counterparty1 = fields.Many2one('amanat.contragent', string="Контрагент 1", tracking=True)
    counterparty2 = fields.Many2one('amanat.contragent', string="Контрагент 2", tracking=True)
    wallet1 = fields.Many2one('amanat.wallet', string="Кошелек 1", tracking=True)
    wallet2 = fields.Many2one('amanat.wallet', string="Кошелек 2", tracking=True)

    percent = fields.Float(string="Процент", tracking=True)
    fragment_statement = fields.Boolean(string="Раздробить выписку", tracking=True)
    remaining_statement = fields.Float(string="Остаток для исходной выписки", tracking=True)
    
    range_field = fields.Many2one('amanat.ranges', string="Диапазон", tracking=True)
    date_start = fields.Date(
        string="Дата начало (from Диапазон)", 
        store=True, 
        readonly=True,
        tracking=True,
        related="range_field.date_start"
    )
    date_end = fields.Date(
        string="Дата конец (from Диапазон)", 
        store=True, 
        readonly=True,
        tracking=True,
        related="range_field.date_end"
    )
    range_status = fields.Char(string="Статус диапазона", compute='_compute_range_status', store=True, tracking=True)

    # Оставшиеся поля
    statement_part_1 = fields.Float(string="Выписка дробь 1", digits=(16, 2), tracking=True)
    statement_part_2 = fields.Float(string="Выписка дробь 2", digits=(16, 2), tracking=True)
    statement_part_3 = fields.Float(string="Выписка дробь 3", digits=(16, 2), tracking=True)
    statement_part_4 = fields.Float(string="Выписка дробь 4", digits=(16, 2), tracking=True)
    statement_part_5 = fields.Float(string="Выписка дробь 5", digits=(16, 2), tracking=True)
    statement_part_6 = fields.Float(string="Выписка дробь 6", digits=(16, 2), tracking=True)
    statement_part_7 = fields.Float(string="Выписка дробь 7", digits=(16, 2), tracking=True)
    statement_part_8 = fields.Float(string="Выписка дробь 8", digits=(16, 2), tracking=True)
    statement_part_9 = fields.Float(string="Выписка дробь 9", digits=(16, 2), tracking=True)
    statement_part_10 = fields.Float(string="Выписка дробь 10", digits=(16, 2), tracking=True)
    statement_part_11 = fields.Float(string="Выписка дробь 11", digits=(16, 2), tracking=True)
    statement_part_12 = fields.Float(string="Выписка дробь 12", digits=(16, 2), tracking=True)
    statement_part_13 = fields.Float(string="Выписка дробь 13", digits=(16, 2), tracking=True)
    statement_part_14 = fields.Float(string="Выписка дробь 14", digits=(16, 2), tracking=True)
    statement_part_15 = fields.Float(string="Выписка дробь 15", digits=(16, 2), tracking=True)
    statement_part_16 = fields.Float(string="Выписка дробь 16", digits=(16, 2), tracking=True)
    statement_part_17 = fields.Float(string="Выписка дробь 17", digits=(16, 2), tracking=True)
    statement_part_18 = fields.Float(string="Выписка дробь 18", digits=(16, 2), tracking=True)
    statement_part_19 = fields.Float(string="Выписка дробь 19", digits=(16, 2), tracking=True)
    statement_part_20 = fields.Float(string="Выписка дробь 20", digits=(16, 2), tracking=True)

    remaining_statement = fields.Float(string="Остаток для исходной выписки", tracking=True)

    @api.depends('date', 'date_start', 'date_end')
    def _compute_range_status(self):
        for record in self:
            if record.date and record.date_start and record.date_end:
                if record.date >= record.date_start and record.date <= record.date_end:
                    record.range_status = "Да"
                else:
                    record.range_status = "Нет"
            else:
                record.range_status = "Нет"