
from odoo import models, fields, api
from ..base_model import AmanatBaseModel

class Zayavka(models.Model, AmanatBaseModel):
    _name = 'amanat.zayavka'
    _description = 'Заявки'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _order = 'create_date desc'

    zayavka_id = fields.Char(
        string='ID заявки',
        readonly=True,
        tracking=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('amanat.zayavka.sequence'),
        copy=False
    )

    status = fields.Selection(
        [
            ('1', '1. В работе'),
            ('2', '2. Выставлен инвойс'),
            ('3', '3. Зафиксирован курс'),
            ('4', '4. Подписано поручение'),
            ('5', '5. Готовим на оплату'),
            ('6', '6. Передано на оплату'),
            ('7', '7. Получили ПП'),
            ('8', '8. Получили Swift'),
            ('9', '9. Подписан Акт-отчет'),
            ('10', '10. Ждем рубли'),
            ('11', '11. Получили рубли'),
            ('12', '12. Ждем поступление валюты'),
            ('13', '13. Валюта у получателя'),
            ('14', '14. Запрошен Swift 103'),
            ('15', '15. Получен Swift 103'),
            ('16', '16. Запрошен Swift 199'),
            ('17', '17. Получен Swift 199'),
            ('18', '18. Ожидаем возврат'),
            ('19', '19. Оплачено повторно'),
            ('20', '20. Возврат'),
            ('21', '21. Заявка закрыта'),
            ('22', '22. Отменено клиентом'),
            ('23', '23. Согласован получатель (экспорт)'),
            ('24', '24. Получили валюту (экспорт)'),
            ('25', '25. Оплатили рубли (экспорт)'),
        ],
        string='Статус',
        default='1',
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

    exporter_importer_name = fields.Text(string='Наименование покупателя/продавца', tracking=True)

    bank_swift = fields.Text(string='SWIFT код банка', tracking=True)

    country_id = fields.Many2one('amanat.country', string='Страна', tracking=True)

    is_cross = fields.Boolean(string='Кросс', default=False, tracking=True)

    comment = fields.Text(string='Комментарии по заявке', tracking=True)

    comment_hedge = fields.Text(string='Комментарии по Хэджу', tracking=True)

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
        readonly=False,
        tracking=True,
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
        digits=(16, 4),
        readonly=False,
        tracking=True,
        store=True,
    )

    # GROUP: Клиент
    client_inn = fields.Char(string='ИНН (from Клиент)', related='client_id.inn', store=True, readonly=True, tracking=True)

    client_ruble_paid_date = fields.Date(string='оплачен рубль клиенту (экспорт)', tracking=True)

    client_reward = fields.Float(
        string='Вознаграждение по договору Клиент',
        compute='_compute_client_reward',
        readonly=False,
        store=True,
        tracking=True
    )

    our_client_reward = fields.Float(
        string='Вознаграждение наше Клиент',
        compute='_compute_our_client_reward',
        readonly=False,
        store=True,
        tracking=True
    )

    non_our_client_reward = fields.Float(
        string='Вознаграждение не наше Клиент',
        compute='_compute_non_our_client_reward',
        readonly=False,
        store=True,
        tracking=True
    )

    total_client = fields.Float(
        string='Итого Клиент',
        compute='_compute_total_client',
        readonly=False,
        store=True,
        tracking=True
    )

    total_client_management = fields.Float(
        string='Итого Клиент упр',
        compute='_compute_total_client_management',
        readonly=False,
        store=True,
        tracking=True
    )

    client_payment_cost = fields.Float(
        string='Расход за проведение платежа в валюте заявки',
        compute='_compute_client_payment_cost',
        help="""Если Вид сделки 'Экспорт':  Расход за проведение платежа в валюте заявки = Сумма заявки × Процент (from Расход платежа по РФ(%))
        Иначе: Сумма заявки × % Начисления (from Расход за проведение платежа(%))""",
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    payment_order_rf_client = fields.Float(
        string='Расход платежа по РФ',
        compute='_compute_payment_order_rf_client',
        help="""
        Расход платежа по РФ = (Заявка по курсу в рублях по договору + Вознаграждение по договору Клиент) × Процент (from Расход платежа по РФ(%))
        """,
        readonly=False,
        store=True,
        tracking=True
    )

    client_operating_expenses = fields.Float(
        string='Расход на операционную деятельность',
        compute='_compute_client_operating_expenses',
        readonly=False,
        store=True,
        tracking=True
    )

    client_real_operating_expenses = fields.Float(
        string='Расход на операционную деятельность в валюте заявки',
        compute='_compute_client_real_operating_expenses',
        readonly=False,
        store=True,
        tracking=True
    )

    client_real_operating_expenses_usd = fields.Float(
        string='Расход на операционную деятельность в эквиваленте $',
        compute='_compute_client_real_operating_expenses_usd',
        readonly=False,
        store=True,
        tracking=True
    )

    client_real_operating_expenses_rub = fields.Float(
        string='Расход на операционную деятельность ₽',
        compute='_compute_client_real_operating_expenses_rub',
        readonly=False,
        store=True,
        tracking=True
    )

    client_currency_bought = fields.Float(
        string='Купили валюту',
        compute='_compute_client_currency_bought',
        help="""Если Курс после конвертации партнер равен 0: Купили валюту = 0
        Иначе: Купили валюту = (Итого Клиент - Расход платежа по РФ) ÷ Курс после конвертации партнер""",
        readonly=False,
        store=True,
        tracking=True
    )

    client_currency_bought_real = fields.Float(
        string='Купили валюту в валюте заявки',
        compute='_compute_client_currency_bought_real',
        help="""Если Курс после конвертации в валюте заявки равен 0: Купили валюту в валюте заявки = 0
        Иначе: Купили валюту в валюте заявки = (Итого Клиент - Расход платежа по РФ) ÷ Курс после конвертации в валюте заявки""",
        readonly=False,
        store=True,
        tracking=True
    )

    client_currency_bought_real_usd = fields.Float(
        string='Купили валюту в эквиваленте $',
        compute='_compute_client_currency_bought_real_usd',
        help="""Купили валюту в эквиваленте $ = Купили валюту в валюте заявки × Кросс-курс $ к валюте заявки авто""",
        readonly=False,
        store=True,
        tracking=True
    )

    client_currency_bought_real_rub = fields.Float(
        string='Купили валюту ₽',
        compute='_compute_client_currency_bought_real_rub',
        help="""Купили валюту ₽ = Купили валюту в эквиваленте $ × Курс Джес""",
        readonly=False,
        store=True,
        tracking=True
    )

    client_payment_cost_usd = fields.Float(
        string='Расход за проведение платежа в $',
        compute='_compute_client_payment_cost_usd',
        help="""Расход за проведение платежа в $ = Расход за проведение платежа × Кросс-курс $ к валюте заявки авто + Фикс за сделку $ (from Расход за проведение платежа(%))""",
        readonly=False,
        store=True,
        tracking=True
    )

    client_payment_cost_rub = fields.Float(
        string='Расход за проведение платежа в ₽',
        compute='_compute_client_payment_cost_rub',
        help="""Расход за проведение платежа в ₽ = Расход за проведение платежа в $ × Курс Джес""",
        readonly=False,
        store=True,
        tracking=True
    )

    cost_of_money_client = fields.Float(
        string='Себестоимость денег',
        compute='_compute_cost_of_money_client',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    cost_of_money_client_real = fields.Float(
        string='Себестоимость денег в валюте заявки',
        compute='_compute_cost_of_money_client_real',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    cost_of_money_client_real_usd = fields.Float(
        string='Себестоимость денег в эквиваленте $',
        compute='_compute_cost_of_money_client_real_usd',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    cost_of_money_client_real_rub = fields.Float(
        string='Себестоимость денег ₽',
        compute='_compute_cost_of_money_client_real_rub',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    fin_res_client = fields.Float(
        string='Фин рез',
        compute='_compute_fin_res_client',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    fin_res_client_real = fields.Float(
        string='Фин рез в валюте заявки',
        compute='_compute_fin_res_client_real',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
        help="""Если вид сделки "Экспорт": Фин рез = (Сумма заявки × % Вознаграждения) -  Расход за проведение платежа в валюте заявки - Расход на операционную деятельность в валюте заявки
        
        Если Агент "Тезер" ИЛИ Валюта "USDT" ИЛИ Вид сделки "Импорт-экспорт/Экспорт-импорт":
        • Если Контрагент "А7": Фин рез = (Сумма заявки × % Вознаграждения) - Расход на операционную деятельность в валюте заявки -  Расход за проведение платежа в валюте заявки
        • Иначе: Фин рез = (Сумма заявки × Скрытая комиссия) - Расход на операционную деятельность в валюте заявки -  Расход за проведение платежа в валюте заявки

        Обычный расчет: Фин рез = Купили валюту в валюте заявки -  Расход за проведение платежа в валюте заявки - Себестоимость денег в валюте заявки - Скрытая комиссия Партнера в валюте заявки - Расход на операционную деятельность в валюте заявки - Сумма заявки - Сумма плательщику по валюте заявки"""
    )

    fin_res_client_real_usd = fields.Float(
        string='Фин рез в эквиваленте $',
        compute='_compute_fin_res_client_real_usd',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
        help="""
        Фин рез в эквиваленте $ = Фин рез в валюте заявки × Кросс-курс $ к валюте заявки авто
        """
    )

    fin_res_client_real_rub = fields.Float(
        string='Фин рез ₽',
        compute='_compute_fin_res_client_real_rub',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
        help="""
        Фин рез ₽ = Фин рез в эквиваленте $ × Курс Джес
        """
    )

    # GROUP: Сбер
    sber_reward = fields.Float(
        string='Вознаграждение по договору Сбер',
        compute='_compute_sber_reward',
        readonly=False,
        store=True,
        tracking=True
    )

    our_sber_reward = fields.Float(
        string='Вознаграждение наше Сбер',
        compute='_compute_our_sber_reward',
        readonly=False,
        store=True,
        tracking=True
    )

    non_our_sber_reward = fields.Float(
        string='Вознаграждение не наше Сбер',
        compute='_compute_non_our_sber_reward',
        readonly=False,
        store=True,
        tracking=True
    )

    total_sber = fields.Float(
        string='Итого Сбер',
        compute='_compute_total_sber',
        readonly=False,
        store=True,
        tracking=True
    )

    total_sber_management = fields.Float(
        string='Итого Сбер упр',
        compute='_compute_total_sber_management',
        readonly=False,
        store=True,
        tracking=True
    )

    overall_sber_percent = fields.Float(
        string='Общий процент Сбер',
        compute='_compute_overall_sber_percent',
        readonly=False,
        store=True,
        tracking=True
    )

    rate_real_sber = fields.Float(
        string='Заявка по курсу реальный Сбер',
        compute='_compute_rate_real_sber',
        readonly=False,
        store=True,
        tracking=True
    )

    sber_payment_cost = fields.Float(
        string='Расход за проведение платежа',
        compute='_compute_sber_payment_cost',
        readonly=False,
        store=True,
        digits=(16, 2),
    )

    payment_order_rf_sber = fields.Float(
        string='Расход платежа по РФ',
        compute='_compute_payment_order_rf_sber',
        help="""
        Расход платежа по РФ = (Заявка по курсу в рублях по договору + Вознаграждение по договору) × Процент (from Расход платежа по РФ(%))
        """,
        readonly=False,
        store=True,
        tracking=True
    )

    sber_operating_expenses = fields.Float(
        string='Расход на операционную деятельность',
        compute='_compute_sber_operating_expenses',
        readonly=False,
        store=True,
        tracking=True,
    )

    sber_operating_expenses_real = fields.Float(
        string='Расход на операционную деятельность в валюте заявки',
        compute='_compute_sber_operating_expenses_real',
        readonly=False,
        store=True,
        tracking=True,
    )

    sber_operating_expenses_real_usd = fields.Float(
        string='Расход на операционную деятельность в эквиваленте $',
        compute='_compute_sber_operating_expenses_real_usd',
        readonly=False,
        store=True,
        tracking=True,
    )

    sber_operating_expenses_real_rub = fields.Float(
        string='Расход на операционную деятельность ₽',
        compute='_compute_sber_operating_expenses_real_rub',
        readonly=False,
        store=True,
        tracking=True,
    )

    kupili_valyutu_sber = fields.Float(
        string='Купили валюту',
        compute='_compute_kupili_valyutu_sber',
        readonly=False,
        store=True,
        tracking=True
    )

    kupili_valyutu_sber_real = fields.Float(
        string='Купили валюту в валюте заявки',
        compute='_compute_kupili_valyutu_sber_real',
        readonly=False,
        store=True,
        tracking=True
    )

    kupili_valyutu_sber_real_usd = fields.Float(
        string='Купили валюту в эквиваленте $',
        compute='_compute_kupili_valyutu_sber_real_usd',
        readonly=False,
        store=True,
        tracking=True
    )

    kupili_valyutu_sber_real_rub = fields.Float(
        string='Купили валюту ₽',
        compute='_compute_kupili_valyutu_sber_real_rub',
        readonly=False,
        store=True,
        tracking=True
    )

    sber_payment_cost_usd = fields.Float(
        string='Расход за проведение платежа $',
        compute='_compute_sber_payment_cost_usd',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    sber_payment_cost_rub = fields.Float(
        string='Расход за проведение платежа ₽',
        compute='_compute_sber_payment_cost_rub',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    sber_payment_cost_on_usd = fields.Float(
        string='Расход за проведение платежа в $ Сбер',
        compute='_compute_sber_payment_cost_on_usd',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    sber_payment_cost_on_usd_real = fields.Float(
        string='Расход за проведение платежа в $ Сбер в валюте заявки',
        compute='_compute_sber_payment_cost_on_usd_real',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    sebestoimost_denej_sber = fields.Float(
        string='Себестоимость денег',
        compute='_compute_sebestoimost_denej_sber',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    sebestoimost_denej_sber_real = fields.Float(
        string='Себестоимость денег в валюте заявки',
        compute='_compute_sebestoimost_denej_sber_real',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    sebestoimost_denej_sber_real_usd = fields.Float(
        string='Себестоимость денег в эквиваленте $',
        compute='_compute_sebestoimost_denej_sber_real_usd',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    sebestoimost_denej_sber_real_rub = fields.Float(
        string='Себестоимость денег ₽',
        compute='_compute_sebestoimost_denej_sber_real_rub',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    fin_res_sber = fields.Float(
        string='Фин рез',
        compute='_compute_fin_res_sber',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    fin_res_sber_real = fields.Float(
        string='Фин рез в валюте заявки',
        compute='_compute_fin_res_sber_real',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
        help="""
        Если вид сделки "Экспорт": Фин рез в валюте заявки = (Сумма заявки × % Вознаграждения) - Расход за проведение платежа - Расход на операционную деятельность в валюте заявки
        
        Если Агент "Тезер" ИЛИ Валюта "USDT" ИЛИ Вид сделки "Импорт-экспорт/Экспорт-импорт":
        • Если Контрагент "А7": Фин рез в валюте заявки = (Сумма заявки × % Вознаграждения) - Расход на операционную деятельность в валюте заявки - Расход за проведение платежа
        • Иначе: Фин рез в валюте заявки = (Сумма заявки × Скрытая комиссия) - Расход на операционную деятельность в валюте заявки - Расход за проведение платежа

        Обычный расчет: Фин рез в валюте заявки = Купили валюту в валюте заявки - Расход за проведение платежа - Себестоимость денег в валюте заявки - Скрытая комиссия Партнера в валюте заявки - Расход на операционную деятельность в валюте заявки - Сумма заявки - Сумма плательщику по валюте заявки"""
    )

    fin_res_sber_real_usd = fields.Float(
        string='Фин рез в эквиваленте $',
        compute='_compute_fin_res_sber_real_usd',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
        help="""
        Фин рез в эквиваленте $ = Фин рез в валюте заявки × Кросс-курс $ к валюте заявки авто
        """
    )

    fin_res_sber_real_rub = fields.Float(
        string='Фин рез ₽',
        compute='_compute_fin_res_sber_real_rub',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
        help="""
        Фин рез ₽ = Фин рез в эквиваленте $ × Курс Джес
        """
    )

    # GROUP: Совок
    our_sovok_reward = fields.Float(
        string='Вознаграждение наше Совок',
        compute='_compute_our_sovok_reward',
        readonly=False,
        store=True,
        tracking=True
    )

    sovok_reward = fields.Float(
        string='Вознаграждение по договору Совок',
        compute='_compute_sovok_reward',
        readonly=False,
        store=True,
        tracking=True
    )

    total_sovok = fields.Float(
        string='Итого Совок',
        compute='_compute_total_sovok',
        readonly=False,
        store=True,
        tracking=True
    )

    total_sovok_management = fields.Float(
        string='Итого Совок упр',
        compute='_compute_total_sovok_management',
        readonly=False,
        store=True,
        tracking=True
    )

    overall_sovok_percent = fields.Float(
        string='Общий процент Совок',
        compute='_compute_overall_sovok_percent',
        readonly=False,
        store=True,
        tracking=True
    )

    payment_cost_sovok = fields.Float(
        string='Расход за проведение платежа',
        compute='_compute_payment_cost_sovok',
        readonly=False,
        store=True,
    )

    payment_order_rf_sovok = fields.Float(
        string='Расход платежа по РФ',
        compute='_compute_payment_order_rf_sovok',
        help="""
        Расход платежа по РФ = (Заявка по курсу в рублях по договору + Вознаграждение по договору Совок) × Процент (from Расход платежа по РФ(%))
        """,
        readonly=False,
        store=True,
        tracking=True
    )

    operating_expenses_sovok_partner = fields.Float(
        string='Расход на операционную деятельность партнер',
        compute='_compute_operating_expenses_sovok_partner',
        readonly=False,
        store=True,
        tracking=True
    )

    operating_expenses_sovok_real = fields.Float(
        string='Расход на операционную деятельность в валюте заявки',
        compute='_compute_operating_expenses_sovok_real',
        help="""Если Вид сделки 'Экспорт': Расход на операционную деятельность в валюте заявки = Процент (from Операционные расходы (%)) * Сумма заявки
        Иначе:
        — Если Итого Совок = 0 или Курс после конвертации в валюте заявки = 0: Расход на операционную деятельность в валюте заявки = 0
        — Если Агент 'Тезер' или Валюта 'USDT' или Вид сделки 'Импорт-Экспорт' или Вид сделки 'Экспорт-Импорт': Расход на операционную деятельность в валюте заявки = Сумма заявки × Процент (from Операционные расходы (%))
        — Иначе: Расход на операционную деятельность в валюте заявки = ((Процент (from Операционные расходы (%)) - Корректировка) × Итого Совок) ÷ Курс после конвертации в валюте заявки""",
        readonly=False,
        store=True,
        tracking=True
    )

    operating_expenses_sovok_real_usd = fields.Float(
        string='Расход на операционную деятельность в эквиваленте $',
        compute='_compute_operating_expenses_sovok_real_usd',
        help="""Расход на операционную деятельность в эквиваленте $ = Расход на операционную деятельность в валюте заявки × Кросс-курс $ к валюте заявки авто""",
        readonly=False,
        store=True,
        tracking=True
    )

    operating_expenses_sovok_real_rub = fields.Float(
        string='Расход на операционную деятельность ₽',
        compute='_compute_operating_expenses_sovok_real_rub',
        help="""Расход на операционную деятельность ₽ = Расход на операционную деятельность в эквиваленте $ × Курс Джес""",
        readonly=False,
        store=True,
        tracking=True
    )

    kupili_valyutu_sovok_partner = fields.Float(
        string='Купили валюту Партнер',
        compute='_compute_kupili_valyutu_sovok_partner',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True
    )

    kupili_valyutu_sovok_real = fields.Float(
        string='Купили валюту в валюте заявки',
        compute='_compute_kupili_valyutu_sovok_real',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True
    )

    kupili_valyutu_sovok_real_usd = fields.Float(
        string='Купили валюту в эквиваленте $',
        compute='_compute_kupili_valyutu_sovok_real_usd',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True
    )

    kupili_valyutu_sovok_real_rub = fields.Float(
        string='Купили валюту ₽',
        compute='_compute_kupili_valyutu_sovok_real_rub',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True
    )

    payment_cost_sovok_partner_usd = fields.Float(
        string='Расход за проведение платежа в $ Партнер',
        compute='_compute_payment_cost_sovok_partner_usd',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True
    )

    payment_cost_sovok_real_usd = fields.Float(
        string='Расход за проведение платежа в $ в валюте заявки',
        compute='_compute_payment_cost_sovok_real_usd',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    payment_cost_sovok_real_rub = fields.Float(
        string='Расход за проведение платежа в ₽ в валюте заявки',
        compute='_compute_payment_cost_sovok_real_rub',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    sebestoimost_denej_sovok_real = fields.Float(
        string='Себестоимость денег в валюте заявки',
        compute='_compute_sebestoimost_denej_sovok_real',
        help="""Если агент "Тезер": Себестоимость денег в валюте заявки = 0
        Иначе:
        — Если Кредитный период (from Себестоимость денег(%)) = 0: Себестоимость денег в валюте заявки = 0
        — Иначе: Себестоимость денег в валюте заявки = ((Дата + Колво доп дней (from Себестоимость денег(%))) ÷ Кредитный период (from Себестоимость денег(%))) × Ставка по кредиту (from Себестоимость денег(%)) × Купили валюту в валюте заявки""",
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    sebestoimost_denej_sovok_real_usd = fields.Float(
        string='Себестоимость денег в эквиваленте $',
        compute='_compute_sebestoimost_denej_sovok_real_usd',
        help="""Себестоимость денег в эквиваленте $ = Себестоимость денег в валюте заявки × Кросс-курс $ к валюте заявки авто""",
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    sebestoimost_denej_sovok_real_rub = fields.Float(
        string='Себестоимость денег ₽',
        compute='_compute_sebestoimost_denej_sovok_real_rub',
        help="""Себестоимость денег ₽ = Себестоимость денег в эквиваленте $ × Курс Джес""",
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    fin_res_sovok_partner = fields.Float(
        string='Фин рез Партнер',
        compute='_compute_fin_res_sovok_partner',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    fin_res_sovok_real = fields.Float(
        string='Фин рез в валюте заявки',
        compute='_compute_fin_res_sovok_real',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
        help="""Если вид сделки "Экспорт": Фин рез Совок в валюте заявки = (Сумма заявки × % Вознаграждения) - Расход за проведение платежа - Расход на операционную деятельность в валюте заявки
        
        Если Агент "Тезер" ИЛИ Валюта "USDT" ИЛИ Вид сделки "Импорт-экспорт/Экспорт-импорт":
        • Если Контрагент "А7": Фин рез Совок в валюте заявки = (Сумма заявки × % Вознаграждения) - Расход на операционную деятельность в валюте заявки - Расход за проведение платежа
        • Иначе: Фин рез = (Сумма заявки × Скрытая комиссия) - Расход на операционную деятельность в валюте заявки - Расход за проведение платежа

        Обычный расчет: Фин рез Совок в валюте заявки = Купили валюту в валюте заявки - Расход за проведение платежа - Себестоимость денег в валюте заявки - Скрытая комиссия Партнера в валюте заявки - Расход на операционную деятельность в валюте заявки - Сумма заявки - Сумма плательщику по валюте заявки"""
    )

    fin_res_sovok_real_usd = fields.Float(
        string='Фин рез в эквиваленте $',
        compute='_compute_fin_res_sovok_real_usd',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
        help="""
        Фин рез Совок в эквиваленте $ = Фин рез Совок в валюте заявки × Кросс-курс $ к валюте заявки авто
        """
    )

    fin_res_sovok_real_rub = fields.Float(
        string='Фин рез ₽',
        compute='_compute_fin_res_sovok_real_rub',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
        help="""
        Фин рез ₽ = Фин рез в эквиваленте $ × Курс Джес
        """
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
        [('import', 'Импорт'), ('export', 'Экспорт'), ('import_export', 'Импорт-экспорт'), ('export_import', 'Экспорт-импорт')],
        string='Вид сделки',
        tracking=True,
    )

    instruction_number = fields.Char(string='Номер поручения', tracking=True)

    instruction_signed_date = fields.Date(string='Подписано поручение', tracking=True)

    usd_equivalent = fields.Float(
        string='USD эквивалент',
        compute='_compute_usd_equivalent',
        readonly=False,
        store=True,
        tracking=True
    )

    jess_rate_id = fields.Many2one(
        'amanat.jess_rate', 
        string='Курс Джесс', 
        tracking=True,
        domain="[('currency', '=', currency)]"
    )

    jess_rate = fields.Float(string='Курс Джесс', related='jess_rate_id.rate', tracking=True, digits=(16, 6))

    currency = fields.Selection(
        [
            ('rub', 'RUB'), ('rub_cashe', 'RUB КЭШ'),
            ('usd', 'USD'), ('usd_cashe', 'USD КЭШ'),
            ('usdt', 'USDT'),
            ('euro', 'EURO'), ('euro_cashe', 'EURO КЭШ'),
            ('cny', 'CNY'), ('cny_cashe', 'CNY КЭШ'),
            ('aed', 'AED'), ('aed_cashe', 'AED КЭШ'),
            ('thb', 'THB'), ('thb_cashe', 'THB КЭШ'),
            ('idr', 'IDR'), ('idr_cashe', 'IDR КЭШ'),
            ('inr', 'INR'), ('inr_cashe', 'INR КЭШ'),
        ],
        string='Валюта',
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
        readonly=False,
        store=True,
        tracking=True
    )

    conversion_expenses_currency = fields.Float(
        string='Расходы на конвертацию в валюте',
        compute='_compute_conversion_expenses_currency',
        readonly=False,
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
        readonly=False,
        store=True,
        digits=(16, 4),
        tracking=True
    )

    amount = fields.Float(string='Сумма заявки', tracking=True, digits=(16, 3))

    payment_expense_in_currency = fields.Float(
        string='Расход платежа в валюте',
        compute='_compute_payment_expense_in_currency',
        readonly=False,
        store=True,
        tracking=True,
        help="""Рассчитывается как: Сумма заявки × соответствующий расход платежа
        - Для Сбербанка: Сумма заявки × Расход за проведение платежа (Сбер)
        - Для Совкомбанка: Сумма заявки × Расход за проведение платежа (Совок)
        - Для обычных клиентов: Сумма заявки × Расход за проведение платежа в валюте заявки"""
    )

    vip_conditions = fields.Char(string='Условия VIP', tracking=True)

    price_list_profit_id = fields.Many2one(
        'amanat.price_list_payer_profit', 
        string='Процент плательщика', 
        tracking=True,
        domain="[('payer_subagent_ids', 'in', subagent_payer_ids)]"
    )

    vip_commission = fields.Float(string='Комиссия VIP', digits=(16, 1), tracking=True)

    hidden_commission = fields.Float(string='Скрытая комиссия', tracking=True)

    bank_commission = fields.Float(string='Комиссия +% банка', tracking=True)

    accreditation_commission = fields.Float(string='Комиссия + аккред', tracking=True)
    escrow_commission = fields.Float(string='Комиссия + эскроу', tracking=True)

    rate_field = fields.Float(string='Курс', tracking=True, digits=(16, 4))

    effective_rate = fields.Float(
        string='Эффективный курс',
        compute='_compute_effective_rate',
        store=True,
        digits=(16, 4),
        help='Лучший курс если доступен, иначе курс из поля rate_field'
    )

    hidden_rate = fields.Float(string='Скрытый курс', tracking=True)

    conversion_percent = fields.Float(string='% Конвертации', tracking=True)

    conversion_ratio = fields.Float(
        string="% Конвертации соотношение",
        compute='_compute_conversion_ratio',
        readonly=False,
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
        readonly=False,
        store=True,
        tracking=True
    )

    bank_cross_rate = fields.Float(string='Кросс-курс банка', tracking=True)

    plus_dollar = fields.Float(string='Надбавка в $', tracking=True)

    dollar_cross_rate = fields.Float(string='Кросс-курс $ к Валюте заявки', tracking=True)

    plus_currency = fields.Float(
        string='Надбавка в валюте заявки',
        compute='_compute_plus_currency',
        readonly=False,
        store=True,
        tracking=True
    )

    invoice_plus_percent = fields.Float(
        string='% надбавки от суммы инвойса',
        compute='_compute_invoice_plus_percent',
        readonly=False,
        store=True,
        tracking=True
    )

    reward_percent = fields.Float(
        string='% Вознаграждения',
        compute='_compute_reward_percent',
        readonly=False,
        store=True,
        tracking=True
    )

    hand_reward_percent = fields.Float(
        string='% Вознаграждения',
        tracking=True,
        digits=(16, 6)
    )

    reward_percent_in_contract = fields.Float(
        string='% Вознаграждения по договору',
        tracking=True,
        digits=(16, 6)
    )

    equivalent_amount_usd = fields.Float(
        string='Сумма эквивалент $',
        compute='_compute_equivalent_amount_usd',
        readonly=False,
        store=True,
        tracking=True
    )

    total_fact = fields.Float(
        string='Итого факт',
        compute='_compute_total_fact',
        readonly=False,
        store=True,
        tracking=True
    )

    rate_fixation_date = fields.Date(
        string='Дата фиксации курса',
        tracking=True
    )

    assignment_signed_sovcom = fields.Date(
        string='Подписано поручение (для Совкомбанка)',
        tracking=True,
    )

    calculated_percent = fields.Float(
        string='Рассчетный %',
        compute='_compute_calculated_percent',
        readonly=False,
        store=True,
        tracking=True
    )

    contract_reward = fields.Float(
        string='Вознаграждение по договору',
        compute='_compute_contract_reward',
        readonly=False,
        store=True,
        tracking=True
    )

    sum_from_extracts = fields.Float(
        string='Сумма (from Выписка разнос)', 
        compute='_compute_sum_from_extracts', 
        readonly=False,
        store=True, 
        tracking=True
    )

    rate_real = fields.Float(
        string='Заявка по курсу реальный',
        compute='_compute_rate_real',
        readonly=False,
        store=True,
        tracking=True
    )

    agent_reward = fields.Float(
        string='Агентское вознаграждение',
        compute='_compute_agent_reward',
        readonly=False,
        store=True,
        tracking=True
    )

    actual_reward = fields.Float(
        string='Фактическое вознаграждение',
        compute='_compute_actual_reward',
        readonly=False,
        store=True,
        tracking=True
    )

    non_agent_reward = fields.Float(
        string='Агентское не наше',
        compute='_compute_non_agent_reward',
        readonly=False,
        store=True,
        tracking=True
    )

    agent_our_reward = fields.Float(
        string='Агентское наше',
        compute='_compute_agent_our_reward',
        readonly=False,
        store=True,
        tracking=True
    )

    total_reward = fields.Float(
        string='Общее вознаграждение',
        compute='_compute_total_reward',
        readonly=False,
        store=True,
        tracking=True
    )

    total_amount = fields.Float(
        string='ИТОГО',
        compute='_compute_total_amount',
        readonly=False,
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

    accreditive_revealed_date = fields.Date(string='аккредитив раскрыт', tracking=True)

    act_report_signed_date = fields.Date(string='подписан акт-отчет', tracking=True)

    deal_closed_date = fields.Date(string='сделка закрыта', tracking=True)

    deal_cycle_days = fields.Integer(
        string='Цикл сделки, дн', 
        compute='_compute_deal_cycle_days',
        readonly=False,
        store=True,
        tracking=True
    )

    payment_purpose = fields.Text(string='Назначение платежа', tracking=True)

    subagent_ids = fields.Many2many('amanat.contragent', string='Субагент', tracking=True)

    # Корректируем домен в subagent_payer_ids
    subagent_payer_ids = fields.Many2many(
        'amanat.payer',
        string='Плательщик Субагента',
        domain="[('id', 'in', domain_subagent_payer_ids or [])]",
        tracking=True
    )

    domain_subagent_payer_ids = fields.Json(string='Домен плательщика субагента', compute='_compute_domain_subagent_payer_ids', store=True)

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
            ('1', 'Возврат с последующей оплатой'),
            ('2', 'Возврат с возвратом основной суммы'),
            ('3', 'Возврат с возвратом всей суммы'),
            ('4', 'Возврат с частичной оплатой вознаграждения'),
            ('5', 'Возврат на предоплату следующего заказа'),
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

    # Computed поле для отображения красного индикатора только для Ильзиры  
    show_red_stripe_for_ilzira_zayavka = fields.Char(
        string="Индикатор для Ильзиры (Заявки)", 
        compute="_compute_show_red_stripe_for_ilzira_zayavka", 
        store=False
    )

    bank_vypiska = fields.Char(
        string='Банк Выписка',
        compute='_compute_bank_vypiska',
        store=True,
        tracking=True
    )

    payer_profit_currency = fields.Float(
        string='Сумма плательщику по валюте заявки',
        compute='_compute_payer_profit_currency',
        help="""
        Сумма плательщику по валюте заявки = Сумма × % Начисления (from Процент плательщика)
        """,
        readonly=False,
        store=True,
        tracking=True
    )

    price_list_percent_accrual = fields.Float(
        string='% Начисления (from Процент плательщика)',
        related='price_list_profit_id.percent_accrual',
        store=True,
        readonly=True,
        tracking=True
    )

    zayavka_attachments = fields.Many2many(
        'ir.attachment', 
        'zayavka_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Заявка Вход'
    )

    zayavka_link = fields.Char(string='Заявка ссылка', tracking=True)

    invoice_attachments = fields.Many2many(
        'ir.attachment', 
        'invoice_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Инвойс'
    )

    invoice_link = fields.Char(string='Инвойс ссылка', tracking=True)

    assignment_attachments = fields.Many2many(
        'ir.attachment', 
        'assignment_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Поручение'
    )

    assignment_link = fields.Char(string='Поручение ссылка', tracking=True)

    swift_attachments = fields.Many2many(
        'ir.attachment', 
        'swift_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='SWIFT'
    )

    swift_link = fields.Char(string='SWIFT ссылка', tracking=True)

    swift103_attachments = fields.Many2many(
        'ir.attachment', 
        'swift103_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='SWIFT 103'
    )

    swift103_link = fields.Char(string='SWIFT 103 ссылка', tracking=True)

    swift199_attachments = fields.Many2many(
        'ir.attachment', 
        'swift199_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='SWIFT 199'
    )

    swift199_link = fields.Char(string='SWIFT 199 ссылка', tracking=True)

    report_attachments = fields.Many2many(
        'ir.attachment', 
        'report_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Акт-отчет'
    )

    report_link = fields.Char(string='Акт-отчет ссылка', tracking=True)

    other_documents_attachments = fields.Many2many(
        'ir.attachment', 
        'other_documents_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Прочие документы'
    )

    zayavka_end_attachments = fields.Many2many(
        'ir.attachment', 
        'zayavka_end_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Заявка Выход'
    )

    assignment_end_attachments = fields.Many2many(
        'ir.attachment', 
        'assignment_end_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Поручение Выход'
    )

    screen_sber_attachments = fields.Many2many(
        'ir.attachment', 
        'screen_sber_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Cкрин сбер'
    )

    # Недостающие поля для реорганизации документов
    additional_agreement_attachments = fields.Many2many(
        'ir.attachment', 
        'additional_agreement_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Доп соглашение к поручению'
    )

    assignment_input_attachments = fields.Many2many(
        'ir.attachment', 
        'assignment_input_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Поручение вход'
    )

    # Переименование для консистентности - заменяем zayavka_start_attachments на zayavka_attachments
    zayavka_attachments = fields.Many2many(
        'ir.attachment', 
        'zayavka_attachment_rel', 
        'zayavka_id', 
        'attachment_id', 
        string='Заявка вход'
    )

    # Поле для отображения документов договоров контрагента
    contragent_contract_attachments = fields.Many2many(
        'ir.attachment',
        compute='_compute_contragent_contract_attachments',
        store=True,
        readonly=False,
        string='Договоры контрагента'
    )

    contract_attachments = fields.Many2many(
        'ir.attachment',
        'amanat_zayavka_contract_attachment_rel',
        'zayavka_id',
        'attachment_id',
        string='Контракт'
    )

    contract_appendix_attachments = fields.Many2many(
        'ir.attachment',
        'amanat_zayavka_contract_appendix_attachment_rel',
        'zayavka_id',
        'attachment_id',
        string='Приложение к контракту'
    )

    vbk_attachments = fields.Many2many(
        'ir.attachment',
        'amanat_zayavka_vbk_attachment_rel',
        'zayavka_id',
        'attachment_id',
        string='ВБК'
    )

    invoice_primary_attachments = fields.Many2many(
        'ir.attachment',
        'amanat_zayavka_invoice_primary_attachment_rel',
        'zayavka_id',
        'attachment_id',
        string='Инвойс первичный'
    )

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
        string='Поступление на PC',
        tracking=True,
    )

    waiting_for_replenishment = fields.Float(
        string='Ожидаем пополнения',
        compute='_compute_waiting_for_replenishment',
        readonly=False,
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
        readonly=False,
        store=True,
        tracking=True
    )

    error_sber = fields.Float(
        string='Ошибка Сбер',
        compute='_compute_error_sber',
        store=True,
        readonly=False,
        tracking=True
    )

    error_in_rate = fields.Selection(
        [
            ('error', 'Ошибка в курсе')
        ],
        string='Ошибка в курсе',
        default='error',
        store=True,
        tracking=True
    )

    error_in_bank_rate = fields.Selection(
        [
            ('error', 'Ошибка в курсе банка')
        ],
        string='Ошибка в курсе банка',
        default='error',
        store=True,
        tracking=True
    )

    error_in_xe_rate = fields.Selection(
        [
            ('error', 'Ошибка в курсе XE')
        ],
        string='Ошибка в курсе XE',
        default='error',
        store=True,
        tracking=True
    )

    price_list_carrying_out_id = fields.Many2one(
        'amanat.price_list_payer_carrying_out',
        string='Расход за проведение платежа(%)',
        tracking=True,
        domain="[('payer_partners', 'in', subagent_payer_ids)]"
    )

    price_list_carrying_out_accrual_percentage = fields.Float(
        string='% Начисления (from Расход за проведение платежа(%))',
        related='price_list_carrying_out_id.accrual_percentage',
        store=True,
        readonly=True,
        tracking=True,
    )

    price_list_carrying_out_fixed_deal_fee = fields.Float(
        string='Фикс за сделку $ (from Расход за проведение платежа(%))',
        related='price_list_carrying_out_id.fixed_deal_fee',
        store=True,
        readonly=True,
        tracking=True,
    )

    payment_order_rule_id = fields.Many2one(
        'amanat.payment_order_rule',
        string='Расход платежа по РФ(%)',
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
        string="Процент (from Расход платежа по РФ(%))",
        related='payment_order_rule_id.percent',
        store=True,
        tracking=True
    )
    
    partner_post_conversion_rate = fields.Float(
        string='Курс после конвертации партнер',
        compute='_compute_partner_post_conversion_rate',
        readonly=False,
        store=True,
        tracking=True
    )

    payer_cross_rate_usd = fields.Float(
        string='Кросс-курс $ к валюте заявки',
        digits=(16, 4),
        tracking=True
    )

    payer_cross_rate_usd_auto = fields.Float(
        string='Кросс-курс $ к валюте заявки авто',
        compute='_compute_payer_cross_rate_usd_auto',
        help="""
        — если пусты «Кросс-курс $ к валюте заявки» и «Курс XE» и валюта USD ÷ USD КЭШ: Кросс-курс $ к валюте заявки авто = 1; 
        — если задан «Кросс-курс $ к валюте заявки»: Кросс-курс $ к валюте заявки авто = Кросс-курс $ к валюте заявки; 
        — иначе: Кросс-курс $ к валюте заявки авто = Курс XE
        """,
        readonly=False,
        store=True,
        digits=(16, 4),
        tracking=True
    )

    real_post_conversion_rate = fields.Float(
        string='Курс после конвертации в валюте заявки',
        compute='_compute_real_post_conversion_rate',
        help="""
        Курс после конвертации в валюте заявки = Курс Джесс
        """,
        readonly=False,
        store=True,
        digits=(16, 6),
        tracking=True
    )

    real_post_conversion_rate_usd = fields.Float(
        string='Курс после конвертации в эквиваленте $',
        compute='_compute_real_post_conversion_rate_usd',
        help="""
        Курс после конвертации в эквиваленте $ = Курс после конвертации в валюте заявки × Кросс-курс $ к валюте заявки авто
        """,
        readonly=False,
        store=True,
        digits=(16, 6),
        tracking=True
    )

    payer_cross_rate_rub = fields.Float(
        string='Курс Джес',
        compute='_compute_payer_cross_rate_rub',
        readonly=False,
        store=True,
        digits=(16, 6),
        tracking=True
    )

    real_post_conversion_rate_rub = fields.Float(
        string='Курс после конвертации руб. ₽',
        compute='_compute_real_post_conversion_rate_rub',
        readonly=False,
        store=True,
        help="""
        Курс после конвертации руб. ₽ = Курс после конвертации в эквиваленте $ × Курс Джес
        """,
        digits=(16, 6),
        tracking=True
    )

    payer_profit_usd = fields.Float(
        string='Сумма плательщику $',
        help="""
        — если задан «Кросс-курс $ к валюте заявки авто»: Сумма плательщику $ = Прибыль Плательщика по валюте заявки × Кросс-курс $ к валюте заявки авто × Фикс за сделку $ (из Процент плательщика); 
        — иначе: Сумма плательщику $ = Фикс за сделку $ (из Процент плательщика)
        """,
        compute='_compute_payer_profit_usd',
        readonly=False,
        store=True,
        tracking=True
    )

    payer_profit_rub = fields.Float(
        string='Сумма плательщику ₽',
        compute='_compute_payer_profit_rub',
        help="""Сумма плательщику ₽ = Сумма плательщику $ × Курс Джес""",
        readonly=False,
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
        readonly=False,
        tracking=True,
        store=True
    )

    sebestoimost_denej_sovok_partner = fields.Float(
        string='Себестоимость денег Партнер',
        compute='_compute_sebestoimost_denej_sovok_partner',
        readonly=False,
        store=True,
        digits=(16, 2),
        tracking=True,
    )

    money_cost_rule_id = fields.Many2one(
        'amanat.money_cost_rule',
        string='Себестоимость денег(%)',
        tracking=True
    )

    money_cost_rule_credit_rate = fields.Float(
        string="Ставка по кредиту (from Себестоимость денег(%))",
        related='money_cost_rule_id.credit_rate',
        store=True,
        tracking=True
    )

    money_cost_rule_credit_period = fields.Integer(
        string="Кредитный период (from Себестоимость денег(%))",
        related='money_cost_rule_id.credit_period',
        store=True,
        tracking=True
    )

    money_cost_rule_extra_days = fields.Integer(
        string="Колво доп дней (from Себестоимость денег(%))",
        related='money_cost_rule_id.extra_days',
        store=True,
        tracking=True
    )

    expense_rule_id = fields.Many2one(
        'amanat.expense_rule',
        string='Операционные расходы (%)',
        tracking=True
    )

    percent_from_expense_rule = fields.Float(
        string="Процент (from Операционные расходы (%))",
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
        'amanat.price_list_partners', string='Выплата 1-го партнера(%)'
    )

    price_list_partners_id_accrual_percentage = fields.Float(
        string='% Начисления (from Выплата 1-го партнера(%))',
        related='price_list_partners_id.accrual_percentage',
        store=True,
        readonly=True,
        tracking=True
    )

    price_list_partners_id_fixed_deal_fee = fields.Float(
        string='Фикс за сделку $ (from Выплата 1-го партнера(%))',
        related='price_list_partners_id.fixed_deal_fee',
        store=True,
        readonly=True,
        tracking=True
    )

    price_list_partners_id_2 = fields.Many2one(
        'amanat.price_list_partners', string='Выплата 2-го партнера(%)'
    )

    price_list_partners_id_2_accrual_percentage = fields.Float(
        string='% Начисления (from Выплата 2-го партнера(%))',
        related='price_list_partners_id_2.accrual_percentage',
        store=True,
        readonly=True,
        tracking=True
    )

    price_list_partners_id_2_fixed_deal_fee = fields.Float(
        string='Фикс за сделку $ (from Выплата 2-го партнера(%))',
        related='price_list_partners_id_2.fixed_deal_fee',
        store=True,
        readonly=True,
        tracking=True
    )

    price_list_partners_id_3 = fields.Many2one(
        'amanat.price_list_partners', string='Выплата 3-го партнера(%)'
    )

    price_list_partners_id_3_accrual_percentage = fields.Float(
        string='% Начисления (from Выплата 3-го партнера(%))',
        related='price_list_partners_id_3.accrual_percentage',
        store=True,
        readonly=True,
        tracking=True
    )

    price_list_partners_id_3_fixed_deal_fee = fields.Float(
        string='Фикс за сделку $ (from Выплата 3-го партнера(%))',
        related='price_list_partners_id_3.fixed_deal_fee',
        store=True,
        readonly=True,
        tracking=True
    )

    price_list_partners_id_4 = fields.Many2one(
        'amanat.price_list_partners', string='Выплата 4-го партнера(%)'
    )

    price_list_partners_id_4_accrual_percentage = fields.Float(
        string='% Начисления (from Выплата 4-го партнера(%))',
        related='price_list_partners_id_4.accrual_percentage',
        store=True,
        readonly=True,
        tracking=True
    )

    price_list_partners_id_4_fixed_deal_fee = fields.Float(
        string='Фикс за сделку $ (from Выплата 4-го партнера(%))',
        related='price_list_partners_id_4.fixed_deal_fee',
        store=True,
        readonly=True,
        tracking=True
    )

    price_list_partners_id_5 = fields.Many2one(
        'amanat.price_list_partners', string='Выплата 5-го партнера(%)'
    )

    price_list_partners_id_5_accrual_percentage = fields.Float(
        string='% Начисления (from Выплата 5-го партнера(%))',
        related='price_list_partners_id_5.accrual_percentage',
        store=True,
        readonly=True,
        tracking=True
    )

    price_list_partners_id_5_fixed_deal_fee = fields.Float(
        string='Фикс за сделку $ (from Выплата 5-го партнера(%))',
        related='price_list_partners_id_5.fixed_deal_fee',
        store=True,
        readonly=True,
        tracking=True
    )

    hidden_partner_commission = fields.Float(
        string='Скрытая комиссия Партнера',
        compute='_compute_hidden_partner_commission',
        readonly=False,
        store=True,
        tracking=True
    )

    hidden_partner_commission_real = fields.Float(
        string='Скрытая комиссия Партнера в валюте заявки',
        compute='_compute_hidden_partner_commission_real',
        help="""Если стоит галочка 'Заявка со скрытым курсом': Скрытая комиссия Партнера в валюте заявки = Заявка по курсу реальный * Сумма всех % начислений от Выплат пратнеров / Курс Джесс
        Если стоит галочка 'Расчет заявки, как Сбербанк': Скрытая комиссия Партнера в валюте заявки = Сумма заявки * Сумма всех % начислений от Выплат пратнеров
        Иначе: Скрытая комиссия Партнера в валюте заявки = Вознаграждение не наше Клиент / Курс Джесс""",
        readonly=False,
        store=True,
        tracking=True
    )

    hidden_partner_commission_real_usd = fields.Float(
        string='Скрытая комиссия Партнера в эквиваленте $',
        compute='_compute_hidden_partner_commission_real_usd',
        help="""Скрытая комиссия Партнера в эквиваленте $ = Скрытая комиссия Партнера в валюте заявки × Кросс-курс $ к валюте заявки авто""",
        readonly=False,
        store=True,
        tracking=True
    )

    hidden_partner_commission_real_rub = fields.Float(
        string='Скрытая комиссия Партнера ₽',
        compute='_compute_hidden_partner_commission_real_rub',
        help="""Скрытая комиссия Партнера ₽ = Скрытая комиссия Партнера в эквиваленте $ × Курс Джес""",
        readonly=False,
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
        string="Обновить список правил",
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
        readonly=False,
        tracking=True,
        store=True  # Если нужно хранить в БД
    )

    is_sberbank_contragent = fields.Boolean(
        string='Расчет заявки, как Сбербанк',
        default=False,
    )

    is_sovcombank_contragent = fields.Boolean(
        string='Заявка со скрытым курсом',
        default=False,
    )

    # Возвраты
    cross_return = fields.Boolean(string='Возврат по кроссу', default=False, tracking=True)
    cross_return_date = fields.Date(string='Дата возврата платежа', tracking=True)
    cross_return_currency_pair = fields.Selection(
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
        string='Валютная пара возврата по кроссу',
        tracking=True
    )
    cross_return_bank_rate = fields.Float(string='Кросс-курс банка возврата по кроссу', tracking=True)
    cross_return_conversion_amount = fields.Float(
        string='Сумма после конвертации', 
        tracking=True, 
        readonly=False,
        compute='_compute_cross_return_conversion_amount'
    )

    # Поля для возврата с последующей оплатой (problem_stage == '1')
    change_payer = fields.Boolean(string='Сменить плательщика', default=False, tracking=True)

    return_commission = fields.Float(
        string='Комиссия на возврат',
        tracking=True,
    )

    return_subagent = fields.Many2one(
        'amanat.contragent',
        string='Субагент для возврата',
        tracking=True,
    )

    domain_return_payer_subagent = fields.Json(string='Домен плательщика субагента', compute='_compute_domain_return_payer_subagent', store=True)

    payers_for_return = fields.Many2many(
        'amanat.payer',
        'amanat_zayavka_payer_return_rel',  # Уникальная таблица связи
        'zayavka_id',
        'payer_id',
        domain="[('id', 'in', domain_return_payer_subagent or [])]",
        string='Плательщик для возврата',
        tracking=True,
    )

    possible_payers = fields.Many2many(
        'amanat.payer',
        compute='_compute_possible_payers',
        store=False,  # Не храним в БД, только для domain
    )

    payment_date_again_1 = fields.Date(
        string='Передано в оплату (Импорт) повторно',
        tracking=True,
    )

    supplier_currency_paid_date_again_1 = fields.Date(
        string='Оплачена валюта поставщику повторно',
        tracking=True,
    )

    supplier_currency_received_date_again_1 = fields.Date(
        string='Получена валюта поставщиком (Импорт) повторно',
        tracking=True,
    )

    payment_date_again_2 = fields.Date(
        string='Передано в оплату (Импорт) повторно',
        tracking=True,
    )

    supplier_currency_paid_date_again_2 = fields.Date(
        string='Оплачена валюта поставщику повторно',
        tracking=True,
    )

    supplier_currency_received_date_again_2 = fields.Date(
        string='Получена валюта поставщиком (Импорт) повторно',
        tracking=True,
    )

    payment_date_again_3 = fields.Date(
        string='Передано в оплату (Импорт) повторно',
        tracking=True,
    )

    supplier_currency_paid_date_again_3 = fields.Date(
        string='Оплачена валюта поставщику повторно',
        tracking=True,
    )

    supplier_currency_received_date_again_3 = fields.Date(
        string='Получена валюта поставщиком (Импорт) повторно',
        tracking=True,
    )

    payment_date_again_4 = fields.Date(
        string='Передано в оплату (Импорт) повторно',
        tracking=True,
    )

    supplier_currency_paid_date_again_4 = fields.Date(
        string='Оплачена валюта поставщику повторно',
        tracking=True,
    )

    supplier_currency_received_date_again_4 = fields.Date(
        string='Получена валюта поставщиком (Импорт) повторно',
        tracking=True,
    )

    payment_date_again_5 = fields.Date(
        string='Передано в оплату (Импорт) повторно',
        tracking=True,
    )

    supplier_currency_paid_date_again_5 = fields.Date(
        string='Оплачена валюта поставщику повторно',
        tracking=True,
    )

    supplier_currency_received_date_again_5 = fields.Date(
        string='Получена валюта поставщиком (Импорт) повторно',
        tracking=True,
    )

    # Поля для возврата с возвратом основной суммы (problem_stage == '2')
    return_amount_to_client = fields.Float(
        string='Сумма на возврат клиенту',
        help="""
        Указываем в рублях
        """,
        digits=(16, 2),
        tracking=True,
    )

    payment_order_date_to_client_account = fields.Date(
        string='Дата платежного поручения на расчетный счет клиента',
        tracking=True,
    )

    # Поля для возврата с возвратом всей суммы (problem_stage == '3')
    return_amount = fields.Float(
        string='Сумма на возврат',
        help="""
        Указываем в рублях
        """,
        digits=(16, 2),
        tracking=True,
    )

    payment_order_date_to_client_account_return_all = fields.Date(
        string='Дата возврата на расчетный счет клиента',
        tracking=True,
    )

    # Поля для возврата с частичной оплатой вознаграждения (problem_stage == '4')
    return_amount_to_reward = fields.Float(
        string='Сумма на возврат',
        help="""Указываем в валюте заявки""",
        digits=(16, 2),
        tracking=True,
    )

    return_amount_main = fields.Float(
        string='Основная сумма на возврат',
        help="""
        Указываем в рублях
        """,
        digits=(16, 2),
        tracking=True,
    )

    payment_order_date_to_return = fields.Date(
        string='Дата возврата на расчетный счет клиента',
        tracking=True,
    )

    # Поля для возврата на предоплату следующего заказа (problem_stage == '5')
    return_amount_prepayment_of_next = fields.Float(
        string='Сумма на возврат',
        digits=(16, 2),
        tracking=True,
    )

    payment_order_date_to_prepayment_of_next = fields.Date(
        string='Дата возврата на расчетный счет клиента',
        tracking=True,
    )

    prefix = fields.Boolean(string='Перефикс', default=False)
    hidden_hadge = fields.Boolean(string='Не отображать хэдж', default=False)

    beneficiary_address = fields.Char(string='Адрес получателя', tracking=True)
    beneficiary_bank_name = fields.Char(string='Наименование банка получателя', tracking=True)
    bank_address = fields.Char(string='Адрес банка получателя', tracking=True)
    iban_accc = fields.Char(string='IBAN/ACC', tracking=True)
    contract_number = fields.Char(string='№ контракта', tracking=True)
    
        # Поле для хранения сгенерированных документов
    zayavka_output_attachments = fields.One2many(
        'ir.attachment',
        'res_id',
        domain=[('res_model', '=', 'amanat.zayavka'), ('res_field', '=', 'zayavka_output_attachments')],
        string='Заявка Выход'
    )
    
    # Поле для хранения актов-отчетов
    act_report_attachments = fields.Many2many(
        'ir.attachment',
        'amanat_zayavka_act_report_attachment_rel',
        'zayavka_id',
        'attachment_id',
        string='Акт Отчет'
    )

    link_jess_rate = fields.Boolean(string='Обновить курс Джесс', default=False)

    kassa_name = fields.Char(
        string='Касса',
        compute='_compute_kassa_name',
        store=True,
        readonly=False,
        tracking=True,
        help="Касса автоматически подтягивается на основе выбранного контрагента"
    )

    agency_agreement = fields.Char(string='Агентский договор')

    @api.depends('contragent_id')
    def _compute_kassa_name(self):
        """Автоматически определяет кассу при выборе контрагента"""
        for record in self:
            if record.contragent_id:
                kassa_name = False
                
                # Ищем в Касса Иван
                kassa_ivan = self.env['amanat.kassa_ivan'].search([('contragent_id', '=', record.contragent_id.id)], limit=1)
                if kassa_ivan:
                    kassa_name = 'Касса Иван'
                else:
                    # Ищем в Касса 2
                    kassa_2 = self.env['amanat.kassa_2'].search([('contragent_id', '=', record.contragent_id.id)], limit=1)
                    if kassa_2:
                        kassa_name = 'Касса 2'
                    else:
                        # Ищем в Касса 3
                        kassa_3 = self.env['amanat.kassa_3'].search([('contragent_id', '=', record.contragent_id.id)], limit=1)
                        if kassa_3:
                            kassa_name = 'Касса 3'
                
                record.kassa_name = kassa_name
            else:
                record.kassa_name = False

    @api.onchange('contragent_id')
    def _onchange_contragent_id_kassa(self):
        """Обновляет кассу при изменении контрагента в интерфейсе"""
        if self.contragent_id:
            # Принудительно вызываем пересчет кассы
            self._compute_kassa_name()

    @api.depends('extract_delivery_ids')
    def _compute_show_red_stripe_for_ilzira_zayavka(self):
        """Показывать красный индикатор только для пользователя Ильзира, если выписки разнос не заполнены"""
        current_user = self.env.user
        for record in self:
            # Проверяем имя пользователя и пустое поле выписок разнос
            if current_user.name == 'Ильзира' and not record.extract_delivery_ids:
                record.show_red_stripe_for_ilzira_zayavka = "❌ НЕТ ВЫПИСОК"
            else:
                record.show_red_stripe_for_ilzira_zayavka = False

    @api.depends('contragent_id', 'contragent_id.contract_ids', 'contragent_id.contract_ids.contract_attachments', 'contragent_id.contract_ids.is_actual')
    def _compute_contragent_contract_attachments(self):
        """Подтягивает документы только из актуального договора выбранного контрагента"""
        for record in self:
            if record.contragent_id and record.contragent_id.contract_ids:
                # Ищем актуальный договор (с галочкой is_actual = True)
                actual_contract = record.contragent_id.contract_ids.filtered('is_actual')
                if actual_contract and actual_contract.contract_attachments:
                    record.contragent_contract_attachments = actual_contract.contract_attachments
                else:
                    record.contragent_contract_attachments = self.env['ir.attachment'].browse()
            else:
                record.contragent_contract_attachments = self.env['ir.attachment'].browse()

    @api.model
    def get_zayavka_action_context(self):
        """Динамически определяет контекст для action заявок в зависимости от группы пользователя"""
        context = {'default_status': '1_no_chat'}
        
        # Проверяем, является ли пользователь менеджером
        user = self.env.user
        manager_groups = [
            'amanat.group_amanat_manager',
            'amanat.group_amanat_senior_manager'
        ]
        
        # Если пользователь в группе менеджеров, применяем фильтр "Активные заявки"
        if any(user.has_group(group) for group in manager_groups):
            context['search_default_filter_active_zayavkas'] = 1
        
        return context

    @api.model
    def action_show_related_zayavkas_by_attachment(self, attachment_id=None):
        """Показать все заявки, к которым прикреплен данный документ"""
        print(f"=== action_show_related_zayavkas_by_attachment called with attachment_id={attachment_id} ===")
        if not attachment_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Ошибка!',
                    'message': 'ID документа не указан',
                    'type': 'warning',
                }
            }
        
        # Проверяем, существует ли такой attachment вообще
        attachment = self.env['ir.attachment'].browse(attachment_id)
        if not attachment.exists():
            print(f"DEBUG: Attachment with ID={attachment_id} does not exist!")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Ошибка!',
                    'message': f'Документ с ID {attachment_id} не найден в системе',
                    'type': 'warning',
                }
            }
        
        # Разделяем поля на Many2many и One2many
        many2many_fields = [
            'zayavka_attachments', 'invoice_attachments', 'assignment_attachments',
            'swift_attachments', 'swift103_attachments', 'swift199_attachments', 
            'report_attachments', 'other_documents_attachments', 'zayavka_end_attachments', 
            'assignment_end_attachments', 'screen_sber_attachments', 'contract_attachments',
            'contract_appendix_attachments', 'invoice_primary_attachments', 'vbk_attachments',
            'additional_agreement_attachments', 'assignment_input_attachments', 'act_report_attachments'
        ]
        # Note: contragent_contract_attachments исключено, так как это computed поле
        
        one2many_fields = [
            'zayavka_output_attachments'
        ]
        
        related_zayavkas = self.env['amanat.zayavka'].browse()
        
        # РАСШИРЕННАЯ ЛОГИКА ПОИСКА: Ищем ВСЕ attachment'ы с похожими именами
        print(f"DEBUG: Original attachment name: '{attachment.name}'")
        
        # 1. Поиск по точному имени
        exact_name_attachments = self.env['ir.attachment'].search([
            ('name', '=', attachment.name),
        ])
        print(f"DEBUG: Found {len(exact_name_attachments)} attachments with exact name '{attachment.name}': {exact_name_attachments.ids}")
        
        # 2. Поиск по имени без расширения (на случай, если добавляются суффиксы)
        base_name = attachment.name
        if '.' in base_name:
            name_without_ext = base_name.rsplit('.', 1)[0]
            extension = '.' + base_name.rsplit('.', 1)[1]
            similar_attachments = self.env['ir.attachment'].search([
                ('name', 'ilike', f'{name_without_ext}%{extension}'),
            ])
            print(f"DEBUG: Found {len(similar_attachments)} attachments with similar name pattern '{name_without_ext}%{extension}': {similar_attachments.ids}")
        else:
            similar_attachments = exact_name_attachments
        
        # 3. Поиск по размеру файла (если есть)
        size_attachments = self.env['ir.attachment'].browse()
        if attachment.file_size and attachment.file_size > 0:
            size_attachments = self.env['ir.attachment'].search([
                ('file_size', '=', attachment.file_size),
                ('name', 'ilike', f'%{base_name.split(".")[0]}%'),
            ])
            print(f"DEBUG: Found {len(size_attachments)} attachments with same size {attachment.file_size}: {size_attachments.ids}")
        
        # 4. Поиск по CheckSum (если есть)
        checksum_attachments = self.env['ir.attachment'].browse()
        if hasattr(attachment, 'checksum') and attachment.checksum:
            checksum_attachments = self.env['ir.attachment'].search([
                ('checksum', '=', attachment.checksum),
            ])
            print(f"DEBUG: Found {len(checksum_attachments)} attachments with same checksum: {checksum_attachments.ids}")
        
        # Объединяем все найденные attachment'ы
        all_attachments = exact_name_attachments | similar_attachments | size_attachments | checksum_attachments
        all_attachment_ids = all_attachments.ids
        print(f"DEBUG: TOTAL found {len(all_attachments)} related attachments: {all_attachment_ids}")
        
        # Выводим детальную информацию о найденных attachment'ах
        for att in all_attachments:
            checksum_info = f", checksum={att.checksum[:8]}..." if hasattr(att, 'checksum') and att.checksum else ""
            print(f"DEBUG: Attachment ID={att.id}, name='{att.name}', res_model='{att.res_model}', res_id={att.res_id}, res_field='{att.res_field}', size={att.file_size}{checksum_info}")
        
        # 5. ПРОСТЕЙШАЯ ПРОВЕРКА: Найти ВСЕ заявки, которые содержат исходный attachment
        print(f"DEBUG: === ПРОСТЕЙШАЯ ПРОВЕРКА ===")
        simple_attachments = [attachment_id]  # Только исходный attachment
        print(f"DEBUG: Searching for original attachment ID {attachment_id} in all fields...")
        
        simple_zayavkas = self.env['amanat.zayavka'].browse()
        for field in many2many_fields:
            found = self.search([(field, 'in', simple_attachments)], limit=None)
            if found:
                print(f"DEBUG: Field {field} contains attachment {attachment_id} in {len(found)} zayavkas: {[z.id for z in found]}")
                simple_zayavkas |= found
        
        print(f"DEBUG: Simple check found {len(simple_zayavkas)} zayavkas with original attachment:")
        for z in simple_zayavkas:
            print(f"  - ID{z.id}: {z.zayavka_num or 'No number'}")
        print(f"DEBUG: === КОНЕЦ ПРОСТЕЙШЕЙ ПРОВЕРКИ ===")
        
        # 1. Поиск в Many2many полях
        print(f"DEBUG: Searching in Many2many fields: {many2many_fields}")
        many2many_total = 0
        for field in many2many_fields:
            domain = [(field, 'in', all_attachment_ids)]
            print(f"DEBUG: Searching with domain: {domain}")
            found_zayavkas = self.search(domain, limit=None, order='id')  # Явно убираем лимит в поиске
            print(f"DEBUG: Raw search result count: {len(found_zayavkas)}")
            if found_zayavkas:
                print(f"DEBUG: Many2many field '{field}' found {len(found_zayavkas)} zayavkas:")
                for z in found_zayavkas:
                    print(f"  - ID{z.id}: {z.zayavka_num or 'No number'}")
                many2many_total += len(found_zayavkas)
            else:
                print(f"DEBUG: Many2many field '{field}' found NO zayavkas")
            related_zayavkas |= found_zayavkas
        print(f"DEBUG: Total found in Many2many fields: {many2many_total}")
        print(f"DEBUG: Related zayavkas so far: {len(related_zayavkas)}")
        
        # 2. Поиск в One2many полях (по res_id и res_field)
        print(f"DEBUG: Searching in One2many fields: {one2many_fields}")
        one2many_total = 0
        for same_attachment in all_attachments:
            if same_attachment.res_model == 'amanat.zayavka' and same_attachment.res_field in one2many_fields:
                found_zayavka = self.browse(same_attachment.res_id)
                if found_zayavka.exists():
                    print(f"DEBUG: One2many found zayavka: {found_zayavka.zayavka_num or f'ID{found_zayavka.id}'} (attachment ID: {same_attachment.id})")
                    related_zayavkas |= found_zayavka
                    one2many_total += 1
        print(f"DEBUG: Total found in One2many fields: {one2many_total}")
        print(f"DEBUG: Total before final check: many2many({many2many_total}) + one2many({one2many_total}) = {many2many_total + one2many_total}")
        print(f"DEBUG: Actual recordset length: {len(related_zayavkas)}")
        
        # СПЕЦИАЛЬНАЯ ЛОГИКА ДЛЯ CONTRAGENT_CONTRACT_ATTACHMENTS
        print(f"DEBUG: === SPECIAL SEARCH FOR CONTRACT DOCUMENTS ===")
        
        # Сначала находим все контрагенты, у которых есть такие документы в актуальных договорах
        contract_zayavkas = self.env['amanat.zayavka'].browse()
        
        # Ищем все договоры, которые содержат наши attachment'ы
        contracts_with_attachments = self.env['amanat.contragent.contract'].search([
            ('contract_attachments', 'in', all_attachment_ids),
            ('is_actual', '=', True)
        ])
        print(f"DEBUG: Found {len(contracts_with_attachments)} contracts with these attachments")
        
        if contracts_with_attachments:
            # Находим всех контрагентов этих договоров
            contragent_ids = contracts_with_attachments.mapped('contragent_id').ids
            print(f"DEBUG: Contract contragents: {contragent_ids}")
            
            # Ищем все заявки этих контрагентов
            contract_zayavkas = self.search([('contragent_id', 'in', contragent_ids)], limit=None)
            print(f"DEBUG: Found {len(contract_zayavkas)} zayavkas with same contragents:")
            for z in contract_zayavkas:
                print(f"  - ID{z.id}: {z.zayavka_num or 'No number'} (contragent: {z.contragent_id.name})")
        
        # ОСНОВНОЙ ГЛОБАЛЬНЫЙ ПОИСК
        print(f"DEBUG: === DOING GLOBAL SEARCH ===")
        print(f"DEBUG: Many2many fields: {many2many_fields}")
        
        global_zayavkas = self.env['amanat.zayavka'].browse()
        if many2many_fields:
            # Создаем правильный OR domain для всех полей
            if len(many2many_fields) > 1:
                global_domain = ['|'] * (len(many2many_fields) - 1)
                for field in many2many_fields:
                    global_domain += [(field, 'in', all_attachment_ids)]
            else:
                global_domain = [(many2many_fields[0], 'in', all_attachment_ids)]
            
            print(f"DEBUG: Global domain: {global_domain}")
            global_zayavkas = self.search(global_domain, limit=None, order='id')
            print(f"DEBUG: Global search found {len(global_zayavkas)} zayavkas:")
            for z in global_zayavkas:
                print(f"  - ID{z.id}: {z.zayavka_num or 'No number'}")
        
        # Объединяем все результаты: контракты + глобальный поиск + one2many
        final_zayavkas = global_zayavkas | related_zayavkas | contract_zayavkas
        related_zayavkas = final_zayavkas
        
        print(f"DEBUG: Final result - found {len(related_zayavkas)} related zayavkas")
        print(f"DEBUG: Related zayavka IDs: {related_zayavkas.ids}")
        print(f"DEBUG: Related zayavka numbers: {[z.zayavka_num or f'ID{z.id}' for z in related_zayavkas]}")
        
        # ДОПОЛНИТЕЛЬНАЯ ДИАГНОСТИКА - тестируем domain напрямую
        if related_zayavkas:
            test_domain = [('id', 'in', related_zayavkas.ids)]
            print(f"DEBUG: Testing domain directly: {test_domain}")
            
            # Тест 1: Поиск с лимитом по умолчанию
            test_result_default = self.search(test_domain)
            print(f"DEBUG: Domain search with DEFAULT limit found: {len(test_result_default)} records")
            
            # Тест 2: Поиск без лимита
            test_result_no_limit = self.search(test_domain, limit=None)
            print(f"DEBUG: Domain search with NO limit found: {len(test_result_no_limit)} records")
            
            # Тест 3: Поиск с высоким лимитом
            test_result_high_limit = self.search(test_domain, limit=10000)
            print(f"DEBUG: Domain search with HIGH limit found: {len(test_result_high_limit)} records")
            
            if len(test_result_default) != len(related_zayavkas):
                print(f"WARNING: Default search limit is cutting results! Expected {len(related_zayavkas)}, got {len(test_result_default)}")
        
        if not related_zayavkas:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Информация',
                    'message': f'Документ "{attachment.name}" не используется в других заявках',
                    'type': 'info',
                }
            }
        
        # Возвращаем действие для открытия списка заявок с найденными записями
        return {
            'name': f'Заявки с документом "{attachment.name}" ({len(related_zayavkas)})',
            'type': 'ir.actions.act_window',
            'res_model': 'amanat.zayavka',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],  # Указываем представления
            'domain': [('id', 'in', related_zayavkas.ids)],
            'context': {
                'default_search_domain': [('id', 'in', related_zayavkas.ids)],
                'search_default_attachment_filter': 1,
            },
            'target': 'current',
            'limit': 0,  # Убираем лимит для отображения всех найденных записей
        }

    def action_show_contract_attachment_usage(self):
        """Показать все заявки, использующие документы договоров данного контрагента"""
        print(f"=== action_show_contract_attachment_usage called for zayavka {self.zayavka_num or self.id} ===")
        if not self.contragent_contract_attachments:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Внимание!',
                    'message': 'У данного контрагента нет документов в актуальном договоре',
                    'type': 'warning',
                }
            }

        # Получаем ID всех документов контрагента
        attachment_ids = self.contragent_contract_attachments.ids
        attachment_names = self.contragent_contract_attachments.mapped('name')
        
        print(f"DEBUG: Searching for contract attachments with IDs: {attachment_ids}")
        print(f"DEBUG: Attachment names: {attachment_names}")
        
        # Разделяем поля на Many2many и One2many (ИСКЛЮЧАЕМ contragent_contract_attachments - это computed поле)
        many2many_fields = [
            'zayavka_attachments', 'invoice_attachments', 'assignment_attachments',
            'swift_attachments', 'swift103_attachments', 'swift199_attachments', 
            'report_attachments', 'other_documents_attachments', 'zayavka_end_attachments', 
            'assignment_end_attachments', 'screen_sber_attachments', 'contract_attachments',
            'contract_appendix_attachments', 'invoice_primary_attachments', 'vbk_attachments',
            'additional_agreement_attachments', 'assignment_input_attachments', 'act_report_attachments'
        ]
        
        one2many_fields = [
            'zayavka_output_attachments'
        ]
        
        related_zayavkas = self.env['amanat.zayavka'].browse()
        
        # 1. Поиск в Many2many полях
        print(f"DEBUG: Contract - Searching in Many2many fields: {many2many_fields}")
        for field in many2many_fields:
            domain = [(field, 'in', attachment_ids)]
            found_zayavkas = self.search(domain, limit=None)  # ИСПРАВЛЕНО: добавил limit=None
            if found_zayavkas:
                print(f"DEBUG: Contract Many2many field '{field}' found {len(found_zayavkas)} zayavkas: {[z.zayavka_num or f'ID{z.id}' for z in found_zayavkas]}")
            related_zayavkas |= found_zayavkas
        
        # 2. Поиск в One2many полях 
        print(f"DEBUG: Contract - Searching in One2many fields: {one2many_fields}")
        for attachment in self.contragent_contract_attachments:
            if attachment.res_model == 'amanat.zayavka' and attachment.res_field in one2many_fields:
                found_zayavka = self.env['amanat.zayavka'].browse(attachment.res_id)
                if found_zayavka.exists():
                    print(f"DEBUG: Contract One2many direct link found zayavka: {found_zayavka.zayavka_num or f'ID{found_zayavka.id}'}")
                    related_zayavkas |= found_zayavka
        
        # 3. Дополнительный поиск по именам файлов (дублированные документы)
        if attachment_names:
            same_name_attachments = self.env['ir.attachment'].search([
                ('name', 'in', attachment_names),
                ('id', 'not in', attachment_ids)  # исключаем оригинальные
            ])
            print(f"DEBUG: Contract - Found {len(same_name_attachments)} attachments with same names")
            
            if same_name_attachments:
                # Поиск в Many2many полях
                for field in many2many_fields:
                    domain = [(field, 'in', same_name_attachments.ids)]
                    found_zayavkas = self.search(domain, limit=None)  # ИСПРАВЛЕНО: добавил limit=None
                    if found_zayavkas:
                        print(f"DEBUG: Contract Many2many field '{field}' found by name {len(found_zayavkas)} zayavkas")
                    related_zayavkas |= found_zayavkas
                
                # Поиск в One2many полях
                for same_attachment in same_name_attachments:
                    if same_attachment.res_model == 'amanat.zayavka' and same_attachment.res_field in one2many_fields:
                        found_zayavka = self.env['amanat.zayavka'].browse(same_attachment.res_id)
                        if found_zayavka.exists():
                            print(f"DEBUG: Contract One2many by name found zayavka: {found_zayavka.zayavka_num or f'ID{found_zayavka.id}'}")
                            related_zayavkas |= found_zayavka
        
        # Включаем ВСЕ найденные заявки, в том числе текущую
        # related_zayavkas = related_zayavkas.filtered(lambda z: z.id != self.id)  # Убрали фильтрацию
        print(f"DEBUG: Contract method - found {len(related_zayavkas)} related zayavkas (including current)")
        print(f"DEBUG: Contract Related zayavka IDs: {related_zayavkas.ids}")
        print(f"DEBUG: Contract Related zayavka numbers: {[z.zayavka_num or f'ID{z.id}' for z in related_zayavkas]}")
        
        if not related_zayavkas:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Информация',
                    'message': f'Документы контрагента "{self.contragent_id.name or ""}" ({len(attachment_ids)} документов) не используются в других заявках',
                    'type': 'info',
                }
            }
        
        # Возвращаем действие для открытия списка заявок с найденными записями
        return {
            'name': f'Заявки с документами контрагента "{self.contragent_id.name or ""}" ({len(related_zayavkas)})',
            'type': 'ir.actions.act_window',
            'res_model': 'amanat.zayavka',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],  # Указываем представления
            'domain': [('id', 'in', related_zayavkas.ids)],
            'context': {
                'default_search_domain': [('id', 'in', related_zayavkas.ids)],
                'search_default_contragent_docs_filter': 1,
            },
            'target': 'current',
            'limit': 0,  # Убираем лимит для отображения всех найденных записей
        }
    
    # date_agent_pc = fields.Date(string='Дата агентского на РС')
    
    # Поле для выбора формата генерируемого документа
    document_format = fields.Selection([
        ('pdf', 'PDF'),
        ('docx', 'Word')
    ], string='Формат документа', default='pdf', help='Выберите формат для генерации документа "Индивидуал"')
    
    # Поле для выбора типа шаблона Индивидуал
    fixed_reward = fields.Boolean(
        string='Фиксированное вознаграждение',
        default=True,
        help='Если отмечено - генерируется текущий шаблон "Индивидуал", если не отмечено - генерируется старый формат "Индивидуал старый"'
    )
    
    # Вычисляемое поле для проверки разрешения генерации
    can_generate_individual = fields.Boolean(
        string='Может генерировать Индивидуал',
        compute='_compute_can_generate_individual',
        help='Показывает, может ли текущий агент генерировать документ "Индивидуал"'
    )