from odoo import models, fields, api

class GoldDeal(models.Model):
    _name = 'amanat.gold_deal'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Золото сделка'

    # 1. ID – формируется с помощью последовательности с префиксом "Сделка №"
    name = fields.Char(
        string='ID',
        readonly=True,
        default=lambda self: "Сделка №" + str(self.env['ir.sequence'].next_by_code('amanat.gold_deal.sequence')),
        tracking=True
    )

    # 2. Статус – выбор из трёх вариантов
    status = fields.Selection(
        [('open', 'Открыта'), ('closed', 'Закрыта'), ('archived', 'Архив')],
        string='Статус',
        tracking=True
    )

    # 3. Комментарий – однострочное текстовое поле
    comment = fields.Char(string='Комментарий', tracking=True)

    # 4. Дата
    date = fields.Date(string='Дата', tracking=True)

    # 5. Партнеры – связь один-ко-многим с моделью «Партнеры золото»
    partner_ids = fields.Many2many(
        'amanat.partner_gold',
        relation='amanat_partner_gold_deal_rel',
        column1='gold_deal_id',
        column2='partner_gold_id',
        string='Партнеры',
        tracking=True
    )

    # 6. Чистый вес, гр (Rollup: сумма поля pure_weight из партнеров)
    pure_weight_sum = fields.Float(
        string='Чистый вес, гр (Rollup)',
        compute='_compute_pure_weight_sum',
        store=True,
        tracking=True
    )

    # 7. Общая сумма покупки (Rollup: сумма поля amount_rub из партнеров)
    purchase_total_rub = fields.Float(
        string='Общая сумма покупки',
        compute='_compute_purchase_total_rub',
        store=True,
        tracking=True
    )

    # 8. Сумма закупа в долларах (Rollup: сумма поля purchase_amount_dollar из партнеров)
    purchase_total_dollar = fields.Float(
        string='Сумма закупа в долларах',
        compute='_compute_purchase_total_dollar',
        store=True,
        tracking=True
    )

    # 9. Расходы (Rollup: сумма поля total_expenses из партнеров)
    expenses = fields.Float(
        string='Расходы',
        compute='_compute_expenses',
        store=True,
        tracking=True
    )

    # 10. Услуга (Rollup: сумма поля service из партнеров)
    service = fields.Float(
        string='Услуга',
        compute='_compute_service',
        store=True,
        tracking=True
    )

    # 11. Банк сумм (Rollup: сумма поля bank_sum из партнеров)
    bank_sum = fields.Float(
        string='Банк сумм',
        compute='_compute_bank_sum',
        store=True,
        tracking=True
    )

    # 12. Банк КБ (Rollup: сумма поля bank_kb из партнеров)
    bank_kb = fields.Float(
        string='Банк КБ',
        compute='_compute_bank_kb',
        store=True,
        tracking=True
    )

    # 13. Курьер (Rollup: сумма поля courier из партнеров)
    courier = fields.Float(
        string='Курьер',
        compute='_compute_courier',
        store=True,
        tracking=True
    )

    # 14. Общая сумма (Rollup: сумма поля purchase_usdt из партнеров)
    total_amount = fields.Float(
        string='Общая сумма',
        compute='_compute_total_amount',
        store=True,
        tracking=True
    )

    # 15. Сумма продажи AED (Rollup: сумма поля sale_amount_aed из партнеров)
    sale_amount_aed = fields.Float(
        string='Сумма продажи AED',
        compute='_compute_sale_amount_aed',
        store=True,
        tracking=True
    )

    # 16. Сумма продажи USDT (Rollup: сумма поля purchase_usdt из партнеров)
    sale_amount_usdt = fields.Float(
        string='Сумма продажи USDT',
        compute='_compute_sale_amount_usdt',
        store=True,
        tracking=True
    )

    # 17. Дополнительные расходы
    extra_expenses = fields.Float(string='Дополнительные расходы', tracking=True)

    # 18. Курс итог – вычисляется как Общая сумма покупки / Общая сумма
    final_rate = fields.Float(
        string='Курс итог',
        compute='_compute_final_rate',
        store=True,
        tracking=True
    )

    # 19. Провести вход
    conduct_in = fields.Boolean(string='Провести вход', default=False, tracking=True)

    # 20. Провести выход
    conduct_out = fields.Boolean(string='Провести выход', default=False, tracking=True)

    # 21. Проводка Вита
    vita_posting = fields.Boolean(string='Проводка Вита', default=False, tracking=True)

    # 22. Сверка
    reconciliation = fields.Boolean(string='Сверка', default=False, tracking=True)

    # 23. Перепроводка
    reposting = fields.Boolean(string='Перепроводка', default=False, tracking=True)

    # 24. Пометить на удаление
    mark_for_deletion = fields.Boolean(string='Пометить на удаление', default=False, tracking=True)

    # 25. Сумма по инвойсу
    invoice_amount = fields.Float(string='Сумма по инвойсу', tracking=True)

    # 26. Разница = Общая сумма покупки - Сумма по инвойсу
    difference = fields.Float(
        string='Разница',
        compute='_compute_difference',
        store=True,
        tracking=True
    )

    # 27. Банк – выбор из: Вита, СКБ, Альфа
    bank = fields.Selection(
        [('vita', 'Вита'), ('skb', 'СКБ'), ('alfa', 'Альфа')],
        string='Банк',
        tracking=True
    )

    # 28. Платежка – связь с выпиской разнос (многие ко многим)
    extract_delivery_ids = fields.Many2many(
        'amanat.extract_delivery',
        string='Платежка',
        tracking=True
    )

    # 29. Ордеры – связь с ордерами (многие ко многим)
    order_ids = fields.Many2many(
        'amanat.order',
        string='Ордеры',
        tracking=True
    )

    # 30. Покупатель – связь с Контрагентами
    buyer_id = fields.Many2one(
        'amanat.contragent',
        string='Покупатель',
        tracking=True
    )

    # 31. Хеш
    hash_flag = fields.Boolean(string='Хеш', default=False, tracking=True)

    # --- Compute методы для Rollup/Formula полей ---

    @api.depends('partner_ids.pure_weight')
    def _compute_pure_weight_sum(self):
        for rec in self:
            rec.pure_weight_sum = sum(rec.partner_ids.mapped('pure_weight'))

    @api.depends('partner_ids.amount_rub')
    def _compute_purchase_total_rub(self):
        for rec in self:
            rec.purchase_total_rub = sum(rec.partner_ids.mapped('amount_rub'))

    @api.depends('partner_ids.purchase_amount_dollar')
    def _compute_purchase_total_dollar(self):
        for rec in self:
            rec.purchase_total_dollar = sum(rec.partner_ids.mapped('purchase_amount_dollar'))

    @api.depends('partner_ids.total_expenses')
    def _compute_expenses(self):
        for rec in self:
            rec.expenses = sum(rec.partner_ids.mapped('total_expenses'))

    @api.depends('partner_ids.service_amount')
    def _compute_service(self):
        for rec in self:
            rec.service = sum(rec.partner_ids.mapped('service_amount'))

    @api.depends('partner_ids.bank_amount')
    def _compute_bank_sum(self):
        for rec in self:
            rec.bank_sum = sum(rec.partner_ids.mapped('bank_amount'))

    @api.depends('partner_ids.bank_kb_amount')
    def _compute_bank_kb(self):
        for rec in self:
            rec.bank_kb = sum(rec.partner_ids.mapped('bank_kb_amount'))

    @api.depends('partner_ids.courier_amount')
    def _compute_courier(self):
        for rec in self:
            rec.courier = sum(rec.partner_ids.mapped('courier_amount'))

    @api.depends('partner_ids.purchase_usdt')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.partner_ids.mapped('purchase_usdt'))

    @api.depends('partner_ids.sale_amount_aed')
    def _compute_sale_amount_aed(self):
        for rec in self:
            rec.sale_amount_aed = sum(rec.partner_ids.mapped('sale_amount_aed'))

    @api.depends('partner_ids.purchase_usdt')
    def _compute_sale_amount_usdt(self):
        for rec in self:
            rec.sale_amount_usdt = sum(rec.partner_ids.mapped('purchase_usdt'))

    @api.depends('purchase_total_rub', 'total_amount')
    def _compute_final_rate(self):
        for rec in self:
            rec.final_rate = rec.purchase_total_rub / rec.total_amount if rec.total_amount else 0

    @api.depends('purchase_total_rub', 'invoice_amount')
    def _compute_difference(self):
        for rec in self:
            rec.difference = rec.purchase_total_rub - rec.invoice_amount