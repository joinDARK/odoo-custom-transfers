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
            record.new_field_name = record.real_cross_rate

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
        compute='_compute_best_course_name',
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
    def _compute_best_course_name(self):
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
                rec.best_course_name = False
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
                rec.best_course_name = False
                continue
            
            # Выбор минимального/максимального значения
            if rec.deal_type == 'export':
                min_value = min(valid_courses.values())
                rec.best_course_name = next(k for k, v in valid_courses.items() if v == min_value)
            else:
                max_value = max(valid_courses.values())
                rec.best_course_name = next(k for k, v in valid_courses.items() if v == max_value)

    best_rate = fields.Float(
        string='Лучший курс',
        compute='_compute_best_rate',
        store=True,
    )

    def _compute_best_rate(self): # FIXME: исправить название полей на корректные
        for record in self:
            # Проверяем, если все курсы равны 0
            if (
                record.investing_rate == 0 and
                record.central_bank_rate == 0 and
                record.cross_rate == 0 and
                record.exchange_rate_1 == 0 and
                record.exchange_rate_2 == 0 and
                record.exchange_rate_3 == 0
            ):
                record.best_rate = False  # BLANK()
            else:
                if record.transaction_type == "Экспорт":
                    # Для экспорта ищем минимальное значение среди всех курсов
                    rates = [
                        record.investing_rate or 9999999,
                        record.central_bank_rate or 9999999,
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
                        record.central_bank_rate or -9999999,
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

    def _compute_client_payment_cost(self): # FIXME: исправить название полей на корректные
        for order in self:
            # Получаем сумму заказа
            order_amount = order.amount_total

            # Получаем процент начисления из прайс-листа
            commission_percentage = order.partner_id.commission_percentage  # Предполагается, что есть поле commission_percentage в модели partner

            # Вычисляем расход платежа Клиент
            if order_amount and commission_percentage:
                order.client_payment_cost = order_amount * (commission_percentage / 100)
            else:
                order.client_payment_cost = 0.0

    # TODO добавить поле Платежка РФ Клиент
    # TODO добавить поле Себестоимость денег Клиент реал
    # TODO добавить поле Расход на операционную деятельность Клиент Реал ₽
    # TODO добавить поле Фин рез Клиент реал

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

    def _compute_sber_payment_cost(self): # FIXME: исправить название полей на корректные
        for order in self:
            # Получаем сумму заказа
            order_amount = order.amount_total

            # Получаем процент начисления из прайс-листа
            commission_percentage = order.partner_id.commission_percentage  # Предполагается, что есть поле commission_percentage в модели partner

            # Вычисляем расход платежа Сбер
            if order_amount and commission_percentage:
                order.sber_payment_cost = order_amount * (commission_percentage / 100)
            else:
                order.sber_payment_cost = 0.0
    
    # TODO добавить поле Фин рез Сбер реал
    # TODO добавить поле Платежка РФ Сбер
    # TODO добавить поле Себестоимость денег Сбер реал
    # TODO добавить поле Расход на операционную деятельность Сбер реал ₽

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
            rec.overall_sovok_percent = (rec.rate_field - rec.best_rate) / rec.best_rate

    payment_cost_sovok = fields.Float(
        string='Расход платежа Совок',
        compute='_compute_payment_cost_sovok',
        store=True,
    )

    def _compute_payment_cost_sovok(self): # FIXME: исправить название полей на корректные
        for record in self:
            record.payment_cost_sovok = record.amount * record.commission_percentage

    # TODO добавить поле Платежка РФ Совок
    # TODO добавить поле Себестоимость денег Совок реал
    # TODO добавить поле Расход на операционную деятельность Совок реал ₽
    # TODO добавить поле Фин рез Совок реал

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
    price_list_profit_id = fields.Many2one('amanat.price_list_payer_profit', string='Прайс лист Плательщика Прибыль', tracking=True)
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
    # TODO добавить поля "Банка выгоднее" и "XE"
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

    total_fact = fields.Float(
        string='Итого факт',
        compute='_compute_total_fact',
        store=True,
        tracking=True
    )

    calculated_percent = fields.Float(
        string='Рассчетный %',
        compute='_compute_calculated_percent',
        store=True,
        tracking=True
    )
    rate_rub = fields.Float(
        string='Заявка по курсу в рублях',
        compute='_compute_rate_rub',
        store=True,
        tracking=True
    )
    sum_from_extracts = fields.Float(string='Сумма с выписок', tracking=True)
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
    invoice_date = fields.Date(string='выставлен инвойс', tracking=True)
    agent_contract_date = fields.Date(string='подписан агент. / субагент. договор', tracking=True)
    bank_registration_date = fields.Date(string='поставлен на учет в банке', tracking=True)
    accreditive_open_date = fields.Date(string='Открыт аккредитив', tracking=True)
    supplier_currency_paid_date = fields.Date(string='оплачена валюта поставщику (импорт) / субагенту (экспорт)', tracking=True, default=fields.Date.today)
    payment_date = fields.Date(string='передано в оплату (импорт) / оплачена валюта (экспорт)', tracking=True)
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
    # TODO добавить поле Выписка разнос (many2many с моделью amanat.extract_delivery)
    # TODO добавить поле Прибыль Плательщика по валюте заявки
    # TODO добавить поле Скрытая комиссия Партнера Реал
    # TODO добавить поле Скрытая комиссия Партнера Реал ₽

    export_agent_flag = fields.Boolean(string="Экспорт/Убираем агентское", tracking=True, default=False)

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
    def _compute_usd_equivalent(self): # TODO реализовать логику
        for rec in self:
            rec.usd_equivalent = rec.xe_rate * rec.amount

    @api.depends('jess_rate', 'cross_rate_pair', 'best_rate', 'amount')
    def _compute_conversion_expenses(self): # TODO реализовать логику
        for rec in self:
            rec.conversion_expenses_rub = ((rec.jess_rate) - rec.best_rate) * rec.amount

    @api.depends('conversion_expenses_rub', 'jess_rate', 'cross_rate_usd_rub')
    def _compute_conversion_expenses_currency(self): # TODO реализовать логику
        for rec in self:
            rec.conversion_expenses_currency = 0.0 

    @api.depends('cross_rate_pair', 'xe_rate')
    def _compute_xe_rate_auto(self): # TODO проверить логику
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

    @api.depends('currency_pair', 'xe_rate', 'cross_rate_pair', 'cross_rate_usd_rub')
    def _compute_real_cross_rate(self): # TODO реализовать логику
        for rec in self:
            rec.real_cross_rate = 0.0

    @api.depends('plus_dollar', 'dollar_cross_rate', 'amount')
    def _compute_plus_currency(self): # TODO реализовать логику
        for rec in self:
            rec.plus_currency = 0.0

    @api.depends('plus_currency')
    def _compute_invoice_plus_percent(self): # TODO реализовать логику
        for rec in self:
            rec.invoice_plus_percent = 0.0

    @api.depends('invoice_plus_percent')
    def _compute_reward_percent(self): # TODO реализовать логику
        for rec in self:
            rec.reward_percent = 0.0

    @api.depends()
    def _compute_total_fact(self): # TODO реализовать логику
        for rec in self:
            rec.total_fact = 0.0

    @api.depends()
    def _compute_calculated_percent(self): # TODO реализовать логику
        for rec in self:
            rec.calculated_percent = 0.0

    @api.depends('xe_rate', 'amount')
    def _compute_rate_rub(self): # TODO реализовать логику
        for rec in self:
            rec.rate_rub = rec.xe_rate * rec.amount

    @api.depends()
    def _compute_rate_real(self): # TODO реализовать логику
        for rec in self:
            rec.rate_real = 0.0

    @api.depends()
    def _compute_agent_reward(self): # TODO реализовать логику
        for rec in self:
            rec.agent_reward = 0.0

    @api.depends()
    def _compute_actual_reward(self): # TODO реализовать логику
        for rec in self:
            rec.actual_reward = 0.0

    @api.depends()
    def _compute_non_agent_reward(self): # TODO реализовать логику
        for rec in self:
            rec.non_agent_reward = 0.0

    @api.depends()
    def _compute_agent_our_reward(self): # TODO реализовать логику
        for rec in self:
            rec.agent_our_reward = 0.0

    @api.depends()
    def _compute_total_reward(self): # TODO реализовать логику
        for rec in self:
            rec.total_reward = 0.0

    @api.depends()
    def _compute_total_amount(self): # TODO реализовать логику
        for rec in self:
            rec.total_amount = 0.0

    @api.depends('subagent_payer_ids', 'subagent_payer_ids.contragents_ids')
    def _compute_subagent_contragent_ids(self): # TODO проверить логику
        for record in self:
            # Собираем контрагентов из всех выбранных плательщиков
            contragents = record.subagent_payer_ids.mapped('contragents_ids')
            record.subagent_ids = [(6, 0, contragents.ids)]