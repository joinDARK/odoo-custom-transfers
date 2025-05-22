from odoo import models, fields, api
from .base_model import AmanatBaseModel

class Zayavka(models.Model, AmanatBaseModel):
    _name = 'amanat.zayavka'
    _description = 'Заявки'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]

    zayavka_id = fields.Char(
        string='ID заявки',
        readonly=True,
        tracking=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.zayavka.sequence'),
        copy=False
    )




    # GROUP: Основная информация
    status = fields.Selection(
        [
            ('close', 'заявка закрыта'),
            ('cancel', 'отменено клиентом'),
            ('1_no_chat', '1. не создан чат'),
            ('export_recipient_agreed', 'согласован получатель (только для Экспорта)'),
            ('10_swift_received', '10. получен свифт'),
            ('1_chat_created', "1'. создан чат"),
            ('4_agent_contract_signed', '4. подписан агент. договор'),
            ('15_return', '15. возврат'),
            ('16_paid_after_return', '16. оплачено повторно после возврата'),
            ('waiting_rub', 'ждем рубли'),
            ('17_money_received', '17. деньги у получателя'),
            ('5_invoice_issued', '5. выставлен инвойс на плательщика'),
            ('3_payer_approval', '3. согласование плательщика'),
            ('waiting_currency_export', 'ждём валюту (только для Экспорта)'),
            ('9', '9. передано на оплату'),
            ('17', '17`. ждём поступление валюты получателю'),
            ('6', '6. зафиксирован курс'),
            ('get_rub', 'получили рубли'),
            ('recevier_rub', 'рубли у получателя (только для Экспорта)'),
            ('13', '13. запрошен свифт 199'),
            ('take_currency', 'получили валюту (только для Экспорта)'),
            ('7', '7. Подписано поручение'),
            ('send_payment_rub', 'передали на оплату рубли (только для Экспорта)'),
            ('wait_send_payment', 'Ожидает передачи в оплату'),
            ('get_pp', 'Получена пп'),
        ],
        string='Статус',
        default='close',
        tracking=True,
    )

    zayavka_num = fields.Char(string='№ заявки', tracking=True)

    manager_ids = fields.Many2many(
        'amanat.manager',
        'amanat_zayavka_manager_rel',
        'zayavka_id',
        'manager_id',
        string='Менеджер',
        tracking=True
    )

    checker_ids = fields.Many2many(
        'amanat.manager',
        'amanat_zayavka_checker_rel',
        'zayavka_id',
        'checker_id',
        string='Проверяющий',
        tracking=True
    )

    num_zayavka = fields.Char(string='Номер заявки', tracking=True)

    date_placement = fields.Date(string='Дата размещения', tracking=True, default=fields.Date.today)

    taken_in_work_date = fields.Date(string='Взята в работу', tracking=True, default=fields.Date.today)

    contragent_id = fields.Many2one('amanat.contragent', string='Контрагент', tracking=True)

    agent_id = fields.Many2one('amanat.contragent', string='Агент', tracking=True)

    client_id = fields.Many2one('amanat.contragent', string='Клиент', tracking=True)

    inn = fields.Char(string='ИНН', related='client_id.payer_inn', store=True, readonly=True, tracking=True)

    exporter_importer_name = fields.Text(string='Наименование Экспортера/Импортера', tracking=True)

    bank_swift = fields.Text(string='SWIFT код банка', tracking=True)

    country_id = fields.Many2one('amanat.country', string='Страна', tracking=True)

    is_cross = fields.Boolean(string='Кросс', default=False, tracking=True)

    comment = fields.Text(string='Комментарии по заявке', tracking=True)

    # GROUP: Сравнение курса
    investing_rate = fields.Float(
        string='Курс Инвестинг',
        digits=(16, 4),
    )
    cb_rate = fields.Float(
        string='Курс ЦБ',
        digits=(16, 4),
    )
    cross_rate = fields.Float(
        string='Курс КРОСС',
        compute='_compute_cross_rate',
        store=True
    )

    @api.depends('real_cross_rate')
    def _compute_cross_rate(self):
        for record in self:
            record.cross_rate = record.real_cross_rate

    exchange_rate_1 = fields.Float(
        string='Курс Биржи 1',
        digits=(16, 4),
    )

    exchange_rate_2 = fields.Float(
        string='Курс Биржи 2',
        digits=(16, 4),
    )

    exchange_rate_3 = fields.Float(
        string='Курс Биржи 3',
        digits=(16, 4),
    )

    best_rate_name = fields.Char(
        string='Лучший курс Наименование',
        compute='_compute_best_rate_name',
        store=True,
    )

    @api.depends( 
        'investing_rate',
        'cb_rate',
        'cross_rate',
        'exchange_rate_1',
        'exchange_rate_2',
        'exchange_rate_3',
        'deal_type'
    )
    def _compute_best_rate_name(self):
        for rec in self:
            # Проверка на нулевые значения всех курсов
            if (
                not rec.investing_rate and
                not rec.cb_rate and
                not rec.cross_rate and
                not rec.exchange_rate_1 and
                not rec.exchange_rate_2 and
                not rec.exchange_rate_3
            ):
                rec.best_rate_name = False
                continue
            
            # Формируем список допустимых курсов (без нулей)
            valid_courses = {
                'Курс Инвестинг': rec.investing_rate or None,
                'Курс ЦБ': rec.cb_rate or None,
                'Курс КРОСС': rec.cross_rate or None,
                'Курс Биржи 1': rec.exchange_rate_1 or None,
                'Курс Биржи 2': rec.exchange_rate_2 or None,
                'Курс Биржи 3': rec.exchange_rate_3 or None,
            }
            valid_courses = {k: v for k, v in valid_courses.items() if v is not None}
            
            if not valid_courses:
                rec.best_rate_name = False
                continue
            
            # Выбор минимального/максимального значения
            if rec.deal_type == 'export':
                min_value = min(valid_courses.values())
                rec.best_rate_name = next(k for k, v in valid_courses.items() if v == min_value)
            else:
                max_value = max(valid_courses.values())
                rec.best_rate_name = next(k for k, v in valid_courses.items() if v == max_value)

    best_rate = fields.Float(
        string='Лучший курс',
        compute='_compute_best_rate',
        store=True,
    )

    @api.depends(
        'investing_rate', 'cb_rate', 'cross_rate',
        'exchange_rate_1', 'exchange_rate_2', 'exchange_rate_3',
        'deal_type'
    )
    def _compute_best_rate(self):
        for record in self:
            # Проверяем, если все курсы равны 0
            if (
                record.investing_rate == 0 and
                record.cb_rate == 0 and
                record.cross_rate == 0 and
                record.exchange_rate_1 == 0 and
                record.exchange_rate_2 == 0 and
                record.exchange_rate_3 == 0
            ):
                record.best_rate = False  # BLANK()
            else:
                if record.deal_type == "export":
                    # Для экспорта ищем минимальное значение среди всех курсов
                    rates = [
                        record.investing_rate or 9999999,
                        record.cb_rate or 9999999,
                        record.cross_rate or 9999999,
                        record.exchange_rate_1 or 9999999,
                        record.exchange_rate_2 or 9999999,
                        record.exchange_rate_3 or 9999999,
                    ]
                    record.best_rate = min(rates)
                else:
                    # Для импорта ищем максимальное значение среди всех курсов
                    rates = [
                        record.investing_rate or -9999999,
                        record.cb_rate or -9999999,
                        record.cross_rate or -9999999,
                        record.exchange_rate_1 or -9999999,
                        record.exchange_rate_2 or -9999999,
                        record.exchange_rate_3 or -9999999,
                    ]
                    record.best_rate = max(rates)

    # GROUP: Клиент
    client_inn = fields.Char(string='ИНН (from Клиент)', related='client_id.inn', store=True, readonly=True, tracking=True)

    client_ruble_paid_date = fields.Date(string='оплачен рубль клиенту (экспорт)', tracking=True)

    client_reward = fields.Float(
        string='Вознаграждение по договору Клиент',
        compute='_compute_client_reward',
        store=True,
        tracking=True
    )

    @api.depends('reward_percent', 'rate_field', 'amount')
    def _compute_client_reward(self):
        for rec in self:
            rec.client_reward = rec.reward_percent * rec.rate_field * rec.amount

    our_client_reward = fields.Float(
        string='Вознаграждение наше Клиент',
        compute='_compute_our_client_reward',
        store=True,
        tracking=True
    )

    @api.depends('best_rate', 'hidden_commission', 'amount', 'plus_currency')
    def _compute_our_client_reward(self):
        for rec in self:
            rec.our_client_reward = rec.best_rate * rec.hidden_commission * (rec.amount + rec.plus_currency)

    non_our_client_reward = fields.Float(
        string='Вознаграждение не наше Клиент',
        compute='_compute_non_our_client_reward',
        store=True,
        tracking=True
    )

    @api.depends('total_client', 'rate_real', 'our_client_reward')
    def _compute_non_our_client_reward(self):
        for rec in self:
            rec.non_our_client_reward = rec.total_client - (rec.rate_real + rec.our_client_reward)

    total_client = fields.Float(
        string='Итого Клиент',
        compute='_compute_total_client',
        store=True,
        tracking=True
    )

    @api.depends('application_amount_rub_contract', 'client_reward')
    def _compute_total_client(self):
        for rec in self:
            rec.total_client = rec.application_amount_rub_contract + rec.client_reward

    total_client_management = fields.Float(
        string='Итого Клиент упр',
        compute='_compute_total_client_management',
        store=True,
        tracking=True
    )

    @api.depends('rate_real', 'our_client_reward', 'non_our_client_reward')
    def _compute_total_client_management(self):
        for rec in self:
            rec.total_client_management = rec.rate_real + rec.our_client_reward + rec.non_our_client_reward

    client_payment_cost = fields.Float(
        string='Расход платежа Клиент',
        compute='_compute_client_payment_cost',
        store=True,
        digits=(16, 2),
    )

    @api.depends('amount', 'price_list_carrying_out_accrual_percentage')
    def _compute_client_payment_cost(self):
        for rec in self:
            rec.client_payment_cost = (rec.amount or 0) * (rec.price_list_carrying_out_accrual_percentage or 0)

    payment_order_rf_client = fields.Float(
        string='Платежка РФ Клиент',
        compute='_compute_payment_order_rf_client',
        store=True,
        tracking=True
    )

    @api.depends('application_amount_rub_contract', 'client_reward', 'percent_from_payment_order_rule')
    def _compute_payment_order_rf_client(self):
        for rec in self:
            contract_rub = rec.application_amount_rub_contract or 0.0
            client_reward = rec.client_reward or 0.0
            percent = rec.percent_from_payment_order_rule or 0.0

            rec.payment_order_rf_client = (contract_rub + client_reward) * percent

    client_operating_expenses = fields.Float(
        string='Расход на операционную деятельность Клиент',
        compute='_compute_client_operating_expenses',
        store=True,
        tracking=True
    )

    @api.depends('usd_equivalent', 'total_client', 'partner_post_conversion_rate')
    def _compute_client_operating_expenses(self):
        for rec in self:
            usd_equivalent = rec.usd_equivalent or 0.0
            total_client = rec.total_client or 0.0
            partner_rate = rec.partner_post_conversion_rate or 0.0

            if partner_rate == 0.0:
                rec.client_operating_expenses = 0.0
                continue

            if usd_equivalent >= 200000:
                rec.client_operating_expenses = (0.001 * total_client) / partner_rate
            else:
                if total_client == 0:
                    rec.client_operating_expenses = 0.0
                else:
                    value = max(0.002 * total_client, 25000)
                    rec.client_operating_expenses = value / partner_rate

    client_real_operating_expenses = fields.Float(
        string='Расход на операционную деятельность Клиент Реал',
        compute='_compute_client_real_operating_expenses',
        store=True,
        tracking=True
    )

    @api.depends('total_client', 'real_post_conversion_rate', 'percent_from_expense_rule', 'correction')
    def _compute_client_real_operating_expenses(self):
        for rec in self:
            total_client = rec.total_client or 0.0
            real_post_rate = rec.real_post_conversion_rate or 0.0
            percent_rule = rec.percent_from_expense_rule or 0.0
            correction = rec.correction or 0.0

            if total_client == 0 or real_post_rate == 0:
                rec.client_real_operating_expenses = 0.0
            else:
                rec.client_real_operating_expenses = ((percent_rule - correction) * total_client) / real_post_rate

    client_real_operating_expenses_usd = fields.Float(
        string='Расход на операционную деятельность Клиент Реал $',
        compute='_compute_client_real_operating_expenses_usd',
        store=True,
        tracking=True
    )

    @api.depends('client_real_operating_expenses', 'payer_cross_rate_usd_auto')
    def _compute_client_real_operating_expenses_usd(self):
        for rec in self:
            value = (rec.client_real_operating_expenses or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)
            rec.client_real_operating_expenses_usd = value

    client_real_operating_expenses_rub = fields.Float(
        string='Расход на операционную деятельность Клиент Реал ₽',
        compute='_compute_client_real_operating_expenses_rub',
        store=True,
        tracking=True
    )

    @api.depends('client_real_operating_expenses_usd', 'payer_cross_rate_rub')
    def _compute_client_real_operating_expenses_rub(self):
        for rec in self:
            rec.client_real_operating_expenses_rub = (rec.client_real_operating_expenses_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    client_currency_bought = fields.Float(
        string='Купили валюту Клиент',
        compute='_compute_client_currency_bought',
        store=True,
        tracking=True
    )

    @api.depends('total_client', 'payment_order_rf_client', 'partner_post_conversion_rate')
    def _compute_client_currency_bought(self):
        for rec in self:
            total_client = rec.total_client or 0.0
            payment_rf = rec.payment_order_rf_client or 0.0
            partner_rate = rec.partner_post_conversion_rate or 0.0

            if not partner_rate:
                rec.client_currency_bought = 0.0
            else:
                rec.client_currency_bought = (total_client - payment_rf) / partner_rate

    client_currency_bought_real = fields.Float(
        string='Купили валюту Клиент реал',
        compute='_compute_client_currency_bought_real',
        store=True,
        tracking=True
    )

    @api.depends('total_client', 'payment_order_rf_client', 'real_post_conversion_rate')
    def _compute_client_currency_bought_real(self):
        for rec in self:
            total_client = rec.total_client or 0.0
            payment_rf = rec.payment_order_rf_client or 0.0
            real_post_rate = rec.real_post_conversion_rate or 0.0

            if not real_post_rate:
                rec.client_currency_bought_real = 0.0
            else:
                rec.client_currency_bought_real = (total_client - payment_rf) / real_post_rate

    client_currency_bought_real_usd = fields.Float(
        string='Купили валюту Клиент реал $',
        compute='_compute_client_currency_bought_real_usd',
        store=True,
        tracking=True
    )

    @api.depends('client_currency_bought_real', 'payer_cross_rate_usd_auto')
    def _compute_client_currency_bought_real_usd(self):
        for rec in self:
            rec.client_currency_bought_real_usd = (rec.client_currency_bought_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    client_currency_bought_real_rub = fields.Float(
        string='Купили валюту Клиент реал ₽',
        compute='_compute_client_currency_bought_real_rub',
        store=True,
        tracking=True
    )

    @api.depends('client_currency_bought_real_usd', 'payer_cross_rate_rub')
    def _compute_client_currency_bought_real_rub(self):
        for rec in self:
            rec.client_currency_bought_real_rub = (rec.client_currency_bought_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    client_payment_cost_usd = fields.Float(
        string='Расход платежа в $ Клиент',
        compute='_compute_client_payment_cost_usd',
        store=True,
        tracking=True
    )

    @api.depends('payment_cost_sovok', 'payer_cross_rate_usd_auto', 'price_list_carrying_out_fixed_deal_fee')
    def _compute_client_payment_cost_usd(self):
        for rec in self:
            sovok_cost = rec.payment_cost_sovok or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            fixed_fee = rec.price_list_carrying_out_fixed_deal_fee or 0.0

            rec.client_payment_cost_usd = sovok_cost * cross_rate + fixed_fee

    client_payment_cost_rub = fields.Float(
        string='Расход платежа в ₽ Клиент',
        compute='_compute_client_payment_cost_rub',
        store=True,
        tracking=True
    )

    @api.depends('client_payment_cost_usd', 'payer_cross_rate_rub')
    def _compute_client_payment_cost_rub(self):
        for rec in self:
            rec.client_payment_cost_rub = (rec.client_payment_cost_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    cost_of_money_client = fields.Float(
        string='Себестоимость денег Клиент',
        compute='_compute_cost_of_money_client',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    @api.depends('date_days', 'client_currency_bought')
    def _compute_cost_of_money_client(self):
        for rec in self:
            # Формула: ({Дата}+1)/25*0.04*{Купили валюту Клиент}
            if rec.date_days and rec.client_currency_bought:
                days = (fields.Date.today() - rec.date_days).days + 1
                rec.cost_of_money_client = (days / 25) * 0.04 * rec.client_currency_bought
            else:
                rec.cost_of_money_client = 0.0

    cost_of_money_client_real = fields.Float(
        string='Себестоимость денег Клиент реал',
        compute='_compute_cost_of_money_client_real',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    @api.depends('agent_id', 'date_days', 'money_cost_rule_extra_days', 'money_cost_rule_credit_period', 'money_cost_rule_credit_rate', 'client_currency_bought_real')
    def _compute_cost_of_money_client_real(self):
        for rec in self:
            if rec.agent_id and rec.agent_id.name == "Тезер":
                rec.cost_of_money_client_real = 0.0
            else:
                if (rec.date_days is not None and
                    rec.money_cost_rule_extra_days is not None and
                    rec.money_cost_rule_credit_period and
                    rec.money_cost_rule_credit_rate and
                    rec.client_currency_bought_real):
                    
                    total_days = rec.date_days + rec.money_cost_rule_extra_days
                    rec.cost_of_money_client_real = (total_days / rec.money_cost_rule_credit_period) * rec.money_cost_rule_credit_rate * rec.client_currency_bought_real
                else:
                    rec.cost_of_money_client_real = 0.0

    cost_of_money_client_real_usd = fields.Float(
        string='Себестоимость денег Клиент реал $',
        compute='_compute_cost_of_money_client_real_usd',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    @api.depends('cost_of_money_client_real', 'payer_cross_rate_usd_auto')
    def _compute_cost_of_money_client_real_usd(self):
        for rec in self:
            rec.cost_of_money_client_real_usd = (rec.cost_of_money_client_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    cost_of_money_client_real_rub = fields.Float(
        string='Себестоимость денег Клиент реал ₽',
        compute='_compute_cost_of_money_client_real_rub',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    @api.depends('cost_of_money_client_real_usd', 'payer_cross_rate_rub')
    def _compute_cost_of_money_client_real_rub(self):
        for rec in self:
            rec.cost_of_money_client_real_rub = (rec.cost_of_money_client_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    fin_res_client = fields.Float(
        string='Фин рез Клиент',
        compute='_compute_fin_res_client',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    @api.depends(
        'client_currency_bought',
        'client_payment_cost',
        'cost_of_money_client',
        'hidden_partner_commission',
        'client_operating_expenses',
        'amount',
        'payer_profit_currency',
    )
    def _compute_fin_res_client(self):
        for rec in self:
            rec.fin_res_client = (
                (rec.client_currency_bought or 0.0) -
                (rec.client_payment_cost or 0.0) -
                (rec.cost_of_money_client or 0.0) -
                (rec.hidden_partner_commission or 0.0) -
                (rec.client_operating_expenses or 0.0) -
                (rec.amount or 0.0) -
                (rec.payer_profit_currency or 0.0)
            )

    fin_res_client_real = fields.Float(
        string='Фин рез Клиент реал',
        compute='_compute_fin_res_client_real',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    @api.depends(
        'client_currency_bought_real',
        'client_payment_cost',
        'cost_of_money_client_real',
        'hidden_partner_commission_real',
        'client_real_operating_expenses',
        'amount',
        'payer_profit_currency',
    )
    def _compute_fin_res_client_real(self):
        for rec in self:
            rec.fin_res_client_real = (
                (rec.client_currency_bought_real or 0.0) -
                (rec.client_payment_cost or 0.0) -
                (rec.cost_of_money_client_real or 0.0) -
                (rec.hidden_partner_commission_real or 0.0) -
                (rec.client_real_operating_expenses or 0.0) -
                (rec.amount or 0.0) -
                (rec.payer_profit_currency or 0.0)
            )

    fin_res_client_real_usd = fields.Float(
        string='Фин рез Клиент реал $',
        compute='_compute_fin_res_client_real_usd',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    fin_res_client_real_rub = fields.Float(
        string='Фин рез Клиент реал ₽',
        compute='_compute_fin_res_client_real_rub',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    @api.depends('fin_res_client_real', 'payer_cross_rate_usd_auto')
    def _compute_fin_res_client_real_usd(self):
        for rec in self:
            rec.fin_res_client_real_usd = (rec.fin_res_client_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('fin_res_client_real_usd', 'payer_cross_rate_rub')
    def _compute_fin_res_client_real_rub(self):
        for rec in self:
            rec.fin_res_client_real_rub = (rec.fin_res_client_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    # GROUP: Сбер
    sber_reward = fields.Float(
        string='Вознаграждение по договору Сбер',
        compute='_compute_sber_reward',
        store=True,
        tracking=True
    )

    @api.depends('reward_percent', 'rate_field', 'amount')
    def _compute_sber_reward(self):
        for rec in self:
            rec.sber_reward = rec.reward_percent * rec.rate_field * rec.amount

    our_sber_reward = fields.Float(
        string='Вознаграждение наше Сбер',
        compute='_compute_our_sber_reward',
        store=True,
        tracking=True
    )

    @api.depends('rate_field', 'best_rate', 'amount', 'plus_currency', 'sber_reward')
    def _compute_our_sber_reward(self):
        for rec in self:
            rec.our_sber_reward = (rec.rate_field - rec.best_rate) * (rec.amount + rec.plus_currency) + rec.sber_reward

    non_our_sber_reward = fields.Float(
        string='Вознаграждение не наше Сбер',
        compute='_compute_non_our_sber_reward',
        store=True,
        tracking=True
    )

    @api.depends('total_sber', 'our_sber_reward', 'rate_real')
    def _compute_non_our_sber_reward(self):
        for rec in self:
            rec.non_our_sber_reward = rec.total_sber - (rec.our_sber_reward + rec.rate_real)

    total_sber = fields.Float(
        string='Итого Сбер',
        compute='_compute_total_sber',
        store=True,
        tracking=True
    )

    @api.depends('application_amount_rub_contract', 'sber_reward')
    def _compute_total_sber(self):
        for rec in self:
            rec.total_sber = rec.application_amount_rub_contract + rec.sber_reward

    total_sber_management = fields.Float(
        string='Итого Сбер упр',
        compute='_compute_total_sber_management',
        store=True,
        tracking=True
    )

    @api.depends('rate_real', 'our_sber_reward', 'non_our_sber_reward')
    def _compute_total_sber_management(self):
        for rec in self:
            rec.total_sber_management = rec.rate_real + (rec.our_sber_reward + rec.non_our_sber_reward)

    overall_sber_percent = fields.Float(
        string='Общий процент Сбер',
        compute='_compute_overall_sber_percent',
        store=True,
        tracking=True
    )

    @api.depends('hand_reward_percent')
    def _compute_overall_sber_percent(self):
        for rec in self:
            rec.overall_sber_percent = rec.hand_reward_percent

    rate_real_sber = fields.Float(
        string='Заявка по курсу реальный Сбер',
        compute='_compute_rate_real_sber',
        store=True,
        tracking=True
    )

    @api.depends('total_amount', 'agent_our_reward')
    def _compute_rate_real_sber(self):
        for rec in self:
            rec.rate_real_sber = rec.total_amount - rec.agent_our_reward

    sber_payment_cost = fields.Float(
        string='Расход платежа Сбер',
        compute='_compute_sber_payment_cost',
        store=True,
        digits=(16, 2),
    )

    @api.depends('amount', 'price_list_carrying_out_accrual_percentage')
    def _compute_sber_payment_cost(self):
        for rec in self:
            rec.sber_payment_cost = (rec.amount or 0) * (rec.price_list_carrying_out_accrual_percentage or 0)
    
    payment_order_rf_sber = fields.Float(
        string='Платежка РФ Сбер',
        compute='_compute_payment_order_rf_sber',
        store=True,
        tracking=True
    )

    @api.depends('application_amount_rub_contract', 'sber_reward', 'percent_from_payment_order_rule')
    def _compute_payment_order_rf_sber(self):
        for rec in self:
            contract_rub = rec.application_amount_rub_contract or 0.0
            sber_reward = rec.sber_reward or 0.0
            percent = rec.percent_from_payment_order_rule or 0.0

            rec.payment_order_rf_sber = (contract_rub + sber_reward) * percent

    sber_operating_expenses = fields.Float(
        string='Расход на операционную деятельность Сбер',
        compute='_compute_sber_operating_expenses',
        store=True,
        tracking=True,
    )

    @api.depends('usd_equivalent', 'total_sber', 'partner_post_conversion_rate')
    def _compute_sber_operating_expenses(self):
        for rec in self:
            usd_equivalent = rec.usd_equivalent or 0.0
            total_sber = rec.total_sber or 0.0
            partner_rate = rec.partner_post_conversion_rate or 0.0

            if partner_rate == 0.0:
                rec.sber_operating_expenses = 0.0
                continue

            if usd_equivalent >= 200000:
                rec.sber_operating_expenses = (0.001 * total_sber) / partner_rate
            else:
                if total_sber == 0:
                    rec.sber_operating_expenses = 0.0
                else:
                    rec.sber_operating_expenses = max(0.002 * total_sber, 25000) / partner_rate

    sber_operating_expenses_real = fields.Float(
        string='Расход на операционную деятельность Сбер реал',
        compute='_compute_sber_operating_expenses_real',
        store=True,
        tracking=True,
    )

    @api.depends('total_sber', 'percent_from_expense_rule', 'correction', 'real_post_conversion_rate')
    def _compute_sber_operating_expenses_real(self):
        for rec in self:
            if (rec.total_sber == 0 or
                rec.real_post_conversion_rate == 0):
                rec.sber_operating_expenses_real = 0.0
            else:
                rec.sber_operating_expenses_real = (
                    ((rec.percent_from_expense_rule or 0.0) - (rec.correction or 0.0)) *
                    (rec.total_sber or 0.0) /
                    (rec.real_post_conversion_rate or 1.0)
                )

    sber_operating_expenses_real_usd = fields.Float(
        string='Расход на операционную деятельность Сбер реал $',
        compute='_compute_sber_operating_expenses_real_usd',
        store=True,
        tracking=True,
    )

    @api.depends('sber_operating_expenses_real', 'payer_cross_rate_usd_auto')
    def _compute_sber_operating_expenses_real_usd(self):
        for rec in self:
            rec.sber_operating_expenses_real_usd = (rec.sber_operating_expenses_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    sber_operating_expenses_real_rub = fields.Float(
        string='Расход на операционную деятельность Сбер реал ₽',
        compute='_compute_sber_operating_expenses_real_rub',
        store=True,
        tracking=True,
    )

    @api.depends('sber_operating_expenses_real_usd', 'payer_cross_rate_rub')
    def _compute_sber_operating_expenses_real_rub(self):
        for rec in self:
            rec.sber_operating_expenses_real_rub = (rec.sber_operating_expenses_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    kupili_valyutu_sber = fields.Float(
        string='Купили валюту Сбер',
        compute='_compute_kupili_valyutu_sber',
        store=True,
        tracking=True
    )

    @api.depends('total_sber', 'payment_order_rf_sber', 'partner_post_conversion_rate')
    def _compute_kupili_valyutu_sber(self):
        for rec in self:
            if rec.partner_post_conversion_rate:
                rec.kupili_valyutu_sber = (rec.total_sber - rec.payment_order_rf_sber) / rec.partner_post_conversion_rate
            else:
                rec.kupili_valyutu_sber = 0.0

    kupili_valyutu_sber_real = fields.Float(
        string='Купили валюту Сбер реал',
        compute='_compute_kupili_valyutu_sber_real',
        store=True,
        tracking=True
    )

    @api.depends('total_sber', 'payment_order_rf_sber', 'real_post_conversion_rate')
    def _compute_kupili_valyutu_sber_real(self):
        for rec in self:
            if rec.real_post_conversion_rate:
                rec.kupili_valyutu_sber_real = (rec.total_sber - rec.payment_order_rf_sber) / rec.real_post_conversion_rate
            else:
                rec.kupili_valyutu_sber_real = 0.0

    kupili_valyutu_sber_real_usd = fields.Float(
        string='Купили валюту Сбер реал $',
        compute='_compute_kupili_valyutu_sber_real_usd',
        store=True,
        tracking=True
    )

    @api.depends('kupili_valyutu_sber_real', 'payer_cross_rate_usd_auto')
    def _compute_kupili_valyutu_sber_real_usd(self):
        for rec in self:
            rec.kupili_valyutu_sber_real_usd = rec.kupili_valyutu_sber_real * (rec.payer_cross_rate_usd_auto or 0.0)

    kupili_valyutu_sber_real_rub = fields.Float(
        string='Купили валюту Сбер реал ₽',
        compute='_compute_kupili_valyutu_sber_real_rub',
        store=True,
        tracking=True
    )

    @api.depends('kupili_valyutu_sber_real_usd', 'payer_cross_rate_rub')
    def _compute_kupili_valyutu_sber_real_rub(self):
        for rec in self:
            rec.kupili_valyutu_sber_real_rub = rec.kupili_valyutu_sber_real_usd * (rec.payer_cross_rate_rub or 0.0)
    
    sber_payment_cost_usd = fields.Float(
        string='Расход платежа Сбер $',
        compute='_compute_sber_payment_cost_usd',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    sber_payment_cost_rub = fields.Float(
        string='Расход платежа Сбер ₽',
        compute='_compute_sber_payment_cost_rub',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    @api.depends('sber_payment_cost', 'payer_cross_rate_usd_auto')
    def _compute_sber_payment_cost_usd(self):
        for rec in self:
            # Формула: {Расход платежа Сбер $} = {Расход платежа Сбер} * {Кросс-курс Плательщика $ авто}
            rec.sber_payment_cost_usd = (rec.sber_payment_cost or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('sber_payment_cost_usd', 'payer_cross_rate_rub')
    def _compute_sber_payment_cost_rub(self):
        for rec in self:
            # Формула: {Расход платежа Сбер ₽} = {Расход платежа Сбер $} * {Кросс-курс Плательщика ₽}
            rec.sber_payment_cost_rub = (rec.sber_payment_cost_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)
            
    sber_payment_cost_on_usd = fields.Float(
        string='Расход платежа в $ Сбер',
        compute='_compute_sber_payment_cost_on_usd',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    @api.depends('payment_cost_sovok', 'payer_cross_rate_usd_auto', 'price_list_carrying_out_fixed_deal_fee')
    def _compute_sber_payment_cost_on_usd(self):
        for rec in self:
            sovok_cost = rec.payment_cost_sovok or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            fixed_fee = rec.price_list_carrying_out_fixed_deal_fee or 0.0
            rec.sber_payment_cost_on_usd = sovok_cost * cross_rate + fixed_fee

    sber_payment_cost_on_usd_real = fields.Float(
        string='Расход платежа в $ Сбер реал',
        compute='_compute_sber_payment_cost_on_usd_real',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    @api.depends('payment_cost_sovok', 'payer_cross_rate_usd_auto', 'price_list_carrying_out_fixed_deal_fee')
    def _compute_sber_payment_cost_on_usd_real(self):
        for rec in self:
            sovok_cost = rec.payment_cost_sovok or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            fixed_fee = rec.price_list_carrying_out_fixed_deal_fee or 0.0
            rec.sber_payment_cost_on_usd_real = sovok_cost * cross_rate + fixed_fee
            
    sebestoimost_denej_sber = fields.Float(
        string='Себестоимость денег Сбер',
        compute='_compute_sebestoimost_denej_sber',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    @api.depends('date_days', 'kupili_valyutu_sber')
    def _compute_sebestoimost_denej_sber(self):
        for rec in self:
            if rec.date_days and rec.kupili_valyutu_sber:
                days = rec.date_days + 1
                rec.sebestoimost_denej_sber = (days / 25) * 0.04 * rec.kupili_valyutu_sber
            else:
                rec.sebestoimost_denej_sber = 0.0

    sebestoimost_denej_sber_real = fields.Float(
        string='Себестоимость денег Сбер реал',
        compute='_compute_sebestoimost_denej_sber_real',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    @api.depends('agent_id', 'date_days', 'money_cost_rule_extra_days', 'money_cost_rule_credit_period', 'money_cost_rule_credit_rate', 'kupili_valyutu_sber_real')
    def _compute_sebestoimost_denej_sber_real(self):
        for rec in self:
            if rec.agent_id and rec.agent_id.name == "Тезер":
                rec.sebestoimost_denej_sber_real = 0.0
            else:
                if (rec.date_days is not None and
                    rec.money_cost_rule_extra_days is not None and
                    rec.money_cost_rule_credit_period and
                    rec.money_cost_rule_credit_rate and
                    rec.kupili_valyutu_sber_real):
                    
                    total_days = rec.date_days + rec.money_cost_rule_extra_days
                    rec.sebestoimost_denej_sber_real = (total_days / rec.money_cost_rule_credit_period) * rec.money_cost_rule_credit_rate * rec.kupili_valyutu_sber_real
                else:
                    rec.sebestoimost_denej_sber_real = 0.0

    sebestoimost_denej_sber_real_usd = fields.Float(
        string='Себестоимость денег Сбер реал $',
        compute='_compute_sebestoimost_denej_sber_real_usd',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    @api.depends('sebestoimost_denej_sber_real', 'payer_cross_rate_usd_auto')
    def _compute_sebestoimost_denej_sber_real_usd(self):
        for rec in self:
            rec.sebestoimost_denej_sber_real_usd = (rec.sebestoimost_denej_sber_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    sebestoimost_denej_sber_real_rub = fields.Float(
        string='Себестоимость денег Сбер реал ₽',
        compute='_compute_sebestoimost_denej_sber_real_rub',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    @api.depends('sebestoimost_denej_sber_real_usd', 'payer_cross_rate_rub')
    def _compute_sebestoimost_denej_sber_real_rub(self):
        for rec in self:
            rec.sebestoimost_denej_sber_real_rub = (rec.sebestoimost_denej_sber_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)
            
    fin_res_sber = fields.Float(
        string='Фин рез Сбер',
        compute='_compute_fin_res_sber',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    @api.depends(
        'kupili_valyutu_sber',
        'sber_payment_cost',
        'sebestoimost_denej_sber',
        'hidden_partner_commission',
        'sber_operating_expenses',
        'amount',
        'payer_profit_currency'
    )
    def _compute_fin_res_sber(self):
        for rec in self:
            rec.fin_res_sber = (
                (rec.kupili_valyutu_sber or 0.0) -
                (rec.sber_payment_cost or 0.0) -
                (rec.sebestoimost_denej_sber or 0.0) -
                (rec.hidden_partner_commission or 0.0) -
                (rec.sber_operating_expenses or 0.0) -
                (rec.amount or 0.0) -
                (rec.payer_profit_currency or 0.0)
            )

    fin_res_sber_real = fields.Float(
        string='Фин рез Сбер реал',
        compute='_compute_fin_res_sber_real',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    @api.depends(
        'kupili_valyutu_sber_real',
        'sber_payment_cost',
        'sebestoimost_denej_sber_real',
        'hidden_partner_commission_real',
        'sber_operating_expenses_real',
        'amount',
        'payer_profit_currency'
    )
    def _compute_fin_res_sber_real(self):
        for rec in self:
            rec.fin_res_sber_real = (
                (rec.kupili_valyutu_sber_real or 0.0) -
                (rec.sber_payment_cost or 0.0) -
                (rec.sebestoimost_denej_sber_real or 0.0) -
                (rec.hidden_partner_commission_real or 0.0) -
                (rec.sber_operating_expenses_real or 0.0) -
                (rec.amount or 0.0) -
                (rec.payer_profit_currency or 0.0)
            )
            
    fin_res_sber_real_usd = fields.Float(
        string='Фин рез Сбер реал $',
        compute='_compute_fin_res_sber_real_usd',
        store=True,
        digits=(16, 2),
        tracking=True,
    )
    
    @api.depends('fin_res_sber_real', 'payer_cross_rate_usd_auto')
    def _compute_fin_res_sber_real_usd(self):
        for rec in self:
            rec.fin_res_sber_real_usd = (rec.fin_res_sber_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    fin_res_sber_real_rub = fields.Float(
        string='Фин рез Сбер реал ₽',
        compute='_compute_fin_res_sber_real_rub',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    @api.depends('fin_res_sber_real_usd', 'payer_cross_rate_rub')
    def _compute_fin_res_sber_real_rub(self):
        for rec in self:
            rec.fin_res_sber_real_rub = (rec.fin_res_sber_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    # GROUP: Совок
    our_sovok_reward = fields.Float(
        string='Вознаграждение наше Совок',
        compute='_compute_our_sovok_reward',
        store=True,
        tracking=True
    )

    @api.depends('rate_field', 'best_rate', 'amount')
    def _compute_our_sovok_reward(self):
        for rec in self:
            rec.our_sovok_reward = (rec.rate_field - rec.best_rate) * rec.amount

    sovok_reward = fields.Float(
        string='Вознаграждение по договору Совок',
        compute='_compute_sovok_reward',
        store=True,
        tracking=True
    )

    @api.depends()
    def _compute_sovok_reward(self): # Здесь все нормально
        for rec in self:
            rec.sovok_reward = 0.0

    total_sovok = fields.Float(
        string='Итого Совок',
        compute='_compute_total_sovok',
        store=True,
        tracking=True
    )

    @api.depends('application_amount_rub_contract')
    def _compute_total_sovok(self):
        for rec in self:
            rec.total_sovok = rec.application_amount_rub_contract

    total_sovok_management = fields.Float(
        string='Итого Совок упр',
        compute='_compute_total_sovok_management',
        store=True,
        tracking=True
    )

    @api.depends('rate_real', 'our_sovok_reward')
    def _compute_total_sovok_management(self):
        for rec in self:
            rec.total_sovok_management = rec.rate_real + rec.our_sovok_reward

    overall_sovok_percent = fields.Float(
        string='Общий процент Совок',
        compute='_compute_overall_sovok_percent',
        store=True,
        tracking=True
    )

    @api.depends('rate_field', 'best_rate')
    def _compute_overall_sovok_percent(self):
        for rec in self:
            if rec.best_rate:  # Проверка на ноль
                rec.overall_sovok_percent = (rec.rate_field - rec.best_rate) / rec.best_rate
            else:
                rec.overall_sovok_percent = 0.0

    payment_cost_sovok = fields.Float(
        string='Расход платежа Совок',
        compute='_compute_payment_cost_sovok',
        store=True,
    )

    @api.depends('amount', 'price_list_percent_accrual')
    def _compute_payment_cost_sovok(self):
        for record in self:
            amount = record.amount or 0.0
            percent = record.price_list_percent_accrual or 0.0
            record.payment_cost_sovok = amount * percent

    payment_order_rf_sovok = fields.Float(
        string='Платежка РФ Совок',
        compute='_compute_payment_order_rf_sovok',
        store=True,
        tracking=True
    )

    @api.depends('application_amount_rub_contract', 'sovok_reward', 'percent_from_payment_order_rule')
    def _compute_payment_order_rf_sovok(self):
        for rec in self:
            contract_rub = rec.application_amount_rub_contract or 0.0
            sovok_reward = rec.sovok_reward or 0.0
            percent = rec.percent_from_payment_order_rule or 0.0
            rec.payment_order_rf_sovok = (contract_rub + sovok_reward) * percent

    operating_expenses_sovok_partner = fields.Float(
        string='Расход на операционную деятельность Совок партнер',
        compute='_compute_operating_expenses_sovok_partner',
        store=True,
        tracking=True
    )

    @api.depends('usd_equivalent', 'total_sovok', 'partner_post_conversion_rate')
    def _compute_operating_expenses_sovok_partner(self):
        for rec in self:
            usd_equivalent = rec.usd_equivalent or 0.0
            total_sovok = rec.total_sovok or 0.0
            partner_rate = rec.partner_post_conversion_rate or 0.0

            if partner_rate == 0.0:
                rec.operating_expenses_sovok_partner = 0.0
                continue

            if usd_equivalent >= 200000:
                rec.operating_expenses_sovok_partner = (0.001 * total_sovok) / partner_rate
            else:
                if total_sovok == 0:
                    rec.operating_expenses_sovok_partner = 0.0
                else:
                    value = max(0.002 * total_sovok, 25000)
                    rec.operating_expenses_sovok_partner = value / partner_rate

    operating_expenses_sovok_real = fields.Float(
        string='Расход на операционную деятельность Совок реал',
        compute='_compute_operating_expenses_sovok_real',
        store=True,
        tracking=True
    )

    @api.depends('total_sovok', 'percent_from_expense_rule', 'correction', 'real_post_conversion_rate')
    def _compute_operating_expenses_sovok_real(self):
        for rec in self:
            total_sovok = rec.total_sovok or 0.0
            percent = rec.percent_from_expense_rule or 0.0
            correction = rec.correction or 0.0
            real_rate = rec.real_post_conversion_rate or 0.0

            if total_sovok == 0 or real_rate == 0:
                rec.operating_expenses_sovok_real = 0.0
            else:
                rec.operating_expenses_sovok_real = ((percent - correction) * total_sovok) / real_rate

    operating_expenses_sovok_real_usd = fields.Float(
        string='Расход на операционную деятельность Совок реал $',
        compute='_compute_operating_expenses_sovok_real_usd',
        store=True,
        tracking=True
    )

    @api.depends('operating_expenses_sovok_real', 'payer_cross_rate_usd_auto')
    def _compute_operating_expenses_sovok_real_usd(self):
        for rec in self:
            rec.operating_expenses_sovok_real_usd = (rec.operating_expenses_sovok_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    operating_expenses_sovok_real_rub = fields.Float(
        string='Расход на операционную деятельность Совок реал ₽',
        compute='_compute_operating_expenses_sovok_real_rub',
        store=True,
        tracking=True
    )

    @api.depends('operating_expenses_sovok_real_usd', 'payer_cross_rate_rub')
    def _compute_operating_expenses_sovok_real_rub(self):
        for rec in self:
            rec.operating_expenses_sovok_real_rub = (rec.operating_expenses_sovok_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)


    # ==========================================================================
    # DONE добавить поле купили валюту совок партнер
    kupili_valyutu_sovok_partner = fields.Float(
    string='Купили валюту Совок Партнер',
    compute='_compute_kupili_valyutu_sovok_partner',
    store=True,
    digits=(16, 2),
    tracking=True
    )

    @api.depends('total_sovok', 'payment_order_rf_sovok', 'partner_post_conversion_rate')
    def _compute_kupili_valyutu_sovok_partner(self):
        for rec in self:
            total_sovok = rec.total_sovok or 0.0
            payment_rf_sovok = rec.payment_order_rf_sovok or 0.0
            partner_rate = rec.partner_post_conversion_rate or 0.0
            if partner_rate == 0.0:
                rec.kupili_valyutu_sovok_partner = 0.0
            else:
                rec.kupili_valyutu_sovok_partner = (total_sovok - payment_rf_sovok) / partner_rate


    # DONE добавить поле Купили валюту Совок Реал ({Итого Совок}-{Платежка РФ Совок})/{Курс после конвертации реал}
    kupili_valyutu_sovok_real = fields.Float(
    string='Купили валюту Совок Реал',
    compute='_compute_kupili_valyutu_sovok_real',
    store=True,
    digits=(16, 2),
    tracking=True
    )

    @api.depends('total_sovok', 'payment_order_rf_sovok', 'real_post_conversion_rate')
    def _compute_kupili_valyutu_sovok_real(self):
        for rec in self:
            total_sovok = rec.total_sovok or 0.0
            payment_rf_sovok = rec.payment_order_rf_sovok or 0.0
            real_rate = rec.real_post_conversion_rate or 0.0
            if real_rate == 0.0:
                rec.kupili_valyutu_sovok_real = 0.0
            else:
                rec.kupili_valyutu_sovok_real = (total_sovok - payment_rf_sovok) / real_rate

                
    # DONE добавить поле Купили валюту Совок Реал $ {Купили валюту Совок Реал}*{Кросс-курс Плательщика $ авто}
    kupili_valyutu_sovok_real_usd = fields.Float(
        string='Купили валюту Совок Реал $',
        compute='_compute_kupili_valyutu_sovok_real_usd',
        store=True,
        digits=(16, 2),
        tracking=True
    )

    @api.depends('kupili_valyutu_sovok_real', 'payer_cross_rate_usd_auto')
    def _compute_kupili_valyutu_sovok_real_usd(self):
        for rec in self:
            kupili_valyutu = rec.kupili_valyutu_sovok_real or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            rec.kupili_valyutu_sovok_real_usd = kupili_valyutu * cross_rate


    # DONE добавить поле Купили валюту Совок Реал ₽ {Купили валюту Совок Реал $}*{Кросс-курс Плательщика ₽}
    kupili_valyutu_sovok_real_rub = fields.Float(
        string='Купили валюту Совок Реал ₽',
        compute='_compute_kupili_valyutu_sovok_real_rub',
        store=True,
        digits=(16, 2),
        tracking=True
    )

    @api.depends('kupili_valyutu_sovok_real_usd', 'payer_cross_rate_rub')
    def _compute_kupili_valyutu_sovok_real_rub(self):
        for rec in self:
            rec.kupili_valyutu_sovok_real_rub = (rec.kupili_valyutu_sovok_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)




    # DONE добавить поле Расход платежа в $ Совок партнер {Расход платежа Совок}*{Кросс-курс Плательщика $ авто}+{Фикс за сделку $ (from Прайс лист)}
    payment_cost_sovok_partner_usd = fields.Float(
        string='Расход платежа в $ Совок партнер',
        compute='_compute_payment_cost_sovok_partner_usd',
        store=True,
        digits=(16, 2),
        tracking=True
    )

    @api.depends('payment_cost_sovok', 'payer_cross_rate_usd_auto', 'price_list_carrying_out_fixed_deal_fee')
    def _compute_payment_cost_sovok_partner_usd(self):
        for rec in self:
            payment_cost = rec.payment_cost_sovok or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            fixed_fee = rec.price_list_carrying_out_fixed_deal_fee or 0.0
            rec.payment_cost_sovok_partner_usd = (payment_cost * cross_rate) + fixed_fee


    # DONE добавить поле Расход платежа в $ Совок реал
    payment_cost_sovok_real_usd = fields.Float(
    string='Расход платежа в $ Совок реал',
    compute='_compute_payment_cost_sovok_real_usd',
    store=True,
    digits=(16, 2),
    tracking=True,
    )

    @api.depends('payment_cost_sovok', 'payer_cross_rate_usd_auto', 'price_list_carrying_out_fixed_deal_fee')
    def _compute_payment_cost_sovok_real_usd(self):
        for rec in self:
            payment_cost = rec.payment_cost_sovok or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            fixed_fee = rec.price_list_carrying_out_fixed_deal_fee or 0.0
            rec.payment_cost_sovok_real_usd = payment_cost * cross_rate + fixed_fee

    # DONE добавить поле Расход платежа в ₽ Совок реал
    payment_cost_sovok_real_rub = fields.Float(
    string='Расход платежа в ₽ Совок реал',
    compute='_compute_payment_cost_sovok_real_rub',
    store=True,
    digits=(16, 2),
    tracking=True,
    )

    @api.depends('payment_cost_sovok_real_usd', 'payer_cross_rate_rub')
    def _compute_payment_cost_sovok_real_rub(self):
        for rec in self:
            usd_cost = rec.payment_cost_sovok_real_usd or 0.0
            rub_rate = rec.payer_cross_rate_rub or 0.0
            rec.payment_cost_sovok_real_rub = usd_cost * rub_rate




    # DONE добавить поле Себестоимость денег Совок реал
    sebestoimost_denej_sovok_real = fields.Float(
    string='Себестоимость денег Совок реал',
    compute='_compute_sebestoimost_denej_sovok_real',
    store=True,
    digits=(16, 2),
    tracking=True,
    )

    @api.depends(
    'agent_id',
    'date_days',
    'money_cost_rule_extra_days',
    'money_cost_rule_credit_period',
    'money_cost_rule_credit_rate',
    'kupili_valyutu_sovok_real'
    )
    def _compute_sebestoimost_denej_sovok_real(self):
        for rec in self:
            if rec.agent_id and rec.agent_id.name == "Тезер":
                rec.sebestoimost_denej_sovok_real = 0.0
            else:
                date_days = rec.date_days or 0
                extra_days = rec.money_cost_rule_extra_days or 0
                credit_period = rec.money_cost_rule_credit_period or 0
                credit_rate = rec.money_cost_rule_credit_rate or 0.0
                kupili_valyutu = rec.kupili_valyutu_sovok_real or 0.0

                if credit_period == 0:
                    rec.sebestoimost_denej_sovok_real = 0.0
                else:
                    total_days = date_days + extra_days
                    rec.sebestoimost_denej_sovok_real = (
                        (total_days / credit_period) * credit_rate * kupili_valyutu
                    )



    # DONE добавить поле Себестоимость денег Совок реал $
    sebestoimost_denej_sovok_real_usd = fields.Float(
    string='Себестоимость денег Совок реал $',
    compute='_compute_sebestoimost_denej_sovok_real_usd',
    store=True,
    digits=(16, 2),
    tracking=True,
    )

    @api.depends('sebestoimost_denej_sovok_real', 'payer_cross_rate_usd_auto')
    def _compute_sebestoimost_denej_sovok_real_usd(self):
        for rec in self:
            sebestoimost = rec.sebestoimost_denej_sovok_real or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            rec.sebestoimost_denej_sovok_real_usd = sebestoimost * cross_rate



    # DONE добавить поле Себестоимость денег Совок реал ₽
    sebestoimost_denej_sovok_real_rub = fields.Float(
    string='Себестоимость денег Совок реал ₽',
    compute='_compute_sebestoimost_denej_sovok_real_rub',
    store=True,
    digits=(16, 2),
    tracking=True,
    )

    @api.depends('sebestoimost_denej_sovok_real_usd', 'payer_cross_rate_rub')
    def _compute_sebestoimost_denej_sovok_real_rub(self):
        for rec in self:
            usd_cost = rec.sebestoimost_denej_sovok_real_usd or 0.0
            rub_rate = rec.payer_cross_rate_rub or 0.0
            rec.sebestoimost_denej_sovok_real_rub = usd_cost * rub_rate





    # DONE добавить поле Фин рез Совок Партнер
    # DONE добавить поле Фин рез Совок реал
    # DONE добавить поле Фин рез Совок реал $
    # DONE добавить поле Фин рез Совок реал ₽

    fin_res_sovok_partner = fields.Float(
        string='Фин рез Совок Партнер',
        compute='_compute_fin_res_sovok_partner',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    fin_res_sovok_real = fields.Float(
        string='Фин рез Совок реал',
        compute='_compute_fin_res_sovok_real',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    fin_res_sovok_real_usd = fields.Float(
        string='Фин рез Совок реал $',
        compute='_compute_fin_res_sovok_real_usd',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    fin_res_sovok_real_rub = fields.Float(
        string='Фин рез Совок реал ₽',
        compute='_compute_fin_res_sovok_real_rub',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    # Computation methods for the new fields
    @api.depends(
        'kupili_valyutu_sovok_partner',
        'payment_cost_sovok',
        'sebestoimost_denej_sovok_partner',
        'hidden_partner_commission',
        'operating_expenses_sovok_partner',
        'amount',
        'payer_profit_currency'
    )
    def _compute_fin_res_sovok_partner(self):
        for rec in self:
            rec.fin_res_sovok_partner = (
                (rec.kupili_valyutu_sovok_partner or 0.0) -
                (rec.payment_cost_sovok or 0.0) -
                (rec.sebestoimost_denej_sovok_partner or 0.0) -
                (rec.hidden_partner_commission or 0.0) -
                (rec.operating_expenses_sovok_partner or 0.0) -
                (rec.amount or 0.0) -
                (rec.payer_profit_currency or 0.0)
            )

    @api.depends(
        'kupili_valyutu_sovok_real',
        'payment_cost_sovok',
        'sebestoimost_denej_sovok_real',
        'hidden_partner_commission_real',
        'operating_expenses_sovok_real',
        'amount',
        'payer_profit_currency'
    )
    def _compute_fin_res_sovok_real(self):
        for rec in self:
            rec.fin_res_sovok_real = (
                (rec.kupili_valyutu_sovok_real or 0.0) -
                (rec.payment_cost_sovok or 0.0) -
                (rec.sebestoimost_denej_sovok_real or 0.0) -
                (rec.hidden_partner_commission_real or 0.0) -
                (rec.operating_expenses_sovok_real or 0.0) -
                (rec.amount or 0.0) -
                (rec.payer_profit_currency or 0.0)
            )

    @api.depends('fin_res_sovok_real', 'payer_cross_rate_usd_auto')
    def _compute_fin_res_sovok_real_usd(self):
        for rec in self:
            rec.fin_res_sovok_real_usd = (
                (rec.fin_res_sovok_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)
            )

    @api.depends('fin_res_sovok_real_usd', 'payer_cross_rate_rub')
    def _compute_fin_res_sovok_real_rub(self):
        for rec in self:
            rec.fin_res_sovok_real_rub = (
                (rec.fin_res_sovok_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)
            )

    # ==========================================================================

    # GROUP: Не сгрупперованное
    payment_conditions = fields.Selection(
        [
            ('accred', 'Аккредитив'),
            ('prepayment', 'Предоплата'),
            ('postpayment', 'Постоплата'),
            ('escrow', 'Эскроу')
        ],
        string='Условия расчета',
        tracking=True,
    )
    deal_type = fields.Selection(
        [('import', 'Импорт'), ('export', 'Экспорт')],
        string='Вид сделки',
        tracking=True,
    )
    instruction_number = fields.Char(string='Номер поручения', tracking=True)
    instruction_signed_date = fields.Date(string='Подписано поручение', tracking=True)
    usd_equivalent = fields.Float(
        string='USD эквивалент',
        compute='_compute_usd_equivalent',
        store=True,
        tracking=True
    )
    jess_rate = fields.Float(string='Курс Джесс', tracking=True, digits=(16, 7))
    currency = fields.Selection(
        [
            ('rub', 'RUB'), ('rub_cashe', 'RUB КЭШ'),
            ('usd', 'USD'), ('usd_cashe', 'USD КЭШ'),
            ('usdt', 'USDT'),
            ('euro', 'EURO'), ('euro_cashe', 'EURO КЭШ'),
            ('cny', 'CNY'), ('cny_cashe', 'CNY КЭШ'),
            ('aed', 'AED'), ('aed_cashe', 'AED КЭШ'),
            ('thb', 'THB'), ('thb_cashe', 'THB КЭШ')
        ],
        string='Валюта',
        default='rub',
        tracking=True
    )
    currency_pair = fields.Selection(
        [
            ('usd_cny', 'USD/CNY'),
            ('cny_usd', 'CNY/USD'),
            ('euro_usd', 'EURO/USD'),
            ('usd_euro', 'USD/EURO'),
            ('aed_usd', 'AED/USD'),
            ('usd_aed', 'USD/AED'),
            ('thb_usd', 'THB/USD'),
            ('usd_thb', 'USD/THB')
        ],
        string='Валютная пара',
        tracking=True
    )
    cross_rate_usd_rub = fields.Float(string='Кросс-курс USD/RUB', tracking=True, digits=(16, 4))
    cross_rate_pair = fields.Float(string='Кросс-курс пары', tracking=True, digits=(16, 8))
    xe_rate = fields.Float(string='Курс XE', tracking=True, digits=(16, 8))
    conversion_expenses_rub = fields.Float(
        string='Расходы на конвертацию в рублях',
        compute='_compute_conversion_expenses',
        store=True,
        tracking=True
    )
    conversion_expenses_currency = fields.Float(
        string='Расходы на конвертацию в валюте',
        compute='_compute_conversion_expenses_currency',
        store=True,
        tracking=True
    )
    xe_rate_auto = fields.Char(
        string='Курс XE АВТО',
        compute='_compute_xe_rate_auto',
        store=True,
        tracking=True
    )
    real_cross_rate = fields.Float(
        string='Курс реальный (кросс)',
        compute='_compute_real_cross_rate',
        store=True,
        digits=(16, 4),
        tracking=True
    )
    amount = fields.Float(string='Сумма заявки', tracking=True, digits=(16, 3))
    vip_conditions = fields.Char(string='Условия VIP', tracking=True)
    price_list_profit_id = fields.Many2one(
        'amanat.price_list_payer_profit', 
        string='Прайс лист Плательщика Прибыль', 
        tracking=True,
        domain="[('payer_subagent_ids', 'in', subagent_payer_ids)]"
    )
    vip_commission = fields.Float(string='Комиссия VIP', digits=(16, 1), tracking=True)
    hidden_commission = fields.Float(string='Скрытая комиссия', tracking=True)
    bank_commission = fields.Float(string='Комиссия +% банка', tracking=True)
    accreditation_commission = fields.Float(string='Комиссия + аккред', tracking=True)
    escrow_commission = fields.Float(string='Комиссия + эскроу', tracking=True)
    rate_field = fields.Float(string='Курс', tracking=True)
    hidden_rate = fields.Float(string='Скрытый курс', tracking=True)
    conversion_percent = fields.Float(string='% Конвертации', tracking=True)
    conversion_ratio = fields.Float(
        string="% Конвертации соотношение",
        compute='_compute_conversion_ratio',
        store=True,
        tracking=True
    )

    @api.depends('cross_rate_pair', 'xe_rate')
    def _compute_conversion_ratio(self):
        for rec in self:
            if rec.cross_rate_pair and rec.xe_rate:
                rec.conversion_ratio = (rec.cross_rate_pair / rec.xe_rate) - 1
            else:
                rec.conversion_ratio = 0.0
    
    profit_rate = fields.Selection(
        [
            ('bank', 'Курс Банка'),
            ('xe', 'XE')
        ],
        string='Валютная пара',
        tracking=True
    )
    course_profitable = fields.Char(
        string='Какой курс выгоднее',
        compute='_compute_course_profitable',
        store=True,
        tracking=True
    )

    @api.depends('conversion_ratio', 'currency_pair')
    def _compute_course_profitable(self):
        # Список валютных пар, которые считаются "особенными"
        special_pairs = ['usd_cny', 'usd_aed', 'usd_thb', 'usd_euro']
        for rec in self:
            conv_ratio = rec.conversion_ratio or 0.0  # {% Конвертации соотношение}
            pair = (rec.currency_pair or '').lower()  # {Валютная пара}

            if conv_ratio == 0:
                rec.course_profitable = False  # Аналог BLANK()
                continue

            if (
                (pair in special_pairs and conv_ratio < 0) or
                (pair not in special_pairs and conv_ratio > 0)
            ):
                rec.course_profitable = "XE"
            else:
                rec.course_profitable = "Курс Банка"

    bank_select = fields.Selection(
        [
            ('1', 'Курс банка для этой сделки прибыльнее, укажите % Конвертации'),
        ],
        string='банка выгоднее',
        tracking=True,
        default='1'
    )
    xe_select = fields.Selection(
        [
            ('1', 'Курс XE для этой сделки прибыльнее, укажите % Конвертации'),
        ],
        string='XE',
        tracking=True,
        default='1'
    )
    conversion_auto = fields.Float(
        string="% Конвертации авто",
        compute='_compute_conversion_auto',
        store=True,
        tracking=True
    )

    @api.depends('conversion_percent', 'conversion_ratio')
    def _compute_conversion_auto(self):
        for rec in self:
            if rec.conversion_percent:
                rec.conversion_auto = rec.conversion_percent
            else:
                rec.conversion_auto = rec.conversion_ratio

    bank_cross_rate = fields.Float(string='Кросс-курс банка', tracking=True)
    plus_dollar = fields.Float(string='Надбавка в $', tracking=True)
    dollar_cross_rate = fields.Float(string='Кросс-курс $ к Валюте заявки', tracking=True)
    plus_currency = fields.Float(
        string='Надбавка в валюте заявки',
        compute='_compute_plus_currency',
        store=True,
        tracking=True
    )
    invoice_plus_percent = fields.Float(
        string='% надбавки от суммы инвойса',
        compute='_compute_invoice_plus_percent',
        store=True,
        tracking=True
    )
    reward_percent = fields.Float(
        string='% Вознаграждения',
        compute='_compute_reward_percent',
        store=True,
        tracking=True
    )
    hand_reward_percent = fields.Float(
        string='% Вознаграждения руками',
        tracking=True,
        digits=(16, 4)
    )
    equivalent_amount_usd = fields.Float(
        string='Сумма эквивалент $',
        compute='_compute_equivalent_amount_usd',
        store=True,
        tracking=True
    )

    @api.depends('xe_rate', 'amount')
    def _compute_equivalent_amount_usd(self):
        for rec in self:
            xe = rec.xe_rate or 0.0   # {Курс XE}
            amount = rec.amount or 0.0  # {Сумма заявки}
            if xe:
                rec.equivalent_amount_usd = xe * amount
            else:
                rec.equivalent_amount_usd = amount

    total_fact = fields.Float(
        string='Итого факт',
        compute='_compute_total_fact',
        store=True,
        tracking=True
    )
    rate_fixation_date = fields.Date(
        string='Дата фиксации курса',
        default=fields.Date.today,
        tracking=True
    )
    assignment_signed_sovcom = fields.Date(
        string='Подписано поручение (для Совкомбанка)',
        tracking=True,
    )
    calculated_percent = fields.Float(
        string='Рассчетный %',
        compute='_compute_calculated_percent',
        store=True,
        tracking=True
    )
    contract_reward = fields.Float(
        string='Вознаграждение по договору',
        compute='_compute_contract_reward',
        store=True,
        tracking=True
    )

    @api.depends('contragent_id.name', 'sovok_reward', 'sber_reward', 'client_reward')
    def _compute_contract_reward(self):
        for rec in self:
            contragent = (rec.contragent_id.name or '').lower()
            if 'совкомбанк' in contragent:
                rec.contract_reward = rec.sovok_reward or 0.0
            elif 'сбербанк' in contragent:
                rec.contract_reward = rec.sber_reward or 0.0
            else:
                rec.contract_reward = rec.client_reward or 0.0
                
    sum_from_extracts = fields.Float(
        string='Сумма (from Выписка разнос)', 
        compute='_compute_sum_from_extracts', 
        store=True, 
        tracking=True
    )

    @api.depends('extract_delivery_ids.amount')
    def _compute_sum_from_extracts(self):
        for rec in self:
            rec.sum_from_extracts = sum(rec.extract_delivery_ids.mapped('amount'))

    rate_real = fields.Float(
        string='Заявка по курсу реальный',
        compute='_compute_rate_real',
        store=True,
        tracking=True
    )
    agent_reward = fields.Float(
        string='Агентское вознаграждение',
        compute='_compute_agent_reward',
        store=True,
        tracking=True
    )
    actual_reward = fields.Float(
        string='Фактическое вознаграждение',
        compute='_compute_actual_reward',
        store=True,
        tracking=True
    )
    non_agent_reward = fields.Float(
        string='Агентское не наше',
        compute='_compute_non_agent_reward',
        store=True,
        tracking=True
    )
    agent_our_reward = fields.Float(
        string='Агентское наше',
        compute='_compute_agent_our_reward',
        store=True,
        tracking=True
    )
    total_reward = fields.Float(
        string='Общее вознаграждение',
        compute='_compute_total_reward',
        store=True,
        tracking=True
    )
    total_amount = fields.Float(
        string='ИТОГО',
        compute='_compute_total_amount',
        store=True,
        tracking=True
    )
    with_accreditive = fields.Boolean(string='С аккредитивом', tracking=True)
    received_initial_docs = fields.Boolean(string='Получили первичные документы', tracking=True)
    invoice_date = fields.Date(string='выставлен инвойс', tracking=True, default=fields.Date.today)
    agent_contract_date = fields.Date(string='подписан агент. / субагент. договор', tracking=True, default=fields.Date.today)
    bank_registration_date = fields.Date(string='поставлен на учет в банке', tracking=True, default=fields.Date.today)
    accreditive_open_date = fields.Date(string='Открыт аккредитив', tracking=True, default=fields.Date.today)
    supplier_currency_paid_date = fields.Date(string='оплачена валюта поставщику (импорт) / субагенту (экспорт)', tracking=True, default=fields.Date.today)
    payment_date = fields.Date(string='передано в оплату (импорт) / оплачена валюта (экспорт)', tracking=True, default=fields.Date.today)
    supplier_currency_received_date = fields.Date(string='получена валюта поставщиком (импорт) / субагентом (экспорт)', tracking=True)
    accreditive_revealed_date = fields.Date(string='аккредитив раскрыт', tracking=True)
    act_report_signed_date = fields.Date(string='подписан акт-отчет', tracking=True)
    deal_closed_date = fields.Date(string='сделка закрыта', tracking=True)
    deal_cycle_days = fields.Integer(string='Цикл сделки, дн', tracking=True)
    payment_purpose = fields.Text(string='Назначение платежа', tracking=True)
    subagent_ids = fields.Many2many('amanat.contragent', string='Субагент', compute='_compute_subagent_contragent_ids', store=True, tracking=True) # TODO возможно нужно будет поменять тип поля
    subagent_payer_ids = fields.Many2many('amanat.payer', string='Плательщик Субагента', tracking=True) # TODO возможно нужно будет поменять тип поля
    application_sequence = fields.Char(string='Порядковый номер заявления', tracking=True)
    subagent_docs_prepared_date = fields.Date(string='Подготовлены документы между агентом и субагентом (дата)', tracking=True)
    swift_received_date = fields.Date(string='Получен SWIFT', tracking=True)
    swift_103_requested_date = fields.Date(string='Запросили SWIFT 103', tracking=True)
    swift_199_requested_date = fields.Date(string='Запросили SWIFT 199', tracking=True)
    swift_103_received_date = fields.Date(string='Получили SWIFT 103', tracking=True)
    swift_199_received_date = fields.Date(string='Получили SWIFT 199', tracking=True)
    return_requested_date = fields.Date(string='Возврат запрошен', tracking=True)
    return_money_received_date = fields.Date(string='Деньги по возврату получены', tracking=True)
    swift_status = fields.Selection(
        [
            ('closed', 'заявка закрыта'),
            ('swift_received', 'SWIFT получен'),
            ('return', 'Возврат'),
            ('money_received', 'деньги у получателя'),
            ('swift_103_requested', 'SWIFT 103 запрошен'),
            ('application_sent', 'заявление отправлено'),
            ('swift_199_requested', 'SWIFT 199 запрошен')
        ],
        string='Статус SWIFT',
        tracking=True
    )
    is_money_stuck = fields.Boolean(string='Зависли деньги', tracking = True, default = False)
    problem_stage = fields.Selection(
        [
            ('1', 'Возврат с последующей отменой'),
            ('2', 'Возврат с повторной оплатой'),
            ('3', 'Деньги не сели поставщику'),
        ],
        string='Стадии проблемы',
        tracking=True
    )
    problem_comment = fields.Text(string='комментарии к заявкам по которым зависли деньги', tracking=True)
    currency_stuck = fields.Selection(
        [
            ('rub', 'RUB'), ('rub_cashe', 'RUB КЭШ'),
            ('usd', 'USD'), ('usd_cashe', 'USD КЭШ'),
            ('usdt', 'USDT'),
            ('euro', 'EURO'), ('euro_cashe', 'EURO КЭШ'),
            ('cny', 'CNY'), ('cny_cashe', 'CNY КЭШ'),
            ('aed', 'AED'), ('aed_cashe', 'AED КЭШ'),
            ('thb', 'THB'), ('thb_cashe', 'THB КЭШ')
        ],
        string='Какая валюта зависла?',
        tracking=True
    )
    sum_stuck = fields.Float(string='Сумма зависла', tracking=True)
    whose_mistake = fields.Selection(
        [
            ('manager', 'Менеджер'), ('client', 'Клиент'),
        ],
        string='Чья ошибка?',
        tracking=True
    )
    extract_delivery_ids = fields.Many2many(
        'amanat.extract_delivery',
        'amanat_zayavka_extract_delivery_rel',
        'zayavka_id',
        'extract_delivery_id',
        string="Выписка разнос", 
        tracking=True
    )
    # TODO узнать, надо добавить поле Банк Выписка (related на поле extract_delivery_ids.bank)
    payer_profit_currency = fields.Float(
        string='Прибыль Плательщика по валюте заявки',
        compute='_compute_payer_profit_currency',
        store=True,
        tracking=True
    )

    @api.depends('amount', 'price_list_profit_id.percent_accrual')
    def _compute_payer_profit_currency(self):
        for rec in self:
            percent = rec.price_list_profit_id.percent_accrual or 0.0
            rec.payer_profit_currency = rec.amount * percent

    price_list_percent_accrual = fields.Float(
        string='% Начисления (from Прайс листа Плательщика Прибыль)',
        related='price_list_profit_id.percent_accrual',
        store=True,
        readonly=True,
        tracking=True
    )
    zayavka_file = fields.Binary(string='Заявка', attachment=True)
    zayavka_link = fields.Char(string='Заявка ссылка', tracking=True)
    invoice_file = fields.Binary(string='Инвойс', attachment=True)
    invoice_link = fields.Char(string='Инвойс ссылка', tracking=True)
    assignment_file = fields.Binary(string='Поручение', attachment=True)
    assignment_link = fields.Char(string='Поручение ссылка', tracking=True)
    swift_file = fields.Binary(string='SWIFT', attachment=True)
    swift_link = fields.Char(string='SWIFT ссылка', tracking=True)
    swift103_file = fields.Binary(string='SWIFT 103', attachment=True)
    swift103_link = fields.Char(string='SWIFT 103 ссылка', tracking=True)
    swift199_file = fields.Binary(string='SWIFT 199', attachment=True)
    swift199_link = fields.Char(string='SWIFT 199 ссылка', tracking=True)
    report_file = fields.Binary(string='Акт-отчет', attachment=True)
    report_link = fields.Char(string='Акт-отчет ссылка', tracking=True)
    money_ran_out = fields.Boolean(string='Сели деньги', tracking=True, default=False)
    received_on_our_pc = fields.Float(string='Поступило на наш РС', tracking=True)
    agent_on_pc = fields.Float(string='Агентское на РС', tracking=True)
    calculation = fields.Float(
        string='Calculation',
        compute='_compute_calculation',
        store=True,
        tracking=True
    )

    @api.depends('total_amount', 'received_on_our_pc', 'agent_on_pc')
    def _compute_calculation(self):
        for rec in self:
            rec.calculation = (rec.total_amount or 0.0) - (rec.received_on_our_pc or 0.0) - (rec.agent_on_pc or 0.0)
    
    bank = fields.Selection(
        [
            ('mti', 'МТИ'),
            ('sberbank', 'Сбербанк'),
            ('sovcombank', 'Совкомбанк'),
            ('morskoy', 'Морской'),
            ('ingosstrah', 'Ингосстрах'),
            ('rosbank', 'Росбанк'),
            ('sdm', 'СДМ банк'),
            ('vtb', 'ВТБ'),
            ('nbs', 'НБС'),
            ('zenit', 'Зенит'),
            ('alpha', 'Альфа банк'),
            ('t-bank', 'Т-Банк'),
        ],
        string='Банк',
        tracking=True
    )
    zayavka_mistake = fields.Text(string='Ошибки по заявке', tracking=True)
    date_received_on_pc12 = fields.Date(
        string='Дата поступления на PC12',
        tracking=True
    )
    date_agent_on_pc = fields.Date(
        string='Дата агентского на PC',
        tracking=True,
    )
    waiting_for_replenishment = fields.Float(
        string='Ожидаем пополнения',
        compute='_compute_waiting_for_replenishment',
        store=True,
        tracking=True
    )

    @api.depends('contragent_id.name', 'total_sovok_management', 'total_sber_management', 'total_client_management', 'sum_from_extracts')
    def _compute_waiting_for_replenishment(self):
        for rec in self:
            contragent_name = (rec.contragent_id.name or '').strip().lower()
            sum_extracts = rec.sum_from_extracts or 0.0

            if 'совкомбанк' in contragent_name:
                value = (rec.total_sovok_management or 0.0) - sum_extracts
            elif 'сбербанк' in contragent_name:
                value = (rec.total_sber_management or 0.0) - sum_extracts
            else:
                value = (rec.total_client_management or 0.0) - sum_extracts

            rec.waiting_for_replenishment = value
    
    deal_amount_received = fields.Selection(
        [
            ('yes', 'Да'),
            ('no', 'нет')
        ],
        string='Пришла ли сумма сделки?',
        compute='_compute_deal_amount_received',
        store=True,
        tracking=True
    )

    @api.depends('extract_delivery_ids', 'application_amount_rub_contract', 'sum_from_extracts')
    def _compute_deal_amount_received(self):
        for rec in self:
            # Проверка на пустоту Many2many: есть ли хоть одна запись
            has_extracts = bool(rec.extract_delivery_ids)
            contract_amount = rec.application_amount_rub_contract or 0.0
            extracts_sum = rec.sum_from_extracts or 0.0

            if has_extracts and contract_amount == extracts_sum:
                rec.deal_amount_received = 'yes'
            else:
                rec.deal_amount_received = 'no'

    total_amount_received = fields.Selection(
        [
            ('yes', 'Да'),
            ('no', 'нет')
        ],
        string='Пришла ли сумма итог?',
        compute='_compute_total_amount_received',
        store=True,
        tracking=True
    )

    @api.depends('extract_delivery_ids', 'sum_from_extracts', 'total_amount')
    def _compute_total_amount_received(self):
        for rec in self:
            # Проверка наличия выписок
            has_extracts = bool(rec.extract_delivery_ids)
            sum_extracts = rec.sum_from_extracts or 0.0
            total = rec.total_amount or 0.0

            if has_extracts and sum_extracts == total:
                rec.total_amount_received = 'yes'
            else:
                rec.total_amount_received = 'no'
                
    order_ids = fields.Many2many(
        'amanat.order',           # Модель ордера (замени на нужную тебе, если другая)
        'amanat_zayavka_order_rel',  # Название связующей таблицы
        'zayavka_id',                # Имя поля для заявки
        'order_id',                  # Имя поля для ордера
        string='Ордеры',
        tracking=True
    )
    sum_from_extracts = fields.Float(
        string='Сумма (from Выписка разнос)', 
        compute='_compute_sum_from_extracts', 
        store=True, 
        tracking=True
    )

    @api.depends('extract_delivery_ids.amount')
    def _compute_sum_from_extracts(self):
        for rec in self:
            # extract_delivery_ids — это Many2many на amanat.extract_delivery
            rec.sum_from_extracts = sum(rec.extract_delivery_ids.mapped('amount'))  # amount — это поле "Сумма" в выписке
    
    error_sovok = fields.Float(
        string='Ошибка Совок',
        compute='_compute_error_sovok',
        store=True,
        tracking=True
    )

    @api.depends('overall_sovok_percent', 'calculated_percent')
    def _compute_error_sovok(self):
        for rec in self:
            # Проверяем, чтобы знаменатель не был нулём
            if rec.calculated_percent:
                rec.error_sovok = (rec.overall_sovok_percent - rec.calculated_percent) / rec.calculated_percent
            else:
                rec.error_sovok = 0.0  # Или False, если нужен BLANK

    error_sber = fields.Float(
        string='Ошибка Сбер',
        compute='_compute_error_sber',
        store=True,
        tracking=True
    )

    @api.depends('overall_sber_percent', 'conversion_auto')
    def _compute_error_sber(self):
        for rec in self:
            if rec.conversion_auto:
                rec.error_sber = (rec.overall_sber_percent - rec.conversion_auto) / rec.conversion_auto
            else:
                rec.error_sber = 0.0  # Или False, если хотите пустое

    error_in_rate = fields.Selection(
        [
            ('error', 'Ошибка в курсе')
        ],
        string='Ошибка в курсе',
        store=True,
        tracking=True
    )
    error_in_bank_rate = fields.Selection(
        [
            ('error', 'Ошибка в курсе банка')
        ],
        string='Ошибка в курсе банка',
        store=True,
        tracking=True
    )
    error_in_xe_rate = fields.Selection(
        [
            ('error', 'Ошибка в курсе XE')
        ],
        string='Ошибка в курсе XE',
        store=True,
        tracking=True
    )
    price_list_carrying_out_id = fields.Many2one(
        'amanat.price_list_payer_carrying_out',
        string='Прайс лист',
        tracking=True,
        domain="[('payer_partner', 'in', subagent_payer_ids)]"
    )
    price_list_carrying_out_accrual_percentage = fields.Float(
        string='% Начисления (from Прайс лист)',
        related='price_list_carrying_out_id.accrual_percentage',
        store=True,
        readonly=True,
        tracking=True,
    )
    price_list_carrying_out_fixed_deal_fee = fields.Float(
        string='Фикс за сделку $ (from Прайс лист)',
        related='price_list_carrying_out_id.fixed_deal_fee',
        store=True,
        readonly=True,
        tracking=True,
    )
    payment_order_rule_id = fields.Many2one(
        'amanat.payment_order_rule',
        string='Правило платежка',
        tracking=True
    )
    percent_from_payment_order_rule = fields.Float(
        string="Процент (from Правило платежка)",
        related='payment_order_rule_id.percent',
        store=True,
        tracking=True
    )
    
    partner_post_conversion_rate = fields.Float(
        string='Курс после конвертации партнер',
        compute='_compute_partner_post_conversion_rate',
        store=True,
        tracking=True
    )

    @api.depends('currency', 'best_rate')
    def _compute_partner_post_conversion_rate(self):
        for rec in self:
            if rec.currency == 'usd':  # у вас значение в Selection 'usd'
                rec.partner_post_conversion_rate = (rec.best_rate or 0.0) * 1.005
            else:
                rec.partner_post_conversion_rate = (rec.best_rate or 0.0) * 1.005 * 1.005

    payer_cross_rate_usd = fields.Float(
        string='Кросс-курс Плательщика $',
        digits=(16, 4),
        tracking=True
    )
    payer_cross_rate_usd_auto = fields.Float(
        string='Кросс-курс Плательщика $ авто',
        compute='_compute_payer_cross_rate_usd_auto',
        store=True,
        digits=(16, 4),
        tracking=True
    )

    @api.depends('payer_cross_rate_usd', 'xe_rate', 'currency')
    def _compute_payer_cross_rate_usd_auto(self):
        for rec in self:
            payer_cross = rec.payer_cross_rate_usd
            xe = rec.xe_rate
            currency = (rec.currency or '').lower()  # чтобы одинаково работало для 'usd' и 'usd_cashe'

            if (not payer_cross) and (not xe) and (currency in ['usd', 'usd_cashe']):
                rec.payer_cross_rate_usd_auto = 1
            elif payer_cross:
                rec.payer_cross_rate_usd_auto = payer_cross
            else:
                rec.payer_cross_rate_usd_auto = xe or 0.0

    real_post_conversion_rate = fields.Float(
        string='Курс после конвертации реал',
        compute='_compute_real_post_conversion_rate',
        store=True,
        digits=(16, 6),
        tracking=True
    )

    @api.depends('jess_rate', 'payer_cross_rate_usd_auto')
    def _compute_real_post_conversion_rate(self):
        for rec in self:
            rec.real_post_conversion_rate = (rec.jess_rate or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    real_post_conversion_rate_usd = fields.Float(
        string='Курс после конвертации реал $',
        compute='_compute_real_post_conversion_rate_usd',
        store=True,
        digits=(16, 6),
        tracking=True
    )

    @api.depends('real_post_conversion_rate', 'payer_cross_rate_usd_auto')
    def _compute_real_post_conversion_rate_usd(self):
        for rec in self:
            rec.real_post_conversion_rate_usd = (rec.real_post_conversion_rate or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    payer_cross_rate_rub = fields.Float(
        string='Кросс-курс Плательщика ₽',
        compute='_compute_payer_cross_rate_rub',
        store=True,
        digits=(16, 6),
        tracking=True
    )

    @api.depends('jess_rate')
    def _compute_payer_cross_rate_rub(self):
        for rec in self:
            rec.payer_cross_rate_rub = rec.jess_rate or 0.0

    real_post_conversion_rate_rub = fields.Float(
        string='Курс после конвертации реал ₽',
        compute='_compute_real_post_conversion_rate_rub',
        store=True,
        digits=(16, 6),
        tracking=True
    )

    @api.depends('real_post_conversion_rate_usd', 'payer_cross_rate_rub')
    def _compute_real_post_conversion_rate_rub(self):
        for rec in self:
            rec.real_post_conversion_rate_rub = (rec.real_post_conversion_rate_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    payer_profit_usd = fields.Float(
        string='Прибыль плательщика $',
        compute='_compute_payer_profit_usd',
        store=True,
        tracking=True
    )

    @api.depends('payer_profit_currency', 'payer_cross_rate_usd_auto', 'price_list_profit_id.fixed_fee')
    def _compute_payer_profit_usd(self):
        for rec in self:
            profit = (rec.payer_profit_currency or 0.0)
            cross_rate = (rec.payer_cross_rate_usd_auto or 0.0)
            fix_fee = (rec.price_list_profit_id.fixed_fee or 0.0)
            if cross_rate:
                rec.payer_profit_usd = profit * cross_rate + fix_fee
            else:
                rec.payer_profit_usd = fix_fee  # или 0.0, если совсем не надо считать без курса

    payer_profit_rub = fields.Float(
        string='Прибыль плательщика ₽',
        compute='_compute_payer_profit_rub',
        store=True,
        tracking=True
    )

    @api.depends('payer_profit_usd', 'payer_cross_rate_rub')
    def _compute_payer_profit_rub(self):
        for rec in self:
            rec.payer_profit_rub = (rec.payer_profit_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)
    
    date_received_on_pc_auto = fields.Char(
        string="Дата поступления на PC АВТО",
        compute='_compute_date_received_on_pc_auto',
        store=True,
        tracking=True
    )

    @api.depends('extract_delivery_ids.date')
    def _compute_date_received_on_pc_auto(self):
        for rec in self:
            dates = rec.extract_delivery_ids.mapped('date')
            # фильтруем пустые
            dates = [d for d in dates if d]
            # форматируем даты в дд.мм.гггг
            date_strs = [fields.Date.to_string(d) for d in dates]
            date_strs = [
                f"{d[8:10]}.{d[5:7]}.{d[0:4]}"
                for d in date_strs if d and len(d) == 10
            ]
            rec.date_received_on_pc_auto = ', '.join(date_strs) if date_strs else False

    date_received_on_pc_payment = fields.Date(
        string="Дата поступления на РС расчет",
        tracking=True,
    )

    date_received_tezera = fields.Date(
        string="Дата поступления ТЕЗЕРА",
        tracking=True,
    )

    date_days = fields.Integer(
        string='Дата', 
        compute='_compute_date_days',
        store=True
    )

    @api.depends(
        'currency',
        'taken_in_work_date',
        'deal_closed_date',
        'contragent_id',
        'date_received_on_pc_payment',
        'assignment_signed_sovcom',
        'rate_fixation_date'
    )
    def _compute_date_days(self):
        for rec in self:
            # Если валюта не из списка — по общей логике
            currency_code = (rec.currency or '').strip().lower()
            if currency_code not in ['usd', 'euro', 'aed', 'cny', 'rub', 'thb']:
                if rec.taken_in_work_date and rec.deal_closed_date:
                    rec.date_days = (rec.deal_closed_date - rec.taken_in_work_date).days
                else:
                    rec.date_days = 1
            else:
                if (rec.contragent_id.name or '').strip() == 'Совкомбанк':
                    if rec.date_received_on_pc_payment and rec.assignment_signed_sovcom:
                        rec.date_days = (rec.date_received_on_pc_payment - rec.assignment_signed_sovcom).days
                    else:
                        rec.date_days = 0
                else:
                    if rec.date_received_on_pc_payment and rec.rate_fixation_date:
                        rec.date_days = (rec.date_received_on_pc_payment - rec.rate_fixation_date).days
                    else:
                        rec.date_days = 0

    # DONE добавить поле Себестоимость денег Совок партнер
    sebestoimost_denej_sovok_partner = fields.Float(
        string='Себестоимость денег Совок партнер',
        compute='_compute_sebestoimost_denej_sovok_partner',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    @api.depends('date_days', 'kupili_valyutu_sovok_partner')
    def _compute_sebestoimost_denej_sovok_partner(self):
        for rec in self:
            date_days = rec.date_days or 0
            kupili_valyutu = rec.kupili_valyutu_sovok_partner or 0.0
            rec.sebestoimost_denej_sovok_partner = ((date_days + 1) / 25) * 0.04 * kupili_valyutu



    money_cost_rule_id = fields.Many2one(
        'amanat.money_cost_rule',
        string='Правило Себестоимость денег',
        tracking=True
    )
    money_cost_rule_credit_rate = fields.Float(
        string="Ставка по кредиту (from Правило Себестоимость денег)",
        related='money_cost_rule_id.credit_rate',
        store=True,
        tracking=True
    )
    money_cost_rule_credit_period = fields.Integer(
        string="Кредитный период (from Правило Себестоимость денег)",
        related='money_cost_rule_id.credit_period',
        store=True,
        tracking=True
    )
    money_cost_rule_extra_days = fields.Integer(
        string="Колво доп дней (from Правило Себестоимость денег)",
        related='money_cost_rule_id.extra_days',
        store=True,
        tracking=True
    )
    expense_rule_id = fields.Many2one(
        'amanat.expense_rule',
        string='Правило расход',
        tracking=True
    )
    percent_from_expense_rule = fields.Float(
        string="Процент (from Правило расход)",
        related='expense_rule_id.percent',
        store=True,
        tracking=True
    )
    correction = fields.Float(
        string='Корректировка',
        digits=(16, 4),
        tracking=True,
    )
    price_list_partners_id = fields.Many2one(
        'amanat.price_list_partners', string='Прайс лист Партнеры'
    )
    price_list_partners_id_accrual_percentage = fields.Float(
        string='% Начисления (from Прайс лист Партнеры)',
        related='price_list_partners_id.accrual_percentage',
        store=True,
        readonly=True,
        tracking=True
    )
    price_list_partners_id_fixed_deal_fee = fields.Float(
        string='Фикс за сделку $ (from Прайс лист Партнеры)',
        related='price_list_partners_id.fixed_deal_fee',
        store=True,
        readonly=True,
        tracking=True
    )
    price_list_partners_id_2 = fields.Many2one(
        'amanat.price_list_partners', string='Прайс лист Партнеры 2'
    )
    price_list_partners_id_2_accrual_percentage = fields.Float(
        string='% Начисления (from Прайс лист Партнеры 2)',
        related='price_list_partners_id_2.accrual_percentage',
        store=True,
        readonly=True,
        tracking=True
    )
    price_list_partners_id_2_fixed_deal_fee = fields.Float(
        string='Фикс за сделку $ (from Прайс лист Партнеры 2)',
        related='price_list_partners_id_2.fixed_deal_fee',
        store=True,
        readonly=True,
        tracking=True
    )
    price_list_partners_id_3 = fields.Many2one(
        'amanat.price_list_partners', string='Прайс лист Партнеры 3'
    )
    price_list_partners_id_3_accrual_percentage = fields.Float(
        string='% Начисления (from Прайс лист Партнеры 3)',
        related='price_list_partners_id_3.accrual_percentage',
        store=True,
        readonly=True,
        tracking=True
    )
    price_list_partners_id_3_fixed_deal_fee = fields.Float(
        string='Фикс за сделку $ (from Прайс лист Партнеры 3)',
        related='price_list_partners_id_3.fixed_deal_fee',
        store=True,
        readonly=True,
        tracking=True
    )
    price_list_partners_id_4 = fields.Many2one(
        'amanat.price_list_partners', string='Прайс лист Партнеры 4'
    )
    price_list_partners_id_4_accrual_percentage = fields.Float(
        string='% Начисления (from Прайс лист Партнеры 4)',
        related='price_list_partners_id_4.accrual_percentage',
        store=True,
        readonly=True,
        tracking=True
    )
    price_list_partners_id_4_fixed_deal_fee = fields.Float(
        string='Фикс за сделку $ (from Прайс лист Партнеры 4)',
        related='price_list_partners_id_4.fixed_deal_fee',
        store=True,
        readonly=True,
        tracking=True
    )
    price_list_partners_id_5 = fields.Many2one(
        'amanat.price_list_partners', string='Прайс лист Партнеры 5'
    )
    price_list_partners_id_5_accrual_percentage = fields.Float(
        string='% Начисления (from Прайс лист Партнеры 5)',
        related='price_list_partners_id_5.accrual_percentage',
        store=True,
        readonly=True,
        tracking=True
    )
    price_list_partners_id_5_fixed_deal_fee = fields.Float(
        string='Фикс за сделку $ (from Прайс лист Партнеры 5)',
        related='price_list_partners_id_5.fixed_deal_fee',
        store=True,
        readonly=True,
        tracking=True
    )
    hidden_partner_commission = fields.Float(
        string='Скрытая комиссия Партнера',
        compute='_compute_hidden_partner_commission',
        store=True,
        tracking=True
    )

    @api.depends(
        'contragent_id.name',
        'rate_real',
        'application_amount_rub_contract',
        'price_list_partners_id_accrual_percentage',
        'price_list_partners_id_2_accrual_percentage',
        'price_list_partners_id_3_accrual_percentage',
        'price_list_partners_id_4_accrual_percentage',
        'price_list_partners_id_5_accrual_percentage',
        'partner_post_conversion_rate',
        'non_our_client_reward'
    )
    def _compute_hidden_partner_commission(self):
        for rec in self:
            contragent = (rec.contragent_id.name or '').strip().lower()
            partner_rate = rec.partner_post_conversion_rate or 1  # На всякий случай, чтобы не делить на ноль

            # Сумма начислений
            accrual_sum = (
                (rec.price_list_partners_id_accrual_percentage or 0.0) +
                (rec.price_list_partners_id_2_accrual_percentage or 0.0) +
                (rec.price_list_partners_id_3_accrual_percentage or 0.0) +
                (rec.price_list_partners_id_4_accrual_percentage or 0.0) +
                (rec.price_list_partners_id_5_accrual_percentage or 0.0)
            )

            if 'совкомбанк' in contragent:
                value = (rec.rate_real or 0.0) * accrual_sum / partner_rate if partner_rate else 0.0
            elif 'сбербанк' in contragent:
                value = (rec.application_amount_rub_contract or 0.0) * accrual_sum / partner_rate if partner_rate else 0.0
            else:
                value = (rec.non_our_client_reward or 0.0) / partner_rate if partner_rate else 0.0

            rec.hidden_partner_commission = value

    hidden_partner_commission_real = fields.Float(
        string='Скрытая комиссия Партнера Реал',
        compute='_compute_hidden_partner_commission_real',
        store=True,
        tracking=True
    )

    @api.depends(
        'contragent_id.name',
        'rate_real',
        'price_list_partners_id_accrual_percentage',
        'jess_rate',
        'application_amount_rub_contract',
        'non_our_client_reward'
    )
    def _compute_hidden_partner_commission_real(self):
        for rec in self:
            contragent = (rec.contragent_id.name or '').strip().lower()
            jess_rate = rec.jess_rate or 1  # На всякий случай, чтобы не делить на ноль

            accrual = rec.price_list_partners_id_accrual_percentage or 0.0

            if 'совкомбанк' in contragent:
                value = (rec.rate_real or 0.0) * accrual / jess_rate if jess_rate else 0.0
            elif 'сбербанк' in contragent:
                value = (rec.application_amount_rub_contract or 0.0) * accrual / jess_rate if jess_rate else 0.0
            else:
                value = (rec.non_our_client_reward or 0.0) / jess_rate if jess_rate else 0.0

            rec.hidden_partner_commission_real = value

    hidden_partner_commission_real_usd = fields.Float(
        string='Скрытая комиссия Партнера Реал $',
        compute='_compute_hidden_partner_commission_real_usd',
        store=True,
        tracking=True
    )

    @api.depends('hidden_partner_commission_real', 'payer_cross_rate_usd_auto')
    def _compute_hidden_partner_commission_real_usd(self):
        for rec in self:
            value = (rec.hidden_partner_commission_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)
            rec.hidden_partner_commission_real_usd = value

    hidden_partner_commission_real_rub = fields.Float(
        string='Скрытая комиссия Партнера Реал ₽',
        compute='_compute_hidden_partner_commission_real_rub',
        store=True,
        tracking=True
    )

    @api.depends('hidden_partner_commission_real_usd', 'payer_cross_rate_rub')
    def _compute_hidden_partner_commission_real_rub(self):
        for rec in self:
            value = (rec.hidden_partner_commission_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)
            rec.hidden_partner_commission_real_rub = value

    send_to_reconciliation = fields.Boolean(
        string="Отправить в Сверку",
        tracking=True,
        default=False,
    )
    export_agent_flag = fields.Boolean(string="Экспорт/Убираем агентское", tracking=True, default=False)
    fin_entry_check = fields.Boolean(
        string="Галочка вход фин",
        tracking=True,
        default=False,
    )
    for_khalida_temp = fields.Boolean(
        string="Для Халиды ( потом удалить )",
        tracking=True,
        default=False,
    )
    hide_in_dashboard = fields.Boolean(
        string="Не отображать в дашборде",
        tracking=True,
        default=False,
    )
    status_range_copy = fields.Selection(
        [('yes', 'Да'), ('no', 'Нет')],
        string='Статус диапазона copy',
        compute='_compute_status_range_copy',
        store=True,
        tracking=True
    )

    @api.depends('rate_fixation_date', 'range_date_start_copy', 'range_date_end_copy')
    def _compute_status_range_copy(self):
        for rec in self:
            date_fix = rec.rate_fixation_date
            date_start = rec.range_date_start_copy
            date_end = rec.range_date_end_copy
            if date_fix and date_start and date_end:
                if date_fix >= date_start and date_fix <= date_end:
                    rec.status_range_copy = 'yes'
                else:
                    rec.status_range_copy = 'no'
            else:
                rec.status_range_copy = 'no'

    status_range = fields.Selection(
        [('yes', 'Да'), ('no', 'Нет')],
        string='Статус диапазона',
        compute='_compute_status_range',
        store=True,
        tracking=True
    )

    @api.depends('rate_fixation_date', 'range_date_start', 'range_date_end')
    def _compute_status_range(self):
        for rec in self:
            date_fix = rec.rate_fixation_date
            date_start = rec.range_date_start
            date_end = rec.range_date_end
            if date_fix and date_start and date_end:
                if date_fix >= date_start and date_fix <= date_end:
                    rec.status_range = 'yes'
                else:
                    rec.status_range = 'no'
            else:
                rec.status_range = 'no'

    range_id = fields.Many2one(
        'amanat.ranges',
        string='Диапазон',
        tracking=True
    )
    range_date_start = fields.Date(
        string='Дата начало (from диапазон)',
        related='range_id.date_start',
        store=True,
        tracking=True,
        readonly=True,
    )
    range_date_end = fields.Date(
        string='Дата конец (from диапазон)',
        related='range_id.date_end',
        store=True,
        tracking=True,
        readonly=True,
    )
    range_date_start_copy = fields.Date(
        string='Дата начало copy (from диапазон)',
        related='range_id.date_start_copy',
        store=True,
        tracking=True,
        readonly=True,
    )
    range_date_end_copy = fields.Date(
        string='Дата конец copy (from диапазон)',
        related='range_id.data_end_copy',
        store=True,
        tracking=True,
        readonly=True,
    )
    application_amount_rub_contract = fields.Float(
        string="Заявка по курсу в рублях по договору",
        compute='_compute_application_amount_rub_contract',
        store=True  # Если нужно хранить в БД
    )

    @api.depends('export_agent_flag', 'contragent_id', 'amount', 'rate_field', 'sber_reward', 'sovok_reward', 'client_reward')
    def _compute_application_amount_rub_contract(self):
        for record in self:
            if record.export_agent_flag:
                if record.contragent_id.name == 'Сбербанк':
                    record.application_amount_rub_contract = record.amount * record.rate_field - record.sber_reward
                elif record.contragent_id.name == 'Совкомбанк':
                    record.application_amount_rub_contract = record.amount * record.rate_field - record.sovok_reward
                else:
                    record.application_amount_rub_contract = record.amount * record.rate_field - record.client_reward
            else:
                record.application_amount_rub_contract = record.amount * record.rate_field

    # --- Compute методы (placeholder реализации) ---
    @api.depends('xe_rate', 'amount')
    def _compute_usd_equivalent(self):
        for rec in self:
            rate = rec.xe_rate if rec.xe_rate else 1.0
            rec.usd_equivalent = rate * rec.amount

    @api.depends('jess_rate', 'xe_rate_auto', 'best_rate', 'amount')
    def _compute_conversion_expenses(self):
        for rec in self:
            try:
                # Преобразуем строку xe_rate_auto в число с плавающей точкой
                payer_cross_rate = float(str(rec.xe_rate_auto).replace(',', '.')) if rec.xe_rate_auto else 0.0
            except ValueError:
                payer_cross_rate = 0.0

            rec.conversion_expenses_rub = ((rec.jess_rate or 0.0) * payer_cross_rate - (rec.best_rate or 0.0)) * (rec.amount or 0.0)

    @api.depends('conversion_expenses_rub', 'jess_rate', 'xe_rate_auto')
    def _compute_conversion_expenses_currency(self):
        for rec in self:
            try:
                payer_cross_rate = float(str(rec.xe_rate_auto).replace(',', '.')) if rec.xe_rate_auto else 0.0
            except ValueError:
                payer_cross_rate = 0.0

            denominator = (rec.jess_rate or 0.0) * payer_cross_rate
            if denominator:
                rec.conversion_expenses_currency = rec.conversion_expenses_rub / denominator
            else:
                rec.conversion_expenses_currency = 0.0

    @api.depends('cross_rate_pair', 'xe_rate')
    def _compute_xe_rate_auto(self):
        for rec in self:
            if not rec.cross_rate_pair or not rec.xe_rate:
                rec.xe_rate_auto = "Пустое поле"
            else:
                xe_rate = rec.xe_rate
                cross_pair = rec.cross_rate_pair
                if abs(cross_pair - xe_rate) <= abs(cross_pair - (1 / xe_rate)):
                    rec.xe_rate_auto = f"{xe_rate:.2f}".replace('.', ',')
                else:
                    rec.xe_rate_auto = f"{1/xe_rate:.2f}".replace('.', ',')

    @api.depends('profit_rate', 'currency_pair', 'xe_rate', 'cross_rate_pair', 'cross_rate_usd_rub', 'conversion_percent')
    def _compute_real_cross_rate(self):
        reverse_pairs = {'cny_usd', 'euro_usd', 'aed_usd', 'thb_usd'}
        for rec in self:
            conv_percent = rec.conversion_percent or 0.0
            usd_rub = rec.cross_rate_usd_rub or 0.0
            xe = rec.xe_rate or 0.0
            pair_rate = rec.cross_rate_pair or 0.0
            is_reverse = (rec.currency_pair or '').lower() in reverse_pairs

            result = 0.0
            if rec.profit_rate == 'xe':
                if is_reverse:
                    if xe != 0:
                        result = (usd_rub / xe) * (1 + conv_percent)
                else:
                    result = (usd_rub * xe) * (1 + conv_percent)
            else:  # profit_rate == 'bank' или None
                if pair_rate:
                    if is_reverse:
                        if pair_rate != 0:
                            result = (usd_rub / pair_rate) * (1 + conv_percent)
                    else:
                        result = (usd_rub * pair_rate) * (1 + conv_percent)
                else:
                    if is_reverse:
                        if xe != 0:
                            result = (usd_rub / xe) * (1 + conv_percent)
                    else:
                        result = (usd_rub * xe) * (1 + conv_percent)

            rec.real_cross_rate = result

    @api.depends('plus_dollar', 'dollar_cross_rate', 'currency')
    def _compute_plus_currency(self):
        for rec in self:
            plus_usd = rec.plus_dollar or 0.0
            cross_rate = rec.dollar_cross_rate or 1.0  # Защита от деления
            currency = rec.currency or ''

            if plus_usd > 0:
                if currency == 'cny':
                    rate = 1 / cross_rate if cross_rate < 5.0 and cross_rate != 0 else cross_rate
                elif currency == 'euro':
                    rate = 1 / cross_rate if cross_rate > 1.0 and cross_rate != 0 else cross_rate
                elif currency == 'aed':
                    rate = 1 / cross_rate if cross_rate < 2.0 and cross_rate != 0 else cross_rate
                elif currency == 'thb':
                    rate = 1 / cross_rate if cross_rate < 15.0 and cross_rate != 0 else cross_rate
                else:  # usd, rub, etc.
                    rate = cross_rate
                rec.plus_currency = plus_usd * rate
            else:
                rec.plus_currency = 0.0

    @api.depends('plus_dollar', 'plus_currency', 'amount')
    def _compute_invoice_plus_percent(self):
        for rec in self:
            if rec.plus_dollar > 0 and rec.amount:
                rec.invoice_plus_percent = rec.plus_currency / rec.amount
            else:
                rec.invoice_plus_percent = 0.0

    @api.depends('plus_dollar', 'hand_reward_percent', 'invoice_plus_percent')
    def _compute_reward_percent(self):
        for rec in self:
            if rec.plus_dollar > 0:
                rec.reward_percent = (rec.hand_reward_percent or 0.0) + (rec.invoice_plus_percent or 0.0)
            else:
                rec.reward_percent = rec.hand_reward_percent or 0.0

    @api.depends(
        'contragent_id.name',
        'rate_real',
        'our_sber_reward',
        'non_our_sber_reward',
        'our_sovok_reward',
        'our_client_reward',
        'non_our_client_reward'
    )
    def _compute_total_fact(self):
        for rec in self:
            contragent = (rec.contragent_id.name or '').lower()

            if 'сбербанк' in contragent:
                rec.total_fact = (
                    (rec.rate_real or 0.0) +
                    (rec.our_sber_reward or 0.0) +
                    (rec.non_our_sber_reward or 0.0)
                )
            elif 'совкомбанк' in contragent:
                rec.total_fact = (
                    (rec.rate_real or 0.0) +
                    (rec.our_sovok_reward or 0.0) +
                    (rec.our_client_reward or 0.0) +
                    (rec.non_our_client_reward or 0.0)
                )
            else:
                rec.total_fact = 0.0

    @api.depends('conversion_auto', 'reward_percent')
    def _compute_calculated_percent(self):
        for rec in self:
            conv = rec.conversion_auto or 0.0
            reward = rec.reward_percent or 0.0
            rec.calculated_percent = ((1 + conv) * (1 + reward)) - 1

    @api.depends('amount', 'best_rate')
    def _compute_rate_real(self):
        for rec in self:
            rec.rate_real = (rec.amount or 0.0) * (rec.best_rate or 0.0)

    @api.depends(
        'amount',
        'reward_percent',
        'escrow_commission',
        'vip_commission',
        'bank_commission',
        'accreditation_commission',
        'rate_field'
    )
    def _compute_agent_reward(self):
        for rec in self:
            amount = rec.amount or 0.0
            rate = rec.rate_field or 0.0

            if rec.reward_percent:
                commission_percent = rec.reward_percent
            elif rec.escrow_commission:
                commission_percent = max(
                    rec.vip_commission or 0.0,
                    rec.bank_commission or 0.0,
                    rec.accreditation_commission or 0.0
                )
            else:
                commission_percent = 0.0

            rec.agent_reward = amount * commission_percent * rate

    @api.depends('best_rate', 'amount', 'hidden_commission')
    def _compute_actual_reward(self):
        for rec in self:
            rec.actual_reward = (rec.best_rate or 0.0) * (rec.amount or 0.0) * ((rec.hidden_commission or 0.0) / 100)

    @api.depends('total_reward', 'actual_reward')
    def _compute_non_agent_reward(self):
        for rec in self:
            rec.non_agent_reward = (rec.total_reward or 0.0) - (rec.actual_reward or 0.0)

    @api.depends('rate_field', 'best_rate', 'amount')
    def _compute_agent_our_reward(self):
        for rec in self:
            rec.agent_our_reward = ((rec.rate_field or 0.0) - (rec.best_rate or 0.0)) * (rec.amount or 0.0)

    @api.depends('total_amount', 'amount', 'best_rate', 'rate_field')
    def _compute_total_reward(self):
        for rec in self:
            best = rec.best_rate if rec.best_rate and rec.best_rate > 0 else rec.rate_field
            rec.total_reward = (rec.total_amount or 0.0) - (rec.amount or 0.0) * (best or 0.0)

    @api.depends('application_amount_rub_contract', 'agent_reward')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = (rec.application_amount_rub_contract or 0.0) + (rec.agent_reward or 0.0)

    @api.depends('subagent_payer_ids', 'subagent_payer_ids.contragents_ids')
    def _compute_subagent_contragent_ids(self): # TODO проверить логику
        for record in self:
            # Собираем контрагентов из всех выбранных плательщиков
            contragents = record.subagent_payer_ids.mapped('contragents_ids')
            record.subagent_ids = [(6, 0, contragents.ids)]

    def write(self, vals):
        # Проверяем, изменилось ли поле "оплачена валюта поставщику (импорт) / субагенту (экспорт)"
        paid_field_name = 'supplier_currency_paid_date'  # <- замени на правильное имя поля

        res = super(Zayavka, self).write(vals)

        # Если поле обновлено, запускаем скрипты
        if paid_field_name in vals:
            for record in self:
                print("Сработала автоматизация")

        return res