# -*- coding: utf-8 -*-
# models/calculators/calculator_50_usd.py
from odoo import models, fields, api
from datetime import date


class Calculator50UsdWizard(models.Model):
    """Калькулятор сделок: EUR/CNY (кросс), USD (обычный), CNY (обычный), EUR (обычный)"""
    _name = 'amanat.calculator.50.usd.wizard'
    _description = 'Расчет добавка в $ / калькулятор сделок'
    _order = 'create_date desc'

    # Информационные поля
    name = fields.Char(string='Название расчета', compute='_compute_name', store=True)
    create_uid = fields.Many2one('res.users', string='Создал', readonly=True)
    create_date = fields.Datetime(string='Дата создания', readonly=True)

    # Основные поля
    date = fields.Date(string='Дата', default=fields.Date.context_today, required=True)

    deal_variant = fields.Selection([
        ('eur_cross', 'EUR (кросс)'),
        ('cny_cross', 'CNY (кросс)'),
        ('usd_addon', 'USD (обычный)'),
        ('cny_addon', 'CNY (обычный)'),
        ('eur_addon', 'EUR (обычный)'),
    ], string='Тип расчета', default='usd_addon', required=True)

    # ---- Общие настройки/параметры ----
    auto_markup_percent = fields.Float(
        string='% надбавки (авто)',
        help='Процент надбавки для расчета клиентского кросс-курса (используется в вариантах EUR/CNY кросс). '
             'Например, 2 означает +2% к курсу.',
        default=0.0,
    )

    # ==========================
    # EUR (кросс к USD) блок
    # ==========================
    eur_invoice_amount = fields.Float(string='Сумма инвойса в EUR')
    usd_rate_cbr = fields.Float(string='Курс $ ЦБ (USD/RUB)', digits=(16, 6),
                                help='Используется для конвертации USD в RUB.')
    eur_xe_rate = fields.Float(string='Курс XE EUR (EUR/USD)', digits=(16, 6),
                               help='Кросс EUR→USD по XE.')

    eur_cross_client = fields.Float(string='Кросскурс EUR→USD (для клиента)', digits=(16, 6),
                                    compute='_compute_all', store=False, readonly=True)
    eur_amount_rub = fields.Float(string='Сумма к оплате в RUB', digits=(16, 2),
                                  compute='_compute_all', store=False, readonly=True)
    eur_commission_percent = fields.Float(string='% Агентского вознаграждения')
    eur_commission_amount = fields.Float(string='Сумма агентского вознаграждения', digits=(16, 2),
                                         compute='_compute_all', store=False, readonly=True)
    eur_total_rub = fields.Float(string='Общая сумма к оплате (RUB)', digits=(16, 2),
                                 compute='_compute_all', store=False, readonly=True)
    eur_to_rub_rate = fields.Float(string='Эффективный курс EUR→RUB', digits=(16, 6),
                                   compute='_compute_all', store=False, readonly=True,
                                   help='Сумма к оплате в рублях / Сумма инвойса в евро (без учета агентского).')

    # ==========================
    # CNY (кросс к USD) блок
    # ==========================
    cny_invoice_amount = fields.Float(string='Сумма инвойса в CNY')
    usd_rate_investing_cny_cross = fields.Float(string='Курс $ (USD/RUB)', digits=(16, 6))
    cny_cross = fields.Float(string='Кросс курс юаня (USD/CNY)', digits=(16, 6),
                             help='Кросс CNY→USD. Для клиента увеличивается на % надбавки (авто).')

    cny_cross_client = fields.Float(string='Кросскурс USD→CNY (для клиента)', digits=(16, 6),
                                    compute='_compute_all', store=False, readonly=True)
    cny_amount_rub = fields.Float(string='Сумма к оплате в RUB', digits=(16, 2),
                                  compute='_compute_all', store=False, readonly=True)
    cny_commission_percent = fields.Float(string='% Агентского вознаграждения')
    cny_commission_amount = fields.Float(string='Сумма агентского вознаграждения', digits=(16, 2),
                                         compute='_compute_all', store=False, readonly=True)
    cny_total_rub = fields.Float(string='Общая сумма к оплате (RUB)', digits=(16, 2),
                                 compute='_compute_all', store=False, readonly=True)
    cny_to_rub_rate = fields.Float(string='Эффективный курс CNY→RUB', digits=(16, 6),
                                   compute='_compute_all', store=False, readonly=True,
                                   help='Сумма к оплате в рублях / Сумма инвойса в юанях (без учета агентского).')

    # ==========================
    # USD (обычный) блок — с добавкой $
    # ==========================
    usd_invoice_amount = fields.Float(string='Сумма инвойса в USD')
    usd_investing_rate = fields.Float(string='Курс $ (USD/RUB)', digits=(16, 6))
    usd_commission_percent = fields.Float(string='% Агентского вознаграждения')

    usd_final_rate_for_payment = fields.Float(string='Итоговый курс для суммы платежа (RUB/USD)', digits=(16, 6),
                                              compute='_compute_all', store=False, readonly=True,
                                              help='Курс $ с учетом процента агентского.')
    usd_payment_amount_rub = fields.Float(string='Сумма платежа (RUB)', digits=(16, 2),
                                          compute='_compute_all', store=False, readonly=True)

    usd_addon_usd = fields.Float(string='Добавка $')
    usd_addon_amount_rub = fields.Float(string='Добавка сумма (RUB)', digits=(16, 2),
                                        compute='_compute_all', store=False, readonly=True)
    usd_total_rub = fields.Float(string='Итого в рублях (RUB)', digits=(16, 2),
                                 compute='_compute_all', store=False, readonly=True)
    usd_final_rate_incl_addon = fields.Float(string='Курс (включая добавку $) (RUB/USD)', digits=(16, 6),
                                             compute='_compute_all', store=False, readonly=True,
                                             help='Итого в рублях / Сумма инвойса в долларах.')

    # ==========================
    # CNY (обычный) блок — с добавкой $
    # ==========================
    cny2_invoice_amount = fields.Float(string='Сумма инвойса в CNY')
    cny2_rate = fields.Float(string='Курс юаня (CNY/RUB)', digits=(16, 6),
                             help='Прямой курс конверсии CNY→RUB.')
    cny2_usd_rate = fields.Float(string='Курс $ (USD/RUB)', digits=(16, 6),
                                 help='Используется для конвертации добавки $ в рубли.')
    cny2_commission_percent = fields.Float(string='% Агентского вознаграждения')

    cny2_final_rate_for_payment = fields.Float(string='Итоговый курс для суммы платежа (RUB/CNY)', digits=(16, 6),
                                               compute='_compute_all', store=False, readonly=True,
                                               help='Курс юаня с учетом процента агентского.')
    cny2_payment_amount_rub = fields.Float(string='Сумма платежа (RUB)', digits=(16, 2),
                                           compute='_compute_all', store=False, readonly=True)
    cny2_addon_usd = fields.Float(string='Добавка $')
    cny2_addon_amount_rub = fields.Float(string='Добавка сумма (RUB)', digits=(16, 2),
                                         compute='_compute_all', store=False, readonly=True)
    cny2_total_rub = fields.Float(string='Итого в рублях (RUB)', digits=(16, 2),
                                  compute='_compute_all', store=False, readonly=True)
    cny2_final_rate_incl_addon = fields.Float(string='Курс (включая добавку $) (RUB/CNY)', digits=(16, 6),
                                              compute='_compute_all', store=False, readonly=True,
                                              help='Итого в рублях / Сумма инвойса в CNY.')

    # ==========================
    # EUR (обычный) блок — с добавкой $
    # ==========================
    eur2_invoice_amount = fields.Float(string='Сумма инвойса в EUR')
    eur2_rate = fields.Float(string='Курс евро (EUR/RUB)', digits=(16, 6),
                             help='Прямой курс конверсии EUR→RUB.')
    eur2_usd_rate = fields.Float(string='Курс $ (USD/RUB)', digits=(16, 6),
                                 help='Курс для пересчета добавки $ в RUB.')
    eur2_commission_percent = fields.Float(string='% Агентского вознаграждения')

    eur2_final_rate_for_payment = fields.Float(string='Итоговый курс для суммы платежа (RUB/EUR)', digits=(16, 6),
                                               compute='_compute_all', store=False, readonly=True,
                                               help='Курс EUR с учетом процента агентского.')
    eur2_payment_amount_rub = fields.Float(string='Сумма платежа (RUB)', digits=(16, 2),
                                           compute='_compute_all', store=False, readonly=True)
    eur2_addon_usd = fields.Float(string='Добавка $')
    eur2_addon_amount_rub = fields.Float(string='Добавка сумма (RUB)', digits=(16, 2),
                                         compute='_compute_all', store=False, readonly=True)
    eur2_total_rub = fields.Float(string='Итого в рублях (RUB)', digits=(16, 2),
                                  compute='_compute_all', store=False, readonly=True)
    eur2_final_rate_incl_addon = fields.Float(string='Курс (включая добавку $) (RUB/EUR)', digits=(16, 6),
                                              compute='_compute_all', store=False, readonly=True,
                                              help='Итого в рублях / Сумма инвойса в EUR.')

    # ========= COMPUTE =========

    @api.depends(
        # EUR cross
        'auto_markup_percent', 'eur_invoice_amount', 'usd_rate_cbr', 'eur_xe_rate', 'eur_commission_percent',
        # CNY cross
        'cny_invoice_amount', 'usd_rate_investing_cny_cross', 'cny_cross', 'cny_commission_percent',
        # USD addon
        'usd_invoice_amount', 'usd_investing_rate', 'usd_commission_percent', 'usd_addon_usd',
        # CNY addon
        'cny2_invoice_amount', 'cny2_rate', 'cny2_usd_rate', 'cny2_commission_percent', 'cny2_addon_usd',
        # EUR addon
        'eur2_invoice_amount', 'eur2_rate', 'eur2_usd_rate', 'eur2_commission_percent', 'eur2_addon_usd',
        # Variant/date also влияет на name
        'deal_variant', 'date',
    )
    def _compute_all(self):
        for rec in self:
            # -------- общие вспомогательные ----------
            markup = (rec.auto_markup_percent or 0.0) / 100.0

            # ===== EUR (кросс) =====
            eur_xe = rec.eur_xe_rate or 0.0  # USD/EUR
            rec.eur_cross_client = eur_xe * (1.0 + markup) if eur_xe else 0.0

            eur_inv = rec.eur_invoice_amount or 0.0
            usd_cbr = rec.usd_rate_cbr or 0.0  # RUB/USD
            eur_amount_rub = eur_inv * rec.eur_cross_client * usd_cbr
            rec.eur_amount_rub = eur_amount_rub

            eur_comm_pct = (rec.eur_commission_percent or 0.0) / 100.0
            rec.eur_commission_amount = eur_amount_rub * eur_comm_pct
            rec.eur_total_rub = eur_amount_rub + rec.eur_commission_amount
            rec.eur_to_rub_rate = (eur_amount_rub / eur_inv) if eur_inv else 0.0

            # ===== CNY (кросс) =====
            cny_cross = rec.cny_cross or 0.0  # CNY/USD
            rec.cny_cross_client = cny_cross * (1.0 + markup) if cny_cross else 0.0

            cny_inv = rec.cny_invoice_amount or 0.0
            usd_inv_rate = rec.usd_rate_investing_cny_cross or 0.0  # RUB/USD
            if rec.cny_cross_client:
                usd_amount_from_cny = cny_inv / rec.cny_cross_client  # (CNY / (CNY/USD)) => USD
            else:
                usd_amount_from_cny = 0.0
            cny_amount_rub = usd_amount_from_cny * usd_inv_rate
            rec.cny_amount_rub = cny_amount_rub

            cny_comm_pct = (rec.cny_commission_percent or 0.0) / 100.0
            rec.cny_commission_amount = cny_amount_rub * cny_comm_pct
            rec.cny_total_rub = cny_amount_rub + rec.cny_commission_amount
            rec.cny_to_rub_rate = (cny_amount_rub / cny_inv) if cny_inv else 0.0

            # ===== USD (обычный) =====
            usd_inv = rec.usd_invoice_amount or 0.0
            usd_rate_investing = rec.usd_investing_rate or 0.0  # RUB/USD
            usd_comm_pct = (rec.usd_commission_percent or 0.0) / 100.0

            rec.usd_final_rate_for_payment = usd_rate_investing * (1.0 + usd_comm_pct) if usd_rate_investing else 0.0
            usd_payment_rub = usd_inv * rec.usd_final_rate_for_payment
            rec.usd_payment_amount_rub = usd_payment_rub

            usd_addon = rec.usd_addon_usd or 0.0
            rec.usd_addon_amount_rub = usd_addon * usd_rate_investing
            rec.usd_total_rub = usd_payment_rub + rec.usd_addon_amount_rub
            rec.usd_final_rate_incl_addon = (rec.usd_total_rub / usd_inv) if usd_inv else 0.0

            # ===== CNY (обычный) =====
            cny2_inv = rec.cny2_invoice_amount or 0.0
            cny2_rate = rec.cny2_rate or 0.0  # RUB/CNY
            cny2_comm_pct = (rec.cny2_commission_percent or 0.0) / 100.0

            rec.cny2_final_rate_for_payment = cny2_rate * (1.0 + cny2_comm_pct) if cny2_rate else 0.0
            cny2_payment_rub = cny2_inv * rec.cny2_final_rate_for_payment
            rec.cny2_payment_amount_rub = cny2_payment_rub

            cny2_addon_usd = rec.cny2_addon_usd or 0.0
            cny2_usd_rate = rec.cny2_usd_rate or 0.0  # RUB/USD
            rec.cny2_addon_amount_rub = cny2_addon_usd * cny2_usd_rate
            rec.cny2_total_rub = cny2_payment_rub + rec.cny2_addon_amount_rub
            rec.cny2_final_rate_incl_addon = (rec.cny2_total_rub / cny2_inv) if cny2_inv else 0.0

            # ===== EUR (обычный) =====
            eur2_inv = rec.eur2_invoice_amount or 0.0
            eur2_rate = rec.eur2_rate or 0.0  # RUB/EUR
            eur2_comm_pct = (rec.eur2_commission_percent or 0.0) / 100.0

            rec.eur2_final_rate_for_payment = eur2_rate * (1.0 + eur2_comm_pct) if eur2_rate else 0.0
            eur2_payment_rub = eur2_inv * rec.eur2_final_rate_for_payment
            rec.eur2_payment_amount_rub = eur2_payment_rub

            eur2_addon_usd = rec.eur2_addon_usd or 0.0
            eur2_usd_rate = rec.eur2_usd_rate or 0.0  # RUB/USD
            rec.eur2_addon_amount_rub = eur2_addon_usd * eur2_usd_rate
            rec.eur2_total_rub = eur2_payment_rub + rec.eur2_addon_amount_rub
            rec.eur2_final_rate_incl_addon = (rec.eur2_total_rub / eur2_inv) if eur2_inv else 0.0

    @api.depends('deal_variant', 'date')
    def _compute_name(self):
        label_map = {
            'eur_cross': 'EUR (кросс)',
            'cny_cross': 'CNY (кросс)',
            'usd_addon': 'USD (обычный)',
            'cny_addon': 'CNY (обычный)',
            'eur_addon': 'EUR (обычный)',
        }
        for rec in self:
            variant = label_map.get(rec.deal_variant or 'usd_addon')
            dt = rec.date or fields.Date.context_today(rec)
            rec.name = f'{variant} — {dt}'
