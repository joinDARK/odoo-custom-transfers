from odoo import api, fields, models

class ZayavkaComputes(models.Model):
    _inherit = 'amanat.zayavka'

    @api.depends('real_cross_rate')
    def _compute_cross_rate(self):
        for record in self:
            record.cross_rate = record.real_cross_rate

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
                'Курс КРОСС': rec.cross_rate or None if rec.is_cross else None,
                'Курс Биржи 1': rec.exchange_rate_1 or None,
                'Курс Биржи 2': rec.exchange_rate_2 or None,
                'Курс Биржи 3': rec.exchange_rate_3 or None,
            }
            # Если не выбрана галочка is_cross, исключаем кросс-курс
            if not rec.is_cross and 'Курс КРОСС' in valid_courses:
                valid_courses['Курс КРОСС'] = None
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
                # Если не выбрана галочка is_cross, кросс-курс не участвует
                if record.deal_type == "export":
                    rates = [
                        record.investing_rate or 9999999,
                        record.cb_rate or 9999999,
                        (record.cross_rate if record.is_cross else None) or 9999999,
                        record.exchange_rate_1 or 9999999,
                        record.exchange_rate_2 or 9999999,
                        record.exchange_rate_3 or 9999999,
                    ]
                    # Исключаем кросс-курс если is_cross не выбран
                    if not record.is_cross:
                        rates[2] = 9999999
                    record.best_rate = min(rates)
                else:
                    rates = [
                        record.investing_rate or -9999999,
                        record.cb_rate or -9999999,
                        (record.cross_rate if record.is_cross else None) or -9999999,
                        record.exchange_rate_1 or -9999999,
                        record.exchange_rate_2 or -9999999,
                        record.exchange_rate_3 or -9999999,
                    ]
                    if not record.is_cross:
                        rates[2] = -9999999
                    record.best_rate = max(rates)

    @api.depends('reward_percent', 'rate_field', 'amount')
    def _compute_client_reward(self):
        for rec in self:
            rec.client_reward = rec.reward_percent * rec.rate_field * rec.amount

    @api.depends('best_rate', 'hidden_commission', 'amount', 'plus_currency')
    def _compute_our_client_reward(self):
        for rec in self:
            rec.our_client_reward = rec.best_rate * rec.hidden_commission * (rec.amount + rec.plus_currency)

    @api.depends('total_client', 'rate_real', 'our_client_reward')
    def _compute_non_our_client_reward(self):
        for rec in self:
            rec.non_our_client_reward = rec.total_client - (rec.rate_real + rec.our_client_reward)

    @api.depends('application_amount_rub_contract', 'client_reward')
    def _compute_total_client(self):
        for rec in self:
            rec.total_client = rec.application_amount_rub_contract + rec.client_reward

    @api.depends('rate_real', 'our_client_reward', 'non_our_client_reward')
    def _compute_total_client_management(self):
        for rec in self:
            rec.total_client_management = rec.rate_real + rec.our_client_reward + rec.non_our_client_reward

    @api.depends('amount', 'price_list_carrying_out_accrual_percentage')
    def _compute_client_payment_cost(self):
        for rec in self:
            rec.client_payment_cost = (rec.amount or 0) * (rec.price_list_carrying_out_accrual_percentage or 0)

    @api.depends('application_amount_rub_contract', 'client_reward', 'percent_from_payment_order_rule')
    def _compute_payment_order_rf_client(self):
        for rec in self:
            contract_rub = rec.application_amount_rub_contract or 0.0
            client_reward = rec.client_reward or 0.0
            percent = rec.percent_from_payment_order_rule or 0.0

            rec.payment_order_rf_client = (contract_rub + client_reward) * percent

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

    @api.depends('client_real_operating_expenses', 'payer_cross_rate_usd_auto')
    def _compute_client_real_operating_expenses_usd(self):
        for rec in self:
            value = (rec.client_real_operating_expenses or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)
            rec.client_real_operating_expenses_usd = value

    @api.depends('client_real_operating_expenses_usd', 'payer_cross_rate_rub')
    def _compute_client_real_operating_expenses_rub(self):
        for rec in self:
            rec.client_real_operating_expenses_rub = (rec.client_real_operating_expenses_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

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

    @api.depends('client_currency_bought_real', 'payer_cross_rate_usd_auto')
    def _compute_client_currency_bought_real_usd(self):
        for rec in self:
            rec.client_currency_bought_real_usd = (rec.client_currency_bought_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('client_currency_bought_real_usd', 'payer_cross_rate_rub')
    def _compute_client_currency_bought_real_rub(self):
        for rec in self:
            rec.client_currency_bought_real_rub = (rec.client_currency_bought_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    @api.depends('payment_cost_sovok', 'payer_cross_rate_usd_auto', 'price_list_carrying_out_fixed_deal_fee')
    def _compute_client_payment_cost_usd(self):
        for rec in self:
            sovok_cost = rec.payment_cost_sovok or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            fixed_fee = rec.price_list_carrying_out_fixed_deal_fee or 0.0

            rec.client_payment_cost_usd = sovok_cost * cross_rate + fixed_fee

    @api.depends('client_payment_cost_usd', 'payer_cross_rate_rub')
    def _compute_client_payment_cost_rub(self):
        for rec in self:
            rec.client_payment_cost_rub = (rec.client_payment_cost_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    @api.depends('date_days', 'client_currency_bought')
    def _compute_cost_of_money_client(self):
        for rec in self:
            # Формула: ({Дата}+1)/25*0.04*{Купили валюту Клиент}
            if rec.date_days and rec.client_currency_bought:
                days = rec.date_days + 1
                rec.cost_of_money_client = (days / 25) * 0.04 * rec.client_currency_bought
            else:
                rec.cost_of_money_client = 0.0

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

    @api.depends('cost_of_money_client_real', 'payer_cross_rate_usd_auto')
    def _compute_cost_of_money_client_real_usd(self):
        for rec in self:
            rec.cost_of_money_client_real_usd = (rec.cost_of_money_client_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('cost_of_money_client_real_usd', 'payer_cross_rate_rub')
    def _compute_cost_of_money_client_real_rub(self):
        for rec in self:
            rec.cost_of_money_client_real_rub = (rec.cost_of_money_client_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

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

    @api.depends('fin_res_client_real', 'payer_cross_rate_usd_auto')
    def _compute_fin_res_client_real_usd(self):
        for rec in self:
            rec.fin_res_client_real_usd = (rec.fin_res_client_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('fin_res_client_real_usd', 'payer_cross_rate_rub')
    def _compute_fin_res_client_real_rub(self):
        for rec in self:
            rec.fin_res_client_real_rub = (rec.fin_res_client_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    @api.depends('reward_percent', 'rate_field', 'amount')
    def _compute_sber_reward(self):
        for rec in self:
            rec.sber_reward = rec.reward_percent * rec.rate_field * rec.amount

    @api.depends('rate_field', 'best_rate', 'amount', 'plus_currency', 'sber_reward')
    def _compute_our_sber_reward(self):
        for rec in self:
            rec.our_sber_reward = (rec.rate_field - rec.best_rate) * (rec.amount + rec.plus_currency) + rec.sber_reward

    @api.depends('total_sber', 'our_sber_reward', 'rate_real')
    def _compute_non_our_sber_reward(self):
        for rec in self:
            rec.non_our_sber_reward = rec.total_sber - (rec.our_sber_reward + rec.rate_real)

    @api.depends('application_amount_rub_contract', 'sber_reward')
    def _compute_total_sber(self):
        for rec in self:
            rec.total_sber = rec.application_amount_rub_contract + rec.sber_reward

    @api.depends('rate_real', 'our_sber_reward', 'non_our_sber_reward')
    def _compute_total_sber_management(self):
        for rec in self:
            rec.total_sber_management = rec.rate_real + (rec.our_sber_reward + rec.non_our_sber_reward)

    @api.depends('hand_reward_percent')
    def _compute_overall_sber_percent(self):
        for rec in self:
            rec.overall_sber_percent = rec.hand_reward_percent

    @api.depends('total_amount', 'agent_our_reward')
    def _compute_rate_real_sber(self):
        for rec in self:
            rec.rate_real_sber = rec.total_amount - rec.agent_our_reward

    @api.depends('amount', 'price_list_carrying_out_accrual_percentage')
    def _compute_sber_payment_cost(self):
        for rec in self:
            rec.sber_payment_cost = (rec.amount or 0) * (rec.price_list_carrying_out_accrual_percentage or 0)

    @api.depends('application_amount_rub_contract', 'sber_reward', 'percent_from_payment_order_rule')
    def _compute_payment_order_rf_sber(self):
        for rec in self:
            contract_rub = rec.application_amount_rub_contract or 0.0
            sber_reward = rec.sber_reward or 0.0
            percent = rec.percent_from_payment_order_rule or 0.0

            rec.payment_order_rf_sber = (contract_rub + sber_reward) * percent

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

    @api.depends('sber_operating_expenses_real', 'payer_cross_rate_usd_auto')
    def _compute_sber_operating_expenses_real_usd(self):
        for rec in self:
            rec.sber_operating_expenses_real_usd = (rec.sber_operating_expenses_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('sber_operating_expenses_real_usd', 'payer_cross_rate_rub')
    def _compute_sber_operating_expenses_real_rub(self):
        for rec in self:
            rec.sber_operating_expenses_real_rub = (rec.sber_operating_expenses_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    @api.depends('total_sber', 'payment_order_rf_sber', 'partner_post_conversion_rate')
    def _compute_kupili_valyutu_sber(self):
        for rec in self:
            if rec.partner_post_conversion_rate:
                rec.kupili_valyutu_sber = (rec.total_sber - rec.payment_order_rf_sber) / rec.partner_post_conversion_rate
            else:
                rec.kupili_valyutu_sber = 0.0

    @api.depends('total_sber', 'payment_order_rf_sber', 'real_post_conversion_rate')
    def _compute_kupili_valyutu_sber_real(self):
        for rec in self:
            if rec.real_post_conversion_rate:
                rec.kupili_valyutu_sber_real = (rec.total_sber - rec.payment_order_rf_sber) / rec.real_post_conversion_rate
            else:
                rec.kupili_valyutu_sber_real = 0.0

    @api.depends('kupili_valyutu_sber_real', 'payer_cross_rate_usd_auto')
    def _compute_kupili_valyutu_sber_real_usd(self):
        for rec in self:
            rec.kupili_valyutu_sber_real_usd = rec.kupili_valyutu_sber_real * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('kupili_valyutu_sber_real_usd', 'payer_cross_rate_rub')
    def _compute_kupili_valyutu_sber_real_rub(self):
        for rec in self:
            rec.kupili_valyutu_sber_real_rub = rec.kupili_valyutu_sber_real_usd * (rec.payer_cross_rate_rub or 0.0)

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

    @api.depends('payment_cost_sovok', 'payer_cross_rate_usd_auto', 'price_list_carrying_out_fixed_deal_fee')
    def _compute_sber_payment_cost_on_usd(self):
        for rec in self:
            sovok_cost = rec.payment_cost_sovok or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            fixed_fee = rec.price_list_carrying_out_fixed_deal_fee or 0.0
            rec.sber_payment_cost_on_usd = sovok_cost * cross_rate + fixed_fee

    @api.depends('payment_cost_sovok', 'payer_cross_rate_usd_auto', 'price_list_carrying_out_fixed_deal_fee')
    def _compute_sber_payment_cost_on_usd_real(self):
        for rec in self:
            sovok_cost = rec.payment_cost_sovok or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            fixed_fee = rec.price_list_carrying_out_fixed_deal_fee or 0.0
            rec.sber_payment_cost_on_usd_real = sovok_cost * cross_rate + fixed_fee

    @api.depends('date_days', 'kupili_valyutu_sber')
    def _compute_sebestoimost_denej_sber(self):
        for rec in self:
            if rec.date_days and rec.kupili_valyutu_sber:
                days = rec.date_days + 1
                rec.sebestoimost_denej_sber = (days / 25) * 0.04 * rec.kupili_valyutu_sber
            else:
                rec.sebestoimost_denej_sber = 0.0

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

    @api.depends('sebestoimost_denej_sber_real', 'payer_cross_rate_usd_auto')
    def _compute_sebestoimost_denej_sber_real_usd(self):
        for rec in self:
            rec.sebestoimost_denej_sber_real_usd = (rec.sebestoimost_denej_sber_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('sebestoimost_denej_sber_real_usd', 'payer_cross_rate_rub')
    def _compute_sebestoimost_denej_sber_real_rub(self):
        for rec in self:
            rec.sebestoimost_denej_sber_real_rub = (rec.sebestoimost_denej_sber_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

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

    @api.depends('fin_res_sber_real', 'payer_cross_rate_usd_auto')
    def _compute_fin_res_sber_real_usd(self):
        for rec in self:
            rec.fin_res_sber_real_usd = (rec.fin_res_sber_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('fin_res_sber_real_usd', 'payer_cross_rate_rub')
    def _compute_fin_res_sber_real_rub(self):
        for rec in self:
            rec.fin_res_sber_real_rub = (rec.fin_res_sber_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    @api.depends('rate_field', 'best_rate', 'amount')
    def _compute_our_sovok_reward(self):
        for rec in self:
            rec.our_sovok_reward = (rec.rate_field - rec.best_rate) * rec.amount

    @api.depends()
    def _compute_sovok_reward(self): # Здесь все нормально
        for rec in self:
            rec.sovok_reward = 0.0

    @api.depends('application_amount_rub_contract')
    def _compute_total_sovok(self):
        for rec in self:
            rec.total_sovok = rec.application_amount_rub_contract

    @api.depends('rate_real', 'our_sovok_reward')
    def _compute_total_sovok_management(self):
        for rec in self:
            rec.total_sovok_management = rec.rate_real + rec.our_sovok_reward

    @api.depends('rate_field', 'best_rate')
    def _compute_overall_sovok_percent(self):
        for rec in self:
            if rec.best_rate:  # Проверка на ноль
                rec.overall_sovok_percent = (rec.rate_field - rec.best_rate) / rec.best_rate
            else:
                rec.overall_sovok_percent = 0.0

    @api.depends('amount', 'price_list_carrying_out_accrual_percentage')
    def _compute_payment_cost_sovok(self):
        for record in self:
            amount = record.amount or 0.0
            percent = record.price_list_carrying_out_accrual_percentage or 0.0
            record.payment_cost_sovok = amount * percent

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

    @api.depends('operating_expenses_sovok_real', 'payer_cross_rate_usd_auto')
    def _compute_operating_expenses_sovok_real_usd(self):
        for rec in self:
            rec.operating_expenses_sovok_real_usd = (rec.operating_expenses_sovok_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('operating_expenses_sovok_real_usd', 'payer_cross_rate_rub')
    def _compute_operating_expenses_sovok_real_rub(self):
        for rec in self:
            rec.operating_expenses_sovok_real_rub = (rec.operating_expenses_sovok_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

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

    @api.depends('kupili_valyutu_sovok_real', 'payer_cross_rate_usd_auto')
    def _compute_kupili_valyutu_sovok_real_usd(self):
        for rec in self:
            kupili_valyutu = rec.kupili_valyutu_sovok_real or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            rec.kupili_valyutu_sovok_real_usd = kupili_valyutu * cross_rate

    @api.depends('kupili_valyutu_sovok_real_usd', 'payer_cross_rate_rub')
    def _compute_kupili_valyutu_sovok_real_rub(self):
        for rec in self:
            rec.kupili_valyutu_sovok_real_rub = (rec.kupili_valyutu_sovok_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    @api.depends('payment_cost_sovok', 'payer_cross_rate_usd_auto', 'price_list_carrying_out_fixed_deal_fee')
    def _compute_payment_cost_sovok_partner_usd(self):
        for rec in self:
            payment_cost = rec.payment_cost_sovok or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            fixed_fee = rec.price_list_carrying_out_fixed_deal_fee or 0.0
            rec.payment_cost_sovok_partner_usd = (payment_cost * cross_rate) + fixed_fee

    @api.depends('payment_cost_sovok', 'payer_cross_rate_usd_auto', 'price_list_carrying_out_fixed_deal_fee')
    def _compute_payment_cost_sovok_real_usd(self):
        for rec in self:
            payment_cost = rec.payment_cost_sovok or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            fixed_fee = rec.price_list_carrying_out_fixed_deal_fee or 0.0
            rec.payment_cost_sovok_real_usd = payment_cost * cross_rate + fixed_fee

    @api.depends('payment_cost_sovok_real_usd', 'payer_cross_rate_rub')
    def _compute_payment_cost_sovok_real_rub(self):
        for rec in self:
            usd_cost = rec.payment_cost_sovok_real_usd or 0.0
            rub_rate = rec.payer_cross_rate_rub or 0.0
            rec.payment_cost_sovok_real_rub = usd_cost * rub_rate

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

    @api.depends('sebestoimost_denej_sovok_real', 'payer_cross_rate_usd_auto')
    def _compute_sebestoimost_denej_sovok_real_usd(self):
        for rec in self:
            sebestoimost = rec.sebestoimost_denej_sovok_real or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            rec.sebestoimost_denej_sovok_real_usd = sebestoimost * cross_rate

    @api.depends('sebestoimost_denej_sovok_real_usd', 'payer_cross_rate_rub')
    def _compute_sebestoimost_denej_sovok_real_rub(self):
        for rec in self:
            usd_cost = rec.sebestoimost_denej_sovok_real_usd or 0.0
            rub_rate = rec.payer_cross_rate_rub or 0.0
            rec.sebestoimost_denej_sovok_real_rub = usd_cost * rub_rate

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

    @api.depends('cross_rate_pair', 'xe_rate')
    def _compute_conversion_ratio(self):
        for rec in self:
            if rec.cross_rate_pair and rec.xe_rate:
                rec.conversion_ratio = (rec.cross_rate_pair / rec.xe_rate) - 1
            else:
                rec.conversion_ratio = 0.0

    @api.depends('conversion_ratio', 'currency_pair')
    def _compute_course_profitable(self):
        # Список валютных пар, которые считаются "особенными"
        special_pairs = ['usd_cny', 'usd_aed', 'usd_thb', 'usd_euro']
        for rec in self:
            conv_ratio = rec.conversion_ratio or 0.0  # {% Конвертации соотношение}
            pair = (rec.currency_pair or '').lower()  # {Валютная пара}

            if conv_ratio == 0:
                rec.course_profitable = ''  # Аналог BLANK()
                continue

            if (
                (pair in special_pairs and conv_ratio < 0) or
                (pair not in special_pairs and conv_ratio > 0)
            ):
                rec.course_profitable = "XE"
            else:
                rec.course_profitable = "Курс Банка"

    @api.depends('conversion_percent', 'conversion_ratio')
    def _compute_conversion_auto(self):
        for rec in self:
            if rec.conversion_percent:
                rec.conversion_auto = rec.conversion_percent
            else:
                rec.conversion_auto = rec.conversion_ratio

    @api.depends('xe_rate', 'amount')
    def _compute_equivalent_amount_usd(self):
        for rec in self:
            xe = rec.xe_rate or 0.0   # {Курс XE}
            amount = rec.amount or 0.0  # {Сумма заявки}
            if xe:
                rec.equivalent_amount_usd = xe * amount
            else:
                rec.equivalent_amount_usd = amount

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

    @api.depends('extract_delivery_ids.amount')
    def _compute_sum_from_extracts(self):
        for rec in self:
            rec.sum_from_extracts = sum(rec.extract_delivery_ids.mapped('amount'))

    @api.depends('subagent_ids', 'subagent_ids.payer_ids')
    def _compute_subagent_payer_ids(self):
        for rec in self:
            # Собираем всех плательщиков для выбранных субагентов
            payers = rec.subagent_ids.mapped('payer_ids')
            rec.subagent_payer_ids = [(6, 0, payers.ids)]

    @api.depends('extract_delivery_ids.bank_document')
    def _compute_bank_vypiska(self):
        for rec in self:
            # Собираем все уникальные значения bank_document из связанных выписок
            bank_names = list(filter(None, rec.extract_delivery_ids.mapped('bank_document')))
            # Убираем дубли и сортируем
            bank_names = sorted(set(bank_names))
            rec.bank_vypiska = ', '.join(bank_names)

    @api.depends('amount', 'price_list_profit_id.percent_accrual')
    def _compute_payer_profit_currency(self):
        for rec in self:
            percent = rec.price_list_profit_id.percent_accrual or 0.0
            rec.payer_profit_currency = rec.amount * percent

    @api.depends('total_amount', 'received_on_our_pc', 'agent_on_pc')
    def _compute_calculation(self):
        for rec in self:
            rec.calculation = (rec.total_amount or 0.0) - (rec.received_on_our_pc or 0.0) - (rec.agent_on_pc or 0.0)

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

    @api.depends('extract_delivery_ids.amount')
    def _compute_sum_from_extracts(self):
        for rec in self:
            # extract_delivery_ids — это Many2many на amanat.extract_delivery
            rec.sum_from_extracts = sum(rec.extract_delivery_ids.mapped('amount'))  # amount — это поле "Сумма" в выписке

    @api.depends('overall_sovok_percent', 'calculated_percent')
    def _compute_error_sovok(self):
        for rec in self:
            # Проверяем, чтобы знаменатель не был нулём
            if rec.calculated_percent:
                rec.error_sovok = (rec.overall_sovok_percent - rec.calculated_percent) / rec.calculated_percent
            else:
                rec.error_sovok = 0.0  # Или False, если нужен BLANK

    @api.depends('overall_sber_percent', 'conversion_auto')
    def _compute_error_sber(self):
        for rec in self:
            if rec.conversion_auto:
                rec.error_sber = (rec.overall_sber_percent - rec.conversion_auto) / rec.conversion_auto
            else:
                rec.error_sber = 0.0  # Или False, если хотите пустое

    @api.depends('currency', 'best_rate')
    def _compute_partner_post_conversion_rate(self):
        for rec in self:
            if rec.currency == 'usd':  # у вас значение в Selection 'usd'
                rec.partner_post_conversion_rate = (rec.best_rate or 0.0) * 1.005
            else:
                rec.partner_post_conversion_rate = (rec.best_rate or 0.0) * 1.005 * 1.005

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

    @api.depends('jess_rate', 'payer_cross_rate_usd_auto')
    def _compute_real_post_conversion_rate(self):
        for rec in self:
            rec.real_post_conversion_rate = (rec.jess_rate or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('real_post_conversion_rate', 'payer_cross_rate_usd_auto')
    def _compute_real_post_conversion_rate_usd(self):
        for rec in self:
            rec.real_post_conversion_rate_usd = (rec.real_post_conversion_rate or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('real_post_conversion_rate_usd', 'payer_cross_rate_rub')
    def _compute_real_post_conversion_rate_rub(self):
        for rec in self:
            rec.real_post_conversion_rate_rub = (rec.real_post_conversion_rate_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

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

    @api.depends('payer_profit_usd', 'payer_cross_rate_rub')
    def _compute_payer_profit_rub(self):
        for rec in self:
            rec.payer_profit_rub = (rec.payer_profit_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

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
            rec.date_received_on_pc_auto = ', '.join(date_strs) if date_strs else Fals

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

    @api.depends('date_days', 'kupili_valyutu_sovok_partner')
    def _compute_sebestoimost_denej_sovok_partner(self):
        for rec in self:
            date_days = rec.date_days or 0
            kupili_valyutu = rec.kupili_valyutu_sovok_partner or 0.0
            rec.sebestoimost_denej_sovok_partner = ((date_days + 1) / 25) * 0.04 * kupili_valyutu

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

    @api.depends('hidden_partner_commission_real', 'payer_cross_rate_usd_auto')
    def _compute_hidden_partner_commission_real_usd(self):
        for rec in self:
            value = (rec.hidden_partner_commission_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)
            rec.hidden_partner_commission_real_usd = value

    @api.depends('hidden_partner_commission_real_usd', 'payer_cross_rate_rub')
    def _compute_hidden_partner_commission_real_rub(self):
        for rec in self:
            value = (rec.hidden_partner_commission_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)
            rec.hidden_partner_commission_real_rub = value

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

    @api.depends('xe_rate', 'amount')
    def _compute_usd_equivalent(self):
        for rec in self:
            rate = rec.xe_rate if rec.xe_rate else 1.0
            rec.usd_equivalent = rate * rec.amount

    @api.depends('jess_rate', 'payer_cross_rate_usd_auto', 'best_rate', 'amount')
    def _compute_conversion_expenses(self):
        for rec in self:
            payer_cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            rec.conversion_expenses_rub = ((rec.jess_rate or 0.0) * payer_cross_rate - (rec.best_rate or 0.0)) * (rec.amount or 0.0)

    @api.depends('conversion_expenses_rub', 'jess_rate', 'payer_cross_rate_usd_auto')
    def _compute_conversion_expenses_currency(self):
        for rec in self:
            denominator = (rec.jess_rate or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)
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

    @api.depends('course_profitable', 'currency_pair', 'xe_rate', 'cross_rate_pair', 'cross_rate_usd_rub', 'conversion_percent')
    def _compute_real_cross_rate(self):
        reverse_pairs = {'cny_usd', 'euro_usd', 'aed_usd', 'thb_usd'}
        for rec in self:
            conv_percent = rec.conversion_percent or 0.0
            usd_rub = rec.cross_rate_usd_rub or 0.0
            xe = rec.xe_rate or 0.0
            pair_rate = rec.cross_rate_pair or 0.0
            is_reverse = (rec.currency_pair or '').lower() in reverse_pairs

            result = 0.0
            if rec.course_profitable.lower() == 'xe':
                if is_reverse:
                    if xe:
                        result = (usd_rub / xe) * (1 + conv_percent)
                    else:
                        result = 0.0
                else:
                    result = (usd_rub * xe) * (1 + conv_percent)
            else:
                if pair_rate:
                    if is_reverse:
                        if pair_rate:
                            result = (usd_rub / pair_rate) * (1 + conv_percent)
                        else:
                            result = 0.0
                    else:
                        result = (usd_rub * pair_rate) * (1 + conv_percent)
                else:
                    if is_reverse:
                        if xe:
                            result = (usd_rub / xe) * (1 + conv_percent)
                        else:
                            result = 0.0
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
    @api.depends('total_client', 'rate_real', 'our_client_reward')
    def _compute_non_our_client_reward(self):
        for rec in self:
            rec.non_our_client_reward = rec.total_client - (rec.rate_real + rec.our_client_reward)

    @api.depends('application_amount_rub_contract', 'client_reward')
    def _compute_total_client(self):
        for rec in self:
            rec.total_client = rec.application_amount_rub_contract + rec.client_reward

    @api.depends('rate_real', 'our_client_reward', 'non_our_client_reward')
    def _compute_total_client_management(self):
        for rec in self:
            rec.total_client_management = rec.rate_real + rec.our_client_reward + rec.non_our_client_reward

    @api.depends('amount', 'price_list_carrying_out_accrual_percentage')
    def _compute_client_payment_cost(self):
        for rec in self:
            rec.client_payment_cost = (rec.amount or 0) * (rec.price_list_carrying_out_accrual_percentage or 0)

    @api.depends('application_amount_rub_contract', 'client_reward', 'percent_from_payment_order_rule')
    def _compute_payment_order_rf_client(self):
        for rec in self:
            contract_rub = rec.application_amount_rub_contract or 0.0
            client_reward = rec.client_reward or 0.0
            percent = rec.percent_from_payment_order_rule or 0.0

            rec.payment_order_rf_client = (contract_rub + client_reward) * percent

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

    @api.depends('client_real_operating_expenses', 'payer_cross_rate_usd_auto')
    def _compute_client_real_operating_expenses_usd(self):
        for rec in self:
            value = (rec.client_real_operating_expenses or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)
            rec.client_real_operating_expenses_usd = value

    @api.depends('client_real_operating_expenses_usd', 'payer_cross_rate_rub')
    def _compute_client_real_operating_expenses_rub(self):
        for rec in self:
            rec.client_real_operating_expenses_rub = (rec.client_real_operating_expenses_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

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

    @api.depends('client_currency_bought_real', 'payer_cross_rate_usd_auto')
    def _compute_client_currency_bought_real_usd(self):
        for rec in self:
            rec.client_currency_bought_real_usd = (rec.client_currency_bought_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('client_currency_bought_real_usd', 'payer_cross_rate_rub')
    def _compute_client_currency_bought_real_rub(self):
        for rec in self:
            rec.client_currency_bought_real_rub = (rec.client_currency_bought_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    @api.depends('payment_cost_sovok', 'payer_cross_rate_usd_auto', 'price_list_carrying_out_fixed_deal_fee')
    def _compute_client_payment_cost_usd(self):
        for rec in self:
            sovok_cost = rec.payment_cost_sovok or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            fixed_fee = rec.price_list_carrying_out_fixed_deal_fee or 0.0

            rec.client_payment_cost_usd = sovok_cost * cross_rate + fixed_fee

    @api.depends('client_payment_cost_usd', 'payer_cross_rate_rub')
    def _compute_client_payment_cost_rub(self):
        for rec in self:
            rec.client_payment_cost_rub = (rec.client_payment_cost_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    @api.depends('date_days', 'client_currency_bought')
    def _compute_cost_of_money_client(self):
        for rec in self:
            # Формула: ({Дата}+1)/25*0.04*{Купили валюту Клиент}
            if rec.date_days and rec.client_currency_bought:
                days = rec.date_days + 1
                rec.cost_of_money_client = (days / 25) * 0.04 * rec.client_currency_bought
            else:
                rec.cost_of_money_client = 0.0

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

    @api.depends('cost_of_money_client_real', 'payer_cross_rate_usd_auto')
    def _compute_cost_of_money_client_real_usd(self):
        for rec in self:
            rec.cost_of_money_client_real_usd = (rec.cost_of_money_client_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('cost_of_money_client_real_usd', 'payer_cross_rate_rub')
    def _compute_cost_of_money_client_real_rub(self):
        for rec in self:
            rec.cost_of_money_client_real_rub = (rec.cost_of_money_client_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

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

    @api.depends('fin_res_client_real', 'payer_cross_rate_usd_auto')
    def _compute_fin_res_client_real_usd(self):
        for rec in self:
            rec.fin_res_client_real_usd = (rec.fin_res_client_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('fin_res_client_real_usd', 'payer_cross_rate_rub')
    def _compute_fin_res_client_real_rub(self):
        for rec in self:
            rec.fin_res_client_real_rub = (rec.fin_res_client_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    @api.depends('reward_percent', 'rate_field', 'amount')
    def _compute_sber_reward(self):
        for rec in self:
            rec.sber_reward = rec.reward_percent * rec.rate_field * rec.amount

    @api.depends('rate_field', 'best_rate', 'amount', 'plus_currency', 'sber_reward')
    def _compute_our_sber_reward(self):
        for rec in self:
            rec.our_sber_reward = (rec.rate_field - rec.best_rate) * (rec.amount + rec.plus_currency) + rec.sber_reward

    @api.depends('total_sber', 'our_sber_reward', 'rate_real')
    def _compute_non_our_sber_reward(self):
        for rec in self:
            rec.non_our_sber_reward = rec.total_sber - (rec.our_sber_reward + rec.rate_real)

    @api.depends('application_amount_rub_contract', 'sber_reward')
    def _compute_total_sber(self):
        for rec in self:
            rec.total_sber = rec.application_amount_rub_contract + rec.sber_reward

    @api.depends('rate_real', 'our_sber_reward', 'non_our_sber_reward')
    def _compute_total_sber_management(self):
        for rec in self:
            rec.total_sber_management = rec.rate_real + (rec.our_sber_reward + rec.non_our_sber_reward)

    @api.depends('hand_reward_percent')
    def _compute_overall_sber_percent(self):
        for rec in self:
            rec.overall_sber_percent = rec.hand_reward_percent

    @api.depends('total_amount', 'agent_our_reward')
    def _compute_rate_real_sber(self):
        for rec in self:
            rec.rate_real_sber = rec.total_amount - rec.agent_our_reward

    @api.depends('amount', 'price_list_carrying_out_accrual_percentage')
    def _compute_sber_payment_cost(self):
        for rec in self:
            rec.sber_payment_cost = (rec.amount or 0) * (rec.price_list_carrying_out_accrual_percentage or 0)

    @api.depends('application_amount_rub_contract', 'sber_reward', 'percent_from_payment_order_rule')
    def _compute_payment_order_rf_sber(self):
        for rec in self:
            contract_rub = rec.application_amount_rub_contract or 0.0
            sber_reward = rec.sber_reward or 0.0
            percent = rec.percent_from_payment_order_rule or 0.0

            rec.payment_order_rf_sber = (contract_rub + sber_reward) * percent

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

    @api.depends('sber_operating_expenses_real', 'payer_cross_rate_usd_auto')
    def _compute_sber_operating_expenses_real_usd(self):
        for rec in self:
            rec.sber_operating_expenses_real_usd = (rec.sber_operating_expenses_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('sber_operating_expenses_real_usd', 'payer_cross_rate_rub')
    def _compute_sber_operating_expenses_real_rub(self):
        for rec in self:
            rec.sber_operating_expenses_real_rub = (rec.sber_operating_expenses_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    @api.depends('total_sber', 'payment_order_rf_sber', 'partner_post_conversion_rate')
    def _compute_kupili_valyutu_sber(self):
        for rec in self:
            if rec.partner_post_conversion_rate:
                rec.kupili_valyutu_sber = (rec.total_sber - rec.payment_order_rf_sber) / rec.partner_post_conversion_rate
            else:
                rec.kupili_valyutu_sber = 0.0

    @api.depends('total_sber', 'payment_order_rf_sber', 'real_post_conversion_rate')
    def _compute_kupili_valyutu_sber_real(self):
        for rec in self:
            if rec.real_post_conversion_rate:
                rec.kupili_valyutu_sber_real = (rec.total_sber - rec.payment_order_rf_sber) / rec.real_post_conversion_rate
            else:
                rec.kupili_valyutu_sber_real = 0.0

    @api.depends('kupili_valyutu_sber_real', 'payer_cross_rate_usd_auto')
    def _compute_kupili_valyutu_sber_real_usd(self):
        for rec in self:
            rec.kupili_valyutu_sber_real_usd = rec.kupili_valyutu_sber_real * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('kupili_valyutu_sber_real_usd', 'payer_cross_rate_rub')
    def _compute_kupili_valyutu_sber_real_rub(self):
        for rec in self:
            rec.kupili_valyutu_sber_real_rub = rec.kupili_valyutu_sber_real_usd * (rec.payer_cross_rate_rub or 0.0)

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

    @api.depends('payment_cost_sovok', 'payer_cross_rate_usd_auto', 'price_list_carrying_out_fixed_deal_fee')
    def _compute_sber_payment_cost_on_usd(self):
        for rec in self:
            sovok_cost = rec.payment_cost_sovok or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            fixed_fee = rec.price_list_carrying_out_fixed_deal_fee or 0.0
            rec.sber_payment_cost_on_usd = sovok_cost * cross_rate + fixed_fee

    @api.depends('payment_cost_sovok', 'payer_cross_rate_usd_auto', 'price_list_carrying_out_fixed_deal_fee')
    def _compute_sber_payment_cost_on_usd_real(self):
        for rec in self:
            sovok_cost = rec.payment_cost_sovok or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            fixed_fee = rec.price_list_carrying_out_fixed_deal_fee or 0.0
            rec.sber_payment_cost_on_usd_real = sovok_cost * cross_rate + fixed_fee

    @api.depends('date_days', 'kupili_valyutu_sber')
    def _compute_sebestoimost_denej_sber(self):
        for rec in self:
            if rec.date_days and rec.kupili_valyutu_sber:
                days = rec.date_days + 1
                rec.sebestoimost_denej_sber = (days / 25) * 0.04 * rec.kupili_valyutu_sber
            else:
                rec.sebestoimost_denej_sber = 0.0

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

    @api.depends('sebestoimost_denej_sber_real', 'payer_cross_rate_usd_auto')
    def _compute_sebestoimost_denej_sber_real_usd(self):
        for rec in self:
            rec.sebestoimost_denej_sber_real_usd = (rec.sebestoimost_denej_sber_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('sebestoimost_denej_sber_real_usd', 'payer_cross_rate_rub')
    def _compute_sebestoimost_denej_sber_real_rub(self):
        for rec in self:
            rec.sebestoimost_denej_sber_real_rub = (rec.sebestoimost_denej_sber_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

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

    @api.depends('fin_res_sber_real', 'payer_cross_rate_usd_auto')
    def _compute_fin_res_sber_real_usd(self):
        for rec in self:
            rec.fin_res_sber_real_usd = (rec.fin_res_sber_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('fin_res_sber_real_usd', 'payer_cross_rate_rub')
    def _compute_fin_res_sber_real_rub(self):
        for rec in self:
            rec.fin_res_sber_real_rub = (rec.fin_res_sber_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    @api.depends('rate_field', 'best_rate', 'amount')
    def _compute_our_sovok_reward(self):
        for rec in self:
            rec.our_sovok_reward = (rec.rate_field - rec.best_rate) * rec.amount

    @api.depends()
    def _compute_sovok_reward(self): # Здесь все нормально
        for rec in self:
            rec.sovok_reward = 0.0

    @api.depends('application_amount_rub_contract')
    def _compute_total_sovok(self):
        for rec in self:
            rec.total_sovok = rec.application_amount_rub_contract

    @api.depends('rate_real', 'our_sovok_reward')
    def _compute_total_sovok_management(self):
        for rec in self:
            rec.total_sovok_management = rec.rate_real + rec.our_sovok_reward

    @api.depends('rate_field', 'best_rate')
    def _compute_overall_sovok_percent(self):
        for rec in self:
            if rec.best_rate:  # Проверка на ноль
                rec.overall_sovok_percent = (rec.rate_field - rec.best_rate) / rec.best_rate
            else:
                rec.overall_sovok_percent = 0.0

    @api.depends('amount', 'price_list_carrying_out_accrual_percentage')
    def _compute_payment_cost_sovok(self):
        for record in self:
            amount = record.amount or 0.0
            percent = record.price_list_carrying_out_accrual_percentage or 0.0
            record.payment_cost_sovok = amount * percent

    @api.depends('application_amount_rub_contract', 'sovok_reward', 'percent_from_payment_order_rule')
    def _compute_payment_order_rf_sovok(self):
        for rec in self:
            contract_rub = rec.application_amount_rub_contract or 0.0
            sovok_reward = rec.sovok_reward or 0.0
            percent = rec.percent_from_payment_order_rule or 0.0
            rec.payment_order_rf_sovok = (contract_rub + sovok_reward) * percent

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

    @api.depends('operating_expenses_sovok_real', 'payer_cross_rate_usd_auto')
    def _compute_operating_expenses_sovok_real_usd(self):
        for rec in self:
            rec.operating_expenses_sovok_real_usd = (rec.operating_expenses_sovok_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('operating_expenses_sovok_real_usd', 'payer_cross_rate_rub')
    def _compute_operating_expenses_sovok_real_rub(self):
        for rec in self:
            rec.operating_expenses_sovok_real_rub = (rec.operating_expenses_sovok_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

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

    @api.depends('kupili_valyutu_sovok_real', 'payer_cross_rate_usd_auto')
    def _compute_kupili_valyutu_sovok_real_usd(self):
        for rec in self:
            kupili_valyutu = rec.kupili_valyutu_sovok_real or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            rec.kupili_valyutu_sovok_real_usd = kupili_valyutu * cross_rate

    @api.depends('kupili_valyutu_sovok_real_usd', 'payer_cross_rate_rub')
    def _compute_kupili_valyutu_sovok_real_rub(self):
        for rec in self:
            rec.kupili_valyutu_sovok_real_rub = (rec.kupili_valyutu_sovok_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

    @api.depends('payment_cost_sovok', 'payer_cross_rate_usd_auto', 'price_list_carrying_out_fixed_deal_fee')
    def _compute_payment_cost_sovok_partner_usd(self):
        for rec in self:
            payment_cost = rec.payment_cost_sovok or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            fixed_fee = rec.price_list_carrying_out_fixed_deal_fee or 0.0
            rec.payment_cost_sovok_partner_usd = (payment_cost * cross_rate) + fixed_fee

    @api.depends('payment_cost_sovok', 'payer_cross_rate_usd_auto', 'price_list_carrying_out_fixed_deal_fee')
    def _compute_payment_cost_sovok_real_usd(self):
        for rec in self:
            payment_cost = rec.payment_cost_sovok or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            fixed_fee = rec.price_list_carrying_out_fixed_deal_fee or 0.0
            rec.payment_cost_sovok_real_usd = payment_cost * cross_rate + fixed_fee

    @api.depends('payment_cost_sovok_real_usd', 'payer_cross_rate_rub')
    def _compute_payment_cost_sovok_real_rub(self):
        for rec in self:
            usd_cost = rec.payment_cost_sovok_real_usd or 0.0
            rub_rate = rec.payer_cross_rate_rub or 0.0
            rec.payment_cost_sovok_real_rub = usd_cost * rub_rate

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

    @api.depends('sebestoimost_denej_sovok_real', 'payer_cross_rate_usd_auto')
    def _compute_sebestoimost_denej_sovok_real_usd(self):
        for rec in self:
            sebestoimost = rec.sebestoimost_denej_sovok_real or 0.0
            cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            rec.sebestoimost_denej_sovok_real_usd = sebestoimost * cross_rate

    @api.depends('sebestoimost_denej_sovok_real_usd', 'payer_cross_rate_rub')
    def _compute_sebestoimost_denej_sovok_real_rub(self):
        for rec in self:
            usd_cost = rec.sebestoimost_denej_sovok_real_usd or 0.0
            rub_rate = rec.payer_cross_rate_rub or 0.0
            rec.sebestoimost_denej_sovok_real_rub = usd_cost * rub_rate

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

    @api.depends('cross_rate_pair', 'xe_rate')
    def _compute_conversion_ratio(self):
        for rec in self:
            if rec.cross_rate_pair and rec.xe_rate:
                rec.conversion_ratio = (rec.cross_rate_pair / rec.xe_rate) - 1
            else:
                rec.conversion_ratio = 0.0

    @api.depends('conversion_ratio', 'currency_pair')
    def _compute_course_profitable(self):
        # Список валютных пар, которые считаются "особенными"
        special_pairs = ['usd_cny', 'usd_aed', 'usd_thb', 'usd_euro']
        for rec in self:
            conv_ratio = rec.conversion_ratio or 0.0  # {% Конвертации соотношение}
            pair = (rec.currency_pair or '').lower()  # {Валютная пара}

            if conv_ratio == 0:
                rec.course_profitable = ''  # Аналог BLANK()
                continue

            if (
                (pair in special_pairs and conv_ratio < 0) or
                (pair not in special_pairs and conv_ratio > 0)
            ):
                rec.course_profitable = "XE"
            else:
                rec.course_profitable = "Курс Банка"

    @api.depends('conversion_percent', 'conversion_ratio')
    def _compute_conversion_auto(self):
        for rec in self:
            if rec.conversion_percent:
                rec.conversion_auto = rec.conversion_percent
            else:
                rec.conversion_auto = rec.conversion_ratio

    @api.depends('xe_rate', 'amount')
    def _compute_equivalent_amount_usd(self):
        for rec in self:
            xe = rec.xe_rate or 0.0   # {Курс XE}
            amount = rec.amount or 0.0  # {Сумма заявки}
            if xe:
                rec.equivalent_amount_usd = xe * amount
            else:
                rec.equivalent_amount_usd = amount

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

    @api.depends('extract_delivery_ids.amount')
    def _compute_sum_from_extracts(self):
        for rec in self:
            rec.sum_from_extracts = sum(rec.extract_delivery_ids.mapped('amount'))

    @api.depends('extract_delivery_ids.bank_document')
    def _compute_bank_vypiska(self):
        for rec in self:
            # Собираем все уникальные значения bank_document из связанных выписок
            bank_names = list(filter(None, rec.extract_delivery_ids.mapped('bank_document')))
            # Убираем дубли и сортируем
            bank_names = sorted(set(bank_names))
            rec.bank_vypiska = ', '.join(bank_names)

    @api.depends('amount', 'price_list_profit_id.percent_accrual')
    def _compute_payer_profit_currency(self):
        for rec in self:
            percent = rec.price_list_profit_id.percent_accrual or 0.0
            rec.payer_profit_currency = rec.amount * percent

    @api.depends('total_amount', 'received_on_our_pc', 'agent_on_pc')
    def _compute_calculation(self):
        for rec in self:
            rec.calculation = (rec.total_amount or 0.0) - (rec.received_on_our_pc or 0.0) - (rec.agent_on_pc or 0.0)

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

    @api.depends('extract_delivery_ids.amount')
    def _compute_sum_from_extracts(self):
        for rec in self:
            # extract_delivery_ids — это Many2many на amanat.extract_delivery
            rec.sum_from_extracts = sum(rec.extract_delivery_ids.mapped('amount'))  # amount — это поле "Сумма" в выписке

    @api.depends('overall_sovok_percent', 'calculated_percent')
    def _compute_error_sovok(self):
        for rec in self:
            # Проверяем, чтобы знаменатель не был нулём
            if rec.calculated_percent:
                rec.error_sovok = (rec.overall_sovok_percent - rec.calculated_percent) / rec.calculated_percent
            else:
                rec.error_sovok = 0.0  # Или False, если нужен BLANK

    @api.depends('overall_sber_percent', 'conversion_auto')
    def _compute_error_sber(self):
        for rec in self:
            if rec.conversion_auto:
                rec.error_sber = (rec.overall_sber_percent - rec.conversion_auto) / rec.conversion_auto
            else:
                rec.error_sber = 0.0  # Или False, если хотите пустое

    @api.depends('currency', 'best_rate')
    def _compute_partner_post_conversion_rate(self):
        for rec in self:
            if rec.currency == 'usd':  # у вас значение в Selection 'usd'
                rec.partner_post_conversion_rate = (rec.best_rate or 0.0) * 1.005
            else:
                rec.partner_post_conversion_rate = (rec.best_rate or 0.0) * 1.005 * 1.005

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

    @api.depends('jess_rate', 'payer_cross_rate_usd_auto')
    def _compute_real_post_conversion_rate(self):
        for rec in self:
            rec.real_post_conversion_rate = (rec.jess_rate or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('real_post_conversion_rate', 'payer_cross_rate_usd_auto')
    def _compute_real_post_conversion_rate_usd(self):
        for rec in self:
            rec.real_post_conversion_rate_usd = (rec.real_post_conversion_rate or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)

    @api.depends('jess_rate')
    def _compute_payer_cross_rate_rub(self):
        for rec in self:
            rec.payer_cross_rate_rub = rec.jess_rate or 0.0

    @api.depends('real_post_conversion_rate_usd', 'payer_cross_rate_rub')
    def _compute_real_post_conversion_rate_rub(self):
        for rec in self:
            rec.real_post_conversion_rate_rub = (rec.real_post_conversion_rate_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

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

    @api.depends('payer_profit_usd', 'payer_cross_rate_rub')
    def _compute_payer_profit_rub(self):
        for rec in self:
            rec.payer_profit_rub = (rec.payer_profit_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)

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

    @api.depends('date_days', 'kupili_valyutu_sovok_partner')
    def _compute_sebestoimost_denej_sovok_partner(self):
        for rec in self:
            date_days = rec.date_days or 0
            kupili_valyutu = rec.kupili_valyutu_sovok_partner or 0.0
            rec.sebestoimost_denej_sovok_partner = ((date_days + 1) / 25) * 0.04 * kupili_valyutu

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

    @api.depends(
        'contragent_id.name',
        'rate_real',
        'price_list_partners_id_accrual_percentage',
        'price_list_partners_id_2_accrual_percentage',
        'price_list_partners_id_3_accrual_percentage',
        'price_list_partners_id_4_accrual_percentage',
        'price_list_partners_id_5_accrual_percentage',
        'jess_rate',
        'amount',
        'non_our_client_reward'
    )
    def _compute_hidden_partner_commission_real(self):
        for rec in self:
            contragent = (rec.contragent_id.name or '').strip().lower()
            jess_rate = rec.jess_rate or 1  # На всякий случай, чтобы не делить на ноль

            accrual = (
                (rec.price_list_partners_id_accrual_percentage or 0.0) +
                (rec.price_list_partners_id_2_accrual_percentage or 0.0) +
                (rec.price_list_partners_id_3_accrual_percentage or 0.0) +
                (rec.price_list_partners_id_4_accrual_percentage or 0.0) +
                (rec.price_list_partners_id_5_accrual_percentage or 0.0)
            )

            if 'совкомбанк' in contragent:
                value = (rec.rate_real or 0.0) * accrual / jess_rate if jess_rate else 0.0
            elif 'сбербанк' in contragent:
                value = (rec.amount or 0.0) * accrual
            else:
                value = (rec.non_our_client_reward or 0.0) / jess_rate if jess_rate else 0.0

            rec.hidden_partner_commission_real = value

    @api.depends('hidden_partner_commission_real', 'payer_cross_rate_usd_auto')
    def _compute_hidden_partner_commission_real_usd(self):
        for rec in self:
            value = (rec.hidden_partner_commission_real or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)
            rec.hidden_partner_commission_real_usd = value

    @api.depends('hidden_partner_commission_real_usd', 'payer_cross_rate_rub')
    def _compute_hidden_partner_commission_real_rub(self):
        for rec in self:
            value = (rec.hidden_partner_commission_real_usd or 0.0) * (rec.payer_cross_rate_rub or 0.0)
            rec.hidden_partner_commission_real_rub = value

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

    @api.depends('xe_rate', 'amount')
    def _compute_usd_equivalent(self):
        for rec in self:
            rate = rec.xe_rate if rec.xe_rate else 1.0
            rec.usd_equivalent = rate * rec.amount

    @api.depends('jess_rate', 'payer_cross_rate_usd_auto', 'best_rate', 'amount')
    def _compute_conversion_expenses(self):
        for rec in self:
            payer_cross_rate = rec.payer_cross_rate_usd_auto or 0.0
            rec.conversion_expenses_rub = ((rec.jess_rate or 0.0) * payer_cross_rate - (rec.best_rate or 0.0)) * (rec.amount or 0.0)

    @api.depends('conversion_expenses_rub', 'jess_rate', 'payer_cross_rate_usd_auto')
    def _compute_conversion_expenses_currency(self):
        for rec in self:
            denominator = (rec.jess_rate or 0.0) * (rec.payer_cross_rate_usd_auto or 0.0)
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

    @api.depends('course_profitable', 'currency_pair', 'xe_rate', 'cross_rate_pair', 'cross_rate_usd_rub', 'conversion_percent')
    def _compute_real_cross_rate(self):
        reverse_pairs = {'cny_usd', 'euro_usd', 'aed_usd', 'thb_usd'}
        for rec in self:
            conv_percent = rec.conversion_percent or 0.0
            usd_rub = rec.cross_rate_usd_rub or 0.0
            xe = rec.xe_rate or 0.0
            pair_rate = rec.cross_rate_pair or 0.0
            is_reverse = (rec.currency_pair or '').lower() in reverse_pairs

            result = 0.0
            if rec.course_profitable.lower() == 'xe':
                if is_reverse:
                    if xe:
                        result = (usd_rub / xe) * (1 + conv_percent)
                    else:
                        result = 0.0
                else:
                    result = (usd_rub * xe) * (1 + conv_percent)
            else:
                if pair_rate:
                    if is_reverse:
                        if pair_rate:
                            result = (usd_rub / pair_rate) * (1 + conv_percent)
                        else:
                            result = 0.0
                    else:
                        result = (usd_rub * pair_rate) * (1 + conv_percent)
                else:
                    if is_reverse:
                        if xe:
                            result = (usd_rub / xe) * (1 + conv_percent)
                        else:
                            result = 0.0
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

    @api.depends('deal_closed_date', 'taken_in_work_date')
    def _compute_deal_cycle_days(self):
        for rec in self:
            if not rec.taken_in_work_date:
                rec.deal_cycle_days = 0
                continue
            
            # Определяем конечную дату: дата закрытия или сегодня
            end_date = rec.deal_closed_date if rec.deal_closed_date else fields.Date.today()
            
            # Вычисляем разность в днях
            delta = end_date - rec.taken_in_work_date
            rec.deal_cycle_days = delta.days