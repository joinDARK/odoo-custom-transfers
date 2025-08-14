# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AmanatCalculatorWizard(models.TransientModel):
    _name = "amanat.calculator.usd.addition.for.all.wizard"
    _description = "Расчет добавка в $ для всех"
    _order = "create_date desc"

    # === Управляющие поля ===
    calc_mode = fields.Selection([
        ("percent", "В %"),
        ("rate", "В КУРС"),
    ], string="Режим расчёта", required=True)

    currency_code = fields.Selection([
        ("USD", "USD"),
        ("CNY", "CNY"),
        ("EUR", "EUR"),
    ], string="Валюта", default="USD", required=True)

    date = fields.Date(string="Дата", default=fields.Date.today, required=True)

    # Информационные поля
    name = fields.Char(string="Название расчета", compute="_compute_name", store=True)
    create_uid = fields.Many2one("res.users", string="Создал")
    create_date = fields.Datetime(string="Дата создания")

    # === Общие вводимые поля ===
    amount = fields.Float(string="Сумма", digits=(16, 2))
    reward_percent = fields.Float(string="Вознаграждение в %", help="Процент вознаграждения менеджера")

    # --- Режим В % ---
    rate = fields.Float(string="Курс", digits=(16, 6), help="Курс к рублю (RUB)")
    xe = fields.Float(string="XE", digits=(16, 10), help="Кросс-курс к USD (до 10 знаков после запятой)")
    usd_equivalent = fields.Float(string="Эквивалент $", digits=(16, 6), compute="_compute_percent_mode", store=True)

    addition = fields.Float(string="Надбавка", digits=(16, 2))
    addition_percent = fields.Float(string="Надбавка в %", digits=(16, 4), compute="_compute_percent_mode", store=True)
    total_percent = fields.Float(string="Процент итог", digits=(16, 4), compute="_compute_percent_mode", store=True)

    # --- Режим В КУРС ---
    real_rate = fields.Float(string="Курс реал", digits=(16, 6))
    usd_rate = fields.Float(string="Курс $", digits=(16, 6), help="Текущий курс USD→RUB (нужен для CNY/EUR в режиме 'В КУРС')")
    addition_usd = fields.Float(string="Надбавка $", digits=(16, 4))
    surcharge_sum_rub = fields.Float(string="Сумма надбавки, RUB", digits=(16, 2), compute="_compute_rate_mode", store=True)
    total_rate = fields.Float(string="Курс итого", digits=(16, 6), compute="_compute_rate_mode", store=True)

    # --- Вычисляемые общие результаты (для обоих режимов) ---
    request_amount_rub = fields.Float(string="Сумма заявки в руб", digits=(16, 2), compute="_compute_results", store=True)
    reward_rub = fields.Float(string="Вознаграждение руб", digits=(16, 2), compute="_compute_results", store=True)
    total_rub = fields.Float(string="Итого", digits=(16, 2), compute="_compute_results", store=True)

    # ===== Компьюты =====
    @api.depends("date", "calc_mode", "currency_code")
    def _compute_name(self):
        for rec in self:
            mode = "В %" if rec.calc_mode == "percent" else "В КУРС"
            rec.name = f"Расчет добавка в $ для всех — {mode} — {rec.currency_code or ''}"

    @api.depends("calc_mode", "currency_code", "amount", "xe", "addition", "reward_percent")
    def _compute_percent_mode(self):
        for rec in self:
            usd_equivalent = 0.0
            addition_percent = 0.0
            total_percent = 0.0

            if rec.calc_mode == "percent":
                # Эквивалент $ нужен лишь для CNY/EUR; для USD оставим 0
                if rec.currency_code in ("CNY", "EUR"):
                    usd_equivalent = (rec.amount or 0.0) * (rec.xe or 0.0)
                # База для надбавки в %
                base = rec.amount if rec.currency_code == "USD" else usd_equivalent
                if base:
                    addition_percent = (rec.addition or 0.0) / base * 100.0
                total_percent = (rec.reward_percent or 0.0) + addition_percent

            rec.usd_equivalent = usd_equivalent
            rec.addition_percent = addition_percent
            rec.total_percent = total_percent

    @api.depends("calc_mode", "currency_code", "real_rate", "usd_rate", "addition_usd", "amount")
    def _compute_rate_mode(self):
        for rec in self:
            surcharge_sum_rub = 0.0
            total_rate = 0.0
            if rec.calc_mode == "rate":
                if rec.currency_code == "USD":
                    surcharge_sum_rub = (rec.real_rate or 0.0) * (rec.addition_usd or 0.0)
                else:
                    # Для CNY/EUR используем курс USD → RUB
                    surcharge_sum_rub = (rec.usd_rate or 0.0) * (rec.addition_usd or 0.0)
                # Итоговый курс: реал + надбавка в рублях на единицу товара
                if rec.amount:
                    total_rate = (rec.real_rate or 0.0) + (surcharge_sum_rub / rec.amount)
                else:
                    total_rate = rec.real_rate or 0.0
            rec.surcharge_sum_rub = surcharge_sum_rub
            rec.total_rate = total_rate

    @api.depends(
        "calc_mode", "amount", "rate", "total_rate", "total_percent", "reward_percent"
    )
    def _compute_results(self):
        for rec in self:
            request_amount_rub = 0.0
            reward_rub = 0.0
            total_rub = 0.0

            if rec.calc_mode == "percent":
                request_amount_rub = (rec.amount or 0.0) * (rec.rate or 0.0)
                reward_rub = request_amount_rub * ((rec.total_percent or 0.0) / 100.0)
            else:
                request_amount_rub = (rec.amount or 0.0) * (rec.total_rate or 0.0)
                reward_rub = request_amount_rub * ((rec.reward_percent or 0.0) / 100.0)

            total_rub = request_amount_rub + reward_rub

            rec.request_amount_rub = request_amount_rub
            rec.reward_rub = reward_rub
            rec.total_rub = total_rub