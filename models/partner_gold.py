from odoo import models, fields, api

class PartnerGold(models.Model):
    _name = 'amanat.partner_gold'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'Партнеры золото'

    # 1. ID Партнера – формируется с помощью последовательности с префиксом "Партнер №"
    name = fields.Char(
        string='ID Партнера',
        readonly=True,
        default=lambda self: "Партнер №" + str(self.env['ir.sequence'].next_by_code('amanat.partner_gold.sequence')),
        tracking=True
    )

    # 2. Дата сделки (по умолчанию текущая дата)
    deal_date = fields.Date(string='Дата сделки', default=fields.Date.context_today, tracking=True)

    # 3. Партнер – связь с Контрагентами
    partner_id = fields.Many2one(
        'amanat.contragent',
        string='Партнер',
        tracking=True
    )

    # 4. Плательщик – связь с Плательщиками
    payer_id = fields.Many2one(
        'amanat.payer',
        string='Плательщик',
        tracking=True
    )

    # 5. Цена за oz в $ (используем поле Monetary)
    currency_id = fields.Many2one(
        'res.currency',
        string='Валюта',
        default=lambda self: self.env.ref('base.USD').id
    )
    price_per_oz = fields.Monetary(string='Цена за oz в $', currency_field='currency_id', tracking=True)

    # 6. Дисконт/премия (в процентах)
    discount_premium = fields.Float(string='Дисконт/премия', tracking=True)

    # 7. Курс банка
    bank_rate = fields.Float(string='Курс банка', tracking=True)

    # 8. Цена закупки, руб/гр – вводится вручную
    purchase_price_rub_per_gram = fields.Float(string='Цена закупки, руб/гр', tracking=True)

    # 10. Чистый вес, гр
    pure_weight = fields.Float(string='Чистый вес, гр', tracking=True)

    # 9. Сумма, руб. = Чистый вес * Цена закупки, руб/гр
    amount_rub = fields.Float(
        string='Сумма, руб.',
        compute='_compute_amount_rub',
        store=True,
        tracking=True
    )

    @api.depends('pure_weight', 'purchase_price_rub_per_gram')
    def _compute_amount_rub(self):
        for rec in self:
            rec.amount_rub = rec.pure_weight * rec.purchase_price_rub_per_gram

    # 11. чистый вес OZ = Чистый вес, гр / 31.1035
    pure_weight_oz = fields.Float(
        string='чистый вес OZ',
        compute='_compute_pure_weight_oz',
        store=True,
        tracking=True
    )

    @api.depends('pure_weight')
    def _compute_pure_weight_oz(self):
        for rec in self:
            rec.pure_weight_oz = rec.pure_weight / 31.1035 if rec.pure_weight else 0

    # 12. Курс $ на дату покупки формула = Курс банка * (1 + Дисконт/премия)
    dollar_rate_formula = fields.Float(
        string='Курс $ на дату покупки формула',
        compute='_compute_dollar_rate_formula',
        store=True,
        tracking=True
    )

    @api.depends('bank_rate', 'discount_premium')
    def _compute_dollar_rate_formula(self):
        for rec in self:
            rec.dollar_rate_formula = rec.bank_rate * (1 + rec.discount_premium)

    # 13. Курс $ на дату покупки – вводится вручную
    dollar_rate = fields.Float(string='Курс $ на дату покупки', tracking=True)

    # 14. Сумма закупа, $ – формула с условием
    purchase_amount_dollar = fields.Float(
        string='Сумма закупа, $',
        compute='_compute_purchase_amount_dollar',
        store=True,
        tracking=True
    )

    @api.depends('amount_rub', 'dollar_rate', 'dollar_rate_formula')
    def _compute_purchase_amount_dollar(self):
        for rec in self:
            if rec.dollar_rate:
                rec.purchase_amount_dollar = rec.amount_rub / rec.dollar_rate
            else:
                rec.purchase_amount_dollar = rec.amount_rub / rec.dollar_rate_formula if rec.dollar_rate_formula else 0

    # 15. Дата продажи – по умолчанию текущая дата
    sale_date = fields.Date(string='Дата продажи', default=fields.Date.context_today, tracking=True)

    # 16. Изначальная цена $/OZ
    initial_price_per_oz = fields.Float(string='Изначальная цена $/OZ', tracking=True)

    # 17. Дисконт продажи $/OZ
    sale_discount_per_oz = fields.Float(string='Дисконт продажи $/OZ', tracking=True)

    # 18. цена продажи $/OZ = Изначальная цена $/OZ - Дисконт продажи $/OZ
    sale_price_per_oz = fields.Float(
        string='цена продажи $/OZ',
        compute='_compute_sale_price_per_oz',
        store=True,
        tracking=True
    )

    @api.depends('initial_price_per_oz', 'sale_discount_per_oz')
    def _compute_sale_price_per_oz(self):
        for rec in self:
            rec.sale_price_per_oz = rec.initial_price_per_oz - rec.sale_discount_per_oz

    # 19. курс AED
    aed_rate = fields.Float(string='курс AED', tracking=True)

    # 20. Сумма продажи AED = цена продажи $/OZ * чистый вес OZ * курс AED
    sale_amount_aed = fields.Float(
        string='Сумма продажи AED',
        compute='_compute_sale_amount_aed',
        store=True,
        tracking=True
    )

    @api.depends('sale_price_per_oz', 'pure_weight_oz', 'aed_rate')
    def _compute_sale_amount_aed(self):
        for rec in self:
            rec.sale_amount_aed = rec.sale_price_per_oz * rec.pure_weight_oz * rec.aed_rate

    # 21. курс USDT
    usdt_rate = fields.Float(string='курс USDT', tracking=True)

    # 22. покупка USDT = Сумма продажи AED / курс USDT
    purchase_usdt = fields.Float(
        string='покупка USDT',
        compute='_compute_purchase_usdt',
        store=True,
        tracking=True
    )

    @api.depends('sale_amount_aed', 'usdt_rate')
    def _compute_purchase_usdt(self):
        for rec in self:
            rec.purchase_usdt = rec.sale_amount_aed / rec.usdt_rate if rec.usdt_rate else 0

    # 23. %Банк
    bank_percent = fields.Float(string='%Банк', tracking=True)

    # 24. Банк сумма = Сумма закупа, $ * %Банк
    bank_amount = fields.Float(
        string='Банк сумма',
        compute='_compute_bank_amount',
        store=True,
        tracking=True
    )

    @api.depends('purchase_amount_dollar', 'bank_percent')
    def _compute_bank_amount(self):
        for rec in self:
            rec.bank_amount = rec.purchase_amount_dollar * rec.bank_percent

    # 25. %Услуга
    service_percent = fields.Float(string='%Услуга', tracking=True)

    # 26. Услуга сумма = Сумма закупа, $ * %Услуга
    service_amount = fields.Float(
        string='Услуга сумма',
        compute='_compute_service_amount',
        store=True,
        tracking=True
    )

    @api.depends('purchase_amount_dollar', 'service_percent')
    def _compute_service_amount(self):
        for rec in self:
            rec.service_amount = rec.purchase_amount_dollar * rec.service_percent

    # 27. %Банк КБ
    bank_kb_percent = fields.Float(string='%Банк КБ', tracking=True)

    # 28. Банк КБ сумма = Сумма закупа, $ * %Банк КБ
    bank_kb_amount = fields.Float(
        string='Банк КБ сумма',
        compute='_compute_bank_kb_amount',
        store=True,
        tracking=True
    )

    @api.depends('purchase_amount_dollar', 'bank_kb_percent')
    def _compute_bank_kb_amount(self):
        for rec in self:
            rec.bank_kb_amount = rec.purchase_amount_dollar * rec.bank_kb_percent

    # 29. %Курьер
    courier_percent = fields.Float(string='%Курьер', tracking=True)

    # 30. Курьер сумма = Сумма закупа, $ * %Курьер
    courier_amount = fields.Float(
        string='Курьер сумма',
        compute='_compute_courier_amount',
        store=True,
        tracking=True
    )

    @api.depends('purchase_amount_dollar', 'courier_percent')
    def _compute_courier_amount(self):
        for rec in self:
            rec.courier_amount = rec.purchase_amount_dollar * rec.courier_percent

    # 31. Дополнительные расходы – вычисляемые на основе дополнительных входных полей
    total_extra_expenses = fields.Float(string='Доп расходы', tracking=True)
    overall_pure_weight = fields.Float(string='Чистый вес общий', tracking=True)
    extra_expenses_computed = fields.Float(
        string='Дополнительные расходы (расчет)',
        compute='_compute_extra_expenses',
        store=True,
        tracking=True
    )

    @api.depends('total_extra_expenses', 'overall_pure_weight', 'pure_weight')
    def _compute_extra_expenses(self):
        for rec in self:
            rec.extra_expenses_computed = (rec.total_extra_expenses / rec.overall_pure_weight * rec.pure_weight) if rec.overall_pure_weight else 0

    # 32. Золото сделка – связь с моделью Gold Deal (многие ко многим)
    gold_deal_ids = fields.Many2many(
        'amanat.gold_deal',
        string='Золото сделка',
        tracking=True,
        relation='amanat_partner_gold_deal_rel',  # ← имя таблицы связи
        column1='partner_gold_id',                # ← внеш. ключ на текущую модель
        column2='gold_deal_id',                   # ← внеш. ключ на связ. модель
    )

    # 33. Всего расходы = (Сумма закупа, $*%Банк)+(Сумма закупа, $*%Услуга)+(Сумма закупа, $*%Банк КБ)+(Сумма закупа, $*%Курьер)+Дополнительные расходы
    total_expenses = fields.Float(
        string='Всего расходы',
        compute='_compute_total_expenses',
        store=True,
        tracking=True
    )

    @api.depends('purchase_amount_dollar', 'bank_percent', 'service_percent', 'bank_kb_percent', 'courier_percent', 'extra_expenses_computed')
    def _compute_total_expenses(self):
        for rec in self:
            rec.total_expenses = (rec.purchase_amount_dollar * rec.bank_percent +
                                  rec.purchase_amount_dollar * rec.service_percent +
                                  rec.purchase_amount_dollar * rec.bank_kb_percent +
                                  rec.purchase_amount_dollar * rec.courier_percent +
                                  rec.extra_expenses_computed)

    # 34. Общая сумма = покупка USDT - Всего расходы
    overall_amount = fields.Float(
        string='Общая сумма',
        compute='_compute_overall_amount',
        store=True,
        tracking=True
    )

    @api.depends('purchase_usdt', 'total_expenses')
    def _compute_overall_amount(self):
        for rec in self:
            rec.overall_amount = rec.purchase_usdt - rec.total_expenses

    # 35. Прибыль = Общая сумма - Сумма закупа, $
    profit = fields.Float(
        string='Прибыль',
        compute='_compute_profit',
        store=True,
        tracking=True
    )

    @api.depends('overall_amount', 'purchase_amount_dollar')
    def _compute_profit(self):
        for rec in self:
            rec.profit = rec.overall_amount - rec.purchase_amount_dollar

    # 36. Процент сделки = Прибыль / Сумма закупа, $
    deal_percentage = fields.Float(
        string='Процент сделки',
        compute='_compute_deal_percentage',
        store=True,
        tracking=True
    )

    @api.depends('profit', 'purchase_amount_dollar')
    def _compute_deal_percentage(self):
        for rec in self:
            rec.deal_percentage = rec.profit / rec.purchase_amount_dollar if rec.purchase_amount_dollar else 0

    # 37. Курс итог = Сумма, руб. / Общая сумма
    final_rate = fields.Float(
        string='Курс итог',
        compute='_compute_final_rate',
        store=True,
        tracking=True
    )

    @api.depends('amount_rub', 'overall_amount')
    def _compute_final_rate(self):
        for rec in self:
            rec.final_rate = rec.amount_rub / rec.overall_amount if rec.overall_amount else 0

    # 38. Ордеры – связь с ордерами (многие ко многим)
    order_ids = fields.Many2many(
        'amanat.order',
        string='Ордеры',
        tracking=True
    )

    # 39. Есть роялти?
    has_royalty = fields.Boolean(string='Есть роялти?', default=False, tracking=True)

    # 40. Получатель роялти – связь с Контрагентами
    royalty_recipient_id = fields.Many2one(
        'amanat.contragent',
        string='Получатель роялти',
        tracking=True
    )

    # 41. % первого
    first_percent = fields.Float(string='% первого', tracking=True)

    # 42. Сумма роялти 1 = Сумма, руб. * % первого
    royalty_amount_1 = fields.Float(
        string='Сумма роялти 1',
        compute='_compute_royalty_amount_1',
        store=True,
        tracking=True
    )

    @api.depends('amount_rub', 'first_percent')
    def _compute_royalty_amount_1(self):
        for rec in self:
            rec.royalty_amount_1 = rec.amount_rub * rec.first_percent

    # 43. Дата оплаты – по умолчанию текущая дата
    payment_date = fields.Date(string='Дата оплаты', default=fields.Date.context_today, tracking=True)

    # 44. Провести перевод на золото
    conduct_gold_transfer = fields.Boolean(string='Провести перевод на золото', default=False, tracking=True)

    # 45. Кошелек для перевода – связь с кошельками
    wallet_id = fields.Many2one('amanat.wallet', string='Кошелек для перевода', tracking=True)

    # 46. Чистый вес, гр Rollup (Lookup из Золото сделка)
    lookup_pure_weight = fields.Float(
        string='Чистый вес, гр (Lookup)',
        compute='_compute_lookup_pure_weight',
        store=True,
        tracking=True
    )

    @api.depends('gold_deal_ids.pure_weight_sum')
    def _compute_lookup_pure_weight(self):
        for rec in self:
            rec.lookup_pure_weight = sum(rec.gold_deal_ids.mapped('pure_weight_sum'))

    # 47. Сумма по инвойсу (Lookup из Золото сделка)
    lookup_invoice_amount = fields.Float(
        string='Сумма по инвойсу (Lookup)',
        compute='_compute_lookup_invoice_amount',
        store=True,
        tracking=True
    )

    @api.depends('gold_deal_ids.invoice_amount')
    def _compute_lookup_invoice_amount(self):
        for rec in self:
            rec.lookup_invoice_amount = sum(rec.gold_deal_ids.mapped('invoice_amount'))

    # 48. Процент партнера от всего закупа
    partner_percentage = fields.Float(
        string='Процент партнера от всего закупа',
        compute='_compute_partner_percentage',
        store=True,
        tracking=True
    )

    @api.depends('pure_weight', 'lookup_pure_weight')
    def _compute_partner_percentage(self):
        for rec in self:
            rec.partner_percentage = (rec.pure_weight / rec.lookup_pure_weight * 100) if rec.lookup_pure_weight else 0

    # 49. Сумма партнера от инвойса = Сумма по инвойсу (Lookup) * Процент партнера от всего закупа
    partner_invoice_amount = fields.Float(
        string='Сумма партнера от инвойса',
        compute='_compute_partner_invoice_amount',
        store=True,
        tracking=True
    )

    @api.depends('lookup_invoice_amount', 'partner_percentage')
    def _compute_partner_invoice_amount(self):
        for rec in self:
            rec.partner_invoice_amount = rec.lookup_invoice_amount * rec.partner_percentage / 100