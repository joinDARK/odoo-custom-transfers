from odoo import models, fields, api
from .base_model import AmanatBaseModel

class Zayavka(models.Model, AmanatBaseModel):
    _name = 'amanat.zayavka'
    _description = 'Заявки'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    zayavka_id = fields.Char(
        string='ID заявки',
        readonly=True,
        tracking=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.zayavka.sequence'),
        copy=False
    )
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
            ('waiting_currency_export', 'ждём валюту (только для Экспорта)')
        ],
        string='Статус',
        default='close',
        tracking=True,
    )
    zayavka_num = fields.Char(string='№ заявки', tracking=True)
    date_placement = fields.Date(string='Дата размещения', tracking=True, required=True)
    taken_in_work_date = fields.Date(string='Взята в работу', tracking=True)
    contragent_id = fields.Many2one('amanat.contragent', string='Контрагент', tracking=True)
    agent_id = fields.Many2one('amanat.contragent', string='Агент', tracking=True)
    client_id = fields.Many2one('amanat.contragent', string='Клиент', tracking=True)
    inn = fields.Char(string='ИНН', related='client_id.payer_inn', store=True, readonly=True, tracking=True)
    client_inn = fields.Char(string='ИНН (from Клиент)', related='client_id.inn', store=True, readonly=True, tracking=True)
    exporter_importer_name = fields.Text(string='Наименование Экспортера/Импортера', tracking=True)
    bank_swift = fields.Text(string='SWIFT код банка', tracking=True)
    country_id = fields.Many2one('amanat.country', string='Страна', tracking=True)
    payment_conditions = fields.Selection(
        [
            ('accred', 'Аккредитив'),
            ('prepayment', 'Предоплата'),
            ('postpayment', 'Постоплата'),
            ('escrow', 'Эскроу')
        ],
        string='Условия расчета',
        tracking=True,
        required=True
    )
    deal_type = fields.Selection(
        [('import', 'Импорт'), ('export', 'Экспорт')],
        string='Вид сделки',
        tracking=True,
        required=True
    )
    instruction_number = fields.Char(string='Номер поручения', tracking=True)
    instruction_signed_date = fields.Date(string='Подписано поручение', tracking=True)
    usd_equivalent = fields.Float(
        string='USD эквивалент',
        compute='_compute_usd_equivalent',
        store=True,
        tracking=True
    )
    jess_rate = fields.Float(string='Курс Джесс', tracking=True)
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
    is_cross = fields.Boolean(string='Кросс', default=False, tracking=True)
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
    cross_rate_usd_rub = fields.Float(string='Кросс-курс USD/RUB', tracking=True)
    cross_rate_pair = fields.Float(string='Кросс-курс пары', tracking=True)
    xe_rate = fields.Float(string='Курс XE', tracking=True)
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
        tracking=True
    )
    amount = fields.Float(string='Сумма заявки', tracking=True, required=True)
    vip_conditions = fields.Char(string='Условия VIP', tracking=True)
    price_list_profit_id = fields.Many2one('amanat.price_list_payer_profit', string='Прайс лист Плательщика Прибыль', tracking=True)

    # Новые поля из Airtable
    # manager_ids = fields.Many2many(
    #     'amanat.manager',
    #     'amanat_zayavka_manager_rel',
    #     'zayavka_id',
    #     'manager_id',
    #     string='Менеджер',
    #     tracking=True
    # )
    # checker_ids = fields.Many2many(
    #     'amanat.manager',
    #     'amanat_zayavka_checker_rel',
    #     'zayavka_id',
    #     'checker_id',
    #     string='Проверяющий',
    #     tracking=True
    # )
    vip_commission = fields.Float(string='Комиссия VIP', digits=(16, 1), tracking=True)
    hidden_commission = fields.Float(string='Скрытая комиссия', tracking=True)
    bank_commission = fields.Float(string='Комиссия +% банка', tracking=True)
    accreditation_commission = fields.Float(string='Комиссия + аккред', tracking=True)
    escrow_commission = fields.Float(string='Комиссия + эскроу', tracking=True)
    rate_field = fields.Float(string='Курс', tracking=True)
    hidden_rate = fields.Float(string='Скрытый курс', tracking=True)
    conversion_percent = fields.Float(string='% Конвертации', tracking=True)
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
    sovok_reward = fields.Float(
        string='Вознаграждение по договору Совок',
        compute='_compute_sovok_reward',
        store=True,
        tracking=True
    )
    sber_reward = fields.Float(
        string='Вознаграждение по договору Сбер',
        compute='_compute_sber_reward',
        store=True,
        tracking=True
    )
    client_reward = fields.Float(
        string='Вознаграждение по договору Клиент',
        compute='_compute_client_reward',
        store=True,
        tracking=True
    )
    our_sovok_reward = fields.Float(
        string='Вознаграждение наше Совок',
        compute='_compute_our_sovok_reward',
        store=True,
        tracking=True
    )
    our_sber_reward = fields.Float(
        string='Вознаграждение наше Сбер',
        compute='_compute_our_sber_reward',
        store=True,
        tracking=True
    )
    our_client_reward = fields.Float(
        string='Вознаграждение наше Клиент',
        compute='_compute_our_client_reward',
        store=True,
        tracking=True
    )
    non_our_sber_reward = fields.Float(
        string='Вознаграждение не наше Сбер',
        compute='_compute_non_our_sber_reward',
        store=True,
        tracking=True
    )
    non_our_client_reward = fields.Float(
        string='Вознаграждение не наше Клиент',
        compute='_compute_non_our_client_reward',
        store=True,
        tracking=True
    )
    total_sovok = fields.Float(
        string='Итого Совок',
        compute='_compute_total_sovok',
        store=True,
        tracking=True
    )
    total_sovok_management = fields.Float(
        string='Итого Совок упр',
        compute='_compute_total_sovok_management',
        store=True,
        tracking=True
    )
    total_sber = fields.Float(
        string='Итого Сбер',
        compute='_compute_total_sber',
        store=True,
        tracking=True
    )
    total_sber_management = fields.Float(
        string='Итого Сбер упр',
        compute='_compute_total_sber_management',
        store=True,
        tracking=True
    )
    total_client = fields.Float(
        string='Итого Клиент',
        compute='_compute_total_client',
        store=True,
        tracking=True
    )
    total_client_management = fields.Float(
        string='Итого Клиент упр',
        compute='_compute_total_client_management',
        store=True,
        tracking=True
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
    overall_sovok_percent = fields.Float(
        string='Общий процент Совок',
        compute='_compute_overall_sovok_percent',
        store=True,
        tracking=True
    )
    overall_sber_percent = fields.Float(
        string='Общий процент Сбер',
        compute='_compute_overall_sber_percent',
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
    rate_real_sber = fields.Float(
        string='Заявка по курсу реальный Сбер',
        compute='_compute_rate_real_sber',
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
    supplier_currency_paid_date = fields.Date(string='оплачена валюта поставщику (импорт) / субагенту (экспорт)', tracking=True)
    payment_date = fields.Date(string='передано в оплату (импорт) / оплачена валюта (экспорт)', tracking=True)
    supplier_currency_received_date = fields.Date(string='получена валюта поставщиком (импорт) / субагентом (экспорт)', tracking=True)
    client_ruble_paid_date = fields.Date(string='оплачен рубль клиенту (экспорт)', tracking=True)
    accreditive_revealed_date = fields.Date(string='аккредитив раскрыт', tracking=True)
    act_report_signed_date = fields.Date(string='подписан акт-отчет', tracking=True)
    deal_closed_date = fields.Date(string='сделка закрыта', tracking=True)
    deal_cycle_days = fields.Integer(string='Цикл сделки, дн', tracking=True)
    payment_purpose = fields.Text(string='Назначение платежа', tracking=True)
    subagent_ids = fields.Many2many('amanat.contragent', string='Субагент', compute='_compute_subagent_contragent_ids', store=True, tracking=True)
    subagent_payer_ids = fields.Many2many('amanat.payer', string='Плательщик Субагента', tracking=True)
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

    # --- Compute методы (placeholder реализации) ---
    @api.depends('xe_rate', 'amount')
    def _compute_usd_equivalent(self):
        for rec in self:
            rec.usd_equivalent = rec.xe_rate * rec.amount

    @api.depends('jess_rate', 'cross_rate_pair', 'xe_rate', 'amount')
    def _compute_conversion_expenses(self):
        for rec in self:
            rec.conversion_expenses_rub = 0.0  # Реализуйте логику

    @api.depends('conversion_expenses_rub', 'jess_rate', 'cross_rate_usd_rub')
    def _compute_conversion_expenses_currency(self):
        for rec in self:
            rec.conversion_expenses_currency = 0.0  # Реализуйте логику

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

    @api.depends('currency_pair', 'xe_rate', 'cross_rate_pair', 'cross_rate_usd_rub')
    def _compute_real_cross_rate(self):
        for rec in self:
            rec.real_cross_rate = 0.0  # Реализуйте логику

    @api.depends('plus_dollar', 'dollar_cross_rate', 'amount')
    def _compute_plus_currency(self):
        for rec in self:
            rec.plus_currency = 0.0  # Реализуйте логику

    @api.depends('plus_currency')
    def _compute_invoice_plus_percent(self):
        for rec in self:
            rec.invoice_plus_percent = 0.0  # Реализуйте логику

    @api.depends('invoice_plus_percent')
    def _compute_reward_percent(self):
        for rec in self:
            rec.reward_percent = 0.0  # Реализуйте логику

    @api.depends()
    def _compute_sovok_reward(self):
        for rec in self:
            rec.sovok_reward = 0.0

    @api.depends()
    def _compute_sber_reward(self):
        for rec in self:
            rec.sber_reward = 0.0

    @api.depends()
    def _compute_client_reward(self):
        for rec in self:
            rec.client_reward = 0.0

    @api.depends()
    def _compute_our_sovok_reward(self):
        for rec in self:
            rec.our_sovok_reward = 0.0

    @api.depends()
    def _compute_our_sber_reward(self):
        for rec in self:
            rec.our_sber_reward = 0.0

    @api.depends()
    def _compute_our_client_reward(self):
        for rec in self:
            rec.our_client_reward = 0.0

    @api.depends()
    def _compute_non_our_sber_reward(self):
        for rec in self:
            rec.non_our_sber_reward = 0.0

    @api.depends()
    def _compute_non_our_client_reward(self):
        for rec in self:
            rec.non_our_client_reward = 0.0

    @api.depends()
    def _compute_total_sovok(self):
        for rec in self:
            rec.total_sovok = 0.0

    @api.depends()
    def _compute_total_sovok_management(self):
        for rec in self:
            rec.total_sovok_management = 0.0

    @api.depends()
    def _compute_total_sber(self):
        for rec in self:
            rec.total_sber = 0.0

    @api.depends()
    def _compute_total_sber_management(self):
        for rec in self:
            rec.total_sber_management = 0.0

    @api.depends()
    def _compute_total_client(self):
        for rec in self:
            rec.total_client = 0.0

    @api.depends()
    def _compute_total_client_management(self):
        for rec in self:
            rec.total_client_management = 0.0

    @api.depends()
    def _compute_total_fact(self):
        for rec in self:
            rec.total_fact = 0.0

    @api.depends()
    def _compute_calculated_percent(self):
        for rec in self:
            rec.calculated_percent = 0.0

    @api.depends()
    def _compute_overall_sovok_percent(self):
        for rec in self:
            rec.overall_sovok_percent = 0.0

    @api.depends()
    def _compute_overall_sber_percent(self):
        for rec in self:
            rec.overall_sber_percent = 0.0

    @api.depends('xe_rate', 'amount')
    def _compute_rate_rub(self):
        for rec in self:
            rec.rate_rub = rec.xe_rate * rec.amount

    @api.depends()
    def _compute_rate_real(self):
        for rec in self:
            rec.rate_real = 0.0

    @api.depends()
    def _compute_rate_real_sber(self):
        for rec in self:
            rec.rate_real_sber = 0.0

    @api.depends()
    def _compute_agent_reward(self):
        for rec in self:
            rec.agent_reward = 0.0

    @api.depends()
    def _compute_actual_reward(self):
        for rec in self:
            rec.actual_reward = 0.0

    @api.depends()
    def _compute_non_agent_reward(self):
        for rec in self:
            rec.non_agent_reward = 0.0

    @api.depends()
    def _compute_agent_our_reward(self):
        for rec in self:
            rec.agent_our_reward = 0.0

    @api.depends()
    def _compute_total_reward(self):
        for rec in self:
            rec.total_reward = 0.0

    @api.depends()
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = 0.0

    @api.depends('subagent_payer_ids', 'subagent_payer_ids.contragents_ids')
    def _compute_subagent_contragent_ids(self):
        for record in self:
            # Собираем контрагентов из всех выбранных плательщиков
            contragents = record.subagent_payer_ids.mapped('contragents_ids')
            record.subagent_ids = [(6, 0, contragents.ids)]