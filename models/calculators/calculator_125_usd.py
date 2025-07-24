# models/calculators/calculator_125_usd.py
from odoo import models, fields, api
from datetime import date


class Calculator125UsdWizard(models.Model):
    """Калькулятор 125 USD"""
    _name = 'amanat.calculator.125.usd.wizard'
    _description = 'Калькулятор 125 USD'
    _order = 'create_date desc'

    # Информационные поля
    name = fields.Char(string='Название расчета', compute='_compute_name', store=True)
    create_uid = fields.Many2one('res.users', string='Создал')
    create_date = fields.Datetime(string='Дата создания')

    # Основные поля
    date = fields.Date(string='Дата', default=fields.Date.today, required=True)
    currency = fields.Selection([
        ('usd', 'USD'),
        ('eur', 'EUR'), 
        ('cny', 'CNY (Юань)'),
        ('rub', 'RUB'),
    ], string='Валюта', required=True, default='usd')

    # Поля для юаня
    yuan_cross_rate = fields.Float(string='Кросскурс юань', digits=(16, 4))
    yuan_client_cross_rate = fields.Float(
        string='Кросскурс Юань к доллару для клиента', 
        compute='_compute_client_cross_rates', 
        store=True,
        digits=(16, 4)
    )
    yuan_to_rub_rate = fields.Float(
        string='Курс юаня к рублю', 
        compute='_compute_currency_to_rub_rates', 
        store=True,
        digits=(16, 4)
    )

    # Поля для евро
    eur_xe_rate = fields.Float(string='Курс XE евро', digits=(16, 4))
    eur_client_cross_rate = fields.Float(
        string='Кросскурс Евро к доллару для клиента', 
        compute='_compute_client_cross_rates', 
        store=True,
        digits=(16, 4)
    )
    eur_to_rub_rate = fields.Float(
        string='Курс евро к рублю', 
        compute='_compute_currency_to_rub_rates', 
        store=True,
        digits=(16, 4)
    )

    # Общие поля для юань и евро
    di_percent = fields.Float(string='% Ди', digits=(16, 4))
    di_amount = fields.Float(
        string='Сумма Ди', 
        compute='_compute_di_amount', 
        store=True,
        digits=(16, 4)
    )

    # Основные расчетные поля
    invoice_amount = fields.Float(string='Сумма инвойса', required=True, digits=(16, 4))
    
    # Поля для долларовых операций
    usd_cb_rate = fields.Float(string='Курс $ ЦБ', required=True, digits=(16, 4))
    total_payment_rate = fields.Float(
        string='Итоговый курс для суммы платежа',
        compute='_compute_usd_fields',
        store=True,
        digits=(16, 4)
    )
    payment_amount = fields.Float(
        string='Сумма платежа',
        compute='_compute_usd_fields', 
        store=True,
        digits=(16, 4)
    )
    amount_to_pay_rub = fields.Float(
        string='Сумма к оплате в рублях', 
        compute='_compute_amounts', 
        store=True,
        digits=(16, 4)
    )

    # Агентское вознаграждение
    agent_fee_percent = fields.Float(string='Агентское вознаграждение (%)', digits=(16, 4))
    agent_fee_amount = fields.Float(
        string='Сумма Агентского вознаграждения', 
        compute='_compute_amounts', 
        store=True,
        digits=(16, 4)
    )
    total_amount_to_pay = fields.Float(
        string='Общая сумма к оплате', 
        compute='_compute_amounts', 
        store=True,
        digits=(16, 4)
    )

    # Поля для долларовых сделок (только для USD) - но для 125 USD используем другое значение
    usd_125_amount = fields.Float(
        string='125$', 
        compute='_compute_usd_fields', 
        store=True,
        digits=(16, 4)
    )
    total_rub_amount = fields.Float(
        string='Итого в рублях', 
        compute='_compute_usd_fields', 
        store=True,
        digits=(16, 4)
    )
    
    # Курс включая 125$
    rate_including_125 = fields.Float(
        string='Курс (включая 125$)',
        compute='_compute_rate_including_125',
        store=True,
        digits=(16, 4)
    )

    @api.depends('date', 'currency', 'invoice_amount')
    def _compute_name(self):
        for record in self:
            if record.date and record.currency:
                date_str = record.date.strftime('%d.%m.%Y')
                currency_name = dict(record._fields['currency'].selection).get(record.currency, record.currency)
                record.name = f'Расчет 125 USD от {date_str} ({currency_name})'
            else:
                record.name = 'Расчет 125 USD'

    @api.depends('yuan_cross_rate', 'eur_xe_rate', 'di_percent', 'currency')
    def _compute_di_amount(self):
        for record in self:
            if record.currency == 'cny' and record.yuan_cross_rate:
                record.di_amount = record.yuan_cross_rate * (record.di_percent / 100)
            elif record.currency == 'eur' and record.eur_xe_rate:
                record.di_amount = record.eur_xe_rate * (record.di_percent / 100)
            else:
                record.di_amount = 0

    @api.depends('yuan_cross_rate', 'eur_xe_rate', 'di_amount', 'currency')
    def _compute_client_cross_rates(self):
        for record in self:
            if record.currency == 'cny':
                record.yuan_client_cross_rate = record.yuan_cross_rate + record.di_amount
                record.eur_client_cross_rate = 0
            elif record.currency == 'eur':
                record.eur_client_cross_rate = record.eur_xe_rate + record.di_amount
                record.yuan_client_cross_rate = 0
            else:
                record.yuan_client_cross_rate = 0
                record.eur_client_cross_rate = 0

    @api.depends('invoice_amount', 'yuan_client_cross_rate', 'eur_client_cross_rate', 
                 'usd_cb_rate', 'agent_fee_percent', 'currency')
    def _compute_amounts(self):
        for record in self:
            # Определяем кросскурс в зависимости от валюты
            if record.currency == 'cny' and record.yuan_client_cross_rate:
                cross_rate = record.yuan_client_cross_rate
            elif record.currency == 'eur' and record.eur_client_cross_rate:
                cross_rate = record.eur_client_cross_rate
            elif record.currency == 'usd':
                cross_rate = 1.0  # Для USD кросскурс = 1
            else:
                cross_rate = 1.0

            # Сумма к оплате в рублях
            if record.invoice_amount and record.usd_cb_rate and cross_rate:
                record.amount_to_pay_rub = (record.invoice_amount / cross_rate) * record.usd_cb_rate
            else:
                record.amount_to_pay_rub = 0

            # Сумма агентского вознаграждения (только для юань и евро)
            if record.currency in ['cny', 'eur'] and record.amount_to_pay_rub and record.agent_fee_percent:
                record.agent_fee_amount = record.amount_to_pay_rub * (record.agent_fee_percent / 100)
            else:
                record.agent_fee_amount = 0

            # Общая сумма к оплате
            record.total_amount_to_pay = record.amount_to_pay_rub + record.agent_fee_amount

    @api.depends('amount_to_pay_rub', 'invoice_amount', 'currency')
    def _compute_currency_to_rub_rates(self):
        for record in self:
            if record.currency == 'cny' and record.invoice_amount and record.amount_to_pay_rub:
                record.yuan_to_rub_rate = record.amount_to_pay_rub / record.invoice_amount
                record.eur_to_rub_rate = 0
            elif record.currency == 'eur' and record.invoice_amount and record.amount_to_pay_rub:
                record.eur_to_rub_rate = record.amount_to_pay_rub / record.invoice_amount
                record.yuan_to_rub_rate = 0
            else:
                record.yuan_to_rub_rate = 0
                record.eur_to_rub_rate = 0

    @api.depends('usd_cb_rate', 'amount_to_pay_rub', 'currency', 'agent_fee_percent', 'invoice_amount')
    def _compute_usd_fields(self):
        for record in self:
            if record.currency == 'usd':
                # Итоговый курс для суммы платежа = "Курс $ ЦБ" * (1 + "% Агентское вознаграждение" / 100)
                if record.usd_cb_rate:
                    if record.agent_fee_percent:
                        record.total_payment_rate = record.usd_cb_rate * (1 + record.agent_fee_percent / 100)
                    else:
                        record.total_payment_rate = record.usd_cb_rate
                else:
                    record.total_payment_rate = 0
                
                # Сумма платежа = "Итоговый курс для суммы платежа" * "Сумма инвойса"
                if record.total_payment_rate and record.invoice_amount:
                    record.payment_amount = record.total_payment_rate * record.invoice_amount
                else:
                    record.payment_amount = 0
                
                # 125$ = 125 * "Курс $ ЦБ"
                if record.usd_cb_rate:
                    record.usd_125_amount = 125 * record.usd_cb_rate
                else:
                    record.usd_125_amount = 0
                
                # Итого в рублях = "Сумма платежа" + "125$"
                record.total_rub_amount = record.payment_amount + record.usd_125_amount
            else:
                record.total_payment_rate = 0
                record.payment_amount = 0
                record.usd_125_amount = 0
                record.total_rub_amount = 0

    @api.depends('total_rub_amount', 'invoice_amount')
    def _compute_rate_including_125(self):
        for record in self:
            # Курс (включая 125$) = "Итого в рублях" / "Сумма инвойса в долларах"
            if record.invoice_amount and record.total_rub_amount:
                record.rate_including_125 = record.total_rub_amount / record.invoice_amount
            else:
                record.rate_including_125 = 0

 