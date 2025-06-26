from odoo import models, fields
from ..base_model import AmanatBaseModel

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

    best_rate = fields.Float(
        string='Лучший курс',
        compute='_compute_best_rate',
        store=True,
    )

    # GROUP: Клиент
    client_inn = fields.Char(string='ИНН (from Клиент)', related='client_id.inn', store=True, readonly=True, tracking=True)

    client_ruble_paid_date = fields.Date(string='оплачен рубль клиенту (экспорт)', tracking=True)

    client_reward = fields.Float(
        string='Вознаграждение по договору Клиент',
        compute='_compute_client_reward',
        store=True,
        tracking=True
    )

    our_client_reward = fields.Float(
        string='Вознаграждение наше Клиент',
        compute='_compute_our_client_reward',
        store=True,
        tracking=True
    )

    non_our_client_reward = fields.Float(
        string='Вознаграждение не наше Клиент',
        compute='_compute_non_our_client_reward',
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

    client_payment_cost = fields.Float(
        string='Расход платежа Клиент',
        compute='_compute_client_payment_cost',
        store=True,
        digits=(16, 2),
    )

    payment_order_rf_client = fields.Float(
        string='Платежка РФ Клиент',
        compute='_compute_payment_order_rf_client',
        store=True,
        tracking=True
    )

    client_operating_expenses = fields.Float(
        string='Расход на операционную деятельность Клиент',
        compute='_compute_client_operating_expenses',
        store=True,
        tracking=True
    )

    client_real_operating_expenses = fields.Float(
        string='Расход на операционную деятельность Клиент Реал',
        compute='_compute_client_real_operating_expenses',
        store=True,
        tracking=True
    )

    client_real_operating_expenses_usd = fields.Float(
        string='Расход на операционную деятельность Клиент Реал $',
        compute='_compute_client_real_operating_expenses_usd',
        store=True,
        tracking=True
    )

    client_real_operating_expenses_rub = fields.Float(
        string='Расход на операционную деятельность Клиент Реал ₽',
        compute='_compute_client_real_operating_expenses_rub',
        store=True,
        tracking=True
    )

    client_currency_bought = fields.Float(
        string='Купили валюту Клиент',
        compute='_compute_client_currency_bought',
        store=True,
        tracking=True
    )

    client_currency_bought_real = fields.Float(
        string='Купили валюту Клиент реал',
        compute='_compute_client_currency_bought_real',
        store=True,
        tracking=True
    )

    client_currency_bought_real_usd = fields.Float(
        string='Купили валюту Клиент реал $',
        compute='_compute_client_currency_bought_real_usd',
        store=True,
        tracking=True
    )

    client_currency_bought_real_rub = fields.Float(
        string='Купили валюту Клиент реал ₽',
        compute='_compute_client_currency_bought_real_rub',
        store=True,
        tracking=True
    )

    client_payment_cost_usd = fields.Float(
        string='Расход платежа в $ Клиент',
        compute='_compute_client_payment_cost_usd',
        store=True,
        tracking=True
    )

    client_payment_cost_rub = fields.Float(
        string='Расход платежа в ₽ Клиент',
        compute='_compute_client_payment_cost_rub',
        store=True,
        tracking=True
    )

    cost_of_money_client = fields.Float(
        string='Себестоимость денег Клиент',
        compute='_compute_cost_of_money_client',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    cost_of_money_client_real = fields.Float(
        string='Себестоимость денег Клиент реал',
        compute='_compute_cost_of_money_client_real',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    cost_of_money_client_real_usd = fields.Float(
        string='Себестоимость денег Клиент реал $',
        compute='_compute_cost_of_money_client_real_usd',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    cost_of_money_client_real_rub = fields.Float(
        string='Себестоимость денег Клиент реал ₽',
        compute='_compute_cost_of_money_client_real_rub',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    fin_res_client = fields.Float(
        string='Фин рез Клиент',
        compute='_compute_fin_res_client',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    fin_res_client_real = fields.Float(
        string='Фин рез Клиент реал',
        compute='_compute_fin_res_client_real',
        store=True,
        digits=(16, 2),
        tracking=True,
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

    # GROUP: Сбер
    sber_reward = fields.Float(
        string='Вознаграждение по договору Сбер',
        compute='_compute_sber_reward',
        store=True,
        tracking=True
    )

    our_sber_reward = fields.Float(
        string='Вознаграждение наше Сбер',
        compute='_compute_our_sber_reward',
        store=True,
        tracking=True
    )

    non_our_sber_reward = fields.Float(
        string='Вознаграждение не наше Сбер',
        compute='_compute_non_our_sber_reward',
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

    overall_sber_percent = fields.Float(
        string='Общий процент Сбер',
        compute='_compute_overall_sber_percent',
        store=True,
        tracking=True
    )

    rate_real_sber = fields.Float(
        string='Заявка по курсу реальный Сбер',
        compute='_compute_rate_real_sber',
        store=True,
        tracking=True
    )

    sber_payment_cost = fields.Float(
        string='Расход платежа Сбер',
        compute='_compute_sber_payment_cost',
        store=True,
        digits=(16, 2),
    )

    payment_order_rf_sber = fields.Float(
        string='Платежка РФ Сбер',
        compute='_compute_payment_order_rf_sber',
        store=True,
        tracking=True
    )

    sber_operating_expenses = fields.Float(
        string='Расход на операционную деятельность Сбер',
        compute='_compute_sber_operating_expenses',
        store=True,
        tracking=True,
    )

    sber_operating_expenses_real = fields.Float(
        string='Расход на операционную деятельность Сбер реал',
        compute='_compute_sber_operating_expenses_real',
        store=True,
        tracking=True,
    )

    sber_operating_expenses_real_usd = fields.Float(
        string='Расход на операционную деятельность Сбер реал $',
        compute='_compute_sber_operating_expenses_real_usd',
        store=True,
        tracking=True,
    )

    sber_operating_expenses_real_rub = fields.Float(
        string='Расход на операционную деятельность Сбер реал ₽',
        compute='_compute_sber_operating_expenses_real_rub',
        store=True,
        tracking=True,
    )

    kupili_valyutu_sber = fields.Float(
        string='Купили валюту Сбер',
        compute='_compute_kupili_valyutu_sber',
        store=True,
        tracking=True
    )

    kupili_valyutu_sber_real = fields.Float(
        string='Купили валюту Сбер реал',
        compute='_compute_kupili_valyutu_sber_real',
        store=True,
        tracking=True
    )

    kupili_valyutu_sber_real_usd = fields.Float(
        string='Купили валюту Сбер реал $',
        compute='_compute_kupili_valyutu_sber_real_usd',
        store=True,
        tracking=True
    )

    kupili_valyutu_sber_real_rub = fields.Float(
        string='Купили валюту Сбер реал ₽',
        compute='_compute_kupili_valyutu_sber_real_rub',
        store=True,
        tracking=True
    )

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

    sber_payment_cost_on_usd = fields.Float(
        string='Расход платежа в $ Сбер',
        compute='_compute_sber_payment_cost_on_usd',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    sber_payment_cost_on_usd_real = fields.Float(
        string='Расход платежа в $ Сбер реал',
        compute='_compute_sber_payment_cost_on_usd_real',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    sebestoimost_denej_sber = fields.Float(
        string='Себестоимость денег Сбер',
        compute='_compute_sebestoimost_denej_sber',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    sebestoimost_denej_sber_real = fields.Float(
        string='Себестоимость денег Сбер реал',
        compute='_compute_sebestoimost_denej_sber_real',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    sebestoimost_denej_sber_real_usd = fields.Float(
        string='Себестоимость денег Сбер реал $',
        compute='_compute_sebestoimost_denej_sber_real_usd',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    sebestoimost_denej_sber_real_rub = fields.Float(
        string='Себестоимость денег Сбер реал ₽',
        compute='_compute_sebestoimost_denej_sber_real_rub',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    fin_res_sber = fields.Float(
        string='Фин рез Сбер',
        compute='_compute_fin_res_sber',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    fin_res_sber_real = fields.Float(
        string='Фин рез Сбер реал',
        compute='_compute_fin_res_sber_real',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    fin_res_sber_real_usd = fields.Float(
        string='Фин рез Сбер реал $',
        compute='_compute_fin_res_sber_real_usd',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    fin_res_sber_real_rub = fields.Float(
        string='Фин рез Сбер реал ₽',
        compute='_compute_fin_res_sber_real_rub',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    # GROUP: Совок
    our_sovok_reward = fields.Float(
        string='Вознаграждение наше Совок',
        compute='_compute_our_sovok_reward',
        store=True,
        tracking=True
    )

    sovok_reward = fields.Float(
        string='Вознаграждение по договору Совок',
        compute='_compute_sovok_reward',
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

    overall_sovok_percent = fields.Float(
        string='Общий процент Совок',
        compute='_compute_overall_sovok_percent',
        store=True,
        tracking=True
    )

    payment_cost_sovok = fields.Float(
        string='Расход платежа Совок',
        compute='_compute_payment_cost_sovok',
        store=True,
    )

    payment_order_rf_sovok = fields.Float(
        string='Платежка РФ Совок',
        compute='_compute_payment_order_rf_sovok',
        store=True,
        tracking=True
    )

    operating_expenses_sovok_partner = fields.Float(
        string='Расход на операционную деятельность Совок партнер',
        compute='_compute_operating_expenses_sovok_partner',
        store=True,
        tracking=True
    )

    operating_expenses_sovok_real = fields.Float(
        string='Расход на операционную деятельность Совок реал',
        compute='_compute_operating_expenses_sovok_real',
        store=True,
        tracking=True
    )

    operating_expenses_sovok_real_usd = fields.Float(
        string='Расход на операционную деятельность Совок реал $',
        compute='_compute_operating_expenses_sovok_real_usd',
        store=True,
        tracking=True
    )

    operating_expenses_sovok_real_rub = fields.Float(
        string='Расход на операционную деятельность Совок реал ₽',
        compute='_compute_operating_expenses_sovok_real_rub',
        store=True,
        tracking=True
    )

    kupili_valyutu_sovok_partner = fields.Float(
        string='Купили валюту Совок Партнер',
        compute='_compute_kupili_valyutu_sovok_partner',
        store=True,
        digits=(16, 2),
        tracking=True
    )

    kupili_valyutu_sovok_real = fields.Float(
        string='Купили валюту Совок Реал',
        compute='_compute_kupili_valyutu_sovok_real',
        store=True,
        digits=(16, 2),
        tracking=True
    )

    kupili_valyutu_sovok_real_usd = fields.Float(
        string='Купили валюту Совок Реал $',
        compute='_compute_kupili_valyutu_sovok_real_usd',
        store=True,
        digits=(16, 2),
        tracking=True
    )

    kupili_valyutu_sovok_real_rub = fields.Float(
        string='Купили валюту Совок Реал ₽',
        compute='_compute_kupili_valyutu_sovok_real_rub',
        store=True,
        digits=(16, 2),
        tracking=True
    )

    payment_cost_sovok_partner_usd = fields.Float(
        string='Расход платежа в $ Совок партнер',
        compute='_compute_payment_cost_sovok_partner_usd',
        store=True,
        digits=(16, 2),
        tracking=True
    )

    payment_cost_sovok_real_usd = fields.Float(
        string='Расход платежа в $ Совок реал',
        compute='_compute_payment_cost_sovok_real_usd',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    payment_cost_sovok_real_rub = fields.Float(
        string='Расход платежа в ₽ Совок реал',
        compute='_compute_payment_cost_sovok_real_rub',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    sebestoimost_denej_sovok_real = fields.Float(
        string='Себестоимость денег Совок реал',
        compute='_compute_sebestoimost_denej_sovok_real',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    sebestoimost_denej_sovok_real_usd = fields.Float(
        string='Себестоимость денег Совок реал $',
        compute='_compute_sebestoimost_denej_sovok_real_usd',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    sebestoimost_denej_sovok_real_rub = fields.Float(
        string='Себестоимость денег Совок реал ₽',
        compute='_compute_sebestoimost_denej_sovok_real_rub',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

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

    course_profitable = fields.Char(
        string='Какой курс выгоднее',
        compute='_compute_course_profitable',
        store=True,
        tracking=True
    )

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

    sum_from_extracts = fields.Float(
        string='Сумма (from Выписка разнос)', 
        compute='_compute_sum_from_extracts', 
        store=True, 
        tracking=True
    )

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

    subagent_ids = fields.Many2many('amanat.contragent', string='Субагент', tracking=True)

    subagent_payer_ids = fields.Many2many(
        'amanat.payer',
        string='Плательщик Субагента',
        compute='_compute_subagent_payer_ids',
        store=True,
        tracking=True
    )

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
    )

    bank_vypiska = fields.Char(
        string='Банк Выписка',
        compute='_compute_bank_vypiska',
        store=True,
        tracking=True
    )

    payer_profit_currency = fields.Float(
        string='Прибыль Плательщика по валюте заявки',
        compute='_compute_payer_profit_currency',
        store=True,
        tracking=True
    )

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

    error_sovok = fields.Float(
        string='Ошибка Совок',
        compute='_compute_error_sovok',
        store=True,
        tracking=True
    )

    error_sber = fields.Float(
        string='Ошибка Сбер',
        compute='_compute_error_sber',
        store=True,
        tracking=True
    )

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
        domain="[('payer_partners', 'in', subagent_payer_ids)]"
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

    period_id = fields.Many2one(
        'amanat.period',
        string='Период',
        tracking=True
    )

    period_date_1 = fields.Date(
        string='Дата 1 (from Период)',
        related='period_id.date_1',
        store=True,
        readonly=True,
        tracking=True
    )

    period_date_2 = fields.Date(
        string='Дата 2 (from Период)',
        related='period_id.date_2',
        store=True,
        readonly=True,
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

    real_post_conversion_rate = fields.Float(
        string='Курс после конвертации реал',
        compute='_compute_real_post_conversion_rate',
        store=True,
        digits=(16, 6),
        tracking=True
    )

    real_post_conversion_rate_usd = fields.Float(
        string='Курс после конвертации реал $',
        compute='_compute_real_post_conversion_rate_usd',
        store=True,
        digits=(16, 6),
        tracking=True
    )

    payer_cross_rate_rub = fields.Float(
        string='Кросс-курс Плательщика ₽',
        compute='_compute_payer_cross_rate_rub',
        store=True,
        digits=(16, 6),
        tracking=True
    )

    real_post_conversion_rate_rub = fields.Float(
        string='Курс после конвертации реал ₽',
        compute='_compute_real_post_conversion_rate_rub',
        store=True,
        digits=(16, 6),
        tracking=True
    )

    payer_profit_usd = fields.Float(
        string='Прибыль плательщика $',
        compute='_compute_payer_profit_usd',
        store=True,
        tracking=True
    )

    payer_profit_rub = fields.Float(
        string='Прибыль плательщика ₽',
        compute='_compute_payer_profit_rub',
        store=True,
        tracking=True
    )

    date_received_on_pc_auto = fields.Char(
        string="Дата поступления на PC АВТО",
        compute='_compute_date_received_on_pc_auto',
        store=True,
        tracking=True
    )

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

    sebestoimost_denej_sovok_partner = fields.Float(
        string='Себестоимость денег Совок партнер',
        compute='_compute_sebestoimost_denej_sovok_partner',
        store=True,
        digits=(16, 2),
        tracking=True,
    )

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

    hidden_partner_commission_real = fields.Float(
        string='Скрытая комиссия Партнера Реал',
        compute='_compute_hidden_partner_commission_real',
        store=True,
        tracking=True
    )

    hidden_partner_commission_real_usd = fields.Float(
        string='Скрытая комиссия Партнера Реал $',
        compute='_compute_hidden_partner_commission_real_usd',
        store=True,
        tracking=True
    )

    hidden_partner_commission_real_rub = fields.Float(
        string='Скрытая комиссия Партнера Реал ₽',
        compute='_compute_hidden_partner_commission_real_rub',
        store=True,
        tracking=True
    )

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

    status_range = fields.Selection(
        [('yes', 'Да'), ('no', 'Нет')],
        string='Статус диапазона',
        compute='_compute_status_range',
        store=True,
        tracking=True
    )

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